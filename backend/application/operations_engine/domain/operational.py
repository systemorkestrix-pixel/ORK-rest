from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import DriverStatus, OrderStatus, OrderType, UserRole
from app.models import DeliveryDriver, Order, User, WarehouseItem, WarehouseSupplier
from application.core_engine.domain.settings import get_operational_feature_flags
from application.operations_engine.domain.constants import (
    DELIVERY_DISABLED_MESSAGE,
    KITCHEN_DISABLED_MESSAGE,
    SYSTEM_ORDER_ACTORS,
)
from application.operations_engine.domain.workflow_profiles import resolve_operational_workflow_profile

KITCHEN_FEATURE_DISABLED_MESSAGE = "تم إيقاف وحدة المطبخ من إعدادات النظام."
DELIVERY_FEATURE_DISABLED_MESSAGE = "تم إيقاف وحدة التوصيل من إعدادات النظام."
WAREHOUSE_DISABLED_MESSAGE = "المستودع غير مهيأ بعد. أضف موردًا وصنفًا نشطًا على الأقل قبل تفعيل أدواته."
WAREHOUSE_FEATURE_DISABLED_MESSAGE = "تم إيقاف وحدة المستودع من إعدادات النظام."


def get_or_create_system_order_actor_id(
    db: Session,
    *,
    actor_key: str,
    transaction_scope,
    hash_password,
) -> int:
    actor_meta = SYSTEM_ORDER_ACTORS.get(actor_key, SYSTEM_ORDER_ACTORS["system"])
    existing_id = db.execute(
        select(User.id).where(User.username == actor_meta["username"])
    ).scalars().first()
    if existing_id is not None:
        return int(existing_id)

    with transaction_scope(db):
        existing = db.execute(
            select(User.id).where(User.username == actor_meta["username"])
        ).scalars().first()
        if existing is not None:
            return int(existing)

        actor_user = User(
            name=actor_meta["name"],
            username=actor_meta["username"],
            password_hash=hash_password(f"{uuid4().hex}-system-actor"),
            role=UserRole.MANAGER.value,
            active=False,
        )
        db.add(actor_user)
        db.flush()
        return int(actor_user.id)


def resolve_order_creator_id(
    db: Session,
    created_by: int | None,
    *,
    fallback_actor: str,
    transaction_scope,
    hash_password,
) -> int | None:
    if created_by is not None:
        return created_by
    return get_or_create_system_order_actor_id(
        db,
        actor_key=fallback_actor,
        transaction_scope=transaction_scope,
        hash_password=hash_password,
    )


def count_active_role_users(db: Session, *, role: UserRole) -> int:
    return int(
        db.execute(
            select(func.count(User.id)).where(
                User.role == role.value,
                User.active.is_(True),
            )
        ).scalar_one()
        or 0
    )


def count_active_delivery_users(db: Session) -> int:
    return int(
        db.execute(
            select(func.count(DeliveryDriver.id))
            .select_from(DeliveryDriver)
            .where(
                DeliveryDriver.active.is_(True),
                DeliveryDriver.status != DriverStatus.INACTIVE.value,
            )
        ).scalar_one()
        or 0
    )


def count_active_warehouse_suppliers(db: Session) -> int:
    return int(
        db.execute(
            select(func.count(WarehouseSupplier.id)).where(
                WarehouseSupplier.active.is_(True),
            )
        ).scalar_one()
        or 0
    )


def count_active_warehouse_items(db: Session) -> int:
    return int(
        db.execute(
            select(func.count(WarehouseItem.id)).where(
                WarehouseItem.active.is_(True),
            )
        ).scalar_one()
        or 0
    )


def _has_blocking_orders_for_kitchen_shutdown(db: Session) -> bool:
    blocking_statuses = (
        OrderStatus.SENT_TO_KITCHEN.value,
        OrderStatus.IN_PREPARATION.value,
    )
    return (
        db.execute(
            select(Order.id).where(Order.status.in_(blocking_statuses)).limit(1)
        ).scalar_one_or_none()
        is not None
    )


def _has_blocking_orders_for_delivery_shutdown(db: Session) -> bool:
    blocking_statuses = (
        OrderStatus.SENT_TO_KITCHEN.value,
        OrderStatus.IN_PREPARATION.value,
        OrderStatus.READY.value,
        OrderStatus.OUT_FOR_DELIVERY.value,
    )
    return (
        db.execute(
            select(Order.id)
            .where(
                Order.type == OrderType.DELIVERY.value,
                Order.status.in_(blocking_statuses),
            )
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )


def ensure_kitchen_capacity_reduction_allowed(db: Session) -> None:
    active_kitchen_users = count_active_role_users(db, role=UserRole.KITCHEN)
    if active_kitchen_users > 1:
        return
    if not _has_blocking_orders_for_kitchen_shutdown(db):
        return
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="لا يمكن تعطيل آخر مستخدم مطبخ نشط مع وجود طلبات قيد المطبخ. عيّن بديلًا أولًا.",
    )


