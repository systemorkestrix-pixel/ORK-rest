from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import ManagerTableOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_tables_with_session_summary(
        self,
        *,
        offset: int = 0,
        limit: int | None = None,
        table_ids: list[int] | None = None,
    ) -> list[dict[str, object]]:
        ...


@dataclass
class Input:
    page: int = 1
    page_size: int = 50
    table_ids: list[int] | None = None


@dataclass
class Output:
    result: list[ManagerTableOut]


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    if data.table_ids:
        rows = repo.list_tables_with_session_summary(table_ids=data.table_ids)
    else:
        offset = (data.page - 1) * data.page_size
        rows = repo.list_tables_with_session_summary(offset=offset, limit=data.page_size)
    return Output(result=rows)
