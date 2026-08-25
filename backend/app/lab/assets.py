from typing import Any
from uuid import UUID, uuid5

from app.models.enums import AssetStatus, AssetType, Criticality

LAB_ASSET_NAMESPACE = UUID("8abda546-b4e1-4c61-bd99-09921736e38d")
LAB_HOSTNAMES = ("web-server", "employee-01", "employee-02", "admin-server", "database")
CORPORATE_LAB_SOURCES = (
    "container_health",
    "linux_auth",
    "linux_process",
    "linux_privilege",
    "network",
    "postgresql",
    "web_access",
    "web_application",
)


def stable_id(name: str) -> UUID:
    return uuid5(LAB_ASSET_NAMESPACE, name)


LAB_ASSETS: list[dict[str, Any]] = [
    {
        "id": stable_id("asset-web-server"),
        "hostname": "web-server",
        "display_name": "Corporate Lab Web Server",
        "ip_address": "10.10.10.10",
        "mac_address": "02:42:0a:0a:0a:10",
        "asset_type": AssetType.WEB_SERVER,
        "operating_system": "Debian 13 container",
        "environment": "lab",
        "network_zone": "dmz",
        "status": AssetStatus.UNKNOWN,
        "risk_score": 44,
        "criticality": Criticality.HIGH,
        "metadata_json": {
            "owner": "Web Operations",
            "service": "corporate-portal",
            "container": "sentinel-web",
            "lab_version": "0.1",
        },
    },
    {
        "id": stable_id("asset-employee-01"),
        "hostname": "employee-01",
        "display_name": "Employee Workstation 01",
        "ip_address": "10.10.20.10",
        "mac_address": "02:42:0a:0a:14:10",
        "asset_type": AssetType.WORKSTATION,
        "operating_system": "Debian 13 container",
        "environment": "lab",
        "network_zone": "employee",
        "status": AssetStatus.UNKNOWN,
        "risk_score": 36,
        "criticality": Criticality.MEDIUM,
        "metadata_json": {
            "owner": "Demo User",
            "department": "Engineering",
            "container": "sentinel-employee-01",
            "lab_version": "0.1",
        },
    },
    {
        "id": stable_id("asset-employee-02"),
        "hostname": "employee-02",
        "display_name": "Employee Workstation 02",
        "ip_address": "10.10.20.11",
        "mac_address": "02:42:0a:0a:14:11",
        "asset_type": AssetType.WORKSTATION,
        "operating_system": "Debian 13 container",
        "environment": "lab",
        "network_zone": "employee",
        "status": AssetStatus.UNKNOWN,
        "risk_score": 18,
        "criticality": Criticality.MEDIUM,
        "metadata_json": {
            "owner": "Operations User",
            "department": "Operations",
            "container": "sentinel-employee-02",
            "lab_version": "0.1",
        },
    },
    {
        "id": stable_id("asset-admin-server"),
        "hostname": "admin-server",
        "display_name": "Administrative Server",
        "ip_address": "10.10.30.10",
        "mac_address": "02:42:0a:0a:1e:10",
        "asset_type": AssetType.SERVER,
        "operating_system": "Debian 13 container",
        "environment": "lab",
        "network_zone": "server",
        "status": AssetStatus.UNKNOWN,
        "risk_score": 67,
        "criticality": Criticality.CRITICAL,
        "metadata_json": {
            "owner": "Infrastructure",
            "role": "administration",
            "container": "sentinel-admin",
            "lab_version": "0.1",
        },
    },
    {
        "id": stable_id("asset-database"),
        "hostname": "database",
        "display_name": "Corporate Application Database",
        "ip_address": "10.10.30.20",
        "mac_address": "02:42:0a:0a:1e:20",
        "asset_type": AssetType.DATABASE,
        "operating_system": "PostgreSQL 16 on Alpine Linux",
        "environment": "lab",
        "network_zone": "server",
        "status": AssetStatus.UNKNOWN,
        "risk_score": 52,
        "criticality": Criticality.CRITICAL,
        "metadata_json": {
            "owner": "Data Platform",
            "service": "corp_demo",
            "container": "sentinel-db",
            "lab_version": "0.1",
        },
    },
]
