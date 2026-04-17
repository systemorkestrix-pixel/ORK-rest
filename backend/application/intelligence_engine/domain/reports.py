from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import Float, and_, case, cast, func, select, text
from sqlalchemy.orm import Session

from app.enums import CashboxMovementDirection, FinancialTransactionType, OrderStatus, OrderType, PaymentStatus
from app.models import (
    CashboxMovement,
    FinancialTransaction,
    Order,
    OrderCostEntry,
    OrderItem,
    OrderTransitionLog,
    Product,
    WarehouseOutboundVoucher,
    WarehouseStockLedger,
)

from application.core_engine.domain.helpers import normalize_offset_limit


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


DETAILED_FOOD_REVENUE_TYPES = (
    FinancialTransactionType.FOOD_REVENUE.value,
    FinancialTransactionType.REFUND_FOOD_REVENUE.value,
)
DETAILED_DELIVERY_REVENUE_TYPES = (
    FinancialTransactionType.DELIVERY_REVENUE.value,
    FinancialTransactionType.REFUND_DELIVERY_REVENUE.value,
)
DETAILED_DRIVER_COST_TYPES = (
    FinancialTransactionType.DRIVER_PAYABLE.value,
    FinancialTransactionType.REVERSE_DRIVER_PAYABLE.value,
)


def _signed_financial_amount_case(*, positive_types: tuple[str, ...], negative_types: tuple[str, ...] = ()) -> object:
    whens: list[tuple[object, object]] = []
    if positive_types:
        whens.append((FinancialTransaction.type.in_(positive_types), FinancialTransaction.amount))
    if negative_types:
        whens.append((FinancialTransaction.type.in_(negative_types), -FinancialTransaction.amount))
    return case(*whens, else_=0.0)


def _apply_date_window(stmt, *, start_date: date | None, end_date: date | None, column) -> object:
    if start_date is not None:
        stmt = stmt.where(func.date(column, "localtime") >= start_date.isoformat())
    if end_date is not None:
        stmt = stmt.where(func.date(column, "localtime") <= end_date.isoformat())
    return stmt


def financial_snapshot(
    db: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, float | int]:
    tx_stmt = select(
        func.coalesce(func.sum(_signed_financial_amount_case(positive_types=(FinancialTransactionType.FOOD_REVENUE.value, FinancialTransactionType.SALE.value), negative_types=(FinancialTransactionType.REFUND_FOOD_REVENUE.value,))), 0.0).label("food_sales"),
        func.coalesce(func.sum(_signed_financial_amount_case(positive_types=(FinancialTransactionType.DELIVERY_REVENUE.value,), negative_types=(FinancialTransactionType.REFUND_DELIVERY_REVENUE.value,))), 0.0).label("delivery_revenue"),
        func.coalesce(func.sum(_signed_financial_amount_case(positive_types=(FinancialTransactionType.DRIVER_PAYABLE.value,), negative_types=(FinancialTransactionType.REVERSE_DRIVER_PAYABLE.value,))), 0.0).label("driver_cost"),
        func.coalesce(func.sum(_signed_financial_amount_case(positive_types=(FinancialTransactionType.EXPENSE.value,))), 0.0).label("operating_expenses"),
        func.coalesce(func.sum(_signed_financial_amount_case(positive_types=(FinancialTransactionType.REFUND.value,))), 0.0).label("refunds"),
    )
    tx_stmt = _apply_date_window(tx_stmt, start_date=start_date, end_date=end_date, column=FinancialTransaction.created_at)
    tx_row = db.execute(tx_stmt).one()

    cash_stmt = select(
        func.coalesce(
            func.sum(case((CashboxMovement.direction == CashboxMovementDirection.IN.value, CashboxMovement.amount), else_=0.0)),
            0.0,
        ).label("cash_in"),
        func.coalesce(
            func.sum(case((CashboxMovement.direction == CashboxMovementDirection.OUT.value, CashboxMovement.amount), else_=0.0)),
            0.0,
        ).label("cash_out"),
        func.count(CashboxMovement.id).label("cashbox_transactions_count"),
    )
    cash_stmt = _apply_date_window(cash_stmt, start_date=start_date, end_date=end_date, column=CashboxMovement.created_at)
    cash_row = db.execute(cash_stmt).one()

    order_stmt = (
        select(func.count(Order.id))
        .where(
            Order.status == OrderStatus.DELIVERED.value,
            Order.payment_status != PaymentStatus.REFUNDED.value,
            Order.accounting_recognized_at.is_not(None),
        )
    )
    order_stmt = _apply_date_window(order_stmt, start_date=start_date, end_date=end_date, column=Order.accounting_recognized_at)
    delivered_orders_count = int(db.execute(order_stmt).scalar_one() or 0)

    food_sales = float(tx_row.food_sales or 0.0)
    delivery_revenue = float(tx_row.delivery_revenue or 0.0)
    driver_cost = float(tx_row.driver_cost or 0.0)
    operating_expenses = float(tx_row.operating_expenses or 0.0)
    refunds = float(tx_row.refunds or 0.0)
    gross_revenue = food_sales + delivery_revenue
    total_expenses = driver_cost + operating_expenses
    net = gross_revenue - total_expenses
    avg_order_value = gross_revenue / delivered_orders_count if delivered_orders_count > 0 else 0.0

    return {
        "food_sales": round(food_sales, 2),
        "delivery_revenue": round(delivery_revenue, 2),
        "driver_cost": round(driver_cost, 2),
        "operating_expenses": round(operating_expenses, 2),
        "refunds": round(refunds, 2),
        "sales": round(gross_revenue, 2),
        "expenses": round(total_expenses, 2),
        "net": round(net, 2),
        "cash_in": round(float(cash_row.cash_in or 0.0), 2),
        "cash_out": round(float(cash_row.cash_out or 0.0), 2),
        "cashbox_transactions_count": int(cash_row.cashbox_transactions_count or 0),
        "delivered_orders_count": delivered_orders_count,
        "avg_order_value": round(avg_order_value, 2),
    }


