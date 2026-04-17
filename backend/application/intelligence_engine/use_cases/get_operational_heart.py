from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import OperationalHeartOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def get_operational_heart(self) -> dict[str, object]:
        ...


@dataclass
class Input:
    pass


@dataclass
class Output:
    result: OperationalHeartOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    payload = repo.get_operational_heart()
    return Output(result=payload)
