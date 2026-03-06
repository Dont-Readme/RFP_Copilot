from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.evaluation import EvaluationItem

DEFAULT_EVALUATION_ITEMS = [
    {
        "code": "EV-01",
        "title": "제안 개요 적합성",
        "description": "제안 개요, 목표, 범위 이해도를 평가합니다.",
        "weight": 0.35,
    },
    {
        "code": "EV-02",
        "title": "수행 전략 구체성",
        "description": "수행 전략, KPI, 실행 계획의 구체성을 평가합니다.",
        "weight": 0.4,
    },
    {
        "code": "EV-03",
        "title": "근거 자료 충실성",
        "description": "실적, 인력, 일정 등 근거 자료의 충실성을 평가합니다.",
        "weight": 0.25,
    },
]


def list_evaluation_items(db: Session, project_id: int) -> list[EvaluationItem]:
    statement = (
        select(EvaluationItem)
        .where(EvaluationItem.project_id == project_id)
        .order_by(EvaluationItem.created_at.asc(), EvaluationItem.id.asc())
    )
    return list(db.scalars(statement).all())


def replace_evaluation_items(db: Session, project_id: int, items: list[dict]) -> list[EvaluationItem]:
    db.execute(delete(EvaluationItem).where(EvaluationItem.project_id == project_id))
    db.add_all(
        [
            EvaluationItem(
                project_id=project_id,
                code=item["code"],
                title=item["title"],
                score_text=item.get("score_text", ""),
                description=item.get("description", ""),
                weight=item.get("weight"),
            )
            for item in items
        ]
    )
    db.commit()
    return list_evaluation_items(db, project_id)


def ensure_default_evaluation_items(db: Session, project_id: int) -> list[EvaluationItem]:
    existing = list_evaluation_items(db, project_id)
    if existing:
        return existing
    return replace_evaluation_items(db, project_id, DEFAULT_EVALUATION_ITEMS)
