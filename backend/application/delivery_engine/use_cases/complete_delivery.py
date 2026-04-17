from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Order
from app.schemas import OrderOut, OrderTransitionInput
from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def complete_delivery(
        self,
        *,
        order_id: int,
        actor_id: int,
        success: bool,
        amount_received: float | None,
        notify_bot: bool = True,
    ) -> Order:
        ...


@dataclass
class Input:
    actor_id: int
    order_id: int
    payload: OrderTransitionInput


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
        order = repo.complete_delivery(
            order_id=data.order_id,
            actor_id=data.actor_id,
            success=True,
            amount_received=data.payload.amount_received,
        )

    if event_bus is not None:
        event_bus.publish(
            build_event(
                name=EventTypes.DELIVERY_COMPLETED,
                payload={
                    "order_id": int(order.id),
                    "status": str(order.status),
                    "type": str(order.type),
                },
                actor_id=data.actor_id,
            )
        )
        event_bus.publish(
            build_event(
                name=EventTypes.ORDER_DELIVERED,
                payload={
                    "order_id": int(order.id),
                    "status": str(order.status),
                    "type": str(order.type),
                },
                actor_id=data.actor_id,
            )
        )

    return Output(result=order)
