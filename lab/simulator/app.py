import os
from hmac import compare_digest
from typing import Annotated, Any
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

SIMULATION_KEY = os.environ["SENTINEL_SIMULATION_KEY"]
HOST_HEADERS = {"X-Sentinel-Simulation-Key": SIMULATION_KEY}
HOSTS = {
    "employee": "http://sentinel-employee-01:9090/internal/simulation",
    "admin": "http://sentinel-admin:9090/internal/simulation",
}


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    scenario_id: str = Field(pattern=r"^SCN-[0-9]{3}$", max_length=16)


class AuthenticationFailureRequest(ActionRequest):
    count: int = Field(ge=1, le=15)


def verify_key(
    provided: Annotated[str | None, Header(alias="X-Sentinel-Simulation-Key")] = None,
) -> None:
    if provided is None or not compare_digest(provided, SIMULATION_KEY):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "simulation authentication failed")


app = FastAPI(
    title="SENTINEL Fixed Corporate Lab Action Broker",
    version="0.1",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
InternalKey = Annotated[None, Depends(verify_key)]


async def call_host(host: str, action: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=35, headers=HOST_HEADERS) as client:
            response = await client.post(f"{HOSTS[host]}/{action}", json=payload)
            response.raise_for_status()
            document: Any = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "fixed Corporate Lab action failed"
        ) from exc
    if not isinstance(document, dict) or document.get("status") != "completed":
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "fixed Corporate Lab action was incomplete",
        )
    return document


@app.get("/internal/simulator/health", dependencies=[Depends(verify_key)])
async def health() -> dict[str, str]:
    for host in HOSTS.values():
        try:
            async with httpx.AsyncClient(timeout=3, headers=HOST_HEADERS) as client:
                response = await client.get(f"{host}/health")
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Corporate Lab action agent unavailable",
            ) from exc
    return {"status": "healthy"}


@app.post("/internal/simulator/actions/auth-failures", dependencies=[Depends(verify_key)])
async def authentication_failures(
    payload: AuthenticationFailureRequest,
) -> dict[str, Any]:
    body = payload.model_dump(mode="json")
    await call_host("admin", "prepare-auth", body)
    return await call_host("employee", "auth-failures", body)


@app.post("/internal/simulator/actions/auth-success", dependencies=[Depends(verify_key)])
async def authentication_success(payload: ActionRequest) -> dict[str, Any]:
    body = {**payload.model_dump(mode="json"), "count": 1}
    await call_host("admin", "prepare-auth", body)
    body.pop("count")
    return await call_host("employee", "auth-success", body)


@app.post("/internal/simulator/actions/service-discovery", dependencies=[Depends(verify_key)])
async def service_discovery(payload: ActionRequest) -> dict[str, Any]:
    return await call_host("employee", "service-discovery", payload.model_dump(mode="json"))


@app.post("/internal/simulator/actions/privilege", dependencies=[Depends(verify_key)])
async def privilege(payload: ActionRequest) -> dict[str, Any]:
    return await call_host("admin", "privilege", payload.model_dump(mode="json"))


@app.post("/internal/simulator/actions/database", dependencies=[Depends(verify_key)])
async def database(payload: ActionRequest) -> dict[str, Any]:
    return await call_host("employee", "database", payload.model_dump(mode="json"))
