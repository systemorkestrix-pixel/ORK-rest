from fastapi import HTTPException, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.enums import UserRole
from app.models import (
    DeliveryAssignment,
    DeliveryDriver,
    DeliveryProvider,
    Expense,
    FinancialTransaction,
    Order,
    OrderTransitionLog,
    RefreshToken,
    ResourceMovement,
    SystemSetting,
    User,
    WarehouseInboundVoucher,
    WarehouseOutboundVoucher,
    WarehouseStockCount,
    WarehouseStockLedger,
)
from app.permissions import (
    ROLE_DEFAULT_PERMISSIONS,
    effective_permissions,
    normalize_overrides_for_role,
    parse_permission_overrides,
    permissions_catalog,
    role_assignable_permissions,
    serialize_permission_overrides,
)
from app.security import hash_password
from app.tx import transaction_scope

from application.core_engine.domain.auth import (
    record_security_event,
    revoke_active_refresh_tokens_for_user,
    validate_password_policy,
)
from application.core_engine.domain.helpers import record_system_audit
from application.operations_engine.domain import (
    ensure_kitchen_capacity_reduction_allowed,
)


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستخدم غير موجود.")
    return user


def list_permissions_catalog(*, role: str | None = None) -> list[dict[str, object]]:
    defaults = set(ROLE_DEFAULT_PERMISSIONS.get(role or "", set()))
    rows = permissions_catalog(role=role)
    return [
        {
            **item,
            "default_enabled": bool(item["code"] in defaults),
        }
        for item in rows
    ]


def get_user_permissions_profile(db: Session, *, user_id: int) -> dict[str, object]:
    user = get_user_or_404(db, user_id)
    parsed = parse_permission_overrides(user.permission_overrides_json)
    allow, deny = normalize_overrides_for_role(
        role=user.role,
        allow=parsed["allow"],
        deny=parsed["deny"],
    )
    return {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "default_permissions": sorted(role_assignable_permissions(user.role)),
        "allow_overrides": allow,
        "deny_overrides": deny,
        "effective_permissions": sorted(effective_permissions(user.role, user.permission_overrides_json)),
    }


def update_user_permissions_profile(
    db: Session,
    *,
    user_id: int,
    allow: list[str],
    deny: list[str],
    actor_id: int,
) -> dict[str, object]:
    user = get_user_or_404(db, user_id)
    normalized_allow, normalized_deny = normalize_overrides_for_role(
        role=user.role,
        allow=allow,
        deny=deny,
    )
    previous = parse_permission_overrides(user.permission_overrides_json)
    previous_allow, previous_deny = normalize_overrides_for_role(
        role=user.role,
        allow=previous["allow"],
        deny=previous["deny"],
    )
    serialized = serialize_permission_overrides(allow=normalized_allow, deny=normalized_deny)

    with transaction_scope(db):
        user.permission_overrides_json = serialized
        record_system_audit(
            db,
            module="users",
            action="update_user_permissions",
            entity_type="user",
            entity_id=user.id,
            user_id=actor_id,
            description=(
                f"تحديث صلاحيات المستخدم {user.username}: "
                f"السماح {len(previous_allow)}->{len(normalized_allow)}، "
                f"المنع {len(previous_deny)}->{len(normalized_deny)}."
            ),
        )
    return get_user_permissions_profile(db, user_id=user_id)


def create_user(
    db: Session,
    *,
    name: str,
    username: str,
    password: str,
    role: str,
    active: bool,
    delivery_phone: str | None = None,
    delivery_vehicle: str | None = None,
    actor_id: int | None = None,
) -> User:
    existing = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اسم المستخدم مستخدم بالفعل.")
    validate_password_policy(password=password, username=username)

    user = User(
        name=name,
        username=username,
        password_hash=hash_password(password),
        role=role,
        active=active,
    )
    with transaction_scope(db):
        db.add(user)
        db.flush()
        if actor_id is not None:
            record_system_audit(
                db,
                module="users",
                action="create_user",
                entity_type="user",
                entity_id=user.id,
                user_id=actor_id,
                description=f"إنشاء مستخدم: {username} (الدور: {role}).",
            )
    return user


