from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Expense
from app.schemas import ExpenseCreate, ExpenseOut
from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def create_expense(
        self,
        *,
        title: str,
        category: str,
        cost_center_id: int,
        amount: float,
        note: str | None,
        created_by: int,
    ) -> Expense:
        ...


@dataclass
class Input:
    actor_id: int
    payload: ExpenseCreate


@dataclass
class Output:
    result: ExpenseOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        expense = repo.create_expense(
            title=data.payload.title,
            category=data.payload.category,
            cost_center_id=data.payload.cost_center_id,
            amount=data.payload.amount,
            note=data.payload.note,
            created_by=data.actor_id,
        )

    if event_bus is not None:
        event_bus.publish(
            build_event(
                name=EventTypes.SYSTEM_AUDIT_RECORDED,
                payload={
                    "entity_type": "expense",
                    "entity_id": int(expense.id),
                    "action": "expense_created",
                },
                actor_id=data.actor_id,
            )
        )

    return Output(result=expense)
