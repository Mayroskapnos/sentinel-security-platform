from enum import StrEnum


class AssetType(StrEnum):
    WORKSTATION = "workstation"
    SERVER = "server"
    WEB_SERVER = "web_server"
    DATABASE = "database"
    CONTAINER = "container"
    NETWORK_DEVICE = "network_device"
    UNKNOWN = "unknown"


class AssetStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class Criticality(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventSeverity(StrEnum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RuleType(StrEnum):
    THRESHOLD = "threshold"
    SEQUENCE = "sequence"
    SINGLE_EVENT = "single_event"


class AlertStatus(StrEnum):
    NEW = "new"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class ScenarioRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScenarioStepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_class]
