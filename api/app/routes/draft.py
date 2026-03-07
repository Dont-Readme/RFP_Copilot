from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.evaluation_repo import list_evaluation_items
from app.repositories.library_repo import list_project_assets
from app.repositories.draft_chat_repo import (
    apply_message_to_section,
    create_chat_message,
    get_chat_message,
    list_chat_messages,
    mark_message_applied,
)
from app.repositories.draft_repo import (
    append_review_items,
    ensure_project_workspace,
    get_draft_section,
    get_question,
    list_draft_sections,
    list_questions,
    replace_project_workspace,
    update_draft_section,
    update_question_status,
)
from app.repositories.outline_repo import ensure_project_outline
from app.repositories.project_repo import get_project
from app.repositories.rfp_repo import ensure_rfp_extraction, list_requirement_items
from app.schemas.draft import (
    DraftChatApplyResponse,
    DraftChatMessageRead,
    DraftChatRequest,
    DraftChatResponse,
    DraftGenerateRequest,
    DraftGenerateResponse,
    DraftPlanResponse,
    DraftSectionPlanRead,
    DraftSectionRead,
    DraftSectionUpdate,
    OpenQuestionRead,
    OpenQuestionUpdate,
    RewriteRequest,
    RewriteResponse,
)
from app.services.draft_plan_service import (
    DraftPlanResult,
    DraftSectionPlan,
    build_draft_plan,
)
from app.services.chat_edit_service import ChatEditError, build_chat_edit
from app.services.draft_pipeline_service import run_draft_pipeline
from app.services.draft_service import DraftGenerationError
from app.services.llm_service import LLMService, get_llm_service
from app.services.review_item_service import (
    ReviewItemPayload,
    build_heading_text,
    build_review_items_for_section,
    infer_fallback_review_items,
    locate_heading_for_offset,
    merge_review_payloads,
)
from app.services.rewrite_service import build_rewrite_suggestion

router = APIRouter(tags=["draft"])

def _build_plan_response(project_id: int, result: DraftPlanResult) -> DraftPlanResponse:
    def build_section(section_plan: DraftSectionPlan) -> DraftSectionPlanRead:
        return DraftSectionPlanRead(
            section_id=section_plan.section.id,
            heading_text=section_plan.heading_text,
            depth=section_plan.section.depth,
            heading_path=section_plan.heading_path,
            section_goal=section_plan.section_goal,
            assigned_requirement_titles=[
                (requirement.name or requirement.requirement_no or "요구사항").strip()
                for requirement in section_plan.assigned_requirements
            ],
            assigned_evaluation_titles=[
                (item.item or "평가항목").strip()
                for item in section_plan.assigned_evaluation_items
            ],
            assigned_company_facts=section_plan.assigned_company_facts,
            search_topics=[task.topic for task in section_plan.search_tasks],
            status=section_plan.status,
        )

    return DraftPlanResponse(
        project_id=project_id,
        ready=result.ready,
        warnings=result.warnings,
        sections=[build_section(section_plan) for section_plan in result.sections],
    )


@router.get("/projects/{project_id}/draft/sections", response_model=list[DraftSectionRead])
async def read_draft_sections(
    project_id: int, db: Session = Depends(get_db)
) -> list[DraftSectionRead]:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    ensure_project_workspace(db, project)
    return list_draft_sections(db, project_id)


@router.get("/projects/{project_id}/draft/plan", response_model=DraftPlanResponse)
async def read_draft_plan(
    project_id: int, db: Session = Depends(get_db)
) -> DraftPlanResponse:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    sections = ensure_project_outline(db, project_id)
    extraction = ensure_rfp_extraction(db, project_id)
    requirements = list_requirement_items(db, project_id)
    evaluation_items = list_evaluation_items(db, project_id)
    assets = list_project_assets(db, project_id)
    plan = build_draft_plan(
        project_name=project.name,
        sections=sections,
        extraction=extraction,
        requirements=requirements,
        evaluation_items=evaluation_items,
        assets=assets,
    )
    return _build_plan_response(project_id, plan)


