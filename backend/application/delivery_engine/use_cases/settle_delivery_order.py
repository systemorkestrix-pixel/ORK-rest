from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import DeliverySettlement
from app.schemas import DeliverySettlementOut
from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def settle_delivery_order(self, *, order_id: int, performed_by: int) -> DeliverySettlement:
        ...


@dataclass
class Input:
    actor_id: int
    order_id: int


@dataclass
class Output:
    result: DeliverySettlementOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        settlement = repo.settle_delivery_order(order_id=data.order_id, performed_by=data.actor_id)

    if event_bus is not None:
        event_bus.publish(
            build_event(
                name=EventTypes.DELIVERY_SETTLEMENT_CREATED,
                payload={
                    "order_id": int(settlement.order_id),
                    "settlement_id": int(settlement.id),
                    "status": str(settlement.status),
                },
                actor_id=data.actor_id,
            )
        )

    return Output(result=settlement)
