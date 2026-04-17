from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    WarehouseIntegrationEvent,
    WarehouseItem,
    WarehouseStockBalance,
    WarehouseStockCount,
    WarehouseStockCountLine,
    WarehouseStockLedger,
)

NormalizeText = Callable[[str | None], str | None]
AssertUniqueLines = Callable[[list[int]], None]
BuildStockCountNo = Callable[[int, datetime], str]
GetOrCreateBalance = Callable[[Session, int], WarehouseStockBalance]
ConsumeIntegrationEvents = Callable[[Session], dict[str, int]]
GetStockCount = Callable[[Session, int], dict[str, object]]


def create_stock_count(
    db: Session,
    *,
    note: str | None,
    idempotency_key: str | None,
    items: list[tuple[int, float]],
    actor_id: int,
    normalize_text: NormalizeText,
    assert_unique_lines: AssertUniqueLines,
    build_stock_count_no: BuildStockCountNo,
    get_or_create_balance: GetOrCreateBalance,
    get_stock_count: GetStockCount,
) -> dict[str, object]:
    if not items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="يجب إضافة عنصر واحد على الأقل.")

    item_ids = [item_id for item_id, _ in items]
    assert_unique_lines(item_ids)

    normalized_idempotency = normalize_text(idempotency_key)
    if normalized_idempotency:
        existing = db.execute(
            select(WarehouseStockCount.id).where(WarehouseStockCount.idempotency_key == normalized_idempotency)
        ).scalar_one_or_none()
        if existing is not None:
            return get_stock_count(db, count_id=int(existing))

    fetched_items = db.execute(select(WarehouseItem).where(WarehouseItem.id.in_(item_ids))).scalars().all()
    item_map = {item.id: item for item in fetched_items}
    missing = [item_id for item_id in item_ids if item_id not in item_map]
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"الصنف #{missing[0]} غير موجود أو غير نشط.")

    count_doc = WarehouseStockCount(
        count_no=f"CNT-TMP-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
        note=normalize_text(note),
        idempotency_key=normalized_idempotency,
        status="pending",
        counted_by=actor_id,
        counted_at=datetime.now(UTC),
    )
    db.add(count_doc)
    db.flush()
    count_doc.count_no = build_stock_count_no(int(count_doc.id), count_doc.counted_at)

    for item_id, counted_quantity in items:
        counted_qty = float(counted_quantity)
        if counted_qty < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="الكمية المعدودة لا يمكن أن تكون سالبة.")
        balance = get_or_create_balance(db, int(item_id))
        system_qty = float(balance.quantity or 0)
        unit_cost = float(balance.avg_unit_cost or 0)
        variance_qty = counted_qty - system_qty
        variance_value = variance_qty * unit_cost
        db.add(
            WarehouseStockCountLine(
                count_id=int(count_doc.id),
                item_id=int(item_id),
                system_quantity=system_qty,
                counted_quantity=counted_qty,
                variance_quantity=variance_qty,
                unit_cost=unit_cost,
                variance_value=variance_value,
            )
        )

    return get_stock_count(db, count_id=int(count_doc.id))


def settle_stock_count(
    db: Session,
    *,
    count_id: int,
    actor_id: int,
    get_or_create_balance: GetOrCreateBalance,
    consume_integration_events: ConsumeIntegrationEvents,
    get_stock_count: GetStockCount,
) -> dict[str, object]:
    count_doc = db.execute(select(WarehouseStockCount).where(WarehouseStockCount.id == count_id)).scalar_one_or_none()
    if count_doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="جرد المخزون غير موجود.")
    if count_doc.status == "settled":
        return get_stock_count(db, count_id=count_id)
    if count_doc.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يمكن تسوية جرد ليس في حالة pending.")

    lines = db.execute(
        select(WarehouseStockCountLine).where(WarehouseStockCountLine.count_id == count_id)
    ).scalars().all()

    total_variance_qty = 0.0
    total_variance_value = 0.0
    for line in lines:
        variance_qty = float(line.variance_quantity or 0)
        if abs(variance_qty) < 0.0000001:
            continue

        balance = get_or_create_balance(db, int(line.item_id))
        before_qty = float(balance.quantity or 0)
        before_avg_cost = float(balance.avg_unit_cost or 0)
        after_qty = before_qty + variance_qty
        if after_qty < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="تسوية الجرد ستؤدي إلى رصيد سالب.",
            )

        if variance_qty > 0:
            unit_cost = float(line.unit_cost or before_avg_cost)
            movement_kind = "inbound"
            line_value = abs(variance_qty) * unit_cost
            after_total_value = (before_qty * before_avg_cost) + line_value
            after_avg_cost = (after_total_value / after_qty) if after_qty > 0 else 0.0
        else:
            unit_cost = before_avg_cost if before_avg_cost > 0 else float(line.unit_cost or 0)
            movement_kind = "outbound"
            line_value = -(abs(variance_qty) * unit_cost)
            after_avg_cost = 0.0 if after_qty <= 0 else before_avg_cost

        balance.quantity = after_qty
        balance.avg_unit_cost = after_avg_cost
        balance.updated_at = datetime.now(UTC)

        db.add(
            WarehouseStockLedger(
                item_id=int(line.item_id),
                movement_kind=movement_kind,
                source_type="wh_stock_count",
                source_id=int(count_doc.id),
                quantity=abs(variance_qty),
                unit_cost=unit_cost,
                line_value=line_value,
                running_avg_cost=after_avg_cost,
                balance_before=before_qty,
                balance_after=after_qty,
                note=count_doc.note or f"تسوية جرد {count_doc.count_no}",
                created_by=actor_id,
                created_at=datetime.now(UTC),
            )
        )
        total_variance_qty += variance_qty
        total_variance_value += line_value

    count_doc.status = "settled"
    count_doc.settled_by = actor_id
    count_doc.settled_at = datetime.now(UTC)

    db.add(
        WarehouseIntegrationEvent(
            event_type="warehouse_stock_count_settled",
            source_type="wh_stock_count",
            source_id=int(count_doc.id),
            payload_json=json.dumps(
                {
                    "count_id": int(count_doc.id),
                    "count_no": count_doc.count_no,
                    "total_variance_quantity": round(total_variance_qty, 4),
                    "total_variance_value": round(total_variance_value, 2),
                },
                ensure_ascii=False,
            ),
            status="pending",
        )
    )
    consume_integration_events(db)

    return get_stock_count(db, count_id=int(count_doc.id))
