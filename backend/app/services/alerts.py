from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.enums import AlertStatus
from app.realtime.manager import WebSocketManager, websocket_manager
from app.repositories.alerts import AlertRepository
from app.schemas.alert import AlertDetailResponse, AlertFilters, AlertResponse, AlertUpdate
from app.schemas.common import Page
from app.schemas.realtime import AlertUpdatedMessage
from app.services.risk import RiskService

ALLOWED_TRANSITIONS = {
    AlertStatus.NEW: {AlertStatus.INVESTIGATING, AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE},
    AlertStatus.INVESTIGATING: {AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE},
    AlertStatus.RESOLVED: {AlertStatus.INVESTIGATING},
    AlertStatus.FALSE_POSITIVE: {AlertStatus.INVESTIGATING},
}


class AlertService:
    def __init__(
        self,
        session: AsyncSession,
        manager: WebSocketManager = websocket_manager,
    ) -> None:
        self.session = session
        self.repository = AlertRepository(session)
        self.manager = manager

    async def list(self, filters: AlertFilters) -> Page[AlertResponse]:
        alerts, total = await self.repository.list(filters)
        return Page[AlertResponse].create(
            items=[AlertResponse.model_validate(alert) for alert in alerts],
            page=filters.page,
            page_size=filters.page_size,
            total=total,
        )

    async def get(self, alert_id: UUID) -> AlertDetailResponse:
        alert = await self.repository.get(alert_id, include_events=True)
        if alert is None:
            raise NotFoundError("ALERT_NOT_FOUND", "Requested alert does not exist.")
        return AlertDetailResponse.model_validate(alert)

    async def update(self, alert_id: UUID, payload: AlertUpdate) -> AlertResponse:
        alert = await self.repository.get(alert_id)
        if alert is None:
            raise NotFoundError("ALERT_NOT_FOUND", "Requested alert does not exist.")
        current = AlertStatus(alert.status)
        if payload.status != current and payload.status not in ALLOWED_TRANSITIONS[current]:
            raise ConflictError(
                "INVALID_ALERT_STATUS_TRANSITION",
                f"Alert cannot move from {current.value} to {payload.status.value}.",
            )
        alert.status = payload.status
        await RiskService(self.session).recalculate_asset(alert.asset_id)
        await self.session.commit()
        refreshed = await self.repository.get(alert_id)
        assert refreshed is not None
        response = AlertResponse.model_validate(refreshed)
        await self.manager.broadcast(AlertUpdatedMessage(data=response))
        return response