def daily_report(
    db: Session,
    *,
    offset: int = 0,
    limit: int | None = None,
) -> list[dict[str, float | str]]:
    safe_offset, safe_limit = normalize_offset_limit(offset=offset, limit=limit, max_limit=3650)
    revenue_sub = (
        select(
            func.date(FinancialTransaction.created_at, "localtime").label("day"),
            func.sum(
                _signed_financial_amount_case(
                    positive_types=(FinancialTransactionType.FOOD_REVENUE.value,),
                    negative_types=(FinancialTransactionType.REFUND_FOOD_REVENUE.value,),
                )
            ).label("food_sales"),
            func.sum(
                _signed_financial_amount_case(
                    positive_types=(FinancialTransactionType.DELIVERY_REVENUE.value,),
                    negative_types=(FinancialTransactionType.REFUND_DELIVERY_REVENUE.value,),
                )
            ).label("delivery_revenue"),
            func.sum(
                _signed_financial_amount_case(
                    positive_types=(FinancialTransactionType.DRIVER_PAYABLE.value,),
                    negative_types=(FinancialTransactionType.REVERSE_DRIVER_PAYABLE.value,),
                )
            ).label("driver_cost"),
            func.sum(
                _signed_financial_amount_case(positive_types=(FinancialTransactionType.EXPENSE.value,))
            ).label("operating_expenses"),
            func.sum(
                _signed_financial_amount_case(positive_types=(FinancialTransactionType.REFUND.value,))
            ).label("refunds"),
        )
        .group_by(func.date(FinancialTransaction.created_at, "localtime"))
        .subquery()
    )
    cash_sub = (
        select(
            func.date(CashboxMovement.created_at, "localtime").label("day"),
            func.sum(case((CashboxMovement.direction == CashboxMovementDirection.IN.value, CashboxMovement.amount), else_=0.0)).label("cash_in"),
            func.sum(case((CashboxMovement.direction == CashboxMovementDirection.OUT.value, CashboxMovement.amount), else_=0.0)).label("cash_out"),
        )
        .group_by(func.date(CashboxMovement.created_at, "localtime"))
        .subquery()
    )

    days_sub = select(revenue_sub.c.day.label("day")).union(
        select(cash_sub.c.day.label("day"))
    ).subquery()

    days_stmt = (
        select(
            days_sub.c.day.label("day"),
            func.coalesce(revenue_sub.c.food_sales, 0.0).label("food_sales"),
            func.coalesce(revenue_sub.c.delivery_revenue, 0.0).label("delivery_revenue"),
            func.coalesce(revenue_sub.c.driver_cost, 0.0).label("driver_cost"),
            func.coalesce(revenue_sub.c.operating_expenses, 0.0).label("operating_expenses"),
            func.coalesce(revenue_sub.c.refunds, 0.0).label("refunds"),
            func.coalesce(cash_sub.c.cash_in, 0.0).label("cash_in"),
            func.coalesce(cash_sub.c.cash_out, 0.0).label("cash_out"),
        )
        .select_from(
            days_sub
            .outerjoin(revenue_sub, days_sub.c.day == revenue_sub.c.day)
            .outerjoin(cash_sub, days_sub.c.day == cash_sub.c.day)
        )
        .order_by(days_sub.c.day.desc())
        .offset(safe_offset)
    )
    if safe_limit is not None:
        days_stmt = days_stmt.limit(safe_limit)
    days = db.execute(days_stmt).all()

    result: list[dict[str, float | str]] = []
    for row in days:
        food_sales = float(row.food_sales or 0.0)
        delivery_revenue = float(row.delivery_revenue or 0.0)
        driver_cost = float(row.driver_cost or 0.0)
        operating_expenses = float(row.operating_expenses or 0.0)
        gross_revenue = food_sales + delivery_revenue
        total_expenses = driver_cost + operating_expenses
        net = gross_revenue - total_expenses
        result.append(
            {
                "day": row.day,
                "food_sales": round(food_sales, 2),
                "delivery_revenue": round(delivery_revenue, 2),
                "driver_cost": round(driver_cost, 2),
                "refunds": round(float(row.refunds or 0.0), 2),
                "cash_in": round(float(row.cash_in or 0.0), 2),
                "cash_out": round(float(row.cash_out or 0.0), 2),
                "sales": round(gross_revenue, 2),
                "expenses": round(total_expenses, 2),
                "net": round(net, 2),
            }
        )
    return result

