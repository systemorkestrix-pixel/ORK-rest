from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import OrderStatus
from app.models import Order, OrderTransitionLog, SecurityAuditEvent, SystemAuditLog
from app.orchestration.service_bridge import (
    app_daily_report,
    app_financial_snapshot,
    app_monthly_report,
    app_operational_heart_dashboard,
    app_peak_hours_performance_report,
    app_period_comparison_report,
    app_prep_performance_report,
    app_profitability_report,
    app_report_by_order_type,
)


class IntelligenceRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_dashboard(self) -> dict[str, object]:
        counts = {
            row[0]: row[1]
            for row in self._db.execute(select(Order.status, func.count(Order.id)).group_by(Order.status)).all()
        }
        active_statuses = (
            OrderStatus.CREATED.value,
            OrderStatus.CONFIRMED.value,
            OrderStatus.SENT_TO_KITCHEN.value,
            OrderStatus.IN_PREPARATION.value,
            OrderStatus.READY.value,
            OrderStatus.OUT_FOR_DELIVERY.value,
        )
        active_orders = self._db.execute(
            select(func.count(Order.id)).where(Order.status.in_(active_statuses))
        ).scalar_one()
        snapshot = app_financial_snapshot(
            self._db,
            start_date=datetime.now().date(),
            end_date=datetime.now().date(),
        )
        return {
            "created": counts.get(OrderStatus.CREATED.value, 0),
            "confirmed": counts.get(OrderStatus.CONFIRMED.value, 0),
            "sent_to_kitchen": counts.get(OrderStatus.SENT_TO_KITCHEN.value, 0),
            "in_preparation": counts.get(OrderStatus.IN_PREPARATION.value, 0),
            "ready": counts.get(OrderStatus.READY.value, 0),
            "out_for_delivery": counts.get(OrderStatus.OUT_FOR_DELIVERY.value, 0),
            "delivered": counts.get(OrderStatus.DELIVERED.value, 0),
            "delivery_failed": counts.get(OrderStatus.DELIVERY_FAILED.value, 0),
            "canceled": counts.get(OrderStatus.CANCELED.value, 0),
            "active_orders": active_orders,
            "today_sales": float(snapshot["sales"] or 0.0),
            "today_expenses": float(snapshot["expenses"] or 0.0),
            "today_net": float(snapshot["net"] or 0.0),
        }

    def get_operational_heart(self) -> dict[str, object]:
        return app_operational_heart_dashboard(self._db)

    def report_daily(self, *, offset: int, limit: int) -> list[dict[str, float | str]]:
        return app_daily_report(self._db, offset=offset, limit=limit)

    def report_monthly(self, *, offset: int, limit: int) -> list[dict[str, float | str]]:
        return app_monthly_report(self._db, offset=offset, limit=limit)

    def report_by_order_type(self) -> list[dict[str, float | str | int]]:
        return app_report_by_order_type(self._db)

    def report_performance(self) -> float:
        return app_prep_performance_report(self._db)

    def report_profitability(self, *, start_date, end_date) -> dict[str, object]:
        return app_profitability_report(self._db, start_date=start_date, end_date=end_date)

    def report_period_comparison(self, *, start_date, end_date) -> dict[str, object]:
        return app_period_comparison_report(self._db, start_date=start_date, end_date=end_date)

    def report_peak_hours_performance(self, *, start_date, end_date) -> dict[str, object]:
        return app_peak_hours_performance_report(self._db, start_date=start_date, end_date=end_date)

    def list_order_audit(self, *, offset: int, limit: int) -> list[OrderTransitionLog]:
        return (
            self._db.execute(
                select(OrderTransitionLog)
                .order_by(OrderTransitionLog.timestamp.desc())
                .offset(offset)
                .limit(limit)
            )
            .scalars()
            .all()
        )

    def list_system_audit(self, *, offset: int, limit: int) -> list[SystemAuditLog]:
        return (
            self._db.execute(
                select(SystemAuditLog)
                .order_by(SystemAuditLog.timestamp.desc(), SystemAuditLog.id.desc())
                .offset(offset)
                .limit(limit)
            )
            .scalars()
            .all()
        )

    def list_security_audit(self, *, offset: int, limit: int) -> list[SecurityAuditEvent]:
        return (
            self._db.execute(
                select(SecurityAuditEvent)
                .order_by(SecurityAuditEvent.created_at.desc(), SecurityAuditEvent.id.desc())
                .offset(offset)
                .limit(limit)
            )
            .scalars()
            .all()
        )
