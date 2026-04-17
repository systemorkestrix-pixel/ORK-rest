from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.enums import OrderStatus
from app.models import Order
from app.schemas import OrderOut
from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def transition_order(
        self,
        *,
        order_id: int,
        target_status: OrderStatus,
        performed_by: int,
        amount_received: float | None,
        collect_payment: bool,
        reason_code: str | None,
        reason_note: str | None,
    ) -> Order:
        ...


@dataclass
class Input:
    actor_id: int
    order_id: int


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
        order = repo.transition_order(
            order_id=data.order_id,
            target_status=OrderStatus.IN_PREPARATION,
            performed_by=data.actor_id,
            amount_received=None,
            collect_payment=True,
            reason_code=None,
            reason_note=None,
        )

    if event_bus is not None:
        event_bus.publish(
            build_event(
                name=EventTypes.ORDER_PREPARATION_STARTED,
                payload={
                    "order_id": int(order.id),
                    "status": str(order.status),
                    "type": str(order.type),
                },
                actor_id=data.actor_id,
            )
        )

    return Output(result=order)