def monthly_report(
    db: Session,
    *,
    offset: int = 0,
    limit: int | None = None,
) -> list[dict[str, float | str]]:
    safe_offset, safe_limit = normalize_offset_limit(offset=offset, limit=limit, max_limit=1200)
    monthly_stmt = (
        select(
            func.strftime("%Y-%m", FinancialTransaction.created_at, "localtime").label("month"),
            func.sum(
                _signed_financial_amount_case(
                    positive_types=(FinancialTransactionType.FOOD_REVENUE.value,),
                    negative_types=(FinancialTransactionType.REFUND_FOOD_REVENUE.value,),
                )
            ).label("food_sales"),
            func.sum(
                _signed_financial_amount_case(
                    positive_types=(FinancialTransactionType.DELIVERY_REVENUE.value,),
                    negative_types=(FinancialTransactionType.REFUND_DELIVERY_REVENUE.value,),
                )
            ).label("delivery_revenue"),
            func.sum(
                _signed_financial_amount_case(
                    positive_types=(FinancialTransactionType.DRIVER_PAYABLE.value,),
                    negative_types=(FinancialTransactionType.REVERSE_DRIVER_PAYABLE.value,),
                )
            ).label("driver_cost"),
            func.sum(
                _signed_financial_amount_case(positive_types=(FinancialTransactionType.EXPENSE.value,))
            ).label("operating_expenses"),
            func.sum(
                _signed_financial_amount_case(positive_types=(FinancialTransactionType.REFUND.value,))
            ).label("refunds"),
        )
        .group_by(func.strftime("%Y-%m", FinancialTransaction.created_at, "localtime"))
        .order_by(text("month DESC"))
        .offset(safe_offset)
    )
    if safe_limit is not None:
        monthly_stmt = monthly_stmt.limit(safe_limit)
    sales = db.execute(monthly_stmt).all()
    cash_stmt = (
        select(
            func.strftime("%Y-%m", CashboxMovement.created_at, "localtime").label("month"),
            func.sum(case((CashboxMovement.direction == CashboxMovementDirection.IN.value, CashboxMovement.amount), else_=0.0)).label("cash_in"),
            func.sum(case((CashboxMovement.direction == CashboxMovementDirection.OUT.value, CashboxMovement.amount), else_=0.0)).label("cash_out"),
        )
        .group_by(func.strftime("%Y-%m", CashboxMovement.created_at, "localtime"))
    )
    cash_rows = {
        str(row.month): {"cash_in": float(row.cash_in or 0.0), "cash_out": float(row.cash_out or 0.0)}
        for row in db.execute(cash_stmt).all()
    }
    output: list[dict[str, float | str]] = []
    for row in sales:
        food_sales = float(row.food_sales or 0.0)
        delivery_revenue = float(row.delivery_revenue or 0.0)
        driver_cost = float(row.driver_cost or 0.0)
        operating_expenses = float(row.operating_expenses or 0.0)
        gross_revenue = food_sales + delivery_revenue
        total_expenses = driver_cost + operating_expenses
        cash_values = cash_rows.get(str(row.month), {"cash_in": 0.0, "cash_out": 0.0})
        output.append(
            {
                "month": row.month,
                "food_sales": round(food_sales, 2),
                "delivery_revenue": round(delivery_revenue, 2),
                "driver_cost": round(driver_cost, 2),
                "refunds": round(float(row.refunds or 0.0), 2),
                "cash_in": round(float(cash_values["cash_in"]), 2),
                "cash_out": round(float(cash_values["cash_out"]), 2),
                "sales": round(gross_revenue, 2),
                "expenses": round(total_expenses, 2),
                "net": round(gross_revenue - total_expenses, 2),
            }
        )
    return output

