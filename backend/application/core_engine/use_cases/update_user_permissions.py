from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import UserPermissionsOut, UserPermissionsUpdate


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def update_user_permissions(
        self,
        *,
        user_id: int,
        allow: list[str] | None,
        deny: list[str] | None,
        actor_id: int,
    ) -> UserPermissionsOut:
        ...


@dataclass
class Input:
    actor_id: int
    user_id: int
    payload: UserPermissionsUpdate


@dataclass
class Output:
    result: UserPermissionsOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus=None,
) -> Output:
    with transaction_scope():
        profile = repo.update_user_permissions(
            user_id=data.user_id,
            allow=data.payload.allow,
            deny=data.payload.deny,
            actor_id=data.actor_id,
        )
    return Output(result=profile)
