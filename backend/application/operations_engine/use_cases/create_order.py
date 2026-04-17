from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Order
from app.schemas import CreateOrderInput, OrderOut
from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def create_order(
        self,
        *,
        payload: CreateOrderInput,
        created_by: int | None,
        source_actor: str,
    ) -> Order:
        ...


@dataclass
class Input:
    actor_id: int | None
    payload: CreateOrderInput
    source_actor: str = "system"


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
        order = repo.create_order(
            payload=data.payload,
            created_by=data.actor_id,
            source_actor=data.source_actor,
        )

    if event_bus is not None:
        event_bus.publish(
            build_event(
                name=EventTypes.ORDER_CREATED,
                payload={
                    "order_id": int(order.id),
                    "status": str(order.status),
                    "type": str(order.type),
                    "total": float(order.total or 0.0),
                    "table_id": int(order.table_id) if order.table_id is not None else None,
                },
                actor_id=data.actor_id,
            )
        )

    return Output(result=order)
