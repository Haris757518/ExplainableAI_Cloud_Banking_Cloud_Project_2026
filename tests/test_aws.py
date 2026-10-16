from __future__ import annotations

from datetime import datetime, timezone

from aws.cloudwatch_adapter import CloudWatchAdapter
from aws.discovery import AWSDiscovery
from aws.normalizer import build_aws_sample


class FakeSTS:
    def get_caller_identity(self):
        return {"Account": "123456789012", "Arn": "arn:aws:iam::123456789012:role/AWSSandboxRole"}


class FakePaginator:
    def __init__(self, pages):
        self.pages = pages

    def paginate(self):
        yield from self.pages


class FakeEC2:
    def get_paginator(self, name):
        assert name == "describe_instances"
        return FakePaginator([{"Reservations": [{"Instances": [{"InstanceId": "i-test", "InstanceType": "t3.micro", "State": {"Name": "running"}, "Placement": {"AvailabilityZone": "ap-south-1a"}, "Tags": [{"Key": "Name", "Value": "bank-ec2"}, {"Key": "Service", "Value": "payment-service"}]}]}]}])


class FakeRDS:
    def get_paginator(self, name):
        assert name == "describe_db_instances"
        return FakePaginator([{"DBInstances": [{"DBInstanceIdentifier": "bank-db", "DBInstanceStatus": "available", "Engine": "postgres", "EngineVersion": "16", "DBInstanceClass": "db.t3.micro", "AvailabilityZone": "ap-south-1a", "DBInstanceArn": "arn:aws:rds:ap-south-1:123456789012:db:bank-db"}]}])

    def list_tags_for_resource(self, ResourceName):
        return {"TagList": [{"Key": "Service", "Value": "banking-db"}]}


class FakeCloudWatch:
    def get_metric_data(self, **kwargs):
        out = []
        for i, query in enumerate(kwargs["MetricDataQueries"]):
            out.append({"Id": query["Id"], "Timestamps": [datetime.now(timezone.utc)], "Values": [10.0 + i]})
        return {"MetricDataResults": out}


class FakeSession:
    def __init__(self, region_name=None, profile_name=None):
        self.region_name = region_name
        self.profile_name = profile_name

    def client(self, service, region_name=None, **kwargs):
        return {"sts": FakeSTS(), "ec2": FakeEC2(), "rds": FakeRDS(), "cloudwatch": FakeCloudWatch()}[service]


def test_aws_discovery(monkeypatch):
    monkeypatch.setattr("aws.discovery.boto3.Session", FakeSession)
    d = AWSDiscovery("ap-south-1")
    assert d.status()["connected"] is True
    result = d.discover()
    assert result["counts"] == {"ec2": 1, "rds": 1}
    assert result["ec2"][0]["id"] == "i-test"
    assert result["rds"][0]["id"] == "bank-db"


def test_cloudwatch_get_metric_data(monkeypatch):
    monkeypatch.setattr("aws.cloudwatch_adapter.boto3.Session", FakeSession)
    adapter = CloudWatchAdapter("ap-south-1")
    raw = adapter.collect(["i-test"], ["bank-db"])
    assert raw["source"] == "aws_cloudwatch"
    assert raw["observed_metric_count"] == 16
    assert raw["ec2"][0]["metrics"]["cpu_percent"] == 10.0
    assert raw["rds"][0]["metrics"]["read_latency_s"] == 17.0


def test_aws_graph_uses_real_resource_ids():
    discovery = {
        "ec2": [{"id": "i-test", "name": "bank-ec2", "tags": {"Service": "payment-service"}}],
        "rds": [{"id": "bank-db", "name": "bank-db", "tags": {"Service": "banking-db"}}],
    }
    raw = {
        "ec2": [{"node_id": "i-test", "period_seconds": 60, "metrics": {"cpu_percent": 55}, "observed_metrics": ["cpu_percent"]}],
        "rds": [{"node_id": "bank-db", "period_seconds": 60, "metrics": {"cpu_percent": 40, "read_latency_s": 0.02}, "observed_metrics": ["cpu_percent", "read_latency_s"]}],
    }
    sample = build_aws_sample(discovery, raw)
    ids = {n.id for n in sample.nodes}
    assert ids == {"i-test", "bank-db"}
    assert sample.edges == []
    assert all(t.source in {"aws_cloudwatch", "logical_service"} for t in sample.telemetry)
