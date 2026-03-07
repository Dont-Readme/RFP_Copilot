from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.project import Project  # noqa: E402,F401
from app.models.rfp import ProjectFile, RfpExtraction, RfpRequirementItem  # noqa: E402,F401
from app.models.evaluation import EvaluationItem  # noqa: E402,F401
from app.models.library import LibraryAsset, ProjectAssetLink  # noqa: E402,F401
from app.models.outline import Citation, OutlineSection  # noqa: E402,F401
from app.models.draft import (  # noqa: E402,F401
    DraftChatMessage,
    DraftSearchTask,
    DraftSection,
    DraftSectionPlan,
    OpenQuestion,
)
from app.models.export import ExportSession  # noqa: E402,F401
from app.models.retrieval import DocumentChunk  # noqa: E402,F401