def update_user(
    db: Session,
    *,
    user_id: int,
    name: str,
    role: str,
    active: bool,
    password: str | None = None,
    delivery_phone: str | None = None,
    delivery_vehicle: str | None = None,
    actor_id: int | None = None,
    allow_manager_self_update: bool = False,
) -> User:
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستخدم غير موجود.")
    is_manager_self_update = bool(
        allow_manager_self_update and actor_id is not None and int(actor_id) == int(user.id)
    )
    if user.username == "manager":
        if role != user.role or active != user.active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لا يمكن تعديل دور أو حالة حساب المدير الأساسي.",
            )
        if name != user.name and not is_manager_self_update:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لا يمكن تعديل اسم حساب المدير الأساسي من إدارة المستخدمين.",
            )

    linked_provider = db.execute(
        select(DeliveryProvider).where(DeliveryProvider.account_user_id == user_id)
    ).scalar_one_or_none()
    old_counts_as_kitchen = user.role == UserRole.KITCHEN.value and bool(user.active)
    new_counts_as_kitchen = role == UserRole.KITCHEN.value and active

    if old_counts_as_kitchen and not new_counts_as_kitchen:
        ensure_kitchen_capacity_reduction_allowed(db)
    if linked_provider is not None and role != UserRole.DELIVERY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="هذا المستخدم مرتبط بلوحة جهة توصيل، ولا يمكن تغيير دوره قبل فك الربط عن الجهة.",
        )

    old_name = user.name
    old_role = user.role
    old_active = bool(user.active)
    password_changed = bool(password)

    with transaction_scope(db):
        user.name = name
        user.role = role
        user.active = active
        if password:
            validate_password_policy(password=password, username=user.username)
            user.password_hash = hash_password(password)
            revoked_sessions_count = revoke_active_refresh_tokens_for_user(db, user_id=user.id)
        else:
            revoked_sessions_count = 0
        existing_overrides = parse_permission_overrides(user.permission_overrides_json)
        normalized_allow, normalized_deny = normalize_overrides_for_role(
            role=role,
            allow=existing_overrides["allow"],
            deny=existing_overrides["deny"],
        )
        user.permission_overrides_json = serialize_permission_overrides(
            allow=normalized_allow,
            deny=normalized_deny,
        )

        if actor_id is not None:
            changed_fields: list[str] = []
            if old_name != name:
                changed_fields.append("الاسم")
            if old_role != role:
                changed_fields.append("الدور")
            if old_active != bool(active):
                changed_fields.append("الحالة")
            if password_changed:
                changed_fields.append("كلمة المرور")
                changed_fields.append(f"إنهاء الجلسات النشطة ({revoked_sessions_count})")
            if not changed_fields:
                changed_fields.append("بدون تغييرات جوهرية")
            record_system_audit(
                db,
                module="users",
                action="update_user",
                entity_type="user",
                entity_id=user.id,
                user_id=actor_id,
                description=f"تحديث المستخدم {user.username}: {', '.join(changed_fields)}.",
            )
        if password_changed:
            actor_user = db.execute(select(User).where(User.id == actor_id)).scalar_one_or_none() if actor_id else None
            record_security_event(
                db,
                event_type="password_changed",
                success=True,
                severity="warning",
                username=user.username,
                role=user.role,
                user_id=user.id,
                detail=(
                    f"تم تغيير كلمة المرور"
                    + (f" بواسطة {actor_user.username}." if actor_user else ".")
                    + (f" وتم إنهاء {revoked_sessions_count} جلسة نشطة." if revoked_sessions_count > 0 else "")
                ),
            )

    return user


def delete_user_permanently(
    db: Session,
    *,
    user_id: int,
    actor_id: int,
) -> None:
    user = get_user_or_404(db, user_id)
    driver = db.execute(select(DeliveryDriver).where(DeliveryDriver.user_id == user_id)).scalar_one_or_none()
    linked_provider = db.execute(
        select(DeliveryProvider).where(DeliveryProvider.account_user_id == user_id)
    ).scalar_one_or_none()
    if user.id == actor_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يمكنك حذف حسابك الحالي.")
    if user.username == "manager":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يمكن حذف حساب المدير الأساسي.")
    if user.role == UserRole.KITCHEN.value and user.active:
        ensure_kitchen_capacity_reduction_allowed(db)
    deleted_user_label = f"{user.username} ({user.name})"

    if user.role == UserRole.MANAGER.value and user.active:
        active_managers = int(
            db.execute(
                select(func.count(User.id)).where(
                    User.role == UserRole.MANAGER.value,
                    User.active.is_(True),
                )
            ).scalar_one()
            or 0
        )
        if active_managers <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لا يمكن حذف آخر مدير نشط.",
            )

    reference_checks = [
        (select(Order.id).where(Order.paid_by == user_id).limit(1), "مدفوعات الطلبات"),
        (
            select(Order.id).where(Order.delivery_team_notified_by == user_id).limit(1),
            "إشعارات فريق التوصيل",
        ),
        (select(ResourceMovement.id).where(ResourceMovement.created_by == user_id).limit(1), "حركات الموارد"),
        (
            select(WarehouseInboundVoucher.id).where(WarehouseInboundVoucher.received_by == user_id).limit(1),
            "سندات الوارد",
        ),
        (
            select(WarehouseOutboundVoucher.id).where(WarehouseOutboundVoucher.issued_by == user_id).limit(1),
            "سندات المنصرف",
        ),
        (
            select(WarehouseStockLedger.id).where(WarehouseStockLedger.created_by == user_id).limit(1),
            "قيود مخزون المستودع",
        ),
        (
            select(WarehouseStockCount.id)
            .where(
                or_(
                    WarehouseStockCount.counted_by == user_id,
                    WarehouseStockCount.settled_by == user_id,
                )
            )
            .limit(1),
            "جرد المخزون",
        ),
        (
            select(OrderTransitionLog.id).where(OrderTransitionLog.performed_by == user_id).limit(1),
            "انتقالات الطلبات",
        ),
        (
            select(FinancialTransaction.id).where(FinancialTransaction.created_by == user_id).limit(1),
            "الحركات المالية",
        ),
        (select(Expense.id).where(Expense.created_by == user_id).limit(1), "المصروفات"),
        (select(SystemSetting.key).where(SystemSetting.updated_by == user_id).limit(1), "إعدادات النظام"),
    ]
    for stmt, label in reference_checks:
        if db.execute(stmt).scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"لا يمكن حذف المستخدم لوجود مراجع مرتبطة في {label}.",
            )

    if driver is not None:
        has_driver_assignments = (
            db.execute(
                select(DeliveryAssignment.id).where(DeliveryAssignment.driver_id == driver.id).limit(1)
            ).scalar_one_or_none()
            is not None
        )
        if has_driver_assignments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لا يمكن حذف المستخدم لوجود مهام توصيل مرتبطة بالسائق.",
            )
    if linked_provider is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن حذف المستخدم لأنه مرتبط بلوحة جهة توصيل. فك الربط أولًا من إعدادات جهة التوصيل.",
        )

    with transaction_scope(db):
        db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
        if driver:
            db.delete(driver)
        db.delete(user)
        record_system_audit(
            db,
            module="users",
            action="delete_user",
            entity_type="user",
            entity_id=user_id,
            user_id=actor_id,
            description=f"حذف مستخدم: {deleted_user_label}.",
        )
