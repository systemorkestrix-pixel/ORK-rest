from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    WarehouseInboundItem,
    WarehouseInboundVoucher,
    WarehouseIntegrationEvent,
    WarehouseItem,
    WarehouseStockBalance,
    WarehouseStockLedger,
    WarehouseSupplier,
    WarehouseSupplierItem,
)


NormalizeText = Callable[[str | None], str | None]
AssertUniqueLines = Callable[[list[int]], None]
BuildInboundNo = Callable[[int, datetime], str]
GetOrCreateBalance = Callable[[Session, int], WarehouseStockBalance]
ConsumeIntegrationEvents = Callable[[Session], dict[str, int]]
GetInboundVoucher = Callable[[Session, int], dict[str, object]]


def create_inbound_voucher(
    db: Session,
    *,
    supplier_id: int,
    reference_no: str | None,
    note: str | None,
    idempotency_key: str | None,
    items: list[tuple[int, float, float]],
    actor_id: int,
    normalize_text: NormalizeText,
    assert_unique_lines: AssertUniqueLines,
    build_inbound_no: BuildInboundNo,
    get_or_create_balance: GetOrCreateBalance,
    consume_integration_events: ConsumeIntegrationEvents,
    get_inbound_voucher: GetInboundVoucher,
) -> dict[str, object]:
    if not items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="يجب إضافة عنصر واحد على الأقل.")

    item_ids = [item_id for item_id, _, _ in items]
    assert_unique_lines(item_ids)

    supplier = db.execute(
        select(WarehouseSupplier).where(WarehouseSupplier.id == supplier_id, WarehouseSupplier.active.is_(True))
    ).scalar_one_or_none()
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المورد غير موجود أو غير نشط.")

    normalized_idempotency = normalize_text(idempotency_key)
    if normalized_idempotency:
        existing = db.execute(
            select(WarehouseInboundVoucher.id).where(
                WarehouseInboundVoucher.idempotency_key == normalized_idempotency
            )
        ).scalar_one_or_none()
        if existing is not None:
            return get_inbound_voucher(db, int(existing))

    fetched_items = db.execute(
        select(WarehouseItem).where(WarehouseItem.id.in_(item_ids), WarehouseItem.active.is_(True))
    ).scalars().all()
    item_map = {item.id: item for item in fetched_items}
    missing = [item_id for item_id in item_ids if item_id not in item_map]
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"الصنف #{missing[0]} غير موجود أو غير نشط.")

    allowed_item_ids = set(
        int(item_id)
        for item_id in db.execute(
            select(WarehouseSupplierItem.item_id).where(WarehouseSupplierItem.supplier_id == supplier_id)
        ).scalars().all()
    )
    if not allowed_item_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن إنشاء سند وارد لمورد بلا أصناف مرتبطة.",
        )

    unlinked_item_ids = [item_id for item_id in item_ids if item_id not in allowed_item_ids]
    if unlinked_item_ids:
        first_unlinked = int(unlinked_item_ids[0])
        item_name = item_map[first_unlinked].name if first_unlinked in item_map else f"#{first_unlinked}"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"الصنف '{item_name}' غير مرتبط بهذا المورد.",
        )

    voucher = WarehouseInboundVoucher(
        voucher_no=f"IN-TMP-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
        supplier_id=supplier_id,
        reference_no=normalize_text(reference_no),
        note=normalize_text(note),
        idempotency_key=normalized_idempotency,
        received_by=actor_id,
        posted_at=datetime.now(UTC),
    )
    db.add(voucher)
    db.flush()
    voucher.voucher_no = build_inbound_no(int(voucher.id), voucher.posted_at)

    total_qty = 0.0
    total_cost = 0.0
    for item_id, quantity, unit_cost in items:
        if quantity <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="الكمية يجب أن تكون أكبر من صفر.")
        if unit_cost < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="سعر الوحدة لا يمكن أن يكون سالبا.")

        balance = get_or_create_balance(db, int(item_id))
        before = float(balance.quantity or 0)
        before_avg_cost = float(balance.avg_unit_cost or 0)
        received_qty = float(quantity)
        received_unit_cost = float(unit_cost)
        after = before + received_qty
        after_total_value = (before * before_avg_cost) + (received_qty * received_unit_cost)
        after_avg_cost = (after_total_value / after) if after > 0 else 0.0
        balance.quantity = after
        balance.avg_unit_cost = after_avg_cost
        balance.updated_at = datetime.now(UTC)

        db.add(
            WarehouseInboundItem(
                voucher_id=int(voucher.id),
                item_id=int(item_id),
                quantity=received_qty,
                unit_cost=received_unit_cost,
            )
        )
        db.add(
            WarehouseStockLedger(
                item_id=int(item_id),
                movement_kind="inbound",
                source_type="wh_inbound_voucher",
                source_id=int(voucher.id),
                quantity=received_qty,
                unit_cost=received_unit_cost,
                line_value=received_qty * received_unit_cost,
                running_avg_cost=after_avg_cost,
                balance_before=before,
                balance_after=after,
                note=voucher.note or f"سند وارد {voucher.voucher_no}",
                created_by=actor_id,
                created_at=datetime.now(UTC),
            )
        )

        total_qty += received_qty
        total_cost += received_qty * received_unit_cost

    db.add(
        WarehouseIntegrationEvent(
            event_type="warehouse_inbound_posted",
            source_type="wh_inbound_voucher",
            source_id=int(voucher.id),
            payload_json=json.dumps(
                {
                    "voucher_id": int(voucher.id),
                    "voucher_no": voucher.voucher_no,
                    "supplier_id": supplier_id,
                    "total_quantity": round(total_qty, 4),
                    "total_cost": round(total_cost, 2),
                },
                ensure_ascii=False,
            ),
            status="pending",
        )
    )
    consume_integration_events(db)

    return get_inbound_voucher(db, voucher_id=int(voucher.id))
