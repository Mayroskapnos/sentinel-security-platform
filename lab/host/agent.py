import argparse
import asyncio
import json
import logging
import os
import shlex
import subprocess
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


class JsonLineWriter:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.handler = RotatingFileHandler(
            path, maxBytes=2_000_000, backupCount=2, encoding="utf-8"
        )
        self.handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger = logging.getLogger(f"sentinel.lab.host.{id(self)}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.logger.addHandler(self.handler)

    def write(self, record: dict[str, object]) -> None:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "hostname": os.environ["LAB_HOSTNAME"],
            "source_ip": os.environ["LAB_ASSET_IP"],
            **record,
        }
        self.logger.info(json.dumps(payload, separators=(",", ":")))

    def close(self) -> None:
        self.logger.removeHandler(self.handler)
        self.handler.close()


writer = JsonLineWriter(Path(os.getenv("LAB_LOG_PATH", "/var/log/sentinel-lab/events.jsonl")))


def role_user() -> str:
    return {
        "employee-01": "demo-user",
        "employee-02": "ops-user",
        "admin-server": "admin-demo",
    }.get(os.environ["LAB_HOSTNAME"], "demo-user")


def configure_accounts() -> None:
    password = os.getenv("LAB_SSH_PASSWORD", "corporate_lab_ssh_demo")
    for username in ("demo-user", "ops-user", "admin-demo"):
        subprocess.run(
            ["chpasswd"],
            input=f"{username}:{password}\n",
            text=True,
            check=True,
            capture_output=True,
        )
    subprocess.run(["ssh-keygen", "-A"], check=True, capture_output=True)
    if os.environ["LAB_HOSTNAME"] == "admin-server":
        sudoers = Path("/etc/sudoers.d/sentinel-lab")
        sudoers.write_text(
            "admin-demo ALL=(root) NOPASSWD: /usr/bin/id\n", encoding="utf-8"
        )
        sudoers.chmod(0o440)


def run_as_user(command: list[str], *, environment: dict[str, str] | None = None):
    return subprocess.run(
        ["runuser", "-u", role_user(), "--", *command],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
        env=environment,
    )


def log_process(executable: str, return_code: int, category: str) -> None:
    writer.write(
        {
            "kind": "process_execution",
            "username": role_user(),
            "executable": executable,
            "return_code": return_code,
            "command_category": category,
        }
    )


def web_activity(path: str = "/health") -> int:
    url = f"http://sentinel-web:8080{path}"
    result = run_as_user(["/usr/bin/curl", "--fail", "--silent", "--show-error", url])
    log_process("/usr/bin/curl", result.returncode, "network_client")
    writer.write(
        {
            "kind": "network_connection",
            "username": role_user(),
            "process_name": "curl",
            "destination_ip": "10.10.10.10",
            "destination_port": 8080,
            "observed_destination": "sentinel-web",
            "service": "http",
            "protocol": "tcp",
            "result": "success" if result.returncode == 0 else "failed",
        }
    )
    return result.returncode


def web_login() -> int:
    payload = json.dumps(
        {
            "username": os.getenv("LAB_WEB_USER", "demo-user"),
            "password": os.getenv("LAB_WEB_PASSWORD", "corporate_lab_demo"),
        }
    )
    result = run_as_user(
        [
            "/usr/bin/curl",
            "--fail",
            "--silent",
            "--show-error",
            "--header",
            "Content-Type: application/json",
            "--data",
            payload,
            "http://sentinel-web:8080/login",
        ]
    )
    log_process("/usr/bin/curl", result.returncode, "web_authentication")
    return result.returncode


def database_activity() -> int:
    environment = {
        **os.environ,
        "PGPASSWORD": os.getenv("LAB_DB_PASSWORD", "corporate_lab_db_demo"),
        "PGAPPNAME": "employee-explicit-test",
    }
    result = run_as_user(
        [
            "/usr/bin/psql",
            "--host",
            "sentinel-db",
            "--username",
            os.getenv("LAB_DB_USER", "lab_app"),
            "--dbname",
            os.getenv("LAB_DB_NAME", "corp_demo"),
            "--command",
            "SELECT current_database();",
        ],
        environment=environment,
    )
    log_process("/usr/bin/psql", result.returncode, "database_client")
    writer.write(
        {
            "kind": "network_connection",
            "username": role_user(),
            "process_name": "psql",
            "destination_ip": "10.10.30.20",
            "destination_port": 5432,
            "observed_destination": "sentinel-db",
            "service": "postgresql",
            "protocol": "tcp",
            "result": "success" if result.returncode == 0 else "failed",
        }
    )
    return result.returncode


