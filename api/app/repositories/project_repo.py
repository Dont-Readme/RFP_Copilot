from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.draft import DraftChatMessage, DraftSection, OpenQuestion
from app.models.evaluation import EvaluationItem
from app.models.export import ExportSession
from app.models.library import ProjectAssetLink
from app.models.mapping import EvalMapping, MappingWarning
from app.models.outline import Citation, OutlineSection
from app.models.project import Project
from app.models.retrieval import DocumentChunk
from app.models.rfp import ProjectFile, RfpExtraction, RfpRequirementItem


def list_projects(db: Session) -> list[Project]:
    result = db.scalars(select(Project).order_by(Project.updated_at.desc()))
    return list(result.all())


def get_project(db: Session, project_id: int) -> Project | None:
    return db.get(Project, project_id)


def create_project(db: Session, name: str, owner_user_id: str = "local") -> Project:
    project = Project(name=name, owner_user_id=owner_user_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project: Project, name: str) -> Project:
    project.name = name
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    db.execute(delete(DocumentChunk).where(DocumentChunk.project_id == project.id))
    db.execute(delete(DraftChatMessage).where(DraftChatMessage.project_id == project.id))
    db.execute(delete(ProjectFile).where(ProjectFile.project_id == project.id))
    db.execute(delete(RfpExtraction).where(RfpExtraction.project_id == project.id))
    db.execute(delete(RfpRequirementItem).where(RfpRequirementItem.project_id == project.id))
    db.execute(delete(Citation).where(Citation.project_id == project.id))
    db.execute(delete(OutlineSection).where(OutlineSection.project_id == project.id))
    db.execute(delete(EvalMapping).where(EvalMapping.project_id == project.id))
    db.execute(delete(MappingWarning).where(MappingWarning.project_id == project.id))
    db.execute(delete(EvaluationItem).where(EvaluationItem.project_id == project.id))
    db.execute(delete(ExportSession).where(ExportSession.project_id == project.id))
    db.execute(delete(ProjectAssetLink).where(ProjectAssetLink.project_id == project.id))
    db.execute(delete(OpenQuestion).where(OpenQuestion.project_id == project.id))
    db.execute(delete(DraftSection).where(DraftSection.project_id == project.id))
    db.delete(project)
    db.commit()


def seed_projects_if_empty(db: Session) -> None:
    project_count = db.scalar(select(func.count()).select_from(Project))
    if project_count:
        return

    db.add_all(
        [
            Project(name="2026 스마트시티 제안 대응", owner_user_id="local"),
            Project(name="AI 민원 분석 플랫폼 제안서", owner_user_id="local"),
        ]
    )
    db.commit()
