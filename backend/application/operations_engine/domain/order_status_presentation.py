from __future__ import annotations

from app.enums import OrderStatus, OrderType, PaymentStatus

ORDER_STATUS_ARABIC_LABELS: dict[OrderStatus, str] = {
    OrderStatus.CREATED: "تم الإنشاء",
    OrderStatus.CONFIRMED: "تم التأكيد",
    OrderStatus.SENT_TO_KITCHEN: "أرسل للمطبخ",
    OrderStatus.IN_PREPARATION: "قيد التحضير",
    OrderStatus.READY: "جاهز",
    OrderStatus.OUT_FOR_DELIVERY: "خرج للتوصيل",
    OrderStatus.DELIVERED: "تم التسليم",
    OrderStatus.DELIVERY_FAILED: "فشل التوصيل",
    OrderStatus.CANCELED: "ملغى",
}


def resolve_manager_order_status_label(
    status: OrderStatus | str,
    order_type: OrderType | str | None = None,
    payment_status: PaymentStatus | str | None = None,
) -> str:
    status_value = status if isinstance(status, OrderStatus) else OrderStatus(str(status))
    order_type_value = order_type if isinstance(order_type, OrderType) or order_type is None else OrderType(str(order_type))
    payment_status_value = (
        payment_status if isinstance(payment_status, PaymentStatus) or payment_status is None else PaymentStatus(str(payment_status))
    )

    if status_value != OrderStatus.DELIVERED:
        return ORDER_STATUS_ARABIC_LABELS[status_value]

    if order_type_value == OrderType.DINE_IN:
        return "تمت التسوية" if payment_status_value == PaymentStatus.PAID else "تم التقديم"
    if order_type_value == OrderType.TAKEAWAY:
        return "تم الاستلام"
    return "تم التسليم"


def resolve_customer_order_status_label(
    status: OrderStatus | str,
    order_type: OrderType | str,
    payment_status: PaymentStatus | str | None = None,
) -> str:
    status_value = status if isinstance(status, OrderStatus) else OrderStatus(str(status))
    order_type_value = order_type if isinstance(order_type, OrderType) else OrderType(str(order_type))

    if status_value == OrderStatus.CREATED:
        return "تم استلام الطلب"
    if status_value in {OrderStatus.CONFIRMED, OrderStatus.SENT_TO_KITCHEN}:
        return "تم تأكيد الطلبية"
    if status_value == OrderStatus.IN_PREPARATION:
        return "قيد التحضير"
    if status_value == OrderStatus.READY:
        if order_type_value == OrderType.DELIVERY:
            return "جاهز للخروج"
        if order_type_value == OrderType.DINE_IN:
            return "جاهز للتقديم"
        return "جاهز للاستلام"
    if status_value == OrderStatus.OUT_FOR_DELIVERY:
        return "خرج للتوصيل"
    if status_value == OrderStatus.DELIVERY_FAILED:
        return "تعذر التوصيل"
    if status_value == OrderStatus.CANCELED:
        return "ملغى"
    return resolve_manager_order_status_label(status_value, order_type_value, payment_status)


def resolve_driver_task_status_label(
    *,
    order_status: OrderStatus | str,
    assignment_status: str | None = None,
    dispatch_status: str | None = None,
) -> str:
    order_status_value = order_status if isinstance(order_status, OrderStatus) else OrderStatus(str(order_status))

    if dispatch_status == "offered":
        return "عرض جديد"
    if assignment_status == "assigned":
        return "جاهز للانطلاق"
    if assignment_status == "departed" or order_status_value == OrderStatus.OUT_FOR_DELIVERY:
        return "خرج للتوصيل"
    if assignment_status == "delivered" or order_status_value == OrderStatus.DELIVERED:
        return "تم التسليم"
    if assignment_status == "failed" or order_status_value == OrderStatus.DELIVERY_FAILED:
        return "فشل التوصيل"
    return "بانتظار الإجراء التالي"
