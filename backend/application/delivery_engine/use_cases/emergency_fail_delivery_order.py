from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Order
from app.schemas import EmergencyDeliveryFailInput, OrderOut
from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def emergency_fail_delivery_order(
        self,
        *,
        order_id: int,
        performed_by: int,
        reason_code: str,
        reason_note: str | None,
    ) -> Order:
        ...


@dataclass
class Input:
    actor_id: int
    order_id: int
    payload: EmergencyDeliveryFailInput


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
        order = repo.emergency_fail_delivery_order(
            order_id=data.order_id,
            performed_by=data.actor_id,
            reason_code=data.payload.reason_code,
            reason_note=data.payload.reason_note,
        )

    if event_bus is not None:
        event_bus.publish(
            build_event(
                name=EventTypes.DELIVERY_FAILED,
                payload={
                    "order_id": int(order.id),
                    "status": str(order.status),
                    "type": str(order.type),
                    "reason_code": data.payload.reason_code,
                },
                actor_id=data.actor_id,
            )
        )

    return Output(result=order)
