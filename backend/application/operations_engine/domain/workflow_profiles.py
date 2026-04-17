from __future__ import annotations

from typing import Literal

from app.enums import OrderStatus, OrderType
from application.master_engine.domain.catalog import addon_sequence, normalize_stage_id

PublicWorkflowProfile = Literal["kitchen_managed", "direct_fulfillment", "direct_delivery"]
OperationalWorkflowProfile = Literal["base_direct", "kitchen_managed", "kitchen_delivery_managed"]

_KITCHEN_SEQUENCE = addon_sequence("kitchen")
_DELIVERY_SEQUENCE = addon_sequence("delivery")


def _normalize_order_type(order_type: OrderType | str | None) -> str:
    if isinstance(order_type, OrderType):
        return order_type.value
    return str(order_type or "").strip().lower()


def _normalize_status(current_status: OrderStatus | str | None) -> str:
    if isinstance(current_status, OrderStatus):
        return current_status.value
    return str(current_status or "").strip().upper()


def stage_has_kitchen_workflow(stage_id: str | None) -> bool:
    return addon_sequence(normalize_stage_id(stage_id)) >= _KITCHEN_SEQUENCE


def stage_has_delivery_workflow(stage_id: str | None) -> bool:
    return addon_sequence(normalize_stage_id(stage_id)) >= _DELIVERY_SEQUENCE


def resolve_operational_workflow_profile(
    *,
    activation_stage_id: str | None,
    order_type: OrderType | str | None = None,
) -> OperationalWorkflowProfile:
    order_type_value = _normalize_order_type(order_type)
    normalized_stage_id = normalize_stage_id(activation_stage_id)

    if stage_has_delivery_workflow(normalized_stage_id) and order_type_value == OrderType.DELIVERY.value:
        return "kitchen_delivery_managed"
    if stage_has_kitchen_workflow(normalized_stage_id):
        return "kitchen_managed"
    return "base_direct"


def is_kitchen_managed_profile(profile: OperationalWorkflowProfile | str) -> bool:
    return str(profile) in {"kitchen_managed", "kitchen_delivery_managed"}


def is_delivery_managed_profile(profile: OperationalWorkflowProfile | str) -> bool:
    return str(profile) == "kitchen_delivery_managed"


def resolve_public_workflow_profile(
    *,
    activation_stage_id: str | None = None,
    kitchen_feature_enabled: bool | None = None,
    order_type: OrderType | str | None = None,
    current_status: OrderStatus | str | None = None,
) -> PublicWorkflowProfile:
    status_value = _normalize_status(current_status)
    order_type_value = _normalize_order_type(order_type)

    if status_value in {
        OrderStatus.SENT_TO_KITCHEN.value,
        OrderStatus.IN_PREPARATION.value,
    }:
        return "kitchen_managed"

    if activation_stage_id is not None:
        if stage_has_kitchen_workflow(activation_stage_id):
            return "kitchen_managed"
    elif bool(kitchen_feature_enabled):
        return "kitchen_managed"

    if order_type_value == OrderType.DELIVERY.value:
        return "direct_delivery"

    return "direct_fulfillment"
