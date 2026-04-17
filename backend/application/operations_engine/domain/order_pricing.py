from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OrderLinePricing:
    product_id: int
    quantity: float
    unit_price: float
    line_total: float


@dataclass(frozen=True)
class OrderPricing:
    subtotal: float
    delivery_fee: float
    total: float
    lines: list[OrderLinePricing]


def calculate_order_pricing(
    *,
    items: list[tuple[int, float, float]],
    delivery_fee: float,
) -> OrderPricing:
    """
    Domain-level pricing calculator.
    items: list of (product_id, quantity, unit_price)
    """
    subtotal = 0.0
    lines: list[OrderLinePricing] = []
    for product_id, quantity, unit_price in items:
        safe_qty = float(quantity)
        safe_price = float(unit_price)
        line_total = safe_qty * safe_price
        subtotal += line_total
        lines.append(
            OrderLinePricing(
                product_id=int(product_id),
                quantity=safe_qty,
                unit_price=safe_price,
                line_total=line_total,
            )
        )

    delivery_fee_value = float(delivery_fee)
    total = subtotal + delivery_fee_value
    return OrderPricing(
        subtotal=subtotal,
        delivery_fee=delivery_fee_value,
        total=total,
        lines=lines,
    )
