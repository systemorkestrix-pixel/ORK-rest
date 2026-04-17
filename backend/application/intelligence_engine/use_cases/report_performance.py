from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import ReportPerformance
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def report_performance(self) -> float:
        ...


@dataclass
class Input:
    pass


@dataclass
class Output:
    result: ReportPerformance


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    avg_minutes = repo.report_performance()
    return Output(result=ReportPerformance(avg_prep_minutes=avg_minutes))
