from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def delete_expense_attachment(
        self,
        *,
        expense_id: int,
        attachment_id: int,
        deleted_by: int,
    ) -> None:
        ...


@dataclass
class Input:
    actor_id: int
    attachment_id: int
    expense_id: int


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
        repo.delete_expense_attachment(
            expense_id=data.expense_id,
            attachment_id=data.attachment_id,
            deleted_by=data.actor_id,
        )

    if event_bus is not None:
        event_bus.publish(
            build_event(
                name=EventTypes.SYSTEM_AUDIT_RECORDED,
                payload={
                    "entity_type": "expense_attachment",
                    "entity_id": int(data.attachment_id),
                    "expense_id": int(data.expense_id),
                    "action": "expense_attachment_deleted",
                },
                actor_id=data.actor_id,
            )
        )

    return Output(result=None)
