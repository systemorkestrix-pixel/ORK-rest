from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Order
from app.schemas import OrderOut, OrderRefundInput
from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def refund_order(
        self,
        *,
        order_id: int,
        refunded_by: int,
        note: str | None,
    ) -> Order:
        ...


@dataclass
class Input:
    actor_id: int
    order_id: int
    payload: OrderRefundInput


@dataclass
class Output:
    result: OrderOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        order = repo.refund_order(
            order_id=data.order_id,
            refunded_by=data.actor_id,
            note=data.payload.note,
        )

    if event_bus is not None:
        event_bus.publish(
            build_event(
                name=EventTypes.FINANCIAL_TRANSACTION_CREATED,
                payload={
                    "order_id": int(order.id),
                    "action": "refund",
                    "total": float(order.total or 0.0),
                },
                actor_id=data.actor_id,
            )
        )

    return Output(result=order)
