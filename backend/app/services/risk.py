from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.asset import Asset
from app.models.enums import AlertStatus

SEVERITY_ALERT_RISK = {
    "informational": 5,
    "low": 15,
    "medium": 35,
    "high": 60,
    "critical": 85,
}
CRITICALITY_MODIFIER = {"low": 0, "medium": 3, "high": 7, "critical": 10}
ACTIVE_ALERT_WEIGHT = {"informational": 1, "low": 5, "medium": 10, "high": 20, "critical": 35}


class RiskService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def alert_score(severity: str, criticality: str | None, evidence_count: int) -> float:
        base = SEVERITY_ALERT_RISK[severity]
        asset_modifier = CRITICALITY_MODIFIER.get(criticality or "low", 0)
        evidence_modifier = min(10, max(0, evidence_count - 1))
        return float(min(100, base + asset_modifier + evidence_modifier))

    async def recalculate_asset(self, asset_id: UUID | None) -> None:
        if asset_id is None:
            return
        asset = await self.session.get(Asset, asset_id)
        if asset is None:
            return
        metadata = dict(asset.metadata_json or {})
        baseline = float(metadata.get("baseline_risk_score", asset.risk_score))
        metadata["baseline_risk_score"] = baseline
        severities = await self.session.scalars(
            select(Alert.severity).where(
                Alert.asset_id == asset_id,
                Alert.status.in_([AlertStatus.NEW, AlertStatus.INVESTIGATING]),
            )
        )
        active_risk = sum(ACTIVE_ALERT_WEIGHT[str(severity)] for severity in severities)
        asset.risk_score = float(min(100, baseline + active_risk))
        asset.metadata_json = metadata
        await self.session.flush()
