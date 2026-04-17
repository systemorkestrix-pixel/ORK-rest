from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Expense, ExpenseCostCenter
from application.financial_engine.domain.helpers import normalize_offset_limit, record_system_audit


def _normalize_cost_center_code(value: str) -> str:
    normalized = "".join(char for char in value.strip().upper() if char.isalnum() or char in {"_", "-"})
    if len(normalized) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="رمز مركز التكلفة غير صالح.")
    return normalized


def _normalize_cost_center_name(value: str) -> str:
    normalized = " ".join(value.split()).strip()
    if len(normalized) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اسم مركز التكلفة غير صالح.")
    return normalized


def list_expense_cost_centers(
    db: Session,
    *,
    include_inactive: bool = False,
    offset: int = 0,
    limit: int | None = None,
) -> list[ExpenseCostCenter]:
    safe_offset, safe_limit = normalize_offset_limit(offset=offset, limit=limit, max_limit=500)
    stmt = select(ExpenseCostCenter).order_by(ExpenseCostCenter.active.desc(), ExpenseCostCenter.name.asc())
    if not include_inactive:
        stmt = stmt.where(ExpenseCostCenter.active.is_(True))
    stmt = stmt.offset(safe_offset)
    if safe_limit is not None:
        stmt = stmt.limit(safe_limit)
    return db.execute(stmt).scalars().all()


def create_expense_cost_center(
    db: Session,
    *,
    code: str,
    name: str,
    active: bool,
    actor_id: int,
) -> ExpenseCostCenter:
    normalized_code = _normalize_cost_center_code(code)
    normalized_name = _normalize_cost_center_name(name)
    existing = db.execute(
        select(ExpenseCostCenter).where(
            or_(
                func.lower(ExpenseCostCenter.code) == normalized_code.lower(),
                func.lower(ExpenseCostCenter.name) == normalized_name.lower(),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="رمز أو اسم مركز التكلفة موجود مسبقاً.")

    center = ExpenseCostCenter(
        code=normalized_code,
        name=normalized_name,
        active=active,
        updated_at=datetime.now(UTC),
    )
    db.add(center)
    db.flush()
    record_system_audit(
        db,
        module="expenses",
        action="cost_center_created",
        entity_type="expense_cost_center",
        entity_id=center.id,
        user_id=actor_id,
        description=f"إنشاء مركز تكلفة: {center.name}.",
    )
    return center


def update_expense_cost_center(
    db: Session,
    *,
    center_id: int,
    code: str,
    name: str,
    active: bool,
    actor_id: int,
) -> ExpenseCostCenter:
    center = db.execute(select(ExpenseCostCenter).where(ExpenseCostCenter.id == center_id)).scalar_one_or_none()
    if center is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مركز التكلفة غير موجود.")

    normalized_code = _normalize_cost_center_code(code)
    normalized_name = _normalize_cost_center_name(name)
    conflict = db.execute(
        select(ExpenseCostCenter).where(
            ExpenseCostCenter.id != center_id,
            or_(
                func.lower(ExpenseCostCenter.code) == normalized_code.lower(),
                func.lower(ExpenseCostCenter.name) == normalized_name.lower(),
            ),
        )
    ).scalar_one_or_none()
    if conflict is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="رمز أو اسم مركز التكلفة مستخدم مسبقاً.")

    if not active:
        has_expenses = db.execute(
            select(func.count(Expense.id)).where(Expense.cost_center_id == center_id)
        ).scalar_one()
        if int(has_expenses or 0) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لا يمكن تعطيل مركز تكلفة مرتبط بمصروفات.",
            )

    center.code = normalized_code
    center.name = normalized_name
    center.active = active
    center.updated_at = datetime.now(UTC)
    record_system_audit(
        db,
        module="expenses",
        action="cost_center_updated",
        entity_type="expense_cost_center",
        entity_id=center.id,
        user_id=actor_id,
        description=f"تحديث مركز تكلفة: {center.name}.",
    )
    return center
