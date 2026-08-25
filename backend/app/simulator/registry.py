from dataclasses import dataclass


@dataclass(frozen=True)
class LabTarget:
    id: str
    display_name: str


class LabTargetRegistry:
    """Canonical logical targets; infrastructure addresses never enter scenario data."""

    _targets = {
        "web-server": LabTarget("web-server", "Corporate Lab Web Server"),
        "employee-01": LabTarget("employee-01", "Employee Workstation 01"),
        "employee-02": LabTarget("employee-02", "Employee Workstation 02"),
        "admin-server": LabTarget("admin-server", "Administrative Server"),
        "database": LabTarget("database", "Corporate Application Database"),
    }

    @classmethod
    def contains(cls, target: str) -> bool:
        return target in cls._targets

    @classmethod
    def ids(cls) -> frozenset[str]:
        return frozenset(cls._targets)