def ensure_delivery_capacity_reduction_allowed(db: Session) -> None:
    active_delivery_users = count_active_delivery_users(db)
    if active_delivery_users > 1:
        return
    if not _has_blocking_orders_for_delivery_shutdown(db):
        return
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="لا يمكن تعطيل آخر عنصر توصيل نشط مع وجود طلبات توصيل جارية. عيّن بديلًا أولًا.",
    )


def get_operational_capabilities(db: Session) -> dict[str, object]:
    kitchen_active_users = count_active_role_users(db, role=UserRole.KITCHEN)
    delivery_active_users = count_active_delivery_users(db)
    warehouse_active_suppliers = count_active_warehouse_suppliers(db)
    warehouse_active_items = count_active_warehouse_items(db)
    feature_flags = get_operational_feature_flags(db)

    activation_stage_id = "base"

    try:
        from app.tenant_runtime import infer_tenant_record_from_session
        from application.master_engine.domain.catalog import capability_modes_for_stage

        tenant = infer_tenant_record_from_session(db)
        if tenant is not None:
            activation_stage_id = str(tenant.plan_id or "base")
            capability_modes = capability_modes_for_stage(str(tenant.plan_id))
            feature_flags = {
                **feature_flags,
                "kitchen_feature_enabled": bool(feature_flags["kitchen_feature_enabled"])
                and capability_modes.get("kitchen", "disabled") == "core",
                "delivery_feature_enabled": bool(feature_flags["delivery_feature_enabled"])
                and capability_modes.get("delivery", "disabled") == "core",
                "warehouse_feature_enabled": bool(feature_flags.get("warehouse_feature_enabled", True))
                and capability_modes.get("warehouse", "disabled") == "core",
            }
    except Exception:
        # If tenant context is unavailable, keep the local feature flags unchanged.
        pass

    kitchen_feature_enabled = bool(feature_flags["kitchen_feature_enabled"])
    delivery_feature_enabled = bool(feature_flags["delivery_feature_enabled"])
    warehouse_feature_enabled = bool(feature_flags.get("warehouse_feature_enabled", True))
    kitchen_runtime_enabled = kitchen_active_users > 0
    delivery_runtime_enabled = delivery_active_users > 0
    warehouse_runtime_enabled = warehouse_active_suppliers > 0 and warehouse_active_items > 0

    kitchen_enabled = kitchen_feature_enabled and kitchen_runtime_enabled
    delivery_enabled = delivery_feature_enabled and delivery_runtime_enabled
    warehouse_enabled = warehouse_feature_enabled and warehouse_runtime_enabled
    workflow_profile = resolve_operational_workflow_profile(activation_stage_id=activation_stage_id)

    kitchen_block_reason = None
    if not kitchen_enabled:
        kitchen_block_reason = (
            KITCHEN_FEATURE_DISABLED_MESSAGE
            if not kitchen_feature_enabled
            else KITCHEN_DISABLED_MESSAGE
        )

    delivery_block_reason = None
    if not delivery_enabled:
        delivery_block_reason = (
            DELIVERY_FEATURE_DISABLED_MESSAGE
            if not delivery_feature_enabled
            else DELIVERY_DISABLED_MESSAGE
        )

    warehouse_block_reason = None
    if not warehouse_enabled:
        warehouse_block_reason = (
            WAREHOUSE_FEATURE_DISABLED_MESSAGE
            if not warehouse_feature_enabled
            else WAREHOUSE_DISABLED_MESSAGE
        )

    return {
        "activation_stage_id": activation_stage_id,
        "workflow_profile": workflow_profile,
        "kitchen_feature_enabled": kitchen_feature_enabled,
        "delivery_feature_enabled": delivery_feature_enabled,
        "warehouse_feature_enabled": warehouse_feature_enabled,
        "kitchen_runtime_enabled": kitchen_runtime_enabled,
        "delivery_runtime_enabled": delivery_runtime_enabled,
        "warehouse_runtime_enabled": warehouse_runtime_enabled,
        "kitchen_enabled": kitchen_enabled,
        "delivery_enabled": delivery_enabled,
        "warehouse_enabled": warehouse_enabled,
        "kitchen_active_users": kitchen_active_users,
        "delivery_active_users": delivery_active_users,
        "warehouse_active_suppliers": warehouse_active_suppliers,
        "warehouse_active_items": warehouse_active_items,
        "kitchen_block_reason": kitchen_block_reason,
        "delivery_block_reason": delivery_block_reason,
        "warehouse_block_reason": warehouse_block_reason,
    }


def ensure_kitchen_operational(db: Session) -> None:
    capabilities = get_operational_capabilities(db)
    if capabilities["kitchen_enabled"]:
        return
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(capabilities["kitchen_block_reason"] or KITCHEN_DISABLED_MESSAGE),
    )


def ensure_delivery_operational(db: Session) -> None:
    capabilities = get_operational_capabilities(db)
    if capabilities["delivery_enabled"]:
        return
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(capabilities["delivery_block_reason"] or DELIVERY_DISABLED_MESSAGE),
    )
