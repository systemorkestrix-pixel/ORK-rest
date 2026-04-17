from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import ExpenseCostCenter
from app.schemas import ExpenseCostCenterOut, ExpenseCostCenterUpdate
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def update_expense_cost_center(
        self,
        *,
        center_id: int,
        code: str,
        name: str,
        active: bool,
        actor_id: int,
    ) -> ExpenseCostCenter:
        ...


@dataclass
class Input:
    actor_id: int
    center_id: int
    payload: ExpenseCostCenterUpdate


@dataclass
class Output:
    result: ExpenseCostCenterOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        center = repo.update_expense_cost_center(
            center_id=data.center_id,
            code=data.payload.code,
            name=data.payload.name,
            active=data.payload.active,
            actor_id=data.actor_id,
        )
    return Output(result=center)