def report_by_order_type(db: Session) -> list[dict[str, float | str | int]]:
    rows = db.execute(
        select(
            Order.type.label("order_type"),
            func.count(func.distinct(Order.id)).label("orders_count"),
            func.sum(
                _signed_financial_amount_case(
                    positive_types=(FinancialTransactionType.FOOD_REVENUE.value,),
                    negative_types=(FinancialTransactionType.REFUND_FOOD_REVENUE.value,),
                )
            ).label("food_sales"),
            func.sum(
                _signed_financial_amount_case(
                    positive_types=(FinancialTransactionType.DELIVERY_REVENUE.value,),
                    negative_types=(FinancialTransactionType.REFUND_DELIVERY_REVENUE.value,),
                )
            ).label("delivery_revenue"),
        )
        .select_from(Order)
        .outerjoin(FinancialTransaction, FinancialTransaction.order_id == Order.id)
        .where(Order.status == OrderStatus.DELIVERED.value)
        .group_by(Order.type)
    ).all()
    return [
        {
            "order_type": row.order_type,
            "orders_count": int(row.orders_count or 0),
            "food_sales": round(float(row.food_sales or 0.0), 2),
            "delivery_revenue": round(float(row.delivery_revenue or 0.0), 2),
            "sales": round(float(row.food_sales or 0.0) + float(row.delivery_revenue or 0.0), 2),
        }
        for row in rows
    ]

