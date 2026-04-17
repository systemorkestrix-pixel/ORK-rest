"""
Event Handler: ORDER_DELIVERED
"""
import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from application._shared.event_audit import record_event_audit
from app.database import SessionLocal
from app.enums import FinancialTransactionType, OrderType, PaymentStatus
from app.models import Order
from app.repositories.financial_repository import (
    create_financial_transaction,
    find_latest_order_transaction_by_type,
)
from app.tx import transaction_scope
from core.events.event_bus import DomainEvent

logger = logging.getLogger(__name__)


def handle(event: DomainEvent) -> None:
    order_id = event.payload.get("order_id")
    actor_id = event.actor_id
    if not order_id or actor_id is None:
        return

    db = SessionLocal()
    try:
        order = db.execute(select(Order).where(Order.id == int(order_id))).scalar_one_or_none()
        if order is None:
            return
        if order.type == OrderType.DELIVERY.value:
            return
        if order.payment_status != PaymentStatus.PAID.value:
            return

        existing = find_latest_order_transaction_by_type(
            db,
            order_id=int(order_id),
            tx_type=FinancialTransactionType.SALE.value,
        )
        if existing is None:
            try:
                with transaction_scope(db):
                    create_financial_transaction(
                        db,
                        order_id=int(order_id),
                        delivery_settlement_id=None,
                        expense_id=None,
                        amount=float(order.total or 0.0),
                        tx_type=FinancialTransactionType.SALE.value,
                        direction=None,
                        account_code=None,
                        reference_group=f"event:order_delivered:{order_id}",
                        created_by=int(actor_id),
                        note="Auto sale transaction from OrderDelivered event.",
                    )
            except IntegrityError:
                db.rollback()

        record_event_audit(
            module="event_bus",
            action=event.name,
            entity_type="order",
            entity_id=int(order_id),
            actor_id=actor_id,
            description=f"Order delivered financial check. order_id={order_id}",
            occurred_at=event.occurred_at,
        )
    except Exception:
        logger.exception("Failed to handle ORDER_DELIVERED for order_id=%s", order_id)
    finally:
        db.close()
