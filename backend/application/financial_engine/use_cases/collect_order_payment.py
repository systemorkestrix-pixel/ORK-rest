from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Order
from app.schemas import OrderOut, OrderPaymentCollectionInput
from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def collect_order_payment(
        self,
        *,
        order_id: int,
        collected_by: int,
        amount_received: float | None,
    ) -> Order:
        ...


@dataclass
class Input:
    actor_id: int
    order_id: int
    payload: OrderPaymentCollectionInput


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
        order = repo.collect_order_payment(
            order_id=data.order_id,
            collected_by=data.actor_id,
            amount_received=data.payload.amount_received,
        )

    if event_bus is not None:
        event_bus.publish(
            build_event(
                name=EventTypes.FINANCIAL_TRANSACTION_CREATED,
                payload={
                    "order_id": int(order.id),
                    "action": "collect_payment",
                    "amount_received": float(order.amount_received or 0.0),
                },
                actor_id=data.actor_id,
            )
        )

    return Output(result=order)
