from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import TableSessionOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def get_public_table_session(self, *, table_id: int) -> dict[str, object]:
        ...


@dataclass
class Input:
    table_id: int


@dataclass
class Output:
    result: TableSessionOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    session = repo.get_public_table_session(table_id=data.table_id)
    return Output(result=session)
