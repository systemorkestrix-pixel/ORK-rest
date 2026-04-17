"""
Use Case: CreateInboundVoucher (Inventory Engine)
"""
from dataclasses import dataclass
from typing import Protocol


class TransactionScope(Protocol):
    def __call__(self):
        ...


class WarehouseRepository(Protocol):
    def create_inbound_voucher(self, *args, **kwargs):
        ...


@dataclass
class InboundItemInput:
    item_id: int
    quantity: float
    unit_cost: float


@dataclass
class Input:
    supplier_id: int
    reference_no: str | None
    note: str | None
    idempotency_key: str | None
    items: list[InboundItemInput]
    actor_id: int


@dataclass
class Output:
    voucher_id: int
    voucher_no: str


def execute(*, data: Input, repo: WarehouseRepository, transaction_scope: TransactionScope) -> Output:
    with transaction_scope():
        voucher = repo.create_inbound_voucher(data)
    return Output(voucher_id=int(voucher["id"]), voucher_no=str(voucher["voucher_no"]))
