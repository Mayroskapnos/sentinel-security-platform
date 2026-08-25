from pathlib import Path

import yaml
from pydantic import ValidationError

from app.schemas.simulator import ScenarioDefinition, ScenarioDetail, ScenarioSummary


class ScenarioLoadError(ValueError):
    """Raised when scenario data violates the controlled simulator contract."""


class ScenarioLoader:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or Path(__file__).parent.parent / "scenarios"

    def load(self) -> list[ScenarioDefinition]:
        paths = sorted((*self.directory.glob("*.yml"), *self.directory.glob("*.yaml")))
        if not paths:
            raise ScenarioLoadError(f"No scenario definitions found in {self.directory}")
        scenarios: list[ScenarioDefinition] = []
        seen: dict[str, Path] = {}
        for path in paths:
            try:
                document = yaml.safe_load(path.read_text(encoding="utf-8"))
                scenario = ScenarioDefinition.model_validate(document)
            except (OSError, yaml.YAMLError, ValidationError) as exc:
                raise ScenarioLoadError(f"Invalid scenario {path.name}: {exc}") from exc
            if scenario.id in seen:
                raise ScenarioLoadError(
                    f"Duplicate scenario ID {scenario.id} in "
                    f"{seen[scenario.id].name} and {path.name}"
                )
            seen[scenario.id] = path
            scenarios.append(scenario)
        return scenarios

    def by_id(self, scenario_id: str) -> ScenarioDefinition | None:
        return next((item for item in self.load() if item.id == scenario_id), None)

    def summaries(self) -> list[ScenarioSummary]:
        return [
            ScenarioSummary(
                **scenario.model_dump(exclude={"steps"}), step_count=len(scenario.steps)
            )
            for scenario in self.load()
        ]

    @staticmethod
    def detail(scenario: ScenarioDefinition) -> ScenarioDetail:
        return ScenarioDetail(
            **scenario.model_dump(exclude={"steps"}),
            step_count=len(scenario.steps),
            steps=scenario.steps,
        )
