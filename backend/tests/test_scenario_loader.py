from pathlib import Path

import pytest

from app.simulator.loader import ScenarioLoader, ScenarioLoadError
from app.simulator.registry import LabTargetRegistry

VALID_SCENARIO = """
id: SCN-900
name: Test controlled scenario
description: Fixed safe action for parser validation.
risk: low
estimated_seconds: 10
targets: [employee-01, admin-server]
expected_detections: [DET-SSH-001]
steps:
  - name: Fixed failures
    action: controlled_failed_authentication
    target: employee-01
    count: 10
"""


def write_scenario(directory: Path, contents: str, name: str = "scenario.yml") -> None:
    (directory / name).write_text(contents, encoding="utf-8")


def test_built_in_scenarios_are_valid_and_complete() -> None:
    scenarios = ScenarioLoader().load()

    assert [scenario.id for scenario in scenarios] == [
        "SCN-001",
        "SCN-002",
        "SCN-003",
        "SCN-004",
        "SCN-005",
    ]
    assert scenarios[-1].expected_detections == [
        "DET-SSH-001",
        "DET-SSH-002",
        "DET-NET-001",
        "DET-PRIV-001",
        "DET-DB-001",
    ]
    assert LabTargetRegistry.ids() == {
        "web-server",
        "employee-01",
        "employee-02",
        "admin-server",
        "database",
    }


def test_duplicate_scenario_ids_are_rejected(tmp_path: Path) -> None:
    write_scenario(tmp_path, VALID_SCENARIO, "one.yml")
    write_scenario(tmp_path, VALID_SCENARIO, "two.yml")

    with pytest.raises(ScenarioLoadError, match="Duplicate scenario ID SCN-900"):
        ScenarioLoader(tmp_path).load()


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("action: controlled_failed_authentication", "action: shell"),
        ("target: employee-01", "target: 8.8.8.8"),
        ("target: employee-01", "target: google.com"),
        ("target: employee-01", "target: host.docker.internal"),
        ("count: 10", "count: 16"),
        ("count: 10", "count: 0"),
        ("count: 10", "count: 10\n    command: whoami"),
    ],
)
def test_unsafe_scenario_data_is_rejected(tmp_path: Path, old: str, new: str) -> None:
    write_scenario(tmp_path, VALID_SCENARIO.replace(old, new))

    with pytest.raises(ScenarioLoadError, match="Invalid scenario"):
        ScenarioLoader(tmp_path).load()


def test_negative_wait_and_unsupported_field_are_rejected(tmp_path: Path) -> None:
    wait_scenario = VALID_SCENARIO.replace(
        "action: controlled_failed_authentication\n    target: employee-01\n    count: 10",
        "action: wait\n    seconds: -1",
    )
    write_scenario(tmp_path, wait_scenario)
    with pytest.raises(ScenarioLoadError, match="Invalid scenario"):
        ScenarioLoader(tmp_path).load()

    (tmp_path / "scenario.yml").unlink()
    write_scenario(tmp_path, VALID_SCENARIO + "command: arbitrary\n")
    with pytest.raises(ScenarioLoadError, match="Invalid scenario"):
        ScenarioLoader(tmp_path).load()


@pytest.mark.parametrize(
    "unsafe_definition",
    [
        VALID_SCENARIO.replace("estimated_seconds: 10", "estimated_seconds: 181"),
        VALID_SCENARIO.replace(
            "  - name: Fixed failures",
            "".join(
                f"  - name: Wait {index}\n    action: wait\n    seconds: 1\n"
                for index in range(1, 13)
            )
            + "  - name: Fixed failures",
        ),
        VALID_SCENARIO.replace(
            "  - name: Fixed failures",
            "".join(
                f"  - name: Wait {index}\n    action: wait\n    seconds: 10\n"
                for index in range(1, 4)
            )
            + "  - name: Extra wait\n    action: wait\n    seconds: 1\n"
            + "  - name: Fixed failures",
        ),
    ],
)
def test_scenario_duration_step_and_cumulative_wait_limits(
    tmp_path: Path, unsafe_definition: str
) -> None:
    write_scenario(tmp_path, unsafe_definition)

    with pytest.raises(ScenarioLoadError, match="Invalid scenario"):
        ScenarioLoader(tmp_path).load()
