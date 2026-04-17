from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Protocol

from app.models import Order
from app.schemas import OrderOut
from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def depart_delivery(self, *, order_id: int, actor_id: int, notify_bot: bool = True) -> Order:
        ...


@dataclass
class Input:
    actor_id: int
    order_id: int


@dataclass
class Output:
    result: OrderOut

logger = logging.getLogger(__name__)


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        order = repo.depart_delivery(order_id=data.order_id, actor_id=data.actor_id)

    if event_bus is not None:
        try:
            event_bus.publish(
                build_event(
                    name=EventTypes.DRIVER_DEPARTED,
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
                    name=EventTypes.ORDER_OUT_FOR_DELIVERY,
                    payload={
                        "order_id": int(order.id),
                        "status": str(order.status),
                        "type": str(order.type),
                    },
                    actor_id=data.actor_id,
                )
            )
        except Exception:
            logger.exception("Failed to publish delivery depart events for order_id=%s", order.id)

    return Output(result=order)
