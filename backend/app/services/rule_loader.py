import logging
from pathlib import Path

import yaml
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.detection_rule import DetectionRule
from app.schemas.detection_rule import BundledRuleDefinition

logger = logging.getLogger(__name__)


class RuleLoadError(ValueError):
    """Raised when a bundled rule file is unsafe, malformed, or duplicated."""


class RuleLoader:
    def __init__(self, rules_directory: Path | None = None) -> None:
        self.rules_directory = rules_directory or Path(__file__).parent.parent / "detection_rules"

    def load(self) -> list[BundledRuleDefinition]:
        definitions: list[BundledRuleDefinition] = []
        seen: dict[str, Path] = {}
        rule_files = sorted(
            (*self.rules_directory.glob("*.yml"), *self.rules_directory.glob("*.yaml"))
        )
        if not rule_files:
            raise RuleLoadError(f"No YAML detection rules found in {self.rules_directory}")

        for path in rule_files:
            try:
                document = yaml.safe_load(path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError) as exc:
                raise RuleLoadError(f"Unable to load detection rule {path.name}: {exc}") from exc
            if not isinstance(document, dict):
                raise RuleLoadError(f"Detection rule {path.name} must contain one YAML object")
            try:
                definition = BundledRuleDefinition.model_validate(document)
            except ValidationError as exc:
                raise RuleLoadError(f"Invalid detection rule {path.name}: {exc}") from exc
            if definition.rule_id in seen:
                raise RuleLoadError(
                    f"Duplicate detection rule ID {definition.rule_id} in "
                    f"{seen[definition.rule_id].name} and {path.name}"
                )
            seen[definition.rule_id] = path
            definitions.append(definition)
        return definitions

    async def sync(self, session: AsyncSession) -> list[DetectionRule]:
        """Upsert bundled definitions while preserving analyst enable/disable choices."""
        definitions = self.load()
        existing = {
            rule.rule_id: rule
            for rule in await session.scalars(
                select(DetectionRule).where(
                    DetectionRule.rule_id.in_([definition.rule_id for definition in definitions])
                )
            )
        }
        synchronized: list[DetectionRule] = []
        for definition in definitions:
            rule = existing.get(definition.rule_id)
            if rule is None:
                rule = DetectionRule(rule_id=definition.rule_id, enabled=definition.enabled)
                session.add(rule)
            rule.name = definition.name
            rule.description = definition.description
            rule.rule_type = definition.rule_type
            rule.severity = definition.severity
            rule.event_type = definition.match.event_type
            rule.configuration = definition.stored_configuration()
            rule.mitre_tactic = definition.mitre.tactic if definition.mitre else None
            rule.mitre_technique_id = definition.mitre.technique_id if definition.mitre else None
            rule.mitre_technique_name = (
                definition.mitre.technique_name if definition.mitre else None
            )
            synchronized.append(rule)
        await session.commit()
        logger.info("detection_rules_synchronized count=%d", len(synchronized))
        return synchronized
