from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investigation import InvestigationAnalysis, InvestigationMessage


class InvestigationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_analysis(
        self, analysis_id: UUID, incident_id: UUID | None = None
    ) -> InvestigationAnalysis | None:
        query = select(InvestigationAnalysis).where(InvestigationAnalysis.id == analysis_id)
        if incident_id:
            query = query.where(InvestigationAnalysis.incident_id == incident_id)
        return await self.session.scalar(query)

    async def active_analysis(self, incident_id: UUID) -> InvestigationAnalysis | None:
        return await self.session.scalar(
            select(InvestigationAnalysis)
            .where(
                InvestigationAnalysis.incident_id == incident_id,
                InvestigationAnalysis.status.in_(("pending", "running")),
            )
            .order_by(InvestigationAnalysis.created_at.desc())
            .limit(1)
        )

    async def latest_analysis(self, incident_id: UUID) -> InvestigationAnalysis | None:
        return await self.session.scalar(
            select(InvestigationAnalysis)
            .where(InvestigationAnalysis.incident_id == incident_id)
            .order_by(InvestigationAnalysis.created_at.desc(), InvestigationAnalysis.id.desc())
            .limit(1)
        )

    async def list_analyses(
        self, incident_id: UUID, page: int, page_size: int
    ) -> tuple[list[InvestigationAnalysis], int]:
        from sqlalchemy import func

        total = int(
            await self.session.scalar(
                select(func.count(InvestigationAnalysis.id)).where(
                    InvestigationAnalysis.incident_id == incident_id
                )
            )
            or 0
        )
        rows = list(
            await self.session.scalars(
                select(InvestigationAnalysis)
                .where(InvestigationAnalysis.incident_id == incident_id)
                .order_by(
                    InvestigationAnalysis.created_at.desc(),
                    InvestigationAnalysis.id.desc(),
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return rows, total

    async def recent_messages(self, incident_id: UUID, limit: int) -> list[InvestigationMessage]:
        if limit <= 0:
            return []
        rows = list(
            await self.session.scalars(
                select(InvestigationMessage)
                .where(InvestigationMessage.incident_id == incident_id)
                .order_by(
                    InvestigationMessage.created_at.desc(),
                    InvestigationMessage.id.desc(),
                )
                .limit(limit)
            )
        )
        return list(reversed(rows))

    async def latest_current_completed(
        self, incident_id: UUID, context_hash: str
    ) -> InvestigationAnalysis | None:
        return await self.session.scalar(
            select(InvestigationAnalysis)
            .where(
                InvestigationAnalysis.incident_id == incident_id,
                InvestigationAnalysis.status == "completed",
                InvestigationAnalysis.context_hash == context_hash,
            )
            .order_by(InvestigationAnalysis.created_at.desc())
            .limit(1)
        )
