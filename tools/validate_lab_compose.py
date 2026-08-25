"""Validate corporate-lab isolation invariants in the rendered Compose model."""

from __future__ import annotations

import json
import subprocess
from typing import Any


def rendered_config() -> dict[str, Any]:
    result = subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    document: Any = json.loads(result.stdout)
    if not isinstance(document, dict):
        raise TypeError("Docker Compose config did not return an object")
    return document


def main() -> int:
    config = rendered_config()
    services = config["services"]
    networks = config["networks"]

    for network in ("sentinel_dmz", "sentinel_employee", "sentinel_server"):
        assert networks[network].get("internal") is True, f"{network} must be internal"

    unexposed = (
        "sentinel-db",
        "sentinel-admin",
        "sentinel-employee-01",
        "sentinel-employee-02",
        "sentinel-collector",
        "sentinel-web",
    )
    for service_name in unexposed:
        assert not services[service_name].get("ports"), f"{service_name} must not publish ports"

    web_ports = services["sentinel-lab-gateway"].get("ports", [])
    assert len(web_ports) == 1
    assert web_ports[0].get("host_ip") == "127.0.0.1"

    assert set(services["sentinel-collector"]["networks"]) == {"sentinel_management"}
    assert set(services["backend"]["networks"]) == {"sentinel_management"}
    assert set(services["sentinel-lab-gateway"]["networks"]) == {
        "sentinel_dmz",
        "sentinel_management",
    }
    assert "sentinel_management" not in services["sentinel-web"]["networks"]
    assert set(services["sentinel-employee-01"]["networks"]) == {"sentinel_employee"}
    assert set(services["sentinel-employee-02"]["networks"]) == {"sentinel_employee"}
    assert "sentinel_dmz" not in services["sentinel-db"]["networks"]

    for service_name, service in services.items():
        for volume in service.get("volumes", []):
            source = str(volume.get("source", ""))
            target = str(volume.get("target", ""))
            assert "docker.sock" not in source.lower()
            assert target != "/"
        for port in service.get("ports", []):
            assert port.get("host_ip") != "0.0.0.0", (
                f"{service_name} publishes a port on all host interfaces"
            )

    print("Corporate lab Compose isolation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
