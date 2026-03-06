from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.repositories.project_repo import seed_projects_if_empty
from app.repositories.draft_repo import ensure_project_workspace
from app.repositories.outline_repo import ensure_project_outline
from app.repositories.project_repo import list_projects
from app.routes.draft import router as draft_router
from app.routes.export import router as export_router
from app.routes.health import router as health_router
from app.routes.library import router as library_router
from app.routes.mapping import router as mapping_router
from app.routes.outline import router as outline_router
from app.routes.projects import router as projects_router
from app.routes.rfp import router as rfp_router

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


def _ensure_column(
    connection,
    *,
    table_name: str,
    column_name: str,
    ddl: str,
) -> None:
    inspector = inspect(connection)
    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in existing_columns:
        return
    connection.execute(text(ddl))


def ensure_runtime_schema_compatibility() -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        existing_tables = set(inspector.get_table_names())
        if "project_files" in existing_tables:
            _ensure_column(
                connection,
                table_name="project_files",
                column_name="role",
                ddl="ALTER TABLE project_files ADD COLUMN role VARCHAR(50) NOT NULL DEFAULT 'other'",
            )
        if "rfp_extractions" in existing_tables:
            _ensure_column(
                connection,
                table_name="rfp_extractions",
                column_name="project_summary_text",
                ddl="ALTER TABLE rfp_extractions ADD COLUMN project_summary_text TEXT NOT NULL DEFAULT ''",
            )
        if "evaluation_items" in existing_tables:
            _ensure_column(
                connection,
                table_name="evaluation_items",
                column_name="score_text",
                ddl="ALTER TABLE evaluation_items ADD COLUMN score_text VARCHAR(100) NOT NULL DEFAULT ''",
            )


def initialize_app() -> None:
    settings.app_data_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema_compatibility()
    with SessionLocal() as db:
        seed_projects_if_empty(db)
        for project in list_projects(db):
            ensure_project_outline(db, project.id)
            ensure_project_workspace(db, project)
    logger.info("Application initialized")


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_app()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": "http_error", "message": str(exc.detail), "detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "code": "validation_error",
            "message": "Request validation failed",
            "detail": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "code": "internal_error",
            "message": "Unexpected server error",
            "detail": str(exc),
        },
    )


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "RFP Copilot API"}


app.include_router(health_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(library_router, prefix="/api")
app.include_router(draft_router, prefix="/api")
app.include_router(rfp_router, prefix="/api")
app.include_router(outline_router, prefix="/api")
app.include_router(mapping_router, prefix="/api")
app.include_router(export_router, prefix="/api")
