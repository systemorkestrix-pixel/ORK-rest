from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FinancialTransaction, ShiftClosure
from application.financial_engine.domain.helpers import (
    normalize_offset_limit,
    normalize_optional_text,
    record_system_audit,
)


def close_cash_shift(
    db: Session,
    *,
    closed_by: int,
    opening_cash: float,
    actual_cash: float,
    note: str | None,
    financial_snapshot,
) -> ShiftClosure:
    business_date = datetime.now().date()
    existing = db.execute(select(ShiftClosure).where(ShiftClosure.business_date == business_date)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Shift already closed for this business date.')

    safe_opening_cash = max(0.0, float(opening_cash))
    safe_actual_cash = max(0.0, float(actual_cash))

    db.flush()
    snapshot = financial_snapshot(db, start_date=business_date, end_date=business_date)
    sales_total = float(snapshot['sales'])
    refunds_total = float(snapshot['refunds'])
    expenses_total = float(snapshot['expenses'])
    transactions_count = int(snapshot['cashbox_transactions_count'])
    cash_in = float(snapshot['cash_in'])
    cash_out = float(snapshot['cash_out'])
    if transactions_count > 0:
        expected_cash = safe_opening_cash + cash_in - cash_out
    else:
        expected_cash = safe_opening_cash + sales_total - refunds_total - expenses_total
        business_start = datetime.combine(business_date, datetime.min.time(), tzinfo=UTC)
        business_end = business_start + timedelta(days=1)
        transactions_count = int(
            db.execute(
                select(func.count(FinancialTransaction.id)).where(
                    FinancialTransaction.created_at >= business_start,
                    FinancialTransaction.created_at < business_end,
                )
            ).scalar_one()
            or 0
        )
    variance = safe_actual_cash - expected_cash

    closure = ShiftClosure(
        business_date=business_date,
        opening_cash=safe_opening_cash,
        sales_total=sales_total,
        refunds_total=refunds_total,
        expenses_total=expenses_total,
        expected_cash=expected_cash,
        actual_cash=safe_actual_cash,
        variance=variance,
        transactions_count=transactions_count,
        note=normalize_optional_text(note),
        closed_by=closed_by,
        closed_at=datetime.now(UTC),
    )
    db.add(closure)
    db.flush()
    record_system_audit(
        db,
        module='financial',
        action='close_shift',
        entity_type='shift_closure',
        entity_id=closure.id,
        user_id=closed_by,
        description=(
            f'Closed shift {business_date.isoformat()} | '
            f'Expected cash: {expected_cash:.2f} | Actual cash: {safe_actual_cash:.2f} | '
            f'Variance: {variance:.2f}.'
        ),
    )
    return closure


def list_shift_closures(
    db: Session,
    *,
    offset: int = 0,
    limit: int | None = None,
) -> list[ShiftClosure]:
    safe_offset, safe_limit = normalize_offset_limit(offset=offset, limit=limit, max_limit=500)
    stmt = (
        select(ShiftClosure)
        .order_by(ShiftClosure.business_date.desc(), ShiftClosure.closed_at.desc())
        .offset(safe_offset)
    )
    if safe_limit is not None:
        stmt = stmt.limit(safe_limit)
    return db.execute(stmt).scalars().all()
