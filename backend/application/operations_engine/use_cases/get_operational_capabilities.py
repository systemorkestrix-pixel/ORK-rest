from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import OperationalCapabilitiesOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def get_operational_capabilities(self) -> dict[str, object]:
        ...


@dataclass
class Input:
    pass


@dataclass
class Output:
    result: OperationalCapabilitiesOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    capabilities = repo.get_operational_capabilities()
    return Output(result=capabilities)
