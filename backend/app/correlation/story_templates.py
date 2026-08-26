from dataclasses import dataclass


@dataclass(frozen=True)
class StoryTemplate:
    stage: str
    title: str


STORY_TEMPLATES = {
    "DET-SSH-001": StoryTemplate("credential_activity", "Credential activity observed"),
    "DET-SSH-002": StoryTemplate("authenticated_access", "Authenticated access observed"),
    "DET-NET-001": StoryTemplate("discovery", "Internal service discovery observed"),
    "DET-PRIV-001": StoryTemplate("privilege_activity", "Privileged activity observed"),
    "DET-DB-001": StoryTemplate("database_access", "Unexpected database connection observed"),
}


def story_description(
    rule_id: str,
    *,
    evidence_count: int,
    asset_hostname: str | None,
    username: str | None,
    source_ip: str | None,
    destination_ip: str | None,
) -> str:
    asset = asset_hostname or "an unresolved asset"
    source = source_ip or "an unresolved source"
    destination = destination_ip or "an unresolved destination"
    if rule_id == "DET-SSH-001":
        return f"{evidence_count} failed SSH authentication events were observed against {asset}."
    if rule_id == "DET-SSH-002":
        identity = f" for {username}" if username else ""
        return f"A successful SSH authentication followed repeated failures{identity} on {asset}."
    if rule_id == "DET-NET-001":
        return f"Internal service enumeration activity was observed from {source} on {asset}."
    if rule_id == "DET-PRIV-001":
        return f"Security-relevant privileged command activity was observed on {asset}."
    if rule_id == "DET-DB-001":
        return (
            "An unexpected workstation-to-database connection was observed "
            f"from {source} to {destination}."
        )
    return f"The alert was supported by {evidence_count} persisted security events on {asset}."


def incident_title(stages: set[str]) -> str:
    if {"credential_activity", "authenticated_access"}.issubset(stages):
        if stages & {"discovery", "privilege_activity", "database_access"}:
            return "Possible Credential Compromise and Internal Movement"
        return "Possible Credential Compromise"
    if "credential_activity" in stages:
        return "Suspicious Authentication Activity"
    if "privilege_activity" in stages:
        return "Security-Relevant Privileged Activity"
    if "discovery" in stages:
        return "Suspicious Internal Service Discovery"
    if "database_access" in stages:
        return "Unexpected Database Connection"
    return "Correlated Security Activity"


def stage_summary(stages: list[str]) -> str:
    labels = {
        "credential_activity": "repeated SSH authentication failures",
        "authenticated_access": "a subsequent successful authentication",
        "discovery": "internal service discovery",
        "lateral_or_internal_movement": "observed internal movement",
        "privilege_activity": "privileged activity",
        "database_access": "an unexpected database connection",
    }
    observed = [labels[stage] for stage in stages if stage in labels]
    if not observed:
        return "alert activity supported by persisted security evidence"
    if len(observed) == 1:
        return observed[0]
    return ", ".join(observed[:-1]) + f", and {observed[-1]}"
