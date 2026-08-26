from dataclasses import dataclass


@dataclass(frozen=True)
class CorrelationConfig:
    correlation_window_seconds: int = 900
    minimum_score: int = 50
    candidate_limit: int = 25
    same_scenario_weight: int = 50
    shared_source_ip_weight: int = 20
    shared_username_weight: int = 15
    shared_asset_weight: int = 15
    network_relationship_weight: int = 10
    progression_weight: int = 15
    within_two_minutes_weight: int = 15
    within_five_minutes_weight: int = 10
    within_window_weight: int = 5

    def validate(self) -> None:
        if not 60 <= self.correlation_window_seconds <= 86_400:
            raise ValueError("correlation window must be between 60 seconds and 24 hours")
        if not 1 <= self.minimum_score <= 100:
            raise ValueError("minimum correlation score must be between 1 and 100")
        if not 1 <= self.candidate_limit <= 100:
            raise ValueError("candidate limit must be between 1 and 100")
        weights = [
            self.same_scenario_weight,
            self.shared_source_ip_weight,
            self.shared_username_weight,
            self.shared_asset_weight,
            self.network_relationship_weight,
            self.progression_weight,
            self.within_two_minutes_weight,
            self.within_five_minutes_weight,
            self.within_window_weight,
        ]
        if any(weight < 0 or weight > 100 for weight in weights):
            raise ValueError("correlation weights must be between 0 and 100")


CORRELATION_CONFIG = CorrelationConfig()
CORRELATION_CONFIG.validate()

DETECTION_PROGRESSION = {
    ("DET-SSH-001", "DET-SSH-002"),
    ("DET-SSH-002", "DET-NET-001"),
    ("DET-NET-001", "DET-PRIV-001"),
    ("DET-PRIV-001", "DET-DB-001"),
}


def validate_correlation_config(known_rule_ids: set[str] | None = None) -> None:
    CORRELATION_CONFIG.validate()
    if len(DETECTION_PROGRESSION) != 4:
        raise ValueError("correlation progression definitions must be unique")
    if known_rule_ids is not None:
        referenced = {rule_id for pair in DETECTION_PROGRESSION for rule_id in pair}
        unknown = sorted(referenced - known_rule_ids)
        if unknown:
            raise ValueError(
                f"correlation progression references unknown rules: {', '.join(unknown)}"
            )
