from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import WarehouseSupplierOut, WarehouseSupplierUpdate


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
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
        ...


@dataclass
class Input:
    actor_id: int
    supplier_id: int
    payload: WarehouseSupplierUpdate


@dataclass
class Output:
    result: WarehouseSupplierOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus=None,
) -> Output:
    with transaction_scope():
        supplier = repo.update_supplier(
            supplier_id=data.supplier_id,
            name=data.payload.name,
            phone=data.payload.phone,
            email=data.payload.email,
            address=data.payload.address,
            payment_term_days=data.payload.payment_term_days,
            credit_limit=data.payload.credit_limit,
            quality_rating=data.payload.quality_rating,
            lead_time_days=data.payload.lead_time_days,
            notes=data.payload.notes,
            active=data.payload.active,
            supplied_item_ids=data.payload.supplied_item_ids,
        )
    return Output(result=supplier)
