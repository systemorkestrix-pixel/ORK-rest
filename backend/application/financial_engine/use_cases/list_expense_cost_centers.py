from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import ExpenseCostCenterOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_expense_cost_centers(
        self,
        *,
        include_inactive: bool,
        offset: int,
        limit: int,
    ) -> list[dict[str, object]]:
        ...


@dataclass
class Input:
    include_inactive: bool = False
    page: int = 1
    page_size: int = 50


@dataclass
class Output:
    result: list[ExpenseCostCenterOut]


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    offset = (data.page - 1) * data.page_size
    rows = repo.list_expense_cost_centers(
        include_inactive=data.include_inactive,
        offset=offset,
        limit=data.page_size,
    )
    return Output(result=rows)
