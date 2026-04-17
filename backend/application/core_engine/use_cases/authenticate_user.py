from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import User
from app.schemas import LoginInput
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def authenticate(self, *, username: str, password: str, role: str) -> tuple[User, str, str]:
        ...


@dataclass
class Input:
    payload: LoginInput


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
    user, access_token, refresh_token = repo.authenticate(
        username=data.payload.username,
        password=data.payload.password,
        role=data.payload.role.value,
    )
    return Output(user=user, access_token=access_token, refresh_token=refresh_token)
