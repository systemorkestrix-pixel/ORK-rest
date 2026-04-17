from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import PermissionCatalogItemOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_permissions_catalog(self, *, role: str | None) -> list[dict[str, object]]:
        ...


@dataclass
class Input:
    role: str | None = None
    page: int = 1
    page_size: int = 50


@dataclass
class Output:
    result: list[PermissionCatalogItemOut]


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    items = repo.list_permissions_catalog(role=data.role)
    offset = (data.page - 1) * data.page_size
    return Output(result=items[offset : offset + data.page_size])
