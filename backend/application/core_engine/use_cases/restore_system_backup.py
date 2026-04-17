from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import SystemBackupOut, SystemBackupRestoreInput


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def restore_system_backup(
        self,
        *,
        filename: str,
        confirm_phrase: str,
        actor_id: int,
    ) -> dict[str, object]:
        ...


@dataclass
class Input:
    actor_id: int
    payload: SystemBackupRestoreInput


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
        backup = repo.restore_system_backup(
            filename=data.payload.filename,
            confirm_phrase=data.payload.confirm_phrase,
            actor_id=data.actor_id,
        )
    return Output(result=backup)
