from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Expense
from app.schemas import ExpenseOut, ExpenseReviewInput
from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def approve_expense(
        self,
        *,
        expense_id: int,
        approved_by: int,
        note: str | None,
    ) -> Expense:
        ...


@dataclass
class Input:
    actor_id: int
    expense_id: int
    payload: ExpenseReviewInput


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
        expense = repo.approve_expense(
            expense_id=data.expense_id,
            approved_by=data.actor_id,
            note=data.payload.note,
        )

    if event_bus is not None:
        event_bus.publish(
            build_event(
                name=EventTypes.EXPENSE_APPROVED,
                payload={
                    "expense_id": int(expense.id),
                    "amount": float(expense.amount or 0.0),
                    "status": str(expense.status),
                },
                actor_id=data.actor_id,
            )
        )

    return Output(result=expense)
