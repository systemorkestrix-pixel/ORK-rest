from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import WarehouseOutboundReasonOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_outbound_reasons(self) -> list[dict[str, str]]:
        ...


@dataclass
class Input:
    page: int = 1
    page_size: int = 50


@dataclass
class Output:
    result: list[WarehouseOutboundReasonOut]


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    reasons = repo.list_outbound_reasons()
    offset = (data.page - 1) * data.page_size
    return Output(result=reasons[offset : offset + data.page_size])
