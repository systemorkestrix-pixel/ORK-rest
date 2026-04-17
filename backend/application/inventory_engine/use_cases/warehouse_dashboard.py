from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import WarehouseDashboardOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def warehouse_dashboard(self) -> dict[str, object]:
        ...


@dataclass
class Input:
    pass


@dataclass
class Output:
    result: WarehouseDashboardOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    dashboard = repo.warehouse_dashboard()
    return Output(result=dashboard)
