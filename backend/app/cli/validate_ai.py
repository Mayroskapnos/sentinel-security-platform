from app.investigation.config import assistant_configuration, validate_ai_configuration


def main() -> None:
    validate_ai_configuration()
    configuration = assistant_configuration()
    print(f"Validated optional Investigation Assistant configuration (mode={configuration.mode}).")


if __name__ == "__main__":
    main()
