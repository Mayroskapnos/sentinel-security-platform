import argparse
import asyncio
import json
import logging
import os
import re
import shlex
import socket
import subprocess
from collections import deque
from datetime import UTC, datetime
from hmac import compare_digest
from logging.handlers import RotatingFileHandler
from pathlib import Path
from uuid import UUID

SCENARIO_ID = re.compile(r"^SCN-[0-9]{3}$")
auth_attribution: deque[dict[str, str]] = deque(maxlen=30)


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
        sudoers.write_text("admin-demo ALL=(root) NOPASSWD: /usr/bin/id\n", encoding="utf-8")
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


def log_process(
    executable: str,
    return_code: int,
    category: str,
    attribution: dict[str, str] | None = None,
) -> None:
    writer.write(
        {
            "kind": "process_execution",
            "username": role_user(),
            "executable": executable,
            "return_code": return_code,
            "command_category": category,
            **(attribution or {}),
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


def database_activity(attribution: dict[str, str] | None = None) -> int:
    application_name = "employee-explicit-test"
    if attribution:
        application_name = (
            f"sentinel-sim:{attribution['scenario_run_id']}:{attribution['scenario_id']}"
        )
    environment = {
        **os.environ,
        "PGPASSWORD": os.getenv("LAB_DB_PASSWORD", "corporate_lab_db_demo"),
        "PGAPPNAME": application_name,
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
    log_process("/usr/bin/psql", result.returncode, "database_client", attribution)
    writer.write(
        {
            "kind": "database_client_connection",
            "username": os.getenv("LAB_DB_USER", "lab_app"),
            "process_name": "psql",
            "destination_ip": "10.10.30.20",
            "destination_port": 5432,
            "observed_destination": "sentinel-db",
            "service": "postgresql",
            "protocol": "tcp",
            "database": os.getenv("LAB_DB_NAME", "corp_demo"),
            "result": "success" if result.returncode == 0 else "failed",
            **(attribution or {}),
        }
    )
    return result.returncode


def ssh_activity(success: bool, attribution: dict[str, str] | None = None) -> int:
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
    log_process("/usr/bin/ssh", result.returncode, "remote_administration", attribution)
    return result.returncode


def privilege_activity(attribution: dict[str, str] | None = None) -> int:
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
            **(attribution or {}),
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
            attribution = auth_attribution.popleft() if auth_attribution else {}
            writer.write(
                {
                    "kind": "linux_auth",
                    "destination_ip": os.environ["LAB_ASSET_IP"],
                    "message": message,
                    **attribution,
                }
            )


def service_discovery(attribution: dict[str, str]) -> int:
    if os.environ["LAB_HOSTNAME"] != "employee-01":
        raise RuntimeError("service discovery is only available on employee-01")
    endpoints = (
        ("sentinel-web", "web-server", "10.10.20.20", 80, "http"),
        ("sentinel-web", "web-server", "10.10.20.20", 443, "https"),
        ("sentinel-web", "web-server", "10.10.20.20", 8080, "http-alt"),
        ("sentinel-web", "web-server", "10.10.20.20", 8443, "https-alt"),
        ("sentinel-admin", "admin-server", "10.10.20.30", 22, "ssh"),
        ("sentinel-admin", "admin-server", "10.10.20.30", 2222, "ssh-alt"),
        ("sentinel-admin", "admin-server", "10.10.20.30", 9090, "lab-control"),
        ("sentinel-db", "database", "10.10.20.21", 5432, "postgresql"),
        ("sentinel-db", "database", "10.10.20.21", 5433, "postgresql-alt"),
        ("sentinel-db", "database", "10.10.20.21", 6432, "postgresql-pool"),
    )
    for hostname, logical_target, destination_ip, port, service in endpoints:
        result = "failed"
        source_port = None
        try:
            with socket.create_connection((hostname, port), timeout=0.5) as connection:
                source_port = connection.getsockname()[1]
                result = "success"
        except OSError:
            pass
        writer.write(
            {
                "kind": "network_connection",
                "username": role_user(),
                "process_name": "lab-service-check",
                "source_port": source_port,
                "destination_ip": destination_ip,
                "destination_port": port,
                "observed_destination": logical_target,
                "service": service,
                "protocol": "tcp",
                "result": result,
                **attribution,
            }
        )
    return 0


def validate_attribution(document: object) -> tuple[dict[str, str], int | None]:
    if not isinstance(document, dict):
        raise TypeError("request must be an object")
    allowed = {"run_id", "scenario_id", "count"}
    if set(document) - allowed:
        raise ValueError("unsupported request field")
    run_id = str(UUID(str(document.get("run_id"))))
    scenario_id = document.get("scenario_id")
    if not isinstance(scenario_id, str) or not SCENARIO_ID.fullmatch(scenario_id):
        raise ValueError("invalid scenario ID")
    count = document.get("count")
    if count is not None and (
        not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 15
    ):
        raise ValueError("count must be between 1 and 15")
    return {"scenario_run_id": run_id, "scenario_id": scenario_id}, count


async def simulation_action(path: str, document: object) -> dict[str, object]:
    attribution, count = validate_attribution(document)
    hostname = os.environ["LAB_HOSTNAME"]
    if path == "/internal/simulation/prepare-auth":
        if hostname != "admin-server" or count is None:
            raise ValueError("prepare-auth is unavailable")
        auth_attribution.extend(dict(attribution) for _ in range(count))
        return {"status": "completed", "prepared": count}
    if path == "/internal/simulation/auth-failures":
        if hostname != "employee-01" or count is None:
            raise ValueError("auth-failures is unavailable")
        return_codes = [
            await asyncio.to_thread(ssh_activity, False, attribution) for _ in range(count)
        ]
        return {
            "status": "completed",
            "attempts": count,
            "failed_attempts": sum(return_code != 0 for return_code in return_codes),
        }
    if path == "/internal/simulation/auth-success":
        if hostname != "employee-01" or count is not None:
            raise ValueError("auth-success is unavailable")
        return_code = await asyncio.to_thread(ssh_activity, True, attribution)
    elif path == "/internal/simulation/service-discovery":
        if count is not None:
            raise ValueError("count is unsupported")
        return_code = await asyncio.to_thread(service_discovery, attribution)
    elif path == "/internal/simulation/privilege":
        if count is not None:
            raise ValueError("count is unsupported")
        return_code = await asyncio.to_thread(privilege_activity, attribution)
    elif path == "/internal/simulation/database":
        if hostname != "employee-01" or count is not None:
            raise ValueError("database action is unavailable")
        return_code = await asyncio.to_thread(database_activity, attribution)
    else:
        raise ValueError("unsupported fixed action")
    if return_code != 0:
        raise RuntimeError("controlled action did not complete successfully")
    return {"status": "completed"}


async def handle_control(reader: asyncio.StreamReader, writer_stream: asyncio.StreamWriter) -> None:
    status_code = 400
    payload: dict[str, object] = {"error": "invalid request"}
    try:
        header_bytes = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=3)
        if len(header_bytes) > 4096:
            raise ValueError("headers too large")
        lines = header_bytes.decode("ascii").split("\r\n")
        method, path, _ = lines[0].split(" ", 2)
        headers = {
            key.strip().lower(): value.strip()
            for line in lines[1:]
            if ":" in line
            for key, value in [line.split(":", 1)]
        }
        expected_key = os.environ["SENTINEL_SIMULATION_KEY"]
        if not compare_digest(headers.get("x-sentinel-simulation-key", ""), expected_key):
            status_code, payload = 401, {"error": "authentication failed"}
        elif method == "GET" and path == "/internal/simulation/health":
            status_code, payload = (
                200,
                {"status": "healthy", "host": os.environ["LAB_HOSTNAME"]},
            )
        elif method == "POST" and path.startswith("/internal/simulation/"):
            length = int(headers.get("content-length", "0"))
            if not 1 <= length <= 1024:
                raise ValueError("invalid body size")
            document = json.loads((await reader.readexactly(length)).decode("utf-8"))
            payload = await simulation_action(path, document)
            status_code = 200
        else:
            status_code, payload = 404, {"error": "not found"}
    except (
        ValueError,
        TypeError,
        KeyError,
        json.JSONDecodeError,
        asyncio.IncompleteReadError,
    ):
        pass
    except (OSError, RuntimeError, TimeoutError):
        status_code, payload = 503, {"error": "controlled action failed"}
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    reason = {
        200: "OK",
        400: "Bad Request",
        401: "Unauthorized",
        404: "Not Found",
        503: "Service Unavailable",
    }[status_code]
    response_headers = (
        f"HTTP/1.1 {status_code} {reason}\r\n"
        "Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n\r\n"
    )
    writer_stream.write(response_headers.encode("ascii") + body)
    await writer_stream.drain()
    writer_stream.close()
    await writer_stream.wait_closed()


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
            result = await asyncio.to_thread(run_as_user, ["/usr/bin/ps", "-eo", "pid,comm"])
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
    control = await asyncio.start_server(handle_control, "0.0.0.0", 9090)
    try:
        return_code = await sshd.wait()
        raise RuntimeError(f"sshd stopped unexpectedly with status {return_code}")
    finally:
        control.close()
        await control.wait_closed()
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
