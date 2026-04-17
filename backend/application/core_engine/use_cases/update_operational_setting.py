from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import OperationalSettingOut, OperationalSettingUpdate


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def update_operational_setting(
        self,
        *,
        key: str,
        value: str,
        actor_id: int,
    ) -> dict[str, object]:
        ...


@dataclass
class Input:
    actor_id: int
    payload: OperationalSettingUpdate


@dataclass
class Output:
    result: OperationalSettingOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus=None,
) -> Output:
    with transaction_scope():
        result = repo.update_operational_setting(
            key=data.payload.key,
            value=data.payload.value,
            actor_id=data.actor_id,
        )
    return Output(result=result)