def ssh_activity(success: bool) -> int:
    password = os.getenv("LAB_SSH_PASSWORD", "corporate_lab_ssh_demo") if success else "wrong"
    result = run_as_user(
        [
            "/usr/bin/sshpass",
            "-p",
            password,
            "/usr/bin/ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "ConnectTimeout=5",
            "admin-demo@sentinel-admin",
            "/usr/bin/true",
        ]
    )
    log_process("/usr/bin/ssh", result.returncode, "remote_administration")
    return result.returncode


def privilege_activity() -> int:
    if os.environ["LAB_HOSTNAME"] != "admin-server":
        raise RuntimeError("privilege activity is only available on admin-server")
    result = run_as_user(["/usr/bin/sudo", "/usr/bin/id"])
    writer.write(
        {
            "kind": "sudo_execution",
            "username": role_user(),
            "command": "/usr/bin/id",
            "target_user": "root",
            "return_code": result.returncode,
        }
    )
    return result.returncode


def process_activity() -> int:
    result = run_as_user(["/usr/bin/whoami"])
    log_process("/usr/bin/whoami", result.returncode, "identity")
    return result.returncode


async def capture_sshd(process: asyncio.subprocess.Process) -> None:
    assert process.stderr is not None
    while line := await process.stderr.readline():
        message = line.decode("utf-8", errors="replace").strip()
        if "Accepted " in message or "Failed " in message:
            writer.write(
                {
                    "kind": "linux_auth",
                    "destination_ip": os.environ["LAB_ASSET_IP"],
                    "message": message,
                }
            )


async def background_activity() -> None:
    hostname = os.environ["LAB_HOSTNAME"]
    interval = int(os.getenv("LAB_ACTIVITY_INTERVAL", "50"))
    cycle = 0
    while True:
        writer.write(
            {
                "kind": "container_health",
                "process_name": "lab-agent",
            }
        )
        if hostname == "employee-01":
            await asyncio.to_thread(web_activity, "/api/profile")
            if cycle % 2 == 0:
                await asyncio.to_thread(web_login)
        elif hostname == "employee-02":
            await asyncio.to_thread(web_activity, "/health")
        else:
            result = await asyncio.to_thread(
                run_as_user, ["/usr/bin/ps", "-eo", "pid,comm"]
            )
            log_process("/usr/bin/ps", result.returncode, "administration")
        cycle += 1
        await asyncio.sleep(interval)


async def serve() -> None:
    configure_accounts()
    sshd = await asyncio.create_subprocess_exec(
        "/usr/sbin/sshd",
        "-D",
        "-e",
        stderr=asyncio.subprocess.PIPE,
    )
    capture = asyncio.create_task(capture_sshd(sshd))
    activity = asyncio.create_task(background_activity())
    try:
        return_code = await sshd.wait()
        raise RuntimeError(f"sshd stopped unexpectedly with status {return_code}")
    finally:
        capture.cancel()
        activity.cancel()
        await asyncio.gather(capture, activity, return_exceptions=True)
        writer.close()


def run_activity(name: str) -> int:
    actions = {
        "auth-failure": lambda: ssh_activity(False),
        "auth-success": lambda: ssh_activity(True),
        "database": database_activity,
        "privilege": privilege_activity,
        "process": process_activity,
        "web": lambda: web_activity("/api/profile"),
        "web-login": web_login,
    }
    if name not in actions:
        raise ValueError(f"unsupported activity {shlex.quote(name)}")
    try:
        return actions[name]()
    finally:
        writer.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="SENTINEL corporate lab host agent")
    parser.add_argument("command", nargs="?", default="serve", choices=["serve", "activity"])
    parser.add_argument("activity", nargs="?")
    args = parser.parse_args()
    if args.command == "activity":
        if args.activity is None:
            parser.error("activity name is required")
        raise SystemExit(run_activity(args.activity))
    asyncio.run(serve())


if __name__ == "__main__":
    main()
