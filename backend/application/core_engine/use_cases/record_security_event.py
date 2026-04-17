from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def record_security_event(
        self,
        *,
        event_type: str,
        success: bool,
        severity: str,
        username: str | None,
        role: str | None,
        user_id: int | None,
        ip_address: str | None,
        user_agent: str | None,
        detail: str | None,
    ) -> None:
        ...


@dataclass
class Input:
    event_type: str
    success: bool
    severity: str = "info"
    username: str | None = None
    role: str | None = None
    user_id: int | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    detail: str | None = None


@dataclass
class Output:
    result: bool


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        repo.record_security_event(
            event_type=data.event_type,
            success=bool(data.success),
            severity=str(data.severity),
            username=data.username,
            role=data.role,
            user_id=data.user_id,
            ip_address=data.ip_address,
            user_agent=data.user_agent,
            detail=data.detail,
        )
    if event_bus is not None:
        event_bus.publish(
            build_event(
                name=EventTypes.SECURITY_AUDIT_RECORDED,
                payload={
                    "event_type": data.event_type,
                    "success": bool(data.success),
                    "severity": str(data.severity),
                    "username": data.username,
                    "role": data.role,
                    "user_id": data.user_id,
                },
                actor_id=data.user_id,
            )
        )
    return Output(result=True)
