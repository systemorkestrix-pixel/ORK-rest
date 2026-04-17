from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.enums import OrderStatus
from app.models import Order
from app.schemas import OrderOut, OrderTransitionInput
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
    payload: OrderTransitionInput


@dataclass
class Output:
    result: OrderOut


def _resolve_order_event(target_status: OrderStatus) -> str | None:
    if target_status == OrderStatus.CONFIRMED:
        return EventTypes.ORDER_CONFIRMED
    if target_status == OrderStatus.SENT_TO_KITCHEN:
        return EventTypes.ORDER_SENT_TO_KITCHEN
    if target_status == OrderStatus.IN_PREPARATION:
        return EventTypes.ORDER_PREPARATION_STARTED
    if target_status == OrderStatus.READY:
        return EventTypes.ORDER_READY
    if target_status == OrderStatus.OUT_FOR_DELIVERY:
        return EventTypes.ORDER_OUT_FOR_DELIVERY
    if target_status == OrderStatus.DELIVERED:
        return EventTypes.ORDER_DELIVERED
    if target_status == OrderStatus.CANCELED:
        return EventTypes.ORDER_CANCELED
    return None


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
            target_status=data.payload.target_status,
            performed_by=data.actor_id,
            amount_received=data.payload.amount_received,
            collect_payment=data.payload.collect_payment,
            reason_code=data.payload.reason_code,
            reason_note=data.payload.reason_note,
        )

    event_name = _resolve_order_event(data.payload.target_status)
    if event_bus is not None and event_name is not None:
        event_bus.publish(
            build_event(
                name=event_name,
                payload={
                    "order_id": int(order.id),
                    "status": str(order.status),
                    "type": str(order.type),
                },
                actor_id=data.actor_id,
            )
        )

    return Output(result=order)
