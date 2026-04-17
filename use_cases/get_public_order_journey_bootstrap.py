from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import PublicOrderJourneyBootstrapOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def get_public_order_journey_bootstrap(self, *, table_id: int | None = None) -> dict[str, object]:
        ...


@dataclass
class Input:
    table_id: int | None = None


@dataclass
class Output:
    result: PublicOrderJourneyBootstrapOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    bootstrap = repo.get_public_order_journey_bootstrap(table_id=data.table_id)
    return Output(result=PublicOrderJourneyBootstrapOut(**bootstrap))
