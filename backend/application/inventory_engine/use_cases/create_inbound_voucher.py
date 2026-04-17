from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import WarehouseInboundVoucherCreate, WarehouseInboundVoucherOut
from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
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
        ...


@dataclass
class Input:
    actor_id: int
    payload: WarehouseInboundVoucherCreate


@dataclass
class Output:
    result: WarehouseInboundVoucherOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        voucher = repo.create_inbound_voucher(
            supplier_id=data.payload.supplier_id,
            reference_no=data.payload.reference_no,
            note=data.payload.note,
            idempotency_key=data.payload.idempotency_key,
            items=[(item.item_id, item.quantity, item.unit_cost) for item in data.payload.items],
            actor_id=data.actor_id,
        )

    if event_bus is not None:
        event_bus.publish(
            build_event(
                name=EventTypes.WAREHOUSE_INBOUND_POSTED,
                payload={
                    "voucher_id": int(voucher.get("id")),
                    "voucher_no": voucher.get("voucher_no"),
                    "supplier_id": int(voucher.get("supplier_id")),
                },
                actor_id=data.actor_id,
            )
        )

    return Output(result=voucher)
