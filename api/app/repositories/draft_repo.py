from __future__ import annotations

import json

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.draft import (
    DraftChatMessage,
    DraftSearchTask,
    DraftSection,
    DraftSectionPlan,
    OpenQuestion,
)
from app.models.project import Project
from app.services.review_item_service import ReviewItemPayload


def _build_default_content(project_name: str) -> str:
    return (
        f"# {project_name}\n\n"
        "초안이 아직 생성되지 않았습니다.\n\n"
        "1. RFP 추출 결과를 확인합니다.\n"
        "2. 목차를 정의합니다.\n"
        "3. Draft Workspace에서 초안 생성을 실행합니다.\n"
    )


def ensure_project_workspace(db: Session, project: Project) -> None:
    existing_draft_count = db.scalar(
        select(func.count()).select_from(DraftSection).where(DraftSection.project_id == project.id)
    )
    if not existing_draft_count:
        section = DraftSection(
            project_id=project.id,
            title="초안 준비 상태",
            content_md=_build_default_content(project.name),
            status="ready",
        )
        db.add(section)
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


def list_section_plans(db: Session, project_id: int) -> list[DraftSectionPlan]:
    statement = (
        select(DraftSectionPlan)
        .where(DraftSectionPlan.project_id == project_id)
        .order_by(DraftSectionPlan.outline_section_id.asc(), DraftSectionPlan.id.asc())
    )
    return list(db.scalars(statement).all())


def replace_section_plans(
    db: Session,
    *,
    project_id: int,
    plans: list[dict],
) -> list[DraftSectionPlan]:
    db.execute(delete(DraftSearchTask).where(DraftSearchTask.project_id == project_id))
    db.execute(delete(DraftSectionPlan).where(DraftSectionPlan.project_id == project_id))

    created_plans: list[DraftSectionPlan] = []
    for plan in plans:
        section_plan = DraftSectionPlan(
            project_id=project_id,
            outline_section_id=plan["outline_section_id"],
            heading_text=plan["heading_text"],
            section_goal=plan.get("section_goal", ""),
            assigned_requirement_ids_json=json.dumps(plan.get("assigned_requirement_ids", []), ensure_ascii=False),
            assigned_requirement_text=plan.get("assigned_requirement_text", ""),
            assigned_evaluation_ids_json=json.dumps(plan.get("assigned_evaluation_ids", []), ensure_ascii=False),
            assigned_evaluation_text=plan.get("assigned_evaluation_text", ""),
            assigned_asset_ids_json=json.dumps(plan.get("assigned_asset_ids", []), ensure_ascii=False),
            assigned_company_text=plan.get("assigned_company_text", ""),
            draft_guidance=plan.get("draft_guidance", ""),
            needs_search=bool(plan.get("needs_search", False)),
            search_topics_json=json.dumps(plan.get("search_topics", []), ensure_ascii=False),
            status=plan.get("status", "planned"),
        )
        db.add(section_plan)
        db.flush()
        created_plans.append(section_plan)

        for task in plan.get("search_tasks", []):
            db.add(
                DraftSearchTask(
                    project_id=project_id,
                    outline_section_id=plan["outline_section_id"],
                    topic=task["topic"],
                    reason=task.get("reason", ""),
                    freshness_required=bool(task.get("freshness_required", True)),
                    expected_output=task.get("expected_output", ""),
                    query_text=task.get("query_text", ""),
                    status=task.get("status", "pending"),
                    searched_on=task.get("searched_on", ""),
                )
            )

    db.commit()
    for section_plan in created_plans:
        db.refresh(section_plan)
    return created_plans


def update_section_plan_status(
    db: Session,
    *,
    project_id: int,
    outline_section_id: int,
    status: str,
) -> DraftSectionPlan | None:
    statement = select(DraftSectionPlan).where(
        DraftSectionPlan.project_id == project_id,
        DraftSectionPlan.outline_section_id == outline_section_id,
    )
    section_plan = db.scalars(statement).first()
    if section_plan is None:
        return None
    section_plan.status = status
    db.commit()
    db.refresh(section_plan)
    return section_plan


def list_search_tasks(
    db: Session,
    *,
    project_id: int,
    outline_section_id: int | None = None,
) -> list[DraftSearchTask]:
    statement = (
        select(DraftSearchTask)
        .where(DraftSearchTask.project_id == project_id)
        .order_by(DraftSearchTask.outline_section_id.asc(), DraftSearchTask.id.asc())
    )
    if outline_section_id is not None:
        statement = statement.where(DraftSearchTask.outline_section_id == outline_section_id)
    return list(db.scalars(statement).all())


def update_search_task(
    db: Session,
    *,
    task: DraftSearchTask,
    status: str,
    query_text: str | None = None,
    searched_on: str | None = None,
) -> DraftSearchTask:
    task.status = status
    if query_text is not None:
        task.query_text = query_text
    if searched_on is not None:
        task.searched_on = searched_on
    db.commit()
    db.refresh(task)
    return task


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


def append_review_items(
    db: Session,
    *,
    project_id: int,
    draft_section_id: int,
    review_items: list[ReviewItemPayload],
) -> list[OpenQuestion]:
    if not review_items:
        return []

    existing_items = list_questions(db, project_id)
    existing_by_key = {
        (
            (question.section_heading_text or "").strip(),
            question.question_text.strip(),
            (question.category or "").strip(),
        ): question
        for question in existing_items
    }

    next_index = len(existing_items) + 1
    changed_items: list[OpenQuestion] = []
    for review_item in review_items:
        section_heading_text = review_item.section_heading_text.strip()
        question_text = review_item.question_text.strip()
        category = review_item.category.strip()
        if not section_heading_text or not question_text:
            continue

        item_key = (section_heading_text, question_text, category)
        existing_item = existing_by_key.get(item_key)
        if existing_item is not None:
            if existing_item.status != "open":
                existing_item.status = "open"
                changed_items.append(existing_item)
            continue

        question = OpenQuestion(
            id=f"oq_{project_id}_{next_index:03d}",
            project_id=project_id,
            draft_section_id=draft_section_id,
            outline_section_id=review_item.outline_section_id,
            section_heading_text=section_heading_text,
            question_text=question_text,
            category=category,
            severity=review_item.severity,
            source_agent=review_item.source_agent,
            status="open",
        )
        db.add(question)
        changed_items.append(question)
        existing_by_key[item_key] = question
        next_index += 1

    if not changed_items:
        return []

    db.commit()
    for question in changed_items:
        db.refresh(question)
    return changed_items


def replace_project_workspace(
    db: Session,
    project: Project,
    *,
    title: str,
    content_md: str,
    review_items: list[ReviewItemPayload],
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

    db.execute(delete(DraftChatMessage).where(DraftChatMessage.project_id == project.id))
    db.query(OpenQuestion).filter(OpenQuestion.project_id == project.id).delete()
    created_questions: list[OpenQuestion] = []
    for index, review_item in enumerate(review_items, start=1):
        question = OpenQuestion(
            id=f"oq_{project.id}_{index:03d}",
            project_id=project.id,
            draft_section_id=section.id,
            outline_section_id=review_item.outline_section_id,
            section_heading_text=review_item.section_heading_text.strip(),
            question_text=review_item.question_text.strip(),
            category=review_item.category,
            severity=review_item.severity,
            source_agent=review_item.source_agent,
            status="open",
        )
        db.add(question)
        created_questions.append(question)

    db.commit()
    db.refresh(section)
    for question in created_questions:
        db.refresh(question)
    return section, created_questions
