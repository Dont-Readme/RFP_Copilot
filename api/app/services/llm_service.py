from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import TypeVar, cast

from openai import OpenAI
from pydantic import BaseModel

from app.core.config import get_settings

StructuredResponseT = TypeVar("StructuredResponseT", bound=BaseModel)


@dataclass(frozen=True)
class ModelHealthStatus:
    name: str
    ok: bool
    owner: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class OpenAIHealthStatus:
    configured: bool
    ok: bool
    base_url: str
    active_check: bool
    models: tuple[ModelHealthStatus, ...]
    detail: str | None = None


class LLMConfigurationError(RuntimeError):
    pass


class LLMResponseError(RuntimeError):
    pass


class LLMService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = (
            OpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
                timeout=self.settings.openai_timeout_seconds,
            )
            if self.settings.openai_api_key
            else None
        )

    def is_configured(self) -> bool:
        return bool(self.settings.openai_api_key)

    def require_client(self) -> OpenAI:
        if self._client is None:
            raise LLMConfigurationError("OPENAI_API_KEY is not set")
        return self._client

    def configured_models(self) -> tuple[str, ...]:
        models = [
            self.settings.openai_model_extraction,
            self.settings.openai_model_draft,
            self.settings.openai_model_mapping,
        ]
        return tuple(dict.fromkeys(model.strip() for model in models if model.strip()))

    def parse_chat_completion(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_format: type[StructuredResponseT],
        max_completion_tokens: int = 2500,
    ) -> StructuredResponseT:
        try:
            completion = self.require_client().beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=response_format,
                temperature=0,
                max_completion_tokens=max_completion_tokens,
            )
        except Exception as exc:
            raise LLMResponseError(f"{exc.__class__.__name__}: {exc}") from exc
        if not completion.choices:
            raise LLMResponseError("OpenAI returned no choices")

        message = completion.choices[0].message
        parsed = getattr(message, "parsed", None)
        if parsed is not None:
            return cast(StructuredResponseT, parsed)

        refusal = getattr(message, "refusal", None)
        if refusal:
            raise LLMResponseError(f"OpenAI refused the request: {refusal}")

        content = getattr(message, "content", None)
        if content:
            raise LLMResponseError(f"OpenAI returned an unparseable response: {content}")

        raise LLMResponseError("OpenAI did not return a parseable structured response")

    def describe_health(self, *, active_check: bool = False) -> OpenAIHealthStatus:
        if not self.is_configured():
            return OpenAIHealthStatus(
                configured=False,
                ok=False,
                base_url=self.settings.openai_base_url,
                active_check=active_check,
                models=tuple(
                    ModelHealthStatus(name=model, ok=False, detail="OPENAI_API_KEY is not set")
                    for model in self.configured_models()
                ),
                detail="OPENAI_API_KEY is not set",
            )

        if not active_check:
            return OpenAIHealthStatus(
                configured=True,
                ok=True,
                base_url=self.settings.openai_base_url,
                active_check=False,
                models=tuple(ModelHealthStatus(name=model, ok=True) for model in self.configured_models()),
                detail="Configuration loaded",
            )

        model_statuses: list[ModelHealthStatus] = []
        for model in self.configured_models():
            try:
                response = self._client.models.retrieve(model) if self._client is not None else None
                model_statuses.append(
                    ModelHealthStatus(
                        name=model,
                        ok=True,
                        owner=getattr(response, "owned_by", None),
                    )
                )
            except Exception as exc:
                model_statuses.append(
                    ModelHealthStatus(
                        name=model,
                        ok=False,
                        detail=f"{exc.__class__.__name__}: {exc}",
                    )
                )

        overall_ok = all(status.ok for status in model_statuses)
        detail = "OpenAI model access verified" if overall_ok else "One or more model checks failed"
        return OpenAIHealthStatus(
            configured=True,
            ok=overall_ok,
            base_url=self.settings.openai_base_url,
            active_check=True,
            models=tuple(model_statuses),
            detail=detail,
        )


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    return LLMService()
