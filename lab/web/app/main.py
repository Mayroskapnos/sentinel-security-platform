import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from hmac import compare_digest
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import perf_counter
from typing import AsyncIterator

import psycopg
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class JsonLineWriter:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.handler = RotatingFileHandler(
            path, maxBytes=2_000_000, backupCount=2, encoding="utf-8"
        )
        self.handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger = logging.getLogger(f"sentinel.lab.web.{id(self)}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.logger.addHandler(self.handler)

    def write(self, record: dict[str, object]) -> None:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "hostname": "web-server",
            "destination_ip": "10.10.10.10",
            **record,
        }
        self.logger.info(json.dumps(payload, separators=(",", ":")))

    def close(self) -> None:
        self.logger.removeHandler(self.handler)
        self.handler.close()


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


writer = JsonLineWriter(Path(os.getenv("LAB_LOG_PATH", "/var/log/sentinel-lab/events.jsonl")))


async def heartbeat() -> None:
    while True:
        writer.write(
            {
                "kind": "container_health",
                "source_ip": "10.10.10.10",
                "process_name": "corporate-portal",
            }
        )
        await asyncio.sleep(45)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(heartbeat())
    try:
        yield
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        writer.close()


app = FastAPI(title="SENTINEL Corporate Portal", version="0.1", lifespan=lifespan)


@app.middleware("http")
async def access_log(request: Request, call_next):  # type: ignore[no-untyped-def]
    started = perf_counter()
    response = await call_next(request)
    if request.headers.get("user-agent") != "Docker-Healthcheck":
        client = request.client
        writer.write(
            {
                "kind": "http_request",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((perf_counter() - started) * 1000, 2),
                "client_ip": client.host if client else None,
                "client_port": client.port if client else None,
            }
        )
    return response


@app.get("/")
async def index() -> dict[str, str]:
    return {
        "service": "SENTINEL Corporate Portal",
        "environment": "isolated local lab",
        "version": "0.1",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/login")
async def login_information() -> dict[str, str]:
    return {"demo_user": os.getenv("LAB_WEB_USER", "demo-user")}


@app.post("/login")
async def login(payload: LoginRequest, request: Request) -> JSONResponse:
    expected_user = os.getenv("LAB_WEB_USER", "demo-user")
    expected_password = os.getenv("LAB_WEB_PASSWORD", "corporate_lab_demo")
    accepted = compare_digest(payload.username, expected_user) and compare_digest(
        payload.password, expected_password
    )
    client = request.client
    writer.write(
        {
            "kind": "web_authentication",
            "client_ip": client.host if client else None,
            "client_port": client.port if client else None,
            "username": payload.username,
            "result": "success" if accepted else "failed",
        }
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK if accepted else status.HTTP_401_UNAUTHORIZED,
        content={"status": "authenticated" if accepted else "denied"},
    )


def database_profile() -> dict[str, object]:
    with psycopg.connect(
        host=os.getenv("LAB_DB_HOST", "sentinel-db"),
        port=5432,
        dbname=os.getenv("LAB_DB_NAME", "corp_demo"),
        user=os.getenv("LAB_DB_USER", "lab_app"),
        password=os.getenv("LAB_DB_PASSWORD", "corporate_lab_db_demo"),
        application_name="corporate-portal",
        connect_timeout=5,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT display_name, department FROM employees "
                "WHERE username = %s LIMIT 1",
                ("demo-user",),
            )
            row = cursor.fetchone()
    return {
        "username": "demo-user",
        "display_name": row[0] if row else "Demo User",
        "department": row[1] if row else "Engineering",
    }


@app.get("/api/profile")
async def profile() -> dict[str, object]:
    return await asyncio.to_thread(database_profile)
