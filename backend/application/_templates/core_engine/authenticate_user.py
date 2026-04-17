"""
Use Case: AuthenticateUser (Core Engine)
"""
from dataclasses import dataclass
from typing import Protocol


class AuthRepository(Protocol):
    def authenticate(self, *, username: str, password: str, role: str):
        ...


@dataclass
class Input:
    username: str
    password: str
    role: str


@dataclass
class Output:
    user_id: int
    username: str
    role: str
    access_token: str
    refresh_token: str


def execute(*, data: Input, repo: AuthRepository) -> Output:
    user, access_token, refresh_token = repo.authenticate(
        username=data.username,
        password=data.password,
        role=data.role,
    )
    return Output(
        user_id=int(user.id),
        username=user.username,
        role=user.role,
        access_token=access_token,
        refresh_token=refresh_token,
    )
