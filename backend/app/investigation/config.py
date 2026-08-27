from dataclasses import dataclass
from typing import Literal

from app.core.config import Settings, get_settings

AssistantMode = Literal["disabled", "mock", "configured", "unavailable"]
SUPPORTED_PROVIDERS = {"mock", "openai"}


@dataclass(frozen=True)
class AssistantConfiguration:
    enabled: bool
    mode: AssistantMode
    provider: str | None
    provider_label: str
    model: str | None
    external: bool
    message: str


def assistant_configuration(settings: Settings | None = None) -> AssistantConfiguration:
    settings = settings or get_settings()
    provider = settings.sentinel_ai_provider.strip().lower()
    model = settings.sentinel_ai_model.strip()
    if not settings.sentinel_ai_enabled:
        return AssistantConfiguration(
            enabled=False,
            mode="disabled",
            provider=provider or None,
            provider_label="Investigation Assistant",
            model=model or None,
            external=False,
            message="AI analysis is not configured for this SENTINEL deployment.",
        )
    if provider not in SUPPORTED_PROVIDERS:
        return AssistantConfiguration(
            enabled=False,
            mode="unavailable",
            provider=provider or None,
            provider_label="Investigation Assistant",
            model=model or None,
            external=False,
            message="The configured Investigation Assistant provider is unsupported.",
        )
    if provider == "mock":
        return AssistantConfiguration(
            enabled=True,
            mode="mock",
            provider="mock",
            provider_label="Mock Investigation Provider",
            model=model or "sentinel-mock-v1",
            external=False,
            message="Deterministic local mock analysis is available; no data leaves SENTINEL.",
        )
    if not settings.sentinel_ai_api_key or not model:
        return AssistantConfiguration(
            enabled=False,
            mode="unavailable",
            provider="openai",
            provider_label="OpenAI",
            model=model or None,
            external=True,
            message="OpenAI analysis requires both a model and API key.",
        )
    return AssistantConfiguration(
        enabled=True,
        mode="configured",
        provider="openai",
        provider_label="OpenAI",
        model=model,
        external=True,
        message="External AI analysis is configured.",
    )


def validate_ai_configuration(settings: Settings | None = None) -> None:
    configuration = assistant_configuration(settings)
    if (settings or get_settings()).sentinel_ai_enabled and not configuration.enabled:
        raise ValueError(configuration.message)
