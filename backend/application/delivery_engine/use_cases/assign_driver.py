from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import DeliveryAssignment
from app.schemas import DeliveryAssignmentOut
from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def assign_driver(self, *, order_id: int, actor_id: int, notify_bot: bool = True) -> DeliveryAssignment:
        ...


@dataclass
class Input:
    actor_id: int
    order_id: int


@dataclass
class Output:
    result: DeliveryAssignmentOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        assignment = repo.assign_driver(order_id=data.order_id, actor_id=data.actor_id)

    if event_bus is not None:
        event_bus.publish(
            build_event(
                name=EventTypes.DRIVER_ASSIGNED,
                payload={
                    "order_id": int(assignment.order_id),
                    "assignment_id": int(assignment.id),
                    "driver_id": int(assignment.driver_id),
                    "status": str(assignment.status),
                },
                actor_id=data.actor_id,
            )
        )

    return Output(result=assignment)
