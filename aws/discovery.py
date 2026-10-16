from __future__ import annotations

from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, ProfileNotFound


class AWSDiscoveryError(RuntimeError):
    """Raised when AWS discovery cannot complete."""


class AWSDiscovery:
    """Read-only discovery layer for the AWS resources used by the project."""

    def __init__(self, region: str, profile: str | None = None):
        self.region = region
        self.profile = profile or None
        self.session = None

    def _client(self, service: str):
        if self.session is None:
            self.session = boto3.Session(region_name=self.region, profile_name=self.profile)
        return self.session.client(service, region_name=self.region, config=Config(connect_timeout=4, read_timeout=10, retries={'max_attempts': 1}))

    def status(self) -> dict[str, Any]:
        """Validate AWS credentials without exposing credential material."""
        try:
            identity = self._client("sts").get_caller_identity()
            arn = str(identity.get("Arn", ""))
            return {
                "connected": True,
                "region": self.region,
                "account_id": str(identity.get("Account", "")) or None,
                "principal_type": arn.split(":", 5)[2] if ":" in arn else None,
                "error": None,
            }
        except (BotoCoreError, ClientError, NoCredentialsError, ProfileNotFound) as exc:
            return {
                "connected": False,
                "region": self.region,
                "account_id": None,
                "principal_type": None,
                "error": self._safe_error(exc),
            }

    def discover_ec2(self) -> list[dict[str, Any]]:
        ec2 = self._client("ec2")
        paginator = ec2.get_paginator("describe_instances")
        resources: list[dict[str, Any]] = []
        for page in paginator.paginate():
            for reservation in page.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    tags = {tag["Key"]: tag.get("Value", "") for tag in instance.get("Tags", [])}
                    resources.append(
                        {
                            "id": instance.get("InstanceId"),
                            "name": tags.get("Name") or instance.get("InstanceId"),
                            "state": (instance.get("State") or {}).get("Name"),
                            "instance_type": instance.get("InstanceType"),
                            "availability_zone": (instance.get("Placement") or {}).get("AvailabilityZone"),
                            "tags": tags,
                            "source": "aws_ec2",
                        }
                    )
        return resources

    def discover_rds(self) -> list[dict[str, Any]]:
        rds = self._client("rds")
        paginator = rds.get_paginator("describe_db_instances")
        resources: list[dict[str, Any]] = []
        for page in paginator.paginate():
            for db in page.get("DBInstances", []):
                arn = db.get("DBInstanceArn")
                tags: dict[str, str] = {}
                if arn:
                    try:
                        tag_page = rds.list_tags_for_resource(ResourceName=arn)
                        tags = {tag["Key"]: tag.get("Value", "") for tag in tag_page.get("TagList", [])}
                    except (BotoCoreError, ClientError) as exc:
                        # Tag access is supplementary; resource discovery still succeeds.
                        tags = {"_tag_error": self._safe_error(exc)}
                resources.append(
                    {
                        "id": db.get("DBInstanceIdentifier"),
                        "name": tags.get("Name") or db.get("DBInstanceIdentifier"),
                        "status": db.get("DBInstanceStatus"),
                        "engine": db.get("Engine"),
                        "engine_version": db.get("EngineVersion"),
                        "instance_class": db.get("DBInstanceClass"),
                        "availability_zone": ((db.get("AvailabilityZone") or "") or None),
                        "arn": arn,
                        "tags": tags,
                        "source": "aws_rds",
                    }
                )
        return resources

    def discover(self) -> dict[str, Any]:
        try:
            ec2 = self.discover_ec2()
            rds = self.discover_rds()
            return {
                "region": self.region,
                "ec2": ec2,
                "rds": rds,
                "counts": {"ec2": len(ec2), "rds": len(rds)},
                "source": "aws_discovery",
                "error": None,
            }
        except (BotoCoreError, ClientError, NoCredentialsError, ProfileNotFound) as exc:
            raise AWSDiscoveryError(self._safe_error(exc)) from exc

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        # boto3/botocore errors do not normally include secret material, but keep the
        # UI response bounded and avoid returning request metadata.
        code = getattr(exc, 'response', {}).get('Error', {}).get('Code', type(exc).__name__)
        return f'{code}: AWS access failed. Check the selected profile, region, session expiry, and read permissions.' 