def profitability_report(
    db: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, object]:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="تاريخ البداية يجب أن يكون قبل تاريخ النهاية.")

    cogs_by_order_item_sub = (
        select(
            OrderCostEntry.order_item_id.label("order_item_id"),
            func.sum(OrderCostEntry.cogs_amount).label("actual_cost"),
        )
        .group_by(OrderCostEntry.order_item_id)
        .subquery()
    )

    product_name_expr = func.coalesce(Product.name, OrderItem.product_name)
    category_name_expr = func.coalesce(Product.category, "غير مصنف")

    stmt = (
        select(
            OrderItem.product_id.label("product_id"),
            product_name_expr.label("product_name"),
            category_name_expr.label("category_name"),
            func.sum(OrderItem.quantity).label("quantity_sold"),
            func.sum(cast(OrderItem.quantity, Float) * OrderItem.price).label("revenue"),
            func.sum(func.coalesce(cogs_by_order_item_sub.c.actual_cost, 0.0)).label("actual_cost"),
        )
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .outerjoin(Product, Product.id == OrderItem.product_id)
        .outerjoin(cogs_by_order_item_sub, cogs_by_order_item_sub.c.order_item_id == OrderItem.id)
        .where(
            Order.status == OrderStatus.DELIVERED.value,
            Order.payment_status != PaymentStatus.REFUNDED.value,
        )
    )
    if start_date is not None:
        stmt = stmt.where(func.date(Order.created_at, "localtime") >= start_date.isoformat())
    if end_date is not None:
        stmt = stmt.where(func.date(Order.created_at, "localtime") <= end_date.isoformat())

    stmt = stmt.group_by(
        OrderItem.product_id,
        product_name_expr,
        category_name_expr,
    )
    rows = db.execute(stmt).all()

    by_products: list[dict[str, object]] = []
    category_bucket: dict[str, dict[str, float]] = {}
    total_quantity_sold = 0
    total_revenue = 0.0
    total_estimated_cost = 0.0

    for row in rows:
        quantity_sold = int(row.quantity_sold or 0)
        revenue = float(row.revenue or 0.0)
        actual_cost = float(row.actual_cost or 0.0)
        estimated_unit_cost = (actual_cost / quantity_sold) if quantity_sold > 0 else 0.0
        estimated_cost = actual_cost
        gross_profit = revenue - estimated_cost
        margin_percent = (gross_profit / revenue * 100.0) if revenue > 0 else 0.0

        product_payload = {
            "product_id": int(row.product_id),
            "product_name": str(row.product_name),
            "category_name": str(row.category_name),
            "quantity_sold": quantity_sold,
            "revenue": round(revenue, 2),
            "estimated_unit_cost": round(estimated_unit_cost, 4),
            "estimated_cost": round(estimated_cost, 2),
            "gross_profit": round(gross_profit, 2),
            "margin_percent": round(margin_percent, 2),
        }
        by_products.append(product_payload)

        category_key = str(row.category_name)
        bucket = category_bucket.get(category_key)
        if bucket is None:
            bucket = {"quantity_sold": 0.0, "revenue": 0.0, "estimated_cost": 0.0}
            category_bucket[category_key] = bucket
        bucket["quantity_sold"] += quantity_sold
        bucket["revenue"] += revenue
        bucket["estimated_cost"] += estimated_cost

        total_quantity_sold += quantity_sold
        total_revenue += revenue
        total_estimated_cost += estimated_cost

    by_products.sort(key=lambda item: (float(item["gross_profit"]), float(item["revenue"])), reverse=True)

    by_categories: list[dict[str, object]] = []
    for category_name, metrics in category_bucket.items():
        revenue = float(metrics["revenue"])
        estimated_cost = float(metrics["estimated_cost"])
        gross_profit = revenue - estimated_cost
        margin_percent = (gross_profit / revenue * 100.0) if revenue > 0 else 0.0
        by_categories.append(
            {
                "category_name": category_name,
                "quantity_sold": int(metrics["quantity_sold"]),
                "revenue": round(revenue, 2),
                "estimated_cost": round(estimated_cost, 2),
                "gross_profit": round(gross_profit, 2),
                "margin_percent": round(margin_percent, 2),
            }
        )
    by_categories.sort(key=lambda item: (float(item["gross_profit"]), float(item["revenue"])), reverse=True)

    total_gross_profit = total_revenue - total_estimated_cost
    total_margin_percent = (total_gross_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_quantity_sold": total_quantity_sold,
        "total_revenue": round(total_revenue, 2),
        "total_estimated_cost": round(total_estimated_cost, 2),
        "total_gross_profit": round(total_gross_profit, 2),
        "total_margin_percent": round(total_margin_percent, 2),
        "by_products": by_products,
        "by_categories": by_categories,
    }

def _period_financial_metrics(
    db: Session,
    *,
    start_date: date,
    end_date: date,
    label: str,
) -> dict[str, object]:
    snapshot = financial_snapshot(db, start_date=start_date, end_date=end_date)
    sales_value = float(snapshot["sales"])
    expenses_value = float(snapshot["expenses"])
    delivered_count = int(snapshot["delivered_orders_count"])
    avg_order_value = float(snapshot["avg_order_value"])
    return {
        "label": label,
        "start_date": start_date,
        "end_date": end_date,
        "days_count": ((end_date - start_date).days + 1),
        "food_sales": float(snapshot["food_sales"]),
        "delivery_revenue": float(snapshot["delivery_revenue"]),
        "driver_cost": float(snapshot["driver_cost"]),
        "refunds": float(snapshot["refunds"]),
        "cash_in": float(snapshot["cash_in"]),
        "cash_out": float(snapshot["cash_out"]),
        "sales": round(sales_value, 2),
        "expenses": round(expenses_value, 2),
        "net": round(sales_value - expenses_value, 2),
        "delivered_orders_count": delivered_count,
        "avg_order_value": round(avg_order_value, 2),
    }

