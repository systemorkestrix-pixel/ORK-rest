from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import User
from app.schemas import UserCreate, UserOut


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def create_user(
        self,
        *,
        name: str,
        username: str,
        password: str,
        role: str,
        active: bool,
        delivery_phone: str | None,
        delivery_vehicle: str | None,
        actor_id: int,
    ) -> User:
        ...


@dataclass
class Input:
    actor_id: int
    payload: UserCreate


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
        user = repo.create_user(
            name=data.payload.name,
            username=data.payload.username,
            password=data.payload.password,
            role=data.payload.role.value,
            active=data.payload.active,
            delivery_phone=data.payload.delivery_phone,
            delivery_vehicle=data.payload.delivery_vehicle,
            actor_id=data.actor_id,
        )
    return Output(result=user)
