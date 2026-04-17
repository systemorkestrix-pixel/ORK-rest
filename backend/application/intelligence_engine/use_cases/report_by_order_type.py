from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import ReportByTypeRow
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def report_by_order_type(self) -> list[dict[str, float | str | int]]:
        ...


@dataclass
class Input:
    page: int = 1
    page_size: int = 50


@dataclass
class Output:
    result: list[ReportByTypeRow]


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    rows = repo.report_by_order_type()
    offset = (data.page - 1) * data.page_size
    return Output(result=rows[offset : offset + data.page_size])
