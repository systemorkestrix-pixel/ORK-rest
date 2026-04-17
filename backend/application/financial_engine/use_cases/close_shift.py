from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import ShiftClosure
from app.schemas import ShiftClosureCreate, ShiftClosureOut
from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def close_shift(
        self,
        *,
        closed_by: int,
        opening_cash: float,
        actual_cash: float,
        note: str | None,
    ) -> ShiftClosure:
        ...


@dataclass
class Input:
    actor_id: int
    payload: ShiftClosureCreate


@dataclass
class Output:
    result: ShiftClosureOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        closure = repo.close_shift(
            closed_by=data.actor_id,
            opening_cash=data.payload.opening_cash,
            actual_cash=data.payload.actual_cash,
            note=data.payload.note,
        )

    if event_bus is not None:
        event_bus.publish(
            build_event(
                name=EventTypes.SHIFT_CLOSED,
                payload={
                    "shift_id": int(closure.id),
                    "business_date": closure.business_date.isoformat(),
                    "variance": float(closure.variance or 0.0),
                },
                actor_id=data.actor_id,
            )
        )

    return Output(result=closure)
