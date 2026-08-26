from app.correlation.config import validate_correlation_config
from app.services.rule_loader import RuleLoader


def main() -> None:
    rule_ids = {definition.rule_id for definition in RuleLoader().load()}
    validate_correlation_config(rule_ids)
    print("Validated deterministic incident correlation configuration.")


if __name__ == "__main__":
    main()
