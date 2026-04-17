"""
Use Case: RefreshSession (Core Engine)
"""
from dataclasses import dataclass
from typing import Protocol


class SessionRepository(Protocol):
    def refresh(self, *, refresh_token: str):
        ...


@dataclass
class Input:
    refresh_token: str


@dataclass
class Output:
    user_id: int
    username: str
    role: str
    access_token: str
    refresh_token: str


def execute(*, data: Input, repo: SessionRepository) -> Output:
    user, access_token, refresh_token = repo.refresh(refresh_token=data.refresh_token)
    return Output(
        user_id=int(user.id),
        username=user.username,
        role=user.role,
        access_token=access_token,
        refresh_token=refresh_token,
    )
