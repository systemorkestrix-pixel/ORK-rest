from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import AccountSessionOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_account_sessions(
        self,
        *,
        user_id: int,
        offset: int,
        limit: int,
    ) -> list[dict[str, object]]:
        ...


@dataclass
class Input:
    user_id: int
    page: int = 1
    page_size: int = 50


@dataclass
class Output:
    result: list[AccountSessionOut]


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    offset = (data.page - 1) * data.page_size
    sessions = repo.list_account_sessions(user_id=data.user_id, offset=offset, limit=data.page_size)
    return Output(result=sessions)
