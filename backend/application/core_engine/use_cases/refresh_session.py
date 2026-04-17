from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import User
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def refresh(self, *, refresh_token: str) -> tuple[User, str, str]:
        ...


@dataclass
class Input:
    refresh_token: str


@dataclass
class Output:
    user: User
    access_token: str
    refresh_token: str


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    user, access_token, refresh_token = repo.refresh(refresh_token=data.refresh_token)
    return Output(user=user, access_token=access_token, refresh_token=refresh_token)
