from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import SystemBackupOut


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def create_system_backup(self, *, actor_id: int) -> dict[str, object]:
        ...


@dataclass
class Input:
    actor_id: int


@dataclass
class Output:
    result: SystemBackupOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus=None,
) -> Output:
    with transaction_scope():
        backup = repo.create_system_backup(actor_id=data.actor_id)
    return Output(result=backup)
