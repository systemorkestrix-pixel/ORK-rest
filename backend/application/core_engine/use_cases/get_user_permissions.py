from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import UserPermissionsOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def get_user_permissions(self, *, user_id: int) -> dict[str, object]:
        ...


@dataclass
class Input:
    user_id: int


@dataclass
class Output:
    result: UserPermissionsOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    profile = repo.get_user_permissions(user_id=data.user_id)
    return Output(result=profile)
