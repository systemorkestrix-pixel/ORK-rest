from __future__ import annotations

from sqlalchemy import and_, or_

from app.enums import OrderStatus, PaymentStatus
from app.models import Order

TERMINAL_ORDER_STATUSES = (
    OrderStatus.DELIVERED.value,
    OrderStatus.CANCELED.value,
    OrderStatus.DELIVERY_FAILED.value,
)

ORDER_STATUS_ACTION_ROUTE: dict[str, str] = {
    OrderStatus.CREATED.value: "/manager/orders?status=CREATED",
    OrderStatus.CONFIRMED.value: "/manager/orders?status=CONFIRMED",
    OrderStatus.SENT_TO_KITCHEN.value: "/manager/kitchen-monitor",
    OrderStatus.IN_PREPARATION.value: "/manager/kitchen-monitor",
    OrderStatus.READY.value: "/manager/orders?status=READY",
    OrderStatus.OUT_FOR_DELIVERY.value: "/manager/delivery-team",
    OrderStatus.DELIVERY_FAILED.value: "/manager/orders?status=DELIVERY_FAILED",
    OrderStatus.DELIVERED.value: "/manager/orders?status=DELIVERED",
    OrderStatus.CANCELED.value: "/manager/orders?status=CANCELED",
}

OPERATIONAL_HEART_QUEUE_CONFIG: list[dict[str, object]] = [
    {
        "key": "created",
        "label": "بانتظار التأكيد",
        "statuses": (OrderStatus.CREATED.value,),
        "sla_seconds": 5 * 60,
        "action_route": "/manager/orders?status=CREATED",
    },
    {
        "key": "confirmed",
        "label": "مؤكد بانتظار المطبخ",
        "statuses": (OrderStatus.CONFIRMED.value,),
        "sla_seconds": 7 * 60,
        "action_route": "/manager/orders?status=CONFIRMED",
    },
    {
        "key": "kitchen",
        "label": "داخل المطبخ",
        "statuses": (OrderStatus.SENT_TO_KITCHEN.value, OrderStatus.IN_PREPARATION.value),
        "sla_seconds": 20 * 60,
        "action_route": "/manager/kitchen-monitor",
    },
    {
        "key": "ready",
        "label": "جاهز للتسليم",
        "statuses": (OrderStatus.READY.value,),
        "sla_seconds": 10 * 60,
        "action_route": "/manager/orders?status=READY",
    },
    {
        "key": "out_for_delivery",
        "label": "خارج للتوصيل",
        "statuses": (OrderStatus.OUT_FOR_DELIVERY.value,),
        "sla_seconds": 30 * 60,
        "action_route": "/manager/delivery-team",
    },
]

OPERATIONAL_HEART_TIMELINE_LIMIT = 24
OPERATIONAL_HEART_KITCHEN_WAIT_WARN_SECONDS = 10 * 60
OPERATIONAL_HEART_KITCHEN_WAIT_CRITICAL_SECONDS = 20 * 60
OPERATIONAL_HEART_FINANCIAL_VARIANCE_WARN = 200.0
OPERATIONAL_HEART_FINANCIAL_VARIANCE_CRITICAL = 1000.0
OPERATIONAL_HEART_EXPENSE_HIGH_VALUE_CRITICAL = 50000.0
OPERATIONAL_HEART_EXPENSE_PENDING_TOTAL_CRITICAL = 150000.0
OPERATIONAL_HEART_CONTRACT_VERSION = "2.1"


def _table_session_open_condition():
    return or_(
        Order.status.notin_(TERMINAL_ORDER_STATUSES),
        and_(
            Order.status == OrderStatus.DELIVERED.value,
            Order.payment_status != PaymentStatus.PAID.value,
        ),
    )
