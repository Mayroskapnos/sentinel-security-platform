from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.incident import IncidentDetail
from app.schemas.investigation import InvestigationAnalysisResponse


class ReportNetworkRelationship(BaseModel):
    source_hostname: str
    source_ip: str
    destination_hostname: str
    destination_ip: str
    destination_port: int | None
    protocol: str
    connection_type: str
    first_seen: datetime
    last_seen: datetime
    connection_count: int = Field(ge=1)
    last_status: str


class IncidentReportContext(BaseModel):
    generated_at: datetime
    incident: IncidentDetail
    duration_seconds: int = Field(ge=0)
    network_relationships: list[ReportNetworkRelationship]
    ai_analysis: InvestigationAnalysisResponse | None = None
