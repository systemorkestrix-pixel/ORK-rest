from __future__ import annotations

from sqlalchemy.orm import Session

from app.warehouse_services import (
    create_warehouse_inbound_voucher,
    create_warehouse_outbound_voucher,
    create_warehouse_stock_count,
    create_warehouse_supplier,
    create_warehouse_item,
    list_warehouse_balances,
    list_warehouse_inbound_vouchers,
    list_warehouse_items,
    list_warehouse_ledger,
    list_warehouse_outbound_reasons,
    list_warehouse_outbound_vouchers,
    list_warehouse_stock_counts,
    list_warehouse_suppliers,
    settle_warehouse_stock_count,
    update_warehouse_item,
    update_warehouse_supplier,
    warehouse_dashboard,
)


class WarehouseRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_inbound_voucher(
        self,
        *,
        supplier_id: int,
        reference_no: str | None,
        note: str | None,
        idempotency_key: str | None,
        items: list[tuple[int, float, float]],
        actor_id: int,
    ) -> dict[str, object]:
        return create_warehouse_inbound_voucher(
            self._db,
            supplier_id=supplier_id,
            reference_no=reference_no,
            note=note,
            idempotency_key=idempotency_key,
            items=items,
            actor_id=actor_id,
        )

    def create_outbound_voucher(
        self,
        *,
        reason_code: str,
        reason_note: str | None,
        note: str | None,
        idempotency_key: str | None,
        items: list[tuple[int, float]],
        actor_id: int,
    ) -> dict[str, object]:
        return create_warehouse_outbound_voucher(
            self._db,
            reason_code=reason_code,
            reason_note=reason_note,
            note=note,
            idempotency_key=idempotency_key,
            items=items,
            actor_id=actor_id,
        )

    def create_supplier(
        self,
        *,
        name: str,
        phone: str | None,
        email: str | None,
        address: str | None,
        payment_term_days: int,
        credit_limit: float | None,
        quality_rating: float,
        lead_time_days: int,
        notes: str | None,
        active: bool,
        supplied_item_ids: list[int],
    ) -> dict[str, object]:
        return create_warehouse_supplier(
            self._db,
            name=name,
            phone=phone,
            email=email,
            address=address,
            payment_term_days=payment_term_days,
            credit_limit=credit_limit,
            quality_rating=quality_rating,
            lead_time_days=lead_time_days,
            notes=notes,
            active=active,
            supplied_item_ids=supplied_item_ids,
        )

    def update_supplier(
        self,
        *,
        supplier_id: int,
        name: str,
        phone: str | None,
        email: str | None,
        address: str | None,
        payment_term_days: int,
        credit_limit: float | None,
        quality_rating: float,
        lead_time_days: int,
        notes: str | None,
        active: bool,
        supplied_item_ids: list[int],
    ) -> dict[str, object]:
        return update_warehouse_supplier(
            self._db,
            supplier_id=supplier_id,
            name=name,
            phone=phone,
            email=email,
            address=address,
            payment_term_days=payment_term_days,
            credit_limit=credit_limit,
            quality_rating=quality_rating,
            lead_time_days=lead_time_days,
            notes=notes,
            active=active,
            supplied_item_ids=supplied_item_ids,
        )

    def create_item(
        self,
        *,
        name: str,
        unit: str,
        alert_threshold: float,
        active: bool,
    ):
        return create_warehouse_item(
            self._db,
            name=name,
            unit=unit,
            alert_threshold=alert_threshold,
            active=active,
        )

    def update_item(
        self,
        *,
        item_id: int,
        name: str,
        unit: str,
        alert_threshold: float,
        active: bool,
    ):
        return update_warehouse_item(
            self._db,
            item_id=item_id,
            name=name,
            unit=unit,
            alert_threshold=alert_threshold,
            active=active,
        )

    def create_stock_count(
        self,
        *,
        note: str | None,
        idempotency_key: str | None,
        items: list[tuple[int, float]],
        actor_id: int,
    ) -> dict[str, object]:
        return create_warehouse_stock_count(
            self._db,
            note=note,
            idempotency_key=idempotency_key,
            items=items,
            actor_id=actor_id,
        )

    def settle_stock_count(self, *, count_id: int, actor_id: int) -> dict[str, object]:
        return settle_warehouse_stock_count(self._db, count_id=count_id, actor_id=actor_id)

    def warehouse_dashboard(self) -> dict[str, object]:
        return warehouse_dashboard(self._db)

    def list_suppliers(self, *, offset: int, limit: int) -> list[dict[str, object]]:
        return list_warehouse_suppliers(self._db, offset=offset, limit=limit)

    def list_items(self, *, offset: int, limit: int):
        return list_warehouse_items(self._db, offset=offset, limit=limit)

    def list_balances(
        self,
        *,
        only_low: bool,
        offset: int,
        limit: int,
    ) -> list[dict[str, object]]:
        return list_warehouse_balances(
            self._db,
            only_low=only_low,
            offset=offset,
            limit=limit,
        )

    def list_ledger(
        self,
        *,
        offset: int,
        limit: int,
        item_id: int | None,
        movement_kind: str | None,
    ) -> list[dict[str, object]]:
        return list_warehouse_ledger(
            self._db,
            offset=offset,
            limit=limit,
            item_id=item_id,
            movement_kind=movement_kind,
        )

    def list_inbound_vouchers(self, *, offset: int, limit: int) -> list[dict[str, object]]:
        return list_warehouse_inbound_vouchers(self._db, offset=offset, limit=limit)

    def list_outbound_vouchers(self, *, offset: int, limit: int) -> list[dict[str, object]]:
        return list_warehouse_outbound_vouchers(self._db, offset=offset, limit=limit)

    def list_outbound_reasons(self) -> list[dict[str, str]]:
        return list_warehouse_outbound_reasons()

    def list_stock_counts(self, *, offset: int, limit: int) -> list[dict[str, object]]:
        return list_warehouse_stock_counts(self._db, offset=offset, limit=limit)
