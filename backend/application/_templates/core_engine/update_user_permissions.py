"""
Use Case: UpdateUserPermissions (Core Engine)
"""
from dataclasses import dataclass
from typing import Protocol


class TransactionScope(Protocol):
    def __call__(self):
        ...


class PermissionsRepository(Protocol):
    def update_permissions(self, *, user_id: int, allow: list[str], deny: list[str]):
        ...


@dataclass
class Input:
    user_id: int
    allow: list[str]
    deny: list[str]


@dataclass
class Output:
    user_id: int
    effective_permissions: list[str]


def execute(*, data: Input, repo: PermissionsRepository, transaction_scope: TransactionScope) -> Output:
    with transaction_scope():
        profile = repo.update_permissions(user_id=data.user_id, allow=data.allow, deny=data.deny)
    return Output(user_id=int(profile["user_id"]), effective_permissions=profile["effective_permissions"])
