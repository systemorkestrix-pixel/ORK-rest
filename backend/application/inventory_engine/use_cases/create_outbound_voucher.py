from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import WarehouseOutboundVoucherCreate, WarehouseOutboundVoucherOut
from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
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
        ...


@dataclass
class Input:
    actor_id: int
    payload: WarehouseOutboundVoucherCreate


@dataclass
class Output:
    result: WarehouseOutboundVoucherOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        voucher = repo.create_outbound_voucher(
            reason_code=data.payload.reason_code,
            reason_note=data.payload.reason_note,
            note=data.payload.note,
            idempotency_key=data.payload.idempotency_key,
            items=[(item.item_id, item.quantity) for item in data.payload.items],
            actor_id=data.actor_id,
        )

    if event_bus is not None:
        event_bus.publish(
            build_event(
                name=EventTypes.WAREHOUSE_OUTBOUND_POSTED,
                payload={
                    "voucher_id": int(voucher.get("id")),
                    "voucher_no": voucher.get("voucher_no"),
                    "reason_code": voucher.get("reason_code"),
                },
                actor_id=data.actor_id,
            )
        )

    return Output(result=voucher)
