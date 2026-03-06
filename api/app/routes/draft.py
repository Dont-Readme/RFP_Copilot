from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.evaluation_repo import list_evaluation_items
from app.repositories.draft_chat_repo import (
    apply_message_to_section,
    create_chat_message,
    get_chat_message,
    list_chat_messages,
    mark_message_applied,
)
from app.repositories.draft_repo import (
    ensure_project_workspace,
    get_draft_section,
    get_question,
    list_draft_sections,
    list_questions,
    replace_project_workspace,
    update_draft_section,
    update_question_status,
)
from app.repositories.outline_repo import ensure_project_outline, replace_citations_for_sections
from app.repositories.project_repo import get_project
from app.repositories.rfp_repo import ensure_rfp_extraction, list_requirement_items
from app.schemas.draft import (
    DraftChatApplyResponse,
    DraftChatMessageRead,
    DraftChatRequest,
    DraftChatResponse,
    DraftGenerateRequest,
    DraftGenerateResponse,
    DraftSectionRead,
    DraftSectionUpdate,
    OpenQuestionRead,
    OpenQuestionUpdate,
    RewriteRequest,
    RewriteResponse,
)
from app.services.chat_edit_service import ChatEditError, build_chat_edit
from app.services.draft_service import DraftGenerationError, build_generated_draft
from app.services.llm_service import LLMService, get_llm_service
from app.services.retrieval_service import (
    build_citation_payloads_from_retrieved,
    retrieve_project_chunks,
)
from app.services.rewrite_service import build_rewrite_suggestion

router = APIRouter(tags=["draft"])


@router.get("/projects/{project_id}/draft/sections", response_model=list[DraftSectionRead])
async def read_draft_sections(
    project_id: int, db: Session = Depends(get_db)
) -> list[DraftSectionRead]:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    ensure_project_workspace(db, project)
    return list_draft_sections(db, project_id)


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
    if not extraction.raw_text.strip():
        raise HTTPException(status_code=400, detail="RFP extraction is empty. Upload and extract an RFP first.")
    retrieved_by_section = {
        section.id: retrieve_project_chunks(db, project_id=project_id, query=section.title, limit=4)
        for section in sections
    }
    replace_citations_for_sections(
        db,
        project_id=project_id,
        section_ids=[section.id for section in sections],
        citations=[
            citation
            for section in sections
            for citation in build_citation_payloads_from_retrieved(
                outline_section_id=section.id,
                retrieved=retrieved_by_section.get(section.id, []),
            )
        ],
    )
    try:
        content_md, question_texts = build_generated_draft(
            project_name=project.name,
            sections=sections,
            extraction=extraction,
            requirements=requirements,
            evaluation_items=evaluation_items,
            retrieved_by_section=retrieved_by_section,
            llm_service=llm_service,
        )
    except DraftGenerationError as exc:
        raise HTTPException(status_code=502, detail=f"Draft generation failed: {exc}") from exc
    section, questions = replace_project_workspace(
        db,
        project,
        title="목차 기반 초안",
        content_md=content_md,
        questions=question_texts,
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

    extraction = ensure_rfp_extraction(db, project_id)
    requirements = list_requirement_items(db, project_id)
    evaluation_items = list_evaluation_items(db, project_id)
    if not extraction.raw_text.strip():
        raise HTTPException(status_code=400, detail="RFP extraction is empty. Upload and extract an RFP first.")

    prior_messages = list_chat_messages(db, project_id, section.id)
    retrieval_query = " ".join(
        part.strip()
        for part in [section.title, payload.selection_text or "", payload.message]
        if part.strip()
    )
    retrieved = retrieve_project_chunks(db, project_id=project_id, query=retrieval_query, limit=4)
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
            retrieved=retrieved,
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
    return DraftChatResponse(
        user_message=DraftChatMessageRead.model_validate(user_message),
        assistant_message=DraftChatMessageRead.model_validate(assistant_message),
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
