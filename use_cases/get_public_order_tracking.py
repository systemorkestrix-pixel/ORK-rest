from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import PublicOrderTrackingOut
from application.operations_engine.domain.workflow_profiles import resolve_public_workflow_profile
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def get_public_order_tracking(self, *, tracking_code: str):
        ...

    def get_operational_capabilities(self) -> dict[str, object]:
        ...


@dataclass
class Input:
    tracking_code: str


@dataclass
class Output:
    result: PublicOrderTrackingOut | None


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    order = repo.get_public_order_tracking(tracking_code=data.tracking_code)
    if order is None:
        return Output(result=None)
    capabilities = repo.get_operational_capabilities()
    workflow_profile = resolve_public_workflow_profile(
        activation_stage_id=str(capabilities.get("activation_stage_id") or "base"),
        kitchen_feature_enabled=bool(capabilities.get("kitchen_feature_enabled", True)),
        order_type=order.type,
        current_status=order.status,
    )
    return Output(
        result=PublicOrderTrackingOut(
            tracking_code=order.tracking_code,
            type=order.type,
            status=order.status,
            workflow_profile=workflow_profile,
            payment_status=order.payment_status,
            created_at=order.created_at,
            subtotal=order.subtotal,
            delivery_fee=order.delivery_fee,
            total=order.total,
            notes=order.notes,
            items=list(order.items),
        )
    )
