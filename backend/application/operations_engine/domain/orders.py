from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import OrderStatus, OrderType, PaymentStatus, ProductKind, TableStatus
from app.models import DeliveryAssignment, DeliveryDispatch, DeliveryDriver, DeliveryProvider, DeliverySettlement, Order, OrderItem
from app.schemas import CreateOrderInput
from application.operations_engine.domain.order_pricing import calculate_order_pricing


def create_order(
    db: Session,
    *,
    payload: CreateOrderInput,
    created_by: int | None,
    source_actor: str,
    ensure_delivery_operational,
    fetch_products,
    get_table,
    resolve_order_creator_id,
    get_delivery_policy_settings,
    resolve_delivery_pricing,
    record_transition,
) -> Order:
    if payload.type == OrderType.DELIVERY:
        ensure_delivery_operational(db)

    product_ids = [item.product_id for item in payload.items]
    products = fetch_products(
        db,
        product_ids=product_ids,
        sellable_kind=ProductKind.PRIMARY.value,
    )
    product_map = {product.id: product for product in products}

    missing_products = [pid for pid in product_ids if pid not in product_map]
    if missing_products:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"هذه المنتجات غير متاحة: {missing_products}",
        )

    table = None
    if payload.table_id is not None:
        table = get_table(db, payload.table_id)

    actor_id = resolve_order_creator_id(db, created_by, fallback_actor=source_actor)
    delivery_policy = (
        get_delivery_policy_settings(db)
        if payload.type == OrderType.DELIVERY
        else {"min_order_amount": 0.0, "auto_notify_team": False}
    )
    delivery_pricing = (
        resolve_delivery_pricing(db, location_key=payload.delivery_location_key)
        if payload.type == OrderType.DELIVERY
        else {
            "delivery_fee": 0.0,
            "location_key": None,
            "location_label": None,
            "location_level": None,
            "location_snapshot_json": None,
        }
    )
    fixed_delivery_fee = float(delivery_pricing["delivery_fee"])

    order = Order(
        type=payload.type.value,
        status=OrderStatus.CREATED.value,
        table_id=payload.table_id,
        phone=payload.phone,
        address=payload.address,
        delivery_location_key=delivery_pricing["location_key"],
        delivery_location_label=delivery_pricing["location_label"],
        delivery_location_level=delivery_pricing["location_level"],
        delivery_location_snapshot_json=delivery_pricing["location_snapshot_json"],
        notes=payload.notes,
        subtotal=0,
        delivery_fee=fixed_delivery_fee,
        payment_status=PaymentStatus.UNPAID.value,
        payment_method="cash",
    )
    db.add(order)
    db.flush()

    pricing_items = [
        (item.product_id, item.quantity, float(product_map[item.product_id].price))
        for item in payload.items
    ]
    pricing = calculate_order_pricing(
        items=pricing_items,
        delivery_fee=fixed_delivery_fee,
    )
    for raw_item in payload.items:
        product = product_map[raw_item.product_id]
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=raw_item.quantity,
                price=product.price,
                product_name=product.name,
            )
        )

    order.subtotal = pricing.subtotal
    if payload.type == OrderType.DELIVERY and pricing.subtotal < float(delivery_policy["min_order_amount"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"الحد الأدنى لطلبات التوصيل هو {float(delivery_policy['min_order_amount']):.2f} د.ج.",
        )
    order.total = pricing.total
    if payload.type == OrderType.DINE_IN and table is not None:
        table.status = TableStatus.OCCUPIED.value
    if actor_id is not None:
        record_transition(
            db,
            order_id=order.id,
            from_status=OrderStatus.CREATED.value,
            to_status=OrderStatus.CREATED.value,
            user_id=actor_id,
        )

    return order


def attach_sent_to_kitchen_at(
    db: Session,
    orders: list[Order],
    *,
    fetch_sent_to_kitchen_timestamps,
) -> list[Order]:
    if not orders:
        return orders

    order_ids = [order.id for order in orders]
    sent_map = fetch_sent_to_kitchen_timestamps(
        db,
        order_ids=order_ids,
        sent_to_kitchen_status=OrderStatus.SENT_TO_KITCHEN.value,
    )
    settlements = db.execute(
        select(DeliverySettlement).where(DeliverySettlement.order_id.in_(order_ids))
    ).scalars().all()
    settlement_map = {int(settlement.order_id): settlement for settlement in settlements}
    assignment_rows = db.execute(
        select(
            DeliveryAssignment.order_id,
            DeliveryAssignment.driver_id,
            DeliveryAssignment.status,
            DeliveryDriver.name,
            DeliveryAssignment.assigned_at,
            DeliveryAssignment.departed_at,
            DeliveryAssignment.delivered_at,
        )
        .outerjoin(DeliveryDriver, DeliveryDriver.id == DeliveryAssignment.driver_id)
        .where(DeliveryAssignment.order_id.in_(order_ids))
        .order_by(DeliveryAssignment.order_id.asc(), DeliveryAssignment.id.desc())
    ).all()
    assignment_map: dict[
        int,
        tuple[
            int | None,
            str | None,
            str | None,
            datetime | None,
            datetime | None,
            datetime | None,
        ],
    ] = {}
    for order_id, driver_id, assignment_status, driver_name, assigned_at, departed_at, delivered_at in assignment_rows:
        normalized_order_id = int(order_id)
        if normalized_order_id not in assignment_map:
            assignment_map[normalized_order_id] = (
                int(driver_id) if driver_id is not None else None,
                str(assignment_status) if assignment_status is not None else None,
                str(driver_name) if driver_name else None,
                assigned_at,
                departed_at,
                delivered_at,
            )

    dispatch_rows = db.execute(
        select(
            DeliveryDispatch.order_id,
            DeliveryDispatch.id,
            DeliveryDispatch.status,
            DeliveryDispatch.dispatch_scope,
            DeliveryDispatch.provider_id,
            DeliveryProvider.name,
            DeliveryDispatch.driver_id,
            DeliveryDriver.name,
            DeliveryDispatch.sent_at,
            DeliveryDispatch.responded_at,
        )
        .outerjoin(DeliveryProvider, DeliveryProvider.id == DeliveryDispatch.provider_id)
        .outerjoin(DeliveryDriver, DeliveryDriver.id == DeliveryDispatch.driver_id)
        .where(DeliveryDispatch.order_id.in_(order_ids))
        .order_by(DeliveryDispatch.order_id.asc(), DeliveryDispatch.id.desc())
    ).all()
    dispatch_map: dict[
        int,
        tuple[
            int | None,
            str | None,
            str | None,
            int | None,
            str | None,
            int | None,
            str | None,
            datetime | None,
            datetime | None,
        ],
    ] = {}
    for (
        order_id,
        dispatch_id,
        dispatch_status,
        dispatch_scope,
        provider_id,
        provider_name,
        driver_id,
        driver_name,
        sent_at,
        responded_at,
    ) in dispatch_rows:
        normalized_order_id = int(order_id)
        if normalized_order_id not in dispatch_map:
            dispatch_map[normalized_order_id] = (
                int(dispatch_id) if dispatch_id is not None else None,
                str(dispatch_status) if dispatch_status is not None else None,
                str(dispatch_scope) if dispatch_scope is not None else None,
                int(provider_id) if provider_id is not None else None,
                str(provider_name) if provider_name else None,
                int(driver_id) if driver_id is not None else None,
                str(driver_name) if driver_name else None,
                sent_at,
                responded_at,
            )

    for order in orders:
        setattr(order, "sent_to_kitchen_at", sent_map.get(order.id))
        settlement = settlement_map.get(int(order.id))
        assignment = assignment_map.get(int(order.id))
        dispatch = dispatch_map.get(int(order.id))
        assignment_driver_id = assignment[0] if assignment is not None else None
        assignment_status = assignment[1] if assignment is not None else None
        assignment_driver_name = assignment[2] if assignment is not None else None
        assignment_assigned_at = assignment[3] if assignment is not None else None
        assignment_departed_at = assignment[4] if assignment is not None else None
        assignment_delivered_at = assignment[5] if assignment is not None else None

        # Only expose assignment context while it still represents the current delivery cycle.
        # Historical failed/delivered assignments should not block a new dispatch/retry cycle.
        if assignment_status in {"failed", "delivered"} and str(order.status) not in {
            OrderStatus.DELIVERY_FAILED.value,
            OrderStatus.DELIVERED.value,
            OrderStatus.OUT_FOR_DELIVERY.value,
        }:
            assignment_driver_id = None
            assignment_status = None
            assignment_driver_name = None
            assignment_assigned_at = None
            assignment_departed_at = None
            assignment_delivered_at = None

        setattr(order, "delivery_settlement_id", int(settlement.id) if settlement is not None else None)
        setattr(order, "delivery_settlement_status", settlement.status if settlement is not None else None)
        setattr(
            order,
            "delivery_settlement_remaining_store_due_amount",
            float(settlement.remaining_store_due_amount) if settlement is not None else None,
        )
        setattr(order, "delivery_assignment_status", assignment_status)
        setattr(order, "delivery_assignment_driver_id", assignment_driver_id)
        setattr(order, "delivery_assignment_driver_name", assignment_driver_name)
        setattr(order, "delivery_assignment_assigned_at", assignment_assigned_at)
        setattr(order, "delivery_assignment_departed_at", assignment_departed_at)
        setattr(order, "delivery_assignment_delivered_at", assignment_delivered_at)
        setattr(order, "delivery_dispatch_id", dispatch[0] if dispatch is not None else None)
        setattr(order, "delivery_dispatch_status", dispatch[1] if dispatch is not None else None)
        setattr(order, "delivery_dispatch_scope", dispatch[2] if dispatch is not None else None)
        setattr(order, "delivery_dispatch_provider_id", dispatch[3] if dispatch is not None else None)
        setattr(order, "delivery_dispatch_provider_name", dispatch[4] if dispatch is not None else None)
        setattr(order, "delivery_dispatch_driver_id", dispatch[5] if dispatch is not None else None)
        setattr(order, "delivery_dispatch_driver_name", dispatch[6] if dispatch is not None else None)
        setattr(order, "delivery_dispatch_sent_at", dispatch[7] if dispatch is not None else None)
        setattr(order, "delivery_dispatch_responded_at", dispatch[8] if dispatch is not None else None)
    return orders
