from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool

from app.services.llm_service import OpenAIHealthStatus, get_llm_service, LLMService

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    ok: bool
    openai_configured: bool


class ModelHealthResponse(BaseModel):
    name: str
    ok: bool
    owner: str | None = None
    detail: str | None = None


class OpenAIHealthResponse(BaseModel):
    configured: bool
    ok: bool
    base_url: str
    active_check: bool
    models: list[ModelHealthResponse]
    detail: str | None = None


@router.get("/health")
async def healthcheck(
    llm_service: LLMService = Depends(get_llm_service),
) -> HealthResponse:
    return HealthResponse(ok=True, openai_configured=llm_service.is_configured())


@router.get("/health/openai", response_model=OpenAIHealthResponse)
async def openai_healthcheck(
    active: bool = Query(default=True),
    llm_service: LLMService = Depends(get_llm_service),
) -> OpenAIHealthResponse:
    status: OpenAIHealthStatus = await run_in_threadpool(
        llm_service.describe_health, active_check=active
    )
    return OpenAIHealthResponse(
        configured=status.configured,
        ok=status.ok,
        base_url=status.base_url,
        active_check=status.active_check,
        models=[
            ModelHealthResponse(
                name=model.name,
                ok=model.ok,
                owner=model.owner,
                detail=model.detail,
            )
            for model in status.models
        ],
        detail=status.detail,
    )
