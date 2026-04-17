from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from app.models import DeliverySettlement
from app.schemas import DeliverySettlementOut


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def record_driver_remittance(
        self,
        *,
        settlement_id: int,
        amount: float,
        performed_by: int,
        cash_channel: str,
        note: str | None,
    ) -> DeliverySettlement:
        ...

    def record_driver_payout(
        self,
        *,
        settlement_id: int,
        amount: float,
        performed_by: int,
        cash_channel: str,
        note: str | None,
    ) -> DeliverySettlement:
        ...


@dataclass
class Input:
    actor_id: int
    settlement_id: int
    amount: float
    movement_type: Literal["remittance", "payout"]
    cash_channel: str = "cash_drawer"
    note: str | None = None


@dataclass
class Output:
    result: DeliverySettlementOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus=None,
) -> Output:
    with transaction_scope():
        if data.movement_type == "payout":
            settlement = repo.record_driver_payout(
                settlement_id=data.settlement_id,
                amount=data.amount,
                performed_by=data.actor_id,
                cash_channel=data.cash_channel,
                note=data.note,
            )
        else:
            settlement = repo.record_driver_remittance(
                settlement_id=data.settlement_id,
                amount=data.amount,
                performed_by=data.actor_id,
                cash_channel=data.cash_channel,
                note=data.note,
            )
    return Output(result=settlement)
