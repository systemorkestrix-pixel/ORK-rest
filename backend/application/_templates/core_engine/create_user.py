"""
Use Case: CreateUser (Core Engine)
"""
from dataclasses import dataclass
from typing import Protocol


class TransactionScope(Protocol):
    def __call__(self):
        ...


class UserRepository(Protocol):
    def create(self, *, name: str, username: str, password: str, role: str, active: bool, **kwargs):
        ...


@dataclass
class Input:
    name: str
    username: str
    password: str
    role: str
    active: bool
    delivery_phone: str | None = None
    delivery_vehicle: str | None = None


@dataclass
class Output:
    user_id: int
    username: str
    role: str


def execute(*, data: Input, repo: UserRepository, transaction_scope: TransactionScope) -> Output:
    with transaction_scope():
        user = repo.create(
            name=data.name,
            username=data.username,
            password=data.password,
            role=data.role,
            active=data.active,
            delivery_phone=data.delivery_phone,
            delivery_vehicle=data.delivery_vehicle,
        )
    return Output(user_id=int(user.id), username=user.username, role=user.role)
