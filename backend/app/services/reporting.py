from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.network_connection import NetworkConnection
from app.reporting.renderers import render_html_report, render_pdf_report
from app.repositories.investigations import InvestigationRepository
from app.schemas.reporting import IncidentReportContext, ReportNetworkRelationship
from app.services.incidents import IncidentService
from app.services.investigations import InvestigationService

ReportFormat = Literal["html", "pdf"]


@dataclass(frozen=True)
class GeneratedIncidentReport:
    content: bytes
    media_type: str
    filename: str


class IncidentReportContextBuilder:
    """Build a point-in-time report package from authoritative Incident services."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def build(self, incident_id: UUID, *, include_ai: bool) -> IncidentReportContext:
        incident = await IncidentService(self.session).get(incident_id)
        connection_ids = {
            item.network_connection_id
            for item in incident.story
            if item.network_connection_id is not None
        }
        connections: list[NetworkConnection] = []
        if connection_ids:
            connections = list(
                await self.session.scalars(
                    select(NetworkConnection)
                    .where(NetworkConnection.id.in_(connection_ids))
                    .options(
                        joinedload(NetworkConnection.source_asset),
                        joinedload(NetworkConnection.destination_asset),
                    )
                    .order_by(NetworkConnection.first_seen, NetworkConnection.id)
                )
            )

        ai_analysis = None
        if include_ai:
            latest = await InvestigationRepository(self.session).latest_completed(incident_id)
            if latest is not None:
                ai_analysis = await InvestigationService(self.session).get_analysis(
                    incident_id, latest.id
                )

        duration = max(
            0,
            round((incident.last_activity_at - incident.first_activity_at).total_seconds()),
        )
        return IncidentReportContext(
            generated_at=datetime.now(UTC),
            incident=incident,
            duration_seconds=duration,
            network_relationships=[
                ReportNetworkRelationship(
                    source_hostname=connection.source_asset.hostname,
                    source_ip=connection.source_ip,
                    destination_hostname=connection.destination_asset.hostname,
                    destination_ip=connection.destination_ip,
                    destination_port=connection.destination_port,
                    protocol=connection.protocol,
                    connection_type=connection.connection_type,
                    first_seen=connection.first_seen,
                    last_seen=connection.last_seen,
                    connection_count=connection.connection_count,
                    last_status=connection.last_status,
                )
                for connection in connections
            ],
            ai_analysis=ai_analysis,
        )


class IncidentReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.context_builder = IncidentReportContextBuilder(session)

    async def generate(
        self,
        incident_id: UUID,
        *,
        report_format: ReportFormat,
        include_ai: bool = False,
    ) -> GeneratedIncidentReport:
        context = await self.context_builder.build(incident_id, include_ai=include_ai)
        safe_number = "".join(
            character
            for character in context.incident.incident_number.upper()
            if character.isalnum() or character == "-"
        )[:32]
        if report_format == "html":
            return GeneratedIncidentReport(
                content=render_html_report(context).encode("utf-8"),
                media_type="text/html; charset=utf-8",
                filename=f"SENTINEL_{safe_number}_Report.html",
            )
        return GeneratedIncidentReport(
            content=render_pdf_report(context),
            media_type="application/pdf",
            filename=f"SENTINEL_{safe_number}_Report.pdf",
        )
