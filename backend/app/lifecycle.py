from .enums import OrderStatus, OrderType
from application.operations_engine.domain.workflow_profiles import (
    OperationalWorkflowProfile,
    is_delivery_managed_profile,
    is_kitchen_managed_profile,
)


KITCHEN_MANAGED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.CREATED: {OrderStatus.CONFIRMED, OrderStatus.CANCELED},
    OrderStatus.CONFIRMED: {OrderStatus.SENT_TO_KITCHEN, OrderStatus.CANCELED},
    OrderStatus.SENT_TO_KITCHEN: {OrderStatus.IN_PREPARATION},
    OrderStatus.IN_PREPARATION: {OrderStatus.READY},
    OrderStatus.READY: {OrderStatus.CANCELED, OrderStatus.DELIVERED, OrderStatus.OUT_FOR_DELIVERY},
    OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED, OrderStatus.DELIVERY_FAILED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.DELIVERY_FAILED: set(),
    OrderStatus.CANCELED: set(),
}

BASE_DIRECT_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.CREATED: {OrderStatus.CONFIRMED, OrderStatus.CANCELED},
    OrderStatus.CONFIRMED: {OrderStatus.READY, OrderStatus.CANCELED},
    OrderStatus.SENT_TO_KITCHEN: set(),
    OrderStatus.IN_PREPARATION: set(),
    OrderStatus.READY: {OrderStatus.CANCELED, OrderStatus.DELIVERED, OrderStatus.OUT_FOR_DELIVERY},
    OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED, OrderStatus.DELIVERY_FAILED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.DELIVERY_FAILED: set(),
    OrderStatus.CANCELED: set(),
}


def _validate_transition_map(
    transitions: dict[OrderStatus, set[OrderStatus]],
    canonical_sequence: tuple[OrderStatus, ...],
    *,
    name: str,
) -> list[str]:
    errors: list[str] = []
    for source, target in zip(canonical_sequence, canonical_sequence[1:]):
        if target not in transitions[source]:
            errors.append(f"[{name}] Missing canonical transition: {source.value} -> {target.value}")
    return errors


_TRANSITION_MAP_ERRORS = [
    *_validate_transition_map(
        KITCHEN_MANAGED_TRANSITIONS,
        (
            OrderStatus.CREATED,
            OrderStatus.CONFIRMED,
            OrderStatus.SENT_TO_KITCHEN,
            OrderStatus.IN_PREPARATION,
            OrderStatus.READY,
            OrderStatus.DELIVERED,
        ),
        name="kitchen_managed",
    ),
    *_validate_transition_map(
        BASE_DIRECT_TRANSITIONS,
        (
            OrderStatus.CREATED,
            OrderStatus.CONFIRMED,
            OrderStatus.READY,
            OrderStatus.DELIVERED,
        ),
        name="base_direct",
    ),
]
if _TRANSITION_MAP_ERRORS:
    raise RuntimeError(f"Invalid lifecycle transition map: {_TRANSITION_MAP_ERRORS}")


def _transition_map_for_profile(profile: OperationalWorkflowProfile | str) -> dict[OrderStatus, set[OrderStatus]]:
    if is_kitchen_managed_profile(profile):
        return KITCHEN_MANAGED_TRANSITIONS
    return BASE_DIRECT_TRANSITIONS


def can_transition(
    current: OrderStatus,
    target: OrderStatus,
    order_type: OrderType,
    workflow_profile: OperationalWorkflowProfile | str,
) -> bool:
    transitions = _transition_map_for_profile(workflow_profile)
    if target not in transitions[current]:
        return False

    if current == OrderStatus.READY and target == OrderStatus.OUT_FOR_DELIVERY:
        return order_type == OrderType.DELIVERY and is_delivery_managed_profile(workflow_profile)
    if current == OrderStatus.READY and target == OrderStatus.DELIVERED:
        if order_type == OrderType.DELIVERY:
            return not is_delivery_managed_profile(workflow_profile)
        return True
    if current == OrderStatus.OUT_FOR_DELIVERY:
        return order_type == OrderType.DELIVERY and is_delivery_managed_profile(workflow_profile)
    return True
