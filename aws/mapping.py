from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_mapping(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {"services": {}, "databases": {}}
    p = Path(path)
    if not p.exists():
        return {"services": {}, "databases": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"services": {}, "databases": {}}
    except (OSError, json.JSONDecodeError):
        return {"services": {}, "databases": {}}


def _tag_match(tags: dict[str, Any], keys: tuple[str, ...], expected: str) -> bool:
    expected = expected.strip().lower()
    return any(str(tags.get(key, "")).strip().lower() == expected for key in keys)


def select_ec2(resources: list[dict[str, Any]], mapping: dict[str, Any], service_name: str = "payment-service") -> dict[str, Any] | None:
    services = mapping.get("services", {}) or {}
    configured = (services.get(service_name) or {}).get("ec2_instance_id")
    if configured:
        for item in resources:
            if item.get("id") == configured:
                return item
    for item in resources:
        tags = item.get("tags", {}) or {}
        if _tag_match(tags, ("Service", "Application", "BankingService", "Role"), service_name):
            return item
    return resources[0] if resources else None


def select_rds(resources: list[dict[str, Any]], mapping: dict[str, Any], database_name: str = "banking-db") -> dict[str, Any] | None:
    databases = mapping.get("databases", {}) or {}
    configured = (databases.get(database_name) or {}).get("rds_identifier")
    if configured:
        for item in resources:
            if item.get("id") == configured:
                return item
    for item in resources:
        tags = item.get("tags", {}) or {}
        if _tag_match(tags, ("Service", "Application", "BankingService", "Role"), database_name):
            return item
    return resources[0] if resources else None
