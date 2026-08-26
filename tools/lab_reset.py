"""Remove only corporate-lab volumes after its containers have been stopped and removed."""

from __future__ import annotations

import subprocess

LAB_SERVICES = (
    "sentinel-collector",
    "sentinel-lab-gateway",
    "sentinel-employee-01",
    "sentinel-employee-02",
    "sentinel-admin",
    "sentinel-web",
    "sentinel-db",
)
LAB_VOLUMES = (
    "sentinel_lab_postgres_data",
    "sentinel_lab_web_logs",
    "sentinel_lab_employee_01_logs",
    "sentinel_lab_employee_02_logs",
    "sentinel_lab_admin_logs",
    "sentinel_lab_database_logs",
    "sentinel_lab_collector_state",
)


def run(*arguments: str, check: bool = True) -> None:
    subprocess.run(arguments, check=check)


def main() -> int:
    run("docker", "compose", "stop", *LAB_SERVICES, check=False)
    run("docker", "compose", "rm", "--force", "--stop", *LAB_SERVICES, check=False)
    for volume in LAB_VOLUMES:
        run("docker", "volume", "rm", volume, check=False)
    print(
        "Corporate lab containers, logs, database, and collector checkpoints were reset."
    )
    print("SENTINEL platform history and sentinel_postgres_data were not removed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
