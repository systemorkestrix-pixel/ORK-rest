from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Expense
from app.schemas import ExpenseOut, ExpenseUpdate
from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def update_expense(
        self,
        *,
        expense_id: int,
        title: str,
        category: str,
        cost_center_id: int,
        amount: float,
        note: str | None,
        updated_by: int,
    ) -> Expense:
        ...


@dataclass
class Input:
    actor_id: int
    expense_id: int
    payload: ExpenseUpdate


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
        expense = repo.update_expense(
            expense_id=data.expense_id,
            title=data.payload.title,
            category=data.payload.category,
            cost_center_id=data.payload.cost_center_id,
            amount=data.payload.amount,
            note=data.payload.note,
            updated_by=data.actor_id,
        )

    if event_bus is not None:
        event_bus.publish(
            build_event(
                name=EventTypes.SYSTEM_AUDIT_RECORDED,
                payload={
                    "entity_type": "expense",
                    "entity_id": int(expense.id),
                    "action": "expense_updated",
                },
                actor_id=data.actor_id,
            )
        )

    return Output(result=expense)
