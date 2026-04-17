from __future__ import annotations

from app.enums import DeliveryDispatchStatus, OrderStatus


def can_driver_accept_dispatch(*, order_status: str, dispatch_status: str | None, assignment_status: str | None) -> bool:
    return (
        order_status in {OrderStatus.IN_PREPARATION.value, OrderStatus.READY.value}
        and dispatch_status == DeliveryDispatchStatus.OFFERED.value
        and not assignment_status
    )


def is_driver_waiting_for_ready(*, order_status: str, assignment_status: str | None) -> bool:
    return order_status == OrderStatus.IN_PREPARATION.value and assignment_status == "assigned"


def can_driver_start_delivery(*, order_status: str, assignment_status: str | None) -> bool:
    return order_status == OrderStatus.READY.value and assignment_status == "assigned"


def can_driver_finish_delivery(*, order_status: str, assignment_status: str | None) -> bool:
    return order_status == OrderStatus.OUT_FOR_DELIVERY.value and assignment_status == "departed"