@router.post("/projects/{project_id}/draft/generate", response_model=DraftGenerateResponse)
async def generate_draft(
    project_id: int,
    payload: DraftGenerateRequest,
    db: Session = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service),
) -> DraftGenerateResponse:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    if payload.mode != "full":
        raise HTTPException(status_code=400, detail=f"Unsupported draft mode: {payload.mode}")

    sections = ensure_project_outline(db, project_id)
    extraction = ensure_rfp_extraction(db, project_id)
    requirements = list_requirement_items(db, project_id)
    evaluation_items = list_evaluation_items(db, project_id)
    assets = list_project_assets(db, project_id)
    plan = build_draft_plan(
        project_name=project.name,
        sections=sections,
        extraction=extraction,
        requirements=requirements,
        evaluation_items=evaluation_items,
        assets=assets,
    )
    if not plan.ready:
        detail = " ".join(plan.warnings) or "Draft generation prerequisites are not ready."
        raise HTTPException(status_code=400, detail=detail)

    try:
        content_md, review_items, _ = run_draft_pipeline(
            db=db,
            project=project,
            sections=sections,
            extraction=extraction,
            requirements=requirements,
            evaluation_items=evaluation_items,
            assets=assets,
            llm_service=llm_service,
        )
    except DraftGenerationError as exc:
        raise HTTPException(status_code=502, detail=f"Draft generation failed: {exc}") from exc
    section, questions = replace_project_workspace(
        db,
        project,
        title="목차 기반 초안",
        content_md=content_md,
        review_items=review_items,
    )
    return DraftGenerateResponse(
        section=DraftSectionRead.model_validate(section),
        questions=[OpenQuestionRead.model_validate(question) for question in questions],
    )


@router.patch(
    "/projects/{project_id}/draft/sections/{section_id}",
    response_model=DraftSectionRead,
)
async def update_draft_section_endpoint(
    project_id: int,
    section_id: int,
    payload: DraftSectionUpdate,
    db: Session = Depends(get_db),
) -> DraftSectionRead:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    section = get_draft_section(db, project_id, section_id)
    if section is None:
        raise HTTPException(status_code=404, detail=f"Draft section {section_id} not found")
    return update_draft_section(db, section, payload.content_md)


@router.get("/projects/{project_id}/questions", response_model=list[OpenQuestionRead])
async def read_questions(
    project_id: int, db: Session = Depends(get_db)
) -> list[OpenQuestionRead]:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    ensure_project_workspace(db, project)
    return list_questions(db, project_id)


@router.patch("/projects/{project_id}/questions/{question_id}", response_model=OpenQuestionRead)
async def update_question_endpoint(
    project_id: int,
    question_id: str,
    payload: OpenQuestionUpdate,
    db: Session = Depends(get_db),
) -> OpenQuestionRead:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    question = get_question(db, project_id, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail=f"Question {question_id} not found")
    return update_question_status(db, question, payload.status)


@router.get(
    "/projects/{project_id}/draft/sections/{section_id}/chat",
    response_model=list[DraftChatMessageRead],
)
async def read_draft_chat_messages(
    project_id: int,
    section_id: int,
    db: Session = Depends(get_db),
) -> list[DraftChatMessageRead]:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    section = get_draft_section(db, project_id, section_id)
    if section is None:
        raise HTTPException(status_code=404, detail=f"Draft section {section_id} not found")
    return [DraftChatMessageRead.model_validate(message) for message in list_chat_messages(db, project_id, section.id)]


