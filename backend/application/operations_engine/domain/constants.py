from __future__ import annotations

ORDER_CANCELLATION_REASONS: dict[str, str] = {
    "customer_request": "طلب العميل",
    "duplicate_order": "طلب مكرر",
    "item_unavailable": "نفاد صنف",
    "payment_issue": "تعذر الدفع",
    "operational_issue": "ظرف تشغيلي",
}

KITCHEN_DISABLED_MESSAGE = "نظام المطبخ غير مفعّل في النسخة الحالية."
DELIVERY_DISABLED_MESSAGE = "نظام التوصيل غير مفعّل في النسخة الحالية."

SYSTEM_ORDER_ACTOR_PREFIX = "__actor__:"
SYSTEM_ORDER_ACTORS: dict[str, dict[str, str]] = {
    "public": {
        "username": "__actor__:public",
        "name": "Public",
    },
    "anonymous": {
        "username": "__actor__:anonymous",
        "name": "Anonymous",
    },
    "system": {
        "username": "__actor__:system",
        "name": "System",
    },
}
