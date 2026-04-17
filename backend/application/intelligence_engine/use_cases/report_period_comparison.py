from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.schemas import ReportPeriodComparisonOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def report_period_comparison(self, *, start_date: date | None, end_date: date | None) -> dict[str, object]:
        ...


@dataclass
class Input:
    start_date: date | None = None
    end_date: date | None = None


@dataclass
class Output:
    result: ReportPeriodComparisonOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    payload = repo.report_period_comparison(start_date=data.start_date, end_date=data.end_date)
    return Output(result=payload)
