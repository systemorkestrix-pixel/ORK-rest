"""
Use Case: CreateExpense (Financial Engine)
"""
from dataclasses import dataclass
from typing import Protocol


class TransactionScope(Protocol):
    def __call__(self):
        ...


class ExpenseRepository(Protocol):
    def create_expense(self, *args, **kwargs):
        ...


@dataclass
class Input:
    title: str
    category: str
    cost_center_id: int
    amount: float
    note: str | None
    created_by: int


@dataclass
class Output:
    expense_id: int
    status: str


def execute(*, data: Input, repo: ExpenseRepository, transaction_scope: TransactionScope) -> Output:
    with transaction_scope():
        expense = repo.create_expense(data)
    return Output(expense_id=int(expense.id), status=str(expense.status))
