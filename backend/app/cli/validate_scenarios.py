from app.simulator.loader import ScenarioLoader


def main() -> None:
    scenarios = ScenarioLoader().load()
    print(f"Validated {len(scenarios)} controlled scenario definitions.")


if __name__ == "__main__":
    main()
