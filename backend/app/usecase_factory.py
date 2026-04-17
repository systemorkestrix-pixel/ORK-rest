from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import TypeVar

from fastapi import Request
from sqlalchemy.orm import Session

from app.tx import transaction_scope
from core.events.event_bus import EventBus
from infrastructure.repositories import (
    CoreRepository,
    DeliveryRepository,
    FinancialRepository,
    IntelligenceRepository,
    OperationsRepository,
    OrdersRepository,
    WarehouseRepository,
)

TOutput = TypeVar("TOutput")


def build_transaction_scope(db: Session) -> Callable[[], AbstractContextManager[None]]:
    def _scope() -> AbstractContextManager[None]:
        return transaction_scope(db)

    return _scope


def get_event_bus_from_request(request: Request | None) -> EventBus | None:
    if request is None:
        return None
    return getattr(request.app.state, "event_bus", None)


def build_orders_repository(db: Session) -> OrdersRepository:
    return OrdersRepository(db)


def build_core_repository(db: Session) -> CoreRepository:
    return CoreRepository(db)


def build_operations_repository(db: Session) -> OperationsRepository:
    return OperationsRepository(db)


def build_delivery_repository(db: Session) -> DeliveryRepository:
    return DeliveryRepository(db)


def build_warehouse_repository(db: Session) -> WarehouseRepository:
    return WarehouseRepository(db)


def build_financial_repository(db: Session) -> FinancialRepository:
    return FinancialRepository(db)


def build_intelligence_repository(db: Session) -> IntelligenceRepository:
    return IntelligenceRepository(db)


def run_use_case(
    *,
    execute: Callable[..., TOutput],
    data: object,
    repo: object,
    db: Session,
    request: Request | None = None,
    event_bus: EventBus | None = None,
) -> TOutput:
    bus = event_bus or get_event_bus_from_request(request)
    return execute(
        data=data,
        repo=repo,
        transaction_scope=build_transaction_scope(db),
        event_bus=bus,
    )
