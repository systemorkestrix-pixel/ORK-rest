from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import SecurityAuditEvent
from app.schemas import SecurityAuditEventOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_security_audit(self, *, offset: int, limit: int) -> list[SecurityAuditEvent]:
        ...


@dataclass
class Input:
    page: int = 1
    page_size: int = 50


@dataclass
class Output:
    result: list[SecurityAuditEventOut]


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    offset = (data.page - 1) * data.page_size
    rows = repo.list_security_audit(offset=offset, limit=data.page_size)
    return Output(result=rows)