def period_comparison_report(
    db: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, object]:
    effective_end = end_date or date.today()
    effective_start = start_date or (effective_end - timedelta(days=6))
    if effective_start > effective_end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="تاريخ البداية يجب أن يكون قبل تاريخ النهاية")

    days_count = (effective_end - effective_start).days + 1
    previous_end = effective_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=days_count - 1)

    current_period = _period_financial_metrics(
        db,
        start_date=effective_start,
        end_date=effective_end,
        label="الفترة الحالية",
    )
    previous_period = _period_financial_metrics(
        db,
        start_date=previous_start,
        end_date=previous_end,
        label="الفترة السابقة",
    )

    def build_delta(metric_key: str, metric_label: str) -> dict[str, object]:
        current_value = float(current_period[metric_key])
        previous_value = float(previous_period[metric_key])
        absolute_change = current_value - previous_value
        if previous_value == 0:
            change_percent: float | None = None
        else:
            change_percent = (absolute_change / previous_value) * 100.0
        return {
            "metric": metric_label,
            "current_value": round(current_value, 2),
            "previous_value": round(previous_value, 2),
            "absolute_change": round(absolute_change, 2),
            "change_percent": round(change_percent, 2) if change_percent is not None else None,
        }

    deltas = [
        build_delta("sales", "المبيعات"),
        build_delta("expenses", "المصروفات"),
        build_delta("net", "الصافي"),
        build_delta("delivered_orders_count", "عدد الطلبات المسلّمة"),
        build_delta("avg_order_value", "متوسط قيمة الطلب"),
    ]
    return {
        "current_period": current_period,
        "previous_period": previous_period,
        "deltas": deltas,
    }

def peak_hours_performance_report(
    db: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, object]:
    effective_end = end_date or date.today()
    effective_start = start_date or (effective_end - timedelta(days=13))
    if effective_start > effective_end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="تاريخ البداية يجب أن يكون قبل تاريخ النهاية")

    order_rows = db.execute(
        select(
            func.strftime("%H", Order.created_at, "localtime").label("hour"),
            func.count(Order.id).label("orders_count"),
            func.sum(Order.subtotal).label("food_sales"),
            func.sum(Order.delivery_fee).label("delivery_revenue"),
        )
        .where(
            Order.status == OrderStatus.DELIVERED.value,
            Order.payment_status != PaymentStatus.REFUNDED.value,
            func.date(Order.created_at, "localtime") >= effective_start.isoformat(),
            func.date(Order.created_at, "localtime") <= effective_end.isoformat(),
        )
        .group_by(func.strftime("%H", Order.created_at, "localtime"))
        .order_by(func.strftime("%H", Order.created_at, "localtime").asc())
    ).all()

    sent_sub = (
        select(
            OrderTransitionLog.order_id,
            func.min(OrderTransitionLog.timestamp).label("sent_at"),
        )
        .where(OrderTransitionLog.to_status == OrderStatus.SENT_TO_KITCHEN.value)
        .group_by(OrderTransitionLog.order_id)
        .subquery()
    )
    ready_sub = (
        select(
            OrderTransitionLog.order_id,
            func.min(OrderTransitionLog.timestamp).label("ready_at"),
        )
        .where(OrderTransitionLog.to_status == OrderStatus.READY.value)
        .group_by(OrderTransitionLog.order_id)
        .subquery()
    )

    prep_rows = db.execute(
        select(
            func.strftime("%H", sent_sub.c.sent_at, "localtime").label("hour"),
            func.avg((func.julianday(ready_sub.c.ready_at) - func.julianday(sent_sub.c.sent_at)) * 24 * 60).label("avg_prep"),
        )
        .select_from(sent_sub.join(ready_sub, sent_sub.c.order_id == ready_sub.c.order_id).join(Order, Order.id == sent_sub.c.order_id))
        .where(
            ready_sub.c.ready_at > sent_sub.c.sent_at,
            func.date(Order.created_at, "localtime") >= effective_start.isoformat(),
            func.date(Order.created_at, "localtime") <= effective_end.isoformat(),
        )
        .group_by(func.strftime("%H", sent_sub.c.sent_at, "localtime"))
    ).all()

    overall_avg_prep = db.execute(
        select(
            func.avg((func.julianday(ready_sub.c.ready_at) - func.julianday(sent_sub.c.sent_at)) * 24 * 60)
        )
        .select_from(sent_sub.join(ready_sub, sent_sub.c.order_id == ready_sub.c.order_id).join(Order, Order.id == sent_sub.c.order_id))
        .where(
            ready_sub.c.ready_at > sent_sub.c.sent_at,
            func.date(Order.created_at, "localtime") >= effective_start.isoformat(),
            func.date(Order.created_at, "localtime") <= effective_end.isoformat(),
        )
    ).scalar_one()

    prep_by_hour: dict[str, float] = {
        str(row.hour or "00").zfill(2): float(row.avg_prep or 0.0)
        for row in prep_rows
    }

    by_hours: list[dict[str, object]] = []
    for row in order_rows:
        hour = str(row.hour or "00").zfill(2)
        orders_count = int(row.orders_count or 0)
        food_sales = float(row.food_sales or 0.0)
        delivery_revenue = float(row.delivery_revenue or 0.0)
        sales = food_sales + delivery_revenue
        avg_order_value = (sales / orders_count) if orders_count > 0 else 0.0
        by_hours.append(
            {
                "hour_label": f"{hour}:00 - {hour}:59",
                "orders_count": orders_count,
                "food_sales": round(food_sales, 2),
                "delivery_revenue": round(delivery_revenue, 2),
                "sales": round(sales, 2),
                "avg_order_value": round(avg_order_value, 2),
                "avg_prep_minutes": round(prep_by_hour.get(hour, 0.0), 2),
            }
        )

    peak_row = max(
        by_hours,
        key=lambda item: (int(item["orders_count"]), float(item["sales"])),
        default=None,
    )
    return {
        "start_date": effective_start,
        "end_date": effective_end,
        "days_count": (effective_end - effective_start).days + 1,
        "peak_hour": str(peak_row["hour_label"]) if peak_row is not None else None,
        "peak_orders_count": int(peak_row["orders_count"]) if peak_row is not None else 0,
        "peak_sales": round(float(peak_row["sales"]), 2) if peak_row is not None else 0.0,
        "overall_avg_prep_minutes": round(float(overall_avg_prep or 0.0), 2),
        "by_hours": by_hours,
    }

