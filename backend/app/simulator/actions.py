from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.schemas.simulator import ScenarioStepDefinition


class SimulatorActionError(RuntimeError):
    """A fixed action broker request failed safely."""


class SafeActionRunner:
    """Call only compile-time broker paths; no URL, port, command, or credential is supplied."""

    _paths = {
        "controlled_failed_authentication": "/internal/simulator/actions/auth-failures",
        "controlled_successful_authentication": "/internal/simulator/actions/auth-success",
        "internal_service_discovery": "/internal/simulator/actions/service-discovery",
        "controlled_privileged_activity": "/internal/simulator/actions/privilege",
        "controlled_database_connection": "/internal/simulator/actions/database",
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(
                timeout=5,
                headers={"X-Sentinel-Simulation-Key": self.settings.sentinel_simulation_key},
            ) as client:
                response = await client.get(
                    f"{self.settings.simulator_control_url}/internal/simulator/health"
                )
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def execute(
        self,
        step: ScenarioStepDefinition,
        *,
        run_id: str,
        scenario_id: str,
    ) -> dict[str, Any]:
        path = self._paths.get(step.action)
        if path is None:
            raise SimulatorActionError(f"Action {step.action} is not brokered")
        body: dict[str, Any] = {"run_id": run_id, "scenario_id": scenario_id}
        if step.action == "controlled_failed_authentication":
            body["count"] = step.count
        try:
            async with httpx.AsyncClient(
                timeout=self.settings.simulator_action_timeout_seconds,
                headers={"X-Sentinel-Simulation-Key": self.settings.sentinel_simulation_key},
            ) as client:
                response = await client.post(
                    f"{self.settings.simulator_control_url}{path}", json=body
                )
                response.raise_for_status()
                payload: Any = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SimulatorActionError(
                f"Controlled action {step.action} failed at the internal broker"
            ) from exc
        if not isinstance(payload, dict) or payload.get("status") != "completed":
            raise SimulatorActionError(
                f"Controlled action {step.action} returned an invalid result"
            )
        return payload