@router.post("/projects/{project_id}/draft/chat", response_model=DraftChatResponse)
async def create_draft_chat_turn(
    project_id: int,
    payload: DraftChatRequest,
    db: Session = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service),
) -> DraftChatResponse:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    section = get_draft_section(db, project_id, payload.section_id)
    if section is None:
        raise HTTPException(status_code=404, detail=f"Draft section {payload.section_id} not found")
    outline_sections = ensure_project_outline(db, project_id)

    extraction = ensure_rfp_extraction(db, project_id)
    requirements = list_requirement_items(db, project_id)
    evaluation_items = list_evaluation_items(db, project_id)
    if not extraction.raw_text.strip():
        raise HTTPException(status_code=400, detail="RFP extraction is empty. Upload and extract an RFP first.")

    prior_messages = list_chat_messages(db, project_id, section.id)
    try:
        generated = build_chat_edit(
            llm_service=llm_service,
            project_name=project.name,
            draft_section=section,
            extraction=extraction,
            requirements=requirements,
            evaluation_items=evaluation_items,
            user_message=payload.message.strip(),
            prior_messages=prior_messages,
            selection_start=payload.selection_start,
            selection_end=payload.selection_end,
        )
    except ChatEditError as exc:
        raise HTTPException(status_code=502, detail=f"Draft chat failed: {exc}") from exc

    has_selection = bool((payload.selection_text or "").strip())
    apply_mode = "replace_selection" if has_selection and generated.suggestion_text.strip() else "advice_only"
    user_message = create_chat_message(
        db,
        project_id=project_id,
        draft_section_id=section.id,
        role="user",
        message_text=payload.message.strip(),
        apply_mode="advice_only",
        selection_start=payload.selection_start,
        selection_end=payload.selection_end,
        selection_text=payload.selection_text.strip() if payload.selection_text else None,
    )
    assistant_message = create_chat_message(
        db,
        project_id=project_id,
        draft_section_id=section.id,
        role="assistant",
        message_text=generated.assistant_reply.strip() or "수정 제안을 준비했습니다.",
        suggestion_text=generated.suggestion_text.strip() or None,
        apply_mode=apply_mode,
        selection_start=payload.selection_start,
        selection_end=payload.selection_end,
        selection_text=payload.selection_text.strip() if payload.selection_text else None,
    )
    review_items: list[ReviewItemPayload] = []
    section_heading_text = locate_heading_for_offset(
        content=section.content_md,
        sections=outline_sections,
        offset=payload.selection_start,
    )
    matched_outline_section = next(
        (
            outline_section
            for outline_section in outline_sections
            if build_heading_text(outline_section) == section_heading_text
        ),
        None,
    )
    if section_heading_text:
        review_items = merge_review_payloads(
            build_review_items_for_section(
                outline_section_id=matched_outline_section.id if matched_outline_section else None,
                section_heading_text=section_heading_text,
                item_texts=generated.system_review_items,
                category="missing_evidence",
                severity="medium",
                source_agent="assistant",
            ),
            build_review_items_for_section(
                outline_section_id=matched_outline_section.id if matched_outline_section else None,
                section_heading_text=section_heading_text,
                item_texts=infer_fallback_review_items(
                    section_heading_text=section_heading_text,
                    summary_text=extraction.project_summary_text,
                ),
                category="missing_evidence",
                severity="medium",
                source_agent="system",
            ),
        )

    created_review_items = append_review_items(
        db,
        project_id=project_id,
        draft_section_id=section.id,
        review_items=review_items,
    )
    return DraftChatResponse(
        user_message=DraftChatMessageRead.model_validate(user_message),
        assistant_message=DraftChatMessageRead.model_validate(assistant_message),
        review_items=[OpenQuestionRead.model_validate(item) for item in created_review_items],
    )


@router.post(
    "/projects/{project_id}/draft/chat/{message_id}/apply",
    response_model=DraftChatApplyResponse,
)
async def apply_draft_chat_message(
    project_id: int,
    message_id: int,
    db: Session = Depends(get_db),
) -> DraftChatApplyResponse:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    message = get_chat_message(db, project_id, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail=f"Draft chat message {message_id} not found")
    if message.role != "assistant":
        raise HTTPException(status_code=400, detail="Only assistant messages can be applied")
    if message.apply_mode != "replace_selection" or not message.suggestion_text:
        raise HTTPException(status_code=400, detail="This chat message does not contain an applicable edit")

    section = get_draft_section(db, project_id, message.draft_section_id)
    if section is None:
        raise HTTPException(status_code=404, detail=f"Draft section {message.draft_section_id} not found")

    try:
        updated_section = apply_message_to_section(db, message=message, section=section)
        updated_message = mark_message_applied(db, message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return DraftChatApplyResponse(
        section=DraftSectionRead.model_validate(updated_section),
        message=DraftChatMessageRead.model_validate(updated_message),
    )


@router.post("/projects/{project_id}/rewrite", response_model=RewriteResponse)
async def rewrite_selection(
    project_id: int, payload: RewriteRequest, db: Session = Depends(get_db)
) -> RewriteResponse:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    section = get_draft_section(db, project_id, payload.section_id)
    if section is None:
        raise HTTPException(status_code=404, detail=f"Draft section {payload.section_id} not found")
    replacement_text, diff_hint = build_rewrite_suggestion(
        payload.selected_text, payload.instruction
    )
    return RewriteResponse(replacement_text=replacement_text, diff_hint=diff_hint)