def prep_performance_report(db: Session) -> float:
    sent_sub = (
        select(
            OrderTransitionLog.order_id,
            func.min(OrderTransitionLog.timestamp).label("sent_at"),
        )
        .where(OrderTransitionLog.to_status == OrderStatus.SENT_TO_KITCHEN.value)
        .group_by(OrderTransitionLog.order_id)
        .subquery()
    )
    ready_sub = (
        select(
            OrderTransitionLog.order_id,
            func.min(OrderTransitionLog.timestamp).label("ready_at"),
        )
        .where(OrderTransitionLog.to_status == OrderStatus.READY.value)
        .group_by(OrderTransitionLog.order_id)
        .subquery()
    )

    avg_minutes = db.execute(
        select(
            func.avg(
                (
                    func.julianday(ready_sub.c.ready_at) - func.julianday(sent_sub.c.sent_at)
                )
                * 24
                * 60
            )
        )
        .select_from(sent_sub.join(ready_sub, sent_sub.c.order_id == ready_sub.c.order_id))
        .where(ready_sub.c.ready_at > sent_sub.c.sent_at)
    ).scalar_one()

    return float(avg_minutes or 0.0)

def _resolve_kitchen_metrics_window_start(metrics_window: Literal["day", "week", "month"]) -> date:
    today = datetime.now().date()
    if metrics_window == "week":
        return today - timedelta(days=today.weekday())
    if metrics_window == "month":
        return today.replace(day=1)
    return today


