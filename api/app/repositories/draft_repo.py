from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.draft import DraftSection, OpenQuestion
from app.models.project import Project


def _build_default_content(project_name: str) -> str:
    return (
        f"# {project_name}\n\n"
        "## 제안 개요\n"
        "본 프로젝트의 제안 방향과 목표를 정리합니다.\n\n"
        "[확인 필요(시스템)] 실적 수치와 최신 레퍼런스를 입력해 주세요.\n\n"
        "## 수행 전략\n"
        "- 평가항목과 직접 대응하는 수행 방안을 정리합니다.\n"
        "- 보유 인력과 일정 계획의 근거를 연결합니다.\n\n"
        "[확인 필요(시스템)] 평가항목 2에 대응하는 KPI 문장을 보강해 주세요.\n"
    )


def ensure_project_workspace(db: Session, project: Project) -> None:
    existing_draft_count = db.scalar(
        select(func.count()).select_from(DraftSection).where(DraftSection.project_id == project.id)
    )
    if not existing_draft_count:
        section = DraftSection(
            project_id=project.id,
            title="기본 초안",
            content_md=_build_default_content(project.name),
            status="generated",
        )
        db.add(section)
        db.flush()
        db.add_all(
            [
                OpenQuestion(
                    id=f"oq_{project.id}_001",
                    project_id=project.id,
                    draft_section_id=section.id,
                    question_text="실적 수치와 최신 레퍼런스를 확인해 주세요.",
                    status="open",
                ),
                OpenQuestion(
                    id=f"oq_{project.id}_002",
                    project_id=project.id,
                    draft_section_id=section.id,
                    question_text="평가항목 2와 직접 대응하는 KPI 문장을 보강할지 결정해 주세요.",
                    status="open",
                ),
            ]
        )
        db.commit()


def list_draft_sections(db: Session, project_id: int) -> list[DraftSection]:
    statement = (
        select(DraftSection)
        .where(DraftSection.project_id == project_id)
        .order_by(DraftSection.updated_at.desc())
    )
    return list(db.scalars(statement).all())


def get_draft_section(db: Session, project_id: int, section_id: int) -> DraftSection | None:
    statement = select(DraftSection).where(
        DraftSection.project_id == project_id, DraftSection.id == section_id
    )
    return db.scalars(statement).first()


def update_draft_section(db: Session, section: DraftSection, content_md: str) -> DraftSection:
    section.content_md = content_md
    section.status = "edited"
    db.commit()
    db.refresh(section)
    return section


def list_questions(db: Session, project_id: int) -> list[OpenQuestion]:
    statement = (
        select(OpenQuestion)
        .where(OpenQuestion.project_id == project_id)
        .order_by(OpenQuestion.created_at.asc())
    )
    return list(db.scalars(statement).all())


def get_question(db: Session, project_id: int, question_id: str) -> OpenQuestion | None:
    statement = select(OpenQuestion).where(
        OpenQuestion.project_id == project_id, OpenQuestion.id == question_id
    )
    return db.scalars(statement).first()


def update_question_status(db: Session, question: OpenQuestion, status: str) -> OpenQuestion:
    question.status = status
    db.commit()
    db.refresh(question)
    return question


def replace_project_workspace(
    db: Session, project: Project, *, title: str, content_md: str, questions: list[str]
) -> tuple[DraftSection, list[OpenQuestion]]:
    section = (
        db.scalars(select(DraftSection).where(DraftSection.project_id == project.id)).first()
    )
    if section is None:
        section = DraftSection(
            project_id=project.id,
            title=title,
            content_md=content_md,
            status="generated",
        )
        db.add(section)
        db.flush()
    else:
        section.title = title
        section.content_md = content_md
        section.status = "generated"
        db.flush()

    db.query(OpenQuestion).filter(OpenQuestion.project_id == project.id).delete()
    created_questions: list[OpenQuestion] = []
    for index, question_text in enumerate(questions, start=1):
        question = OpenQuestion(
            id=f"oq_{project.id}_{index:03d}",
            project_id=project.id,
            draft_section_id=section.id,
            question_text=question_text,
            status="open",
        )
        db.add(question)
        created_questions.append(question)

    db.commit()
    db.refresh(section)
    for question in created_questions:
        db.refresh(question)
    return section, created_questions
