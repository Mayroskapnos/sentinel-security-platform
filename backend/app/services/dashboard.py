from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.dashboard import DashboardRepository
from app.schemas.dashboard import ActivityWindow, DashboardActivity, DashboardSummary


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = DashboardRepository(session)

    async def summary(self) -> DashboardSummary:
        values = await self.repository.summary(datetime.now(UTC))
        return DashboardSummary.model_validate(values)

    async def activity(self, hours: int) -> DashboardActivity:
        end = datetime.now(UTC)
        start = end - timedelta(hours=hours)
        values = await self.repository.activity(start, end)
        return DashboardActivity(
            window=ActivityWindow(start=start, end=end, hours=hours),
            **values,
        )
