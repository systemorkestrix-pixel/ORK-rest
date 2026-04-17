from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import User
from app.schemas import UserOut, UserUpdate


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def update_user(
        self,
        *,
        user_id: int,
        name: str,
        role: str,
        active: bool,
        password: str | None,
        delivery_phone: str | None,
        delivery_vehicle: str | None,
        actor_id: int,
        allow_manager_self_update: bool = False,
    ) -> User:
        ...


@dataclass
class Input:
    actor_id: int
    user_id: int
    payload: UserUpdate


@dataclass
class Output:
    result: UserOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus=None,
) -> Output:
    with transaction_scope():
        user = repo.update_user(
            user_id=data.user_id,
            name=data.payload.name,
            role=data.payload.role.value,
            active=data.payload.active,
            password=data.payload.password,
            delivery_phone=data.payload.delivery_phone,
            delivery_vehicle=data.payload.delivery_vehicle,
            actor_id=data.actor_id,
        )
    return Output(result=user)
