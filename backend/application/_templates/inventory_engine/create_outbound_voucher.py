"""
Use Case: CreateOutboundVoucher (Inventory Engine)
"""
from dataclasses import dataclass
from typing import Protocol


class TransactionScope(Protocol):
    def __call__(self):
        ...


class WarehouseRepository(Protocol):
    def create_outbound_voucher(self, *args, **kwargs):
        ...


@dataclass
class OutboundItemInput:
    item_id: int
    quantity: float


@dataclass
class Input:
    reason_code: str
    reason_note: str | None
    note: str | None
    idempotency_key: str | None
    items: list[OutboundItemInput]
    actor_id: int


@dataclass
class Output:
    voucher_id: int
    voucher_no: str


def execute(*, data: Input, repo: WarehouseRepository, transaction_scope: TransactionScope) -> Output:
    with transaction_scope():
        voucher = repo.create_outbound_voucher(data)
    return Output(voucher_id=int(voucher["id"]), voucher_no=str(voucher["voucher_no"]))
