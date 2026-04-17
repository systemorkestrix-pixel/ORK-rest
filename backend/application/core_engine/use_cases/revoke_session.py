from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def revoke_refresh_token(self, *, refresh_token: str) -> tuple[int | None, bool]:
        ...


@dataclass
class Input:
    refresh_token: str


@dataclass
class Output:
    user_id: int | None
    revoked: bool


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus=None,
) -> Output:
    with transaction_scope():
        user_id, revoked = repo.revoke_refresh_token(refresh_token=data.refresh_token)
    return Output(user_id=user_id, revoked=revoked)
