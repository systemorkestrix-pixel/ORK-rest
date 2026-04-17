from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def revoke_user_refresh_sessions(self, *, user_id: int, actor_id: int) -> int:
        ...


@dataclass
class Input:
    actor_id: int
    user_id: int


@dataclass
class Output:
    revoked_count: int


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus=None,
) -> Output:
    with transaction_scope():
        revoked_count = repo.revoke_user_refresh_sessions(user_id=data.user_id, actor_id=data.actor_id)
    return Output(revoked_count=revoked_count)
