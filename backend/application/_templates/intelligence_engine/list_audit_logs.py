"""
Use Case: ListAuditLogs (Intelligence Engine)
"""
from dataclasses import dataclass
from typing import Protocol


class AuditRepository(Protocol):
    def list_order_audit(self, *args, **kwargs):
        ...

    def list_system_audit(self, *args, **kwargs):
        ...

    def list_security_audit(self, *args, **kwargs):
        ...


@dataclass
class Input:
    kind: str  # orders | system | security
    page: int = 1
    page_size: int = 50


@dataclass
class Output:
    rows: list[dict]


def execute(*, data: Input, repo: AuditRepository) -> Output:
    if data.kind == "orders":
        rows = repo.list_order_audit(page=data.page, page_size=data.page_size)
    elif data.kind == "system":
        rows = repo.list_system_audit(page=data.page, page_size=data.page_size)
    else:
        rows = repo.list_security_audit(page=data.page, page_size=data.page_size)
    return Output(rows=rows)
