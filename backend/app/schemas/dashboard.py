from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DashboardSummary(BaseModel):
    total_assets: int = Field(ge=0)
    online_assets: int = Field(ge=0)
    high_risk_assets: int = Field(ge=0)
    events_today: int = Field(ge=0)
    events_last_hour: int = Field(ge=0)
    open_alerts: int = Field(ge=0)
    critical_alerts: int = Field(ge=0)
    high_alerts: int = Field(ge=0)
    open_incidents: int = Field(ge=0)
    critical_incidents: int = Field(ge=0)


class TimeBucket(BaseModel):
    timestamp: datetime
    count: int = Field(ge=0)


class CountBucket(BaseModel):
    name: str
    count: int = Field(ge=0)


class ActiveAssetBucket(BaseModel):
    asset_id: UUID | None
    hostname: str
    count: int = Field(ge=0)


class ActivityWindow(BaseModel):
    start: datetime
    end: datetime
    hours: int


class DashboardActivity(BaseModel):
    window: ActivityWindow
    events_over_time: list[TimeBucket]
    events_by_severity: list[CountBucket]
    events_by_type: list[CountBucket]
    most_active_assets: list[ActiveAssetBucket]