def kitchen_monitor_summary(
    db: Session,
    *,
    metrics_window: Literal["day", "week", "month"] = "day",
) -> dict[str, int | float | str]:
    visible_statuses = (
        OrderStatus.SENT_TO_KITCHEN.value,
        OrderStatus.IN_PREPARATION.value,
        OrderStatus.READY.value,
    )

    count_rows = db.execute(
        select(Order.status, func.count(Order.id))
        .where(Order.status.in_(visible_statuses))
        .group_by(Order.status)
    ).all()
    counts = {str(row[0]): int(row[1] or 0) for row in count_rows}

    oldest_sent_at = db.execute(
        select(func.min(OrderTransitionLog.timestamp))
        .join(Order, Order.id == OrderTransitionLog.order_id)
        .where(
            Order.status.in_(visible_statuses),
            OrderTransitionLog.to_status == OrderStatus.SENT_TO_KITCHEN.value,
        )
    ).scalar_one()

    if oldest_sent_at is None:
        oldest_sent_at = db.execute(
            select(func.min(Order.created_at)).where(Order.status.in_(visible_statuses))
        ).scalar_one()

    oldest_order_wait_seconds = 0
    if oldest_sent_at is not None:
        oldest_order_wait_seconds = max(
            0,
            int((datetime.now(UTC) - _as_utc(oldest_sent_at)).total_seconds()),
        )

    window_start = _resolve_kitchen_metrics_window_start(metrics_window).isoformat()
    window_end = datetime.now().date().isoformat()
    sent_sub = (
        select(
            OrderTransitionLog.order_id,
            func.min(OrderTransitionLog.timestamp).label("sent_at"),
        )
        .where(OrderTransitionLog.to_status == OrderStatus.SENT_TO_KITCHEN.value)
        .group_by(OrderTransitionLog.order_id)
        .subquery()
    )
    ready_sub = (
        select(
            OrderTransitionLog.order_id,
            func.min(OrderTransitionLog.timestamp).label("ready_at"),
        )
        .where(OrderTransitionLog.to_status == OrderStatus.READY.value)
        .group_by(OrderTransitionLog.order_id)
        .subquery()
    )
    avg_prep_today = db.execute(
        select(
            func.avg(
                (
                    func.julianday(ready_sub.c.ready_at) - func.julianday(sent_sub.c.sent_at)
                )
                * 24
                * 60
            )
        )
        .select_from(sent_sub.join(ready_sub, sent_sub.c.order_id == ready_sub.c.order_id))
        .where(
            ready_sub.c.ready_at > sent_sub.c.sent_at,
            func.date(ready_sub.c.ready_at, "localtime") >= window_start,
            func.date(ready_sub.c.ready_at, "localtime") <= window_end,
        )
    ).scalar_one()

    kitchen_reason_codes = ("kitchen_supply", "operational_use")
    kitchen_outbound_quantity_today = float(
        db.execute(
            select(func.coalesce(func.sum(WarehouseStockLedger.quantity), 0.0))
            .select_from(WarehouseStockLedger)
            .join(
                WarehouseOutboundVoucher,
                and_(
                    WarehouseOutboundVoucher.id == WarehouseStockLedger.source_id,
                    WarehouseStockLedger.source_type == "wh_outbound_voucher",
                ),
            )
            .where(
                WarehouseStockLedger.movement_kind == "outbound",
                WarehouseOutboundVoucher.reason_code.in_(kitchen_reason_codes),
                func.date(WarehouseStockLedger.created_at, "localtime") >= window_start,
                func.date(WarehouseStockLedger.created_at, "localtime") <= window_end,
            )
        ).scalar_one()
        or 0.0
    )
    kitchen_outbound_vouchers_today = int(
        db.execute(
            select(func.count(WarehouseOutboundVoucher.id)).where(
                WarehouseOutboundVoucher.reason_code.in_(kitchen_reason_codes),
                func.date(WarehouseOutboundVoucher.posted_at, "localtime") >= window_start,
                func.date(WarehouseOutboundVoucher.posted_at, "localtime") <= window_end,
            )
        ).scalar_one()
        or 0
    )
    kitchen_outbound_items_today = int(
        db.execute(
            select(func.count(func.distinct(WarehouseStockLedger.item_id)))
            .select_from(WarehouseStockLedger)
            .join(
                WarehouseOutboundVoucher,
                and_(
                    WarehouseOutboundVoucher.id == WarehouseStockLedger.source_id,
                    WarehouseStockLedger.source_type == "wh_outbound_voucher",
                ),
            )
            .where(
                WarehouseStockLedger.movement_kind == "outbound",
                WarehouseOutboundVoucher.reason_code.in_(kitchen_reason_codes),
                func.date(WarehouseStockLedger.created_at, "localtime") >= window_start,
                func.date(WarehouseStockLedger.created_at, "localtime") <= window_end,
            )
        ).scalar_one()
        or 0
    )

    return {
        "sent_to_kitchen": counts.get(OrderStatus.SENT_TO_KITCHEN.value, 0),
        "in_preparation": counts.get(OrderStatus.IN_PREPARATION.value, 0),
        "ready": counts.get(OrderStatus.READY.value, 0),
        "oldest_order_wait_seconds": oldest_order_wait_seconds,
        "metrics_window": metrics_window,
        "avg_prep_minutes_today": float(avg_prep_today or 0.0),
        "warehouse_issued_quantity_today": kitchen_outbound_quantity_today,
        "warehouse_issue_vouchers_today": kitchen_outbound_vouchers_today,
        "warehouse_issued_items_today": kitchen_outbound_items_today,
    }
