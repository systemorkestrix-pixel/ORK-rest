from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def delete_expense(self, *, expense_id: int) -> None:
        ...


@dataclass
class Input:
    expense_id: int
    actor_id: int


@dataclass
class Output:
    result: object | None = None


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        repo.delete_expense(expense_id=data.expense_id)

    if event_bus is not None:
        event_bus.publish(
            build_event(
                name=EventTypes.SYSTEM_AUDIT_RECORDED,
                payload={
                    "entity_type": "expense",
                    "entity_id": int(data.expense_id),
                    "action": "expense_deleted",
                },
                actor_id=data.actor_id,
            )
        )

    return Output(result=None)
