from __future__ import annotations

from datetime import UTC, datetime
from datetime import timedelta
from dataclasses import dataclass
import secrets

from fastapi import HTTPException, status
from sqlalchemy import and_, exists, false, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.enums import (
    DeliveryAssignmentStatus,
    DeliveryDispatchScope,
    DeliveryDispatchStatus,
    DriverStatus,
    OrderStatus,
    OrderType,
    PaymentStatus,
    UserRole,
)
from app.models import DeliveryAssignment, DeliveryDispatch, DeliveryDriver, DeliveryProvider, DeliverySettlement, Order, User
from app.orchestration.service_bridge import (
    app_attach_sent_to_kitchen_at,
    app_claim_delivery_order,
    app_emergency_fail_delivery_order,
    app_ensure_delivery_capacity_reduction_allowed,
    app_resolve_order_creator_id,
    app_start_delivery,
)
from app.schemas import DeliveryHistoryOut
from application.delivery_engine.domain.assignments import (
    claim_delivery_order_for_driver,
    start_delivery_for_driver,
)
from application.delivery_engine.domain.completion import (
    complete_delivery as complete_delivery_domain,
    complete_delivery_for_driver,
)
from application.delivery_engine.domain.helpers import get_delivery_driver_for_user
from application.delivery_engine.domain.notifications import notify_delivery_team as notify_delivery_team_domain
from application.operations_engine.domain.helpers import (
    get_order_or_404,
    normalize_optional_text,
    record_system_audit,
    record_transition,
)


@dataclass(slots=True)
class DeliveryScope:
    provider_id: int | None
    driver_id: int | None
    driver_ids_statement: object


class DeliveryRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _push_dispatch_offer_notification(self, *, dispatch_id: int) -> None:
        from application.bot_engine.domain.telegram_delivery_bot import push_delivery_dispatch_offer

        push_delivery_dispatch_offer(db=self._db, dispatch_id=dispatch_id)

    def _push_driver_assignment_update(self, *, driver_id: int, order_id: int, event: str) -> None:
        from application.bot_engine.domain.telegram_delivery_bot import push_driver_assignment_update

        push_driver_assignment_update(
            db=self._db,
            driver_id=driver_id,
            order_id=order_id,
            event=event,
        )

    def _get_delivery_scope(
        self,
        *,
        actor_id: int,
        require_active_provider: bool,
    ) -> DeliveryScope:
        provider = self._db.execute(
            select(DeliveryProvider).where(DeliveryProvider.account_user_id == actor_id)
        ).scalar_one_or_none()
        if provider is not None:
            if require_active_provider and not provider.active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="حساب جهة التوصيل الحالي مرتبط بجهة غير نشطة.",
                )
            return DeliveryScope(
                provider_id=int(provider.id),
                driver_id=None,
                driver_ids_statement=select(DeliveryDriver.id).where(DeliveryDriver.provider_id == provider.id),
            )

        driver = get_delivery_driver_for_user(self._db, user_id=actor_id, require_active=require_active_provider)
        if driver.provider_id is not None:
            driver_ids_statement = select(DeliveryDriver.id).where(DeliveryDriver.provider_id == driver.provider_id)
        else:
            driver_ids_statement = select(DeliveryDriver.id).where(DeliveryDriver.id == driver.id)
        return DeliveryScope(
            provider_id=driver.provider_id,
            driver_id=int(driver.id),
            driver_ids_statement=driver_ids_statement,
        )

    def _resolve_driver_actor_id(self, *, driver: DeliveryDriver) -> int:
        if driver.user_id is not None:
            return int(driver.user_id)
        return int(app_resolve_order_creator_id(self._db, created_by=None, fallback_actor="system"))

    def _get_delivery_account_user_or_404(self, *, user_id: int) -> User:
        normalized_name = " ".join(name.strip().split())
        if len(normalized_name) < 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اسم السائق مطلوب.")
        linked_user_id: int | None = None
        user = self._db.execute(select(User).where(User.id == user_id)).scalar_one_or_none() if user_id is not None else None
        if user_id is not None and user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="حساب جهة التوصيل غير موجود.")
        if user is not None and user.role != UserRole.DELIVERY.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="حساب الجهة يجب أن يكون بدور لوحة جهة التوصيل.",
            )
        return user

    def _get_delivery_account_user_or_404_fixed(self, *, user_id: int) -> User:
        user = self._db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="حساب جهة التوصيل غير موجود.")
        if user.role != UserRole.DELIVERY.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="حساب الجهة يجب أن يكون بدور لوحة جهة التوصيل.",
            )
        return user

    def _validate_provider_account_user(
        self,
        *,
        account_user_id: int | None,
        provider_id: int | None = None,
        provider_type: str,
    ) -> int | None:
        if provider_type == "internal_team":
            return None
        if account_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="حساب لوحة جهة التوصيل مطلوب لهذه الجهة.",
            )
        self._get_delivery_account_user_or_404_fixed(user_id=account_user_id)
        statement = select(DeliveryProvider).where(DeliveryProvider.account_user_id == account_user_id)
        if provider_id is not None:
            statement = statement.where(DeliveryProvider.id != provider_id)
        duplicate = self._db.execute(statement).scalar_one_or_none()
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="هذا الحساب مربوط بالفعل بجهة توصيل أخرى.",
            )
        return int(account_user_id)

    def _driver_has_active_assignment(self, *, driver_id: int) -> bool:
        active_assignment = self._db.execute(
            select(DeliveryAssignment.id)
            .where(
                DeliveryAssignment.driver_id == driver_id,
                DeliveryAssignment.status.in_(
                    [
                        DeliveryAssignmentStatus.ASSIGNED.value,
                        DeliveryAssignmentStatus.DEPARTED.value,
                    ]
                ),
            )
            .order_by(DeliveryAssignment.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        return active_assignment is not None

    def _cancel_other_offered_dispatches_for_driver(
        self,
        *,
        driver_id: int,
        accepted_order_id: int,
        notify_bot: bool = True,
    ) -> None:
        now = datetime.now(UTC)
        other_dispatches = (
            self._db.execute(
                select(DeliveryDispatch).where(
                    DeliveryDispatch.driver_id == driver_id,
                    DeliveryDispatch.status == DeliveryDispatchStatus.OFFERED.value,
                    DeliveryDispatch.order_id != accepted_order_id,
                )
            )
            .scalars()
            .all()
        )
        for dispatch in other_dispatches:
            dispatch.status = DeliveryDispatchStatus.CANCELED.value
            dispatch.responded_at = now
            if notify_bot:
                self._push_driver_assignment_update(
                    driver_id=driver_id,
                    order_id=int(dispatch.order_id),
                    event="dispatch_canceled",
                )

    def _get_driver_or_404(self, *, driver_id: int) -> DeliveryDriver:
        driver = self._db.execute(
            select(DeliveryDriver).options(joinedload(DeliveryDriver.provider)).where(DeliveryDriver.id == driver_id)
        ).scalar_one_or_none()
        if driver is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="سائق التوصيل غير موجود.")
        return driver

    def _ensure_actor_is_driver_login(self, *, actor_id: int) -> None:
        provider_account = self._db.execute(
            select(DeliveryProvider.id).where(DeliveryProvider.account_user_id == actor_id)
        ).scalar_one_or_none()
        if provider_account is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="حساب لوحة جهة التوصيل لا ينفذ مهام السائق مباشرة.",
            )

    def get_driver_telegram_link_status(
        self,
        *,
        driver_id: int,
        bot_username: str | None,
        action_message: str | None = None,
    ) -> dict[str, object]:
        driver = self._get_driver_or_404(driver_id=driver_id)
        deep_link = None
        if bot_username and driver.telegram_link_code:
            deep_link = f"https://t.me/{bot_username}?start={driver.telegram_link_code}"
        active_assignment_row = self._db.execute(
            select(DeliveryAssignment, Order)
            .join(Order, Order.id == DeliveryAssignment.order_id)
            .where(
                DeliveryAssignment.driver_id == driver_id,
                DeliveryAssignment.status.in_(
                    [
                        DeliveryAssignmentStatus.ASSIGNED.value,
                        DeliveryAssignmentStatus.DEPARTED.value,
                    ]
                ),
            )
            .order_by(DeliveryAssignment.id.desc())
            .limit(1)
        ).first()
        offered_dispatch_row = self._db.execute(
            select(DeliveryDispatch, Order)
            .join(Order, Order.id == DeliveryDispatch.order_id)
            .where(
                DeliveryDispatch.driver_id == driver_id,
                DeliveryDispatch.status == DeliveryDispatchStatus.OFFERED.value,
            )
            .order_by(DeliveryDispatch.id.desc())
            .limit(1)
        ).first()

        active_order_id = None
        active_order_status = None
        if active_assignment_row is not None:
            _, active_order = active_assignment_row
            active_order_id = int(active_order.id)
            active_order_status = str(active_order.status)

        offered_order_id = None
        offered_order_status = None
        if offered_dispatch_row is not None:
            _, offered_order = offered_dispatch_row
            offered_order_id = int(offered_order.id)
            offered_order_status = str(offered_order.status)

        if not (driver.telegram_chat_id and driver.telegram_enabled):
            recovery_hint = "أنشئ رابط ربط جديد ثم اطلب من السائق فتحه من Telegram."
        elif active_order_id is not None:
            recovery_hint = f"لدى السائق مهمة جارية على الطلب #{active_order_id}. أكملها أولًا أو أعد إرسالها عند الحاجة."
        elif offered_order_id is not None:
            recovery_hint = f"يوجد عرض مفتوح على الطلب #{offered_order_id}. يمكنك إعادة إرساله إلى البوت."
        else:
            recovery_hint = "لا توجد مهمة أو عروض مفتوحة لهذا السائق الآن. يمكنك إرسال رسالة اختبار للتحقق من الاتصال."
        return {
            "driver_id": int(driver.id),
            "driver_name": driver.name,
            "provider_name": driver.provider_name,
            "linked": bool(driver.telegram_chat_id and driver.telegram_enabled),
            "telegram_enabled": bool(driver.telegram_enabled),
            "telegram_username": driver.telegram_username,
            "telegram_chat_id": driver.telegram_chat_id,
            "telegram_linked_at": driver.telegram_linked_at,
            "link_code": driver.telegram_link_code,
            "link_expires_at": driver.telegram_link_expires_at,
            "bot_username": bot_username,
            "deep_link": deep_link,
            "has_active_task": active_order_id is not None,
            "active_order_id": active_order_id,
            "active_order_status": active_order_status,
            "has_open_offer": offered_order_id is not None,
            "offered_order_id": offered_order_id,
            "offered_order_status": offered_order_status,
            "recovery_hint": recovery_hint,
            "action_message": action_message,
        }

    def create_driver_telegram_link(
        self,
        *,
        driver_id: int,
        actor_id: int,
        bot_username: str | None,
    ) -> dict[str, object]:
        driver = self._db.execute(
            select(DeliveryDriver).where(DeliveryDriver.id == driver_id)
        ).scalar_one_or_none()
        if driver is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="سائق التوصيل غير موجود.")

        now = datetime.now(UTC)
        driver.telegram_link_code = secrets.token_urlsafe(18)
        driver.telegram_link_expires_at = now + timedelta(hours=12)
        record_system_audit(
            self._db,
            module="delivery",
            action="create_driver_telegram_link",
            entity_type="delivery_driver",
            entity_id=int(driver.id),
            user_id=actor_id,
            description=f"إنشاء رابط ربط Telegram للسائق {driver.name}.",
        )
        return self.get_driver_telegram_link_status(driver_id=driver_id, bot_username=bot_username)

    def clear_driver_telegram_link(
        self,
        *,
        driver_id: int,
        actor_id: int,
        bot_username: str | None,
    ) -> dict[str, object]:
        driver = self._db.execute(
            select(DeliveryDriver).where(DeliveryDriver.id == driver_id)
        ).scalar_one_or_none()
        if driver is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="سائق التوصيل غير موجود.")
        driver.telegram_chat_id = None
        driver.telegram_username = None
        driver.telegram_link_code = None
        driver.telegram_link_expires_at = None
        driver.telegram_linked_at = None
        driver.telegram_enabled = False
        record_system_audit(
            self._db,
            module="delivery",
            action="clear_driver_telegram_link",
            entity_type="delivery_driver",
            entity_id=int(driver.id),
            user_id=actor_id,
            description=f"فك ربط Telegram عن السائق {driver.name}.",
        )
        return self.get_driver_telegram_link_status(driver_id=driver_id, bot_username=bot_username)

    def send_driver_telegram_test_message(
        self,
        *,
        driver_id: int,
        actor_id: int,
        bot_username: str | None,
    ) -> dict[str, object]:
        driver = self._get_driver_or_404(driver_id=driver_id)
        from application.bot_engine.domain.telegram_delivery_bot import send_driver_support_test_message

        action_message = send_driver_support_test_message(db=self._db, driver_id=driver_id)
        record_system_audit(
            self._db,
            module="delivery",
            action="send_driver_telegram_test_message",
            entity_type="delivery_driver",
            entity_id=int(driver.id),
            user_id=actor_id,
            description=f"إرسال رسالة اختبار Telegram إلى السائق {driver.name}.",
        )
        return self.get_driver_telegram_link_status(
            driver_id=driver_id,
            bot_username=bot_username,
            action_message=action_message,
        )

    def resend_driver_telegram_flow(
        self,
        *,
        driver_id: int,
        actor_id: int,
        bot_username: str | None,
    ) -> dict[str, object]:
        driver = self._get_driver_or_404(driver_id=driver_id)
        from application.bot_engine.domain.telegram_delivery_bot import resend_driver_latest_flow

        action_message = resend_driver_latest_flow(db=self._db, driver_id=driver_id)
        record_system_audit(
            self._db,
            module="delivery",
            action="resend_driver_telegram_flow",
            entity_type="delivery_driver",
            entity_id=int(driver.id),
            user_id=actor_id,
            description=f"إعادة إرسال آخر عرض أو مهمة Telegram للسائق {driver.name}.",
        )
        return self.get_driver_telegram_link_status(
            driver_id=driver_id,
            bot_username=bot_username,
            action_message=action_message,
        )

    def link_driver_to_telegram_chat(
        self,
        *,
        link_code: str,
        chat_id: str,
        telegram_username: str | None,
    ) -> DeliveryDriver:
        now = datetime.now(UTC)
        driver = self._db.execute(
            select(DeliveryDriver).where(DeliveryDriver.telegram_link_code == link_code)
        ).scalar_one_or_none()
        if driver is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="رمز الربط غير صالح.")
        expires_at = driver.telegram_link_expires_at
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at is None or expires_at < now:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="انتهت صلاحية رمز الربط.")

        already_linked = self._db.execute(
            select(DeliveryDriver).where(
                DeliveryDriver.telegram_chat_id == chat_id,
                DeliveryDriver.id != driver.id,
            )
        ).scalar_one_or_none()
        if already_linked is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="هذا الحساب مرتبط بسائق آخر.")

        driver.telegram_chat_id = chat_id
        driver.telegram_username = telegram_username
        driver.telegram_linked_at = now
        driver.telegram_enabled = True
        driver.telegram_link_code = None
        driver.telegram_link_expires_at = None
        return driver

    def get_driver_by_telegram_chat(self, *, chat_id: str) -> DeliveryDriver | None:
        return self._db.execute(
            select(DeliveryDriver)
            .options(joinedload(DeliveryDriver.provider))
            .where(
                DeliveryDriver.telegram_chat_id == chat_id,
                DeliveryDriver.telegram_enabled.is_(True),
            )
        ).scalar_one_or_none()

    def _ensure_internal_delivery_provider(self) -> DeliveryProvider:
        provider = self._db.execute(
            select(DeliveryProvider).where(DeliveryProvider.is_internal_default.is_(True))
        ).scalar_one_or_none()
        if provider is not None:
            if provider.name != "الفريق الداخلي":
                provider.name = "الفريق الداخلي"
            if provider.provider_type != "internal_team":
                provider.provider_type = "internal_team"
            if not provider.active:
                provider.active = True
            return provider

        provider = self._db.execute(
            select(DeliveryProvider).where(DeliveryProvider.name == "الفريق الداخلي")
        ).scalar_one_or_none()
        if provider is not None:
            provider.is_internal_default = True
            provider.provider_type = "internal_team"
            if not provider.active:
                provider.active = True
            return provider

        provider = DeliveryProvider(
            name="الفريق الداخلي",
            provider_type="internal_team",
            active=True,
            is_internal_default=True,
        )
        self._db.add(provider)
        self._db.flush()
        return provider

    def _ensure_driver_provider_links(self) -> DeliveryProvider:
        internal_provider = self._ensure_internal_delivery_provider()
        missing_provider_drivers = (
            self._db.execute(select(DeliveryDriver).where(DeliveryDriver.provider_id.is_(None))).scalars().all()
        )
        for driver in missing_provider_drivers:
            driver.provider_id = int(internal_provider.id)
        return internal_provider

    def _get_delivery_order_for_dispatch(self, *, order_id: int) -> Order:
        order = self._db.execute(select(Order).where(Order.id == order_id)).scalar_one_or_none()
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="طلب التوصيل غير موجود.")
        if order.type != OrderType.DELIVERY.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="هذا الطلب ليس طلب توصيل.")
        if order.status not in (OrderStatus.IN_PREPARATION.value, OrderStatus.READY.value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="إرسال الطلب للتوصيل متاح فقط أثناء التحضير أو بعد الجاهزية.",
            )
        if order.delivery_team_notified_at is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="يجب إبلاغ التوصيل أولًا قبل إرسال الطلب إلى جهة أو سائق.",
            )
        active_assignment = self._db.execute(
            select(DeliveryAssignment)
            .where(
                DeliveryAssignment.order_id == order_id,
                DeliveryAssignment.status.in_(
                    [
                        DeliveryAssignmentStatus.ASSIGNED.value,
                        DeliveryAssignmentStatus.DEPARTED.value,
                    ]
                ),
            )
            .order_by(DeliveryAssignment.id.desc())
        ).scalar_one_or_none()
        if active_assignment is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="هذا الطلب مرتبط بالفعل بعنصر توصيل نشط.",
            )
        return order

    def assign_driver(self, *, order_id: int, actor_id: int, notify_bot: bool = True) -> DeliveryAssignment:
        self._ensure_actor_is_driver_login(actor_id=actor_id)
        assignment = app_claim_delivery_order(self._db, order_id=order_id, actor_id=actor_id)
        self._cancel_other_offered_dispatches_for_driver(
            driver_id=int(assignment.driver_id),
            accepted_order_id=int(assignment.order_id),
            notify_bot=notify_bot,
        )
        if notify_bot:
            self._push_driver_assignment_update(
                driver_id=int(assignment.driver_id),
                order_id=int(assignment.order_id),
                event="assigned",
            )
        return assignment

    def assign_driver_by_driver_id(
        self,
        *,
        order_id: int,
        driver_id: int,
        notify_bot: bool = True,
    ) -> DeliveryAssignment:
        driver = self._get_driver_or_404(driver_id=driver_id)
        actor_id = self._resolve_driver_actor_id(driver=driver)
        assignment = claim_delivery_order_for_driver(
            self._db,
            order_id=order_id,
            driver_id=driver_id,
            actor_id=actor_id,
        )
        self._cancel_other_offered_dispatches_for_driver(
            driver_id=int(assignment.driver_id),
            accepted_order_id=int(assignment.order_id),
            notify_bot=notify_bot,
        )
        if notify_bot:
            self._push_driver_assignment_update(
                driver_id=int(assignment.driver_id),
                order_id=int(assignment.order_id),
                event="assigned",
            )
        return assignment

    def depart_delivery(self, *, order_id: int, actor_id: int, notify_bot: bool = True) -> Order:
        self._ensure_actor_is_driver_login(actor_id=actor_id)
        order = app_start_delivery(self._db, order_id=order_id, actor_id=actor_id)
        driver = get_delivery_driver_for_user(self._db, user_id=actor_id, require_active=False)
        if notify_bot:
            self._push_driver_assignment_update(
                driver_id=int(driver.id),
                order_id=int(order.id),
                event="departed",
            )
        return order

    def depart_delivery_by_driver_id(
        self,
        *,
        order_id: int,
        driver_id: int,
        notify_bot: bool = True,
    ) -> Order:
        driver = self._get_driver_or_404(driver_id=driver_id)
        actor_id = self._resolve_driver_actor_id(driver=driver)
        order = start_delivery_for_driver(
            self._db,
            order_id=order_id,
            driver_id=driver_id,
            actor_id=actor_id,
        )
        if notify_bot:
            self._push_driver_assignment_update(
                driver_id=int(driver.id),
                order_id=int(order.id),
                event="departed",
            )
        return order

    def complete_delivery(
        self,
        *,
        order_id: int,
        actor_id: int,
        success: bool,
        amount_received: float | None = None,
        notify_bot: bool = True,
    ) -> Order:
        self._ensure_actor_is_driver_login(actor_id=actor_id)
        order = complete_delivery_domain(
            self._db,
            order_id=order_id,
            actor_id=actor_id,
            success=success,
            amount_received=amount_received,
        )
        driver = get_delivery_driver_for_user(self._db, user_id=actor_id, require_active=False)
        if notify_bot:
            self._push_driver_assignment_update(
                driver_id=int(driver.id),
                order_id=int(order.id),
                event="delivered" if success else "failed",
            )
        return order

    def complete_delivery_by_driver_id(
        self,
        *,
        order_id: int,
        driver_id: int,
        success: bool,
        amount_received: float | None = None,
        notify_bot: bool = True,
    ) -> Order:
        driver = self._get_driver_or_404(driver_id=driver_id)
        actor_id = self._resolve_driver_actor_id(driver=driver)
        order = complete_delivery_for_driver(
            self._db,
            order_id=order_id,
            driver_id=driver_id,
            actor_id=actor_id,
            success=success,
            amount_received=amount_received,
        )
        if notify_bot:
            self._push_driver_assignment_update(
                driver_id=int(driver.id),
                order_id=int(order.id),
                event="delivered" if success else "failed",
            )
        return order

    def notify_delivery_team(self, *, order_id: int, actor_id: int) -> Order:
        return notify_delivery_team_domain(self._db, order_id=order_id, actor_id=actor_id)

    def emergency_fail_delivery_order(
        self,
        *,
        order_id: int,
        performed_by: int,
        reason_code: str,
        reason_note: str | None,
    ) -> Order:
        return app_emergency_fail_delivery_order(
            self._db,
            order_id=order_id,
            performed_by=performed_by,
            reason_code=reason_code,
            reason_note=reason_note,
        )

    def resolve_delivery_failure(
        self,
        *,
        order_id: int,
        performed_by: int,
        resolution_action: str,
        resolution_note: str | None,
    ) -> Order:
        order = get_order_or_404(self._db, order_id)
        if order.type != OrderType.DELIVERY.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="هذا الطلب ليس طلب توصيل.")
        if order.status != OrderStatus.DELIVERY_FAILED.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="هذا الطلب ليس في حالة فشل التوصيل.")
        if order.delivery_failure_resolution_status is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="تمت معالجة فشل التوصيل لهذا الطلب بالفعل.")

        normalized_note = normalize_optional_text(resolution_note)
        now = datetime.now(UTC)
        resolution_labels = {
            "retry_delivery": "إعادة التوصيل",
            "convert_to_takeaway": "تحويل إلى استلام",
            "close_failure": "إغلاق نهائي",
        }
        resolution_label = resolution_labels.get(resolution_action)
        if resolution_label is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="إجراء معالجة فشل التوصيل غير معروف.")

        offered_dispatches = (
            self._db.execute(
                select(DeliveryDispatch).where(
                    DeliveryDispatch.order_id == order_id,
                    DeliveryDispatch.status == DeliveryDispatchStatus.OFFERED.value,
                )
            )
            .scalars()
            .all()
        )
        for dispatch in offered_dispatches:
            dispatch.status = DeliveryDispatchStatus.CANCELED.value
            dispatch.responded_at = now

        order.delivery_team_notified_at = None
        order.delivery_team_notified_by = None
        order.delivery_failure_resolution_status = resolution_action
        order.delivery_failure_resolution_note = normalized_note
        order.delivery_failure_resolved_at = now
        order.delivery_failure_resolved_by = performed_by

        if resolution_action == "retry_delivery":
            previous_status = order.status
            order.status = OrderStatus.READY.value
            record_transition(
                self._db,
                order_id=order.id,
                from_status=previous_status,
                to_status=OrderStatus.READY.value,
                user_id=performed_by,
            )
        elif resolution_action == "convert_to_takeaway":
            previous_status = order.status
            order.type = OrderType.TAKEAWAY.value
            order.status = OrderStatus.READY.value
            order.delivery_fee = 0.0
            order.total = float(order.subtotal or 0.0)
            order.payment_status = PaymentStatus.UNPAID.value
            record_transition(
                self._db,
                order_id=order.id,
                from_status=previous_status,
                to_status=OrderStatus.READY.value,
                user_id=performed_by,
            )

        note_suffix = f" | ملاحظة: {normalized_note}" if normalized_note else ""
        record_system_audit(
            self._db,
            module="delivery",
            action="resolve_delivery_failure",
            entity_type="order",
            entity_id=order.id,
            user_id=performed_by,
            description=f"معالجة فشل التوصيل للطلب #{order.id} | الإجراء: {resolution_label}{note_suffix}",
        )
        return order

    def list_delivery_assignments(
        self,
        *,
        actor_id: int,
        actor_role: str,
        offset: int,
        limit: int,
    ) -> list[DeliveryAssignment]:
        if actor_role == UserRole.MANAGER.value:
            return (
                self._db.execute(
                    select(DeliveryAssignment)
                    .order_by(DeliveryAssignment.assigned_at.desc(), DeliveryAssignment.id.desc())
                    .offset(offset)
                    .limit(limit)
                )
                .scalars()
                .all()
            )

        try:
            scope = self._get_delivery_scope(
                actor_id=actor_id,
                require_active_provider=False,
            )
        except HTTPException as error:
            if error.status_code == status.HTTP_400_BAD_REQUEST:
                return []
            raise

        return (
            self._db.execute(
                select(DeliveryAssignment)
                .where(
                    DeliveryAssignment.driver_id.in_(scope.driver_ids_statement),
                    DeliveryAssignment.status.in_(
                        [
                            DeliveryAssignmentStatus.ASSIGNED.value,
                            DeliveryAssignmentStatus.DEPARTED.value,
                        ]
                    ),
                )
                .order_by(DeliveryAssignment.assigned_at.desc(), DeliveryAssignment.id.desc())
                .offset(offset)
                .limit(limit)
            )
            .scalars()
            .all()
        )

    def list_delivery_dispatches(
        self,
        *,
        actor_id: int,
        actor_role: str,
        offset: int,
        limit: int,
    ) -> list[DeliveryDispatch]:
        statement = (
            select(DeliveryDispatch)
            .options(joinedload(DeliveryDispatch.provider), joinedload(DeliveryDispatch.driver))
            .order_by(DeliveryDispatch.sent_at.desc(), DeliveryDispatch.id.desc())
            .offset(offset)
            .limit(limit)
        )
        if actor_role == UserRole.MANAGER.value:
            return self._db.execute(statement).scalars().all()

        try:
            scope = self._get_delivery_scope(
                actor_id=actor_id,
                require_active_provider=False,
            )
        except HTTPException as error:
            if error.status_code == status.HTTP_400_BAD_REQUEST:
                return []
            raise

        scope_filter = or_(
            DeliveryDispatch.driver_id.in_(scope.driver_ids_statement),
            and_(
                DeliveryDispatch.dispatch_scope == DeliveryDispatchScope.PROVIDER.value,
                DeliveryDispatch.provider_id == scope.provider_id if scope.provider_id is not None else false(),
            ),
            DeliveryDispatch.driver_id == scope.driver_id if scope.driver_id is not None else false(),
        )
        return self._db.execute(statement.where(scope_filter)).scalars().all()

    def create_delivery_dispatch(
        self,
        *,
        order_id: int,
        actor_id: int,
        provider_id: int | None,
        driver_id: int | None,
    ) -> DeliveryDispatch:
        self._ensure_driver_provider_links()
        self._get_delivery_order_for_dispatch(order_id=order_id)

        if (provider_id is None and driver_id is None) or (provider_id is not None and driver_id is not None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="اختر جهة توصيل واحدة فقط: جهة أو سائق.",
            )

        now = datetime.now(UTC)
        existing_offers = (
            self._db.execute(
                select(DeliveryDispatch).where(
                    DeliveryDispatch.order_id == order_id,
                    DeliveryDispatch.status == DeliveryDispatchStatus.OFFERED.value,
                )
            )
            .scalars()
            .all()
        )
        for existing_offer in existing_offers:
            existing_offer.status = DeliveryDispatchStatus.CANCELED.value
            existing_offer.responded_at = now

        dispatch_scope = DeliveryDispatchScope.PROVIDER.value
        dispatch_provider_id: int | None = None
        dispatch_driver_id: int | None = None

        if provider_id is not None:
            provider = self._db.execute(
                select(DeliveryProvider).where(DeliveryProvider.id == provider_id)
            ).scalar_one_or_none()
            if provider is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="جهة التوصيل غير موجودة.")
            if not provider.active:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="جهة التوصيل غير نشطة.")
            dispatch_scope = DeliveryDispatchScope.PROVIDER.value
            dispatch_provider_id = int(provider.id)
        else:
            driver = self._db.execute(
                select(DeliveryDriver)
                .options(joinedload(DeliveryDriver.provider))
                .where(DeliveryDriver.id == driver_id)
            ).scalar_one_or_none()
            if driver is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="عنصر التوصيل غير موجود.")
            if not driver.active or str(driver.status) == DriverStatus.INACTIVE.value:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="عنصر التوصيل غير متاح حاليًا.")
            if self._driver_has_active_assignment(driver_id=int(driver.id)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="عنصر التوصيل لديه مهمة نشطة الآن. أكملها أولًا قبل إرسال عرض جديد له.",
                )
            dispatch_scope = DeliveryDispatchScope.DRIVER.value
            dispatch_driver_id = int(driver.id)
            dispatch_provider_id = int(driver.provider_id) if driver.provider_id is not None else None

        dispatch = DeliveryDispatch(
            order_id=order_id,
            provider_id=dispatch_provider_id,
            driver_id=dispatch_driver_id,
            dispatch_scope=dispatch_scope,
            status=DeliveryDispatchStatus.OFFERED.value,
            channel="console",
            sent_at=now,
            created_by=actor_id,
        )
        self._db.add(dispatch)
        self._db.flush()
        dispatch_result = self._db.execute(
            select(DeliveryDispatch)
            .options(joinedload(DeliveryDispatch.provider), joinedload(DeliveryDispatch.driver))
            .where(DeliveryDispatch.id == dispatch.id)
        ).scalar_one()
        if dispatch_result.dispatch_scope == DeliveryDispatchScope.DRIVER.value and dispatch_result.driver_id is not None:
            self._push_dispatch_offer_notification(dispatch_id=int(dispatch_result.id))
        return dispatch_result

    def cancel_delivery_dispatch(
        self,
        *,
        dispatch_id: int,
        actor_id: int,
    ) -> DeliveryDispatch:
        del actor_id
        dispatch = self._db.execute(
            select(DeliveryDispatch)
            .options(joinedload(DeliveryDispatch.provider), joinedload(DeliveryDispatch.driver))
            .where(DeliveryDispatch.id == dispatch_id)
        ).scalar_one_or_none()
        if dispatch is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="عرض التوصيل غير موجود.")
        if dispatch.status != DeliveryDispatchStatus.OFFERED.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يمكن إلغاء هذا العرض الآن.")
        notify_driver_id = int(dispatch.driver_id) if dispatch.driver_id is not None else None
        notify_order_id = int(dispatch.order_id)
        dispatch.status = DeliveryDispatchStatus.CANCELED.value
        dispatch.responded_at = datetime.now(UTC)
        if notify_driver_id is not None:
            self._push_driver_assignment_update(
                driver_id=notify_driver_id,
                order_id=notify_order_id,
                event="dispatch_canceled",
            )
        return dispatch

    def reject_delivery_dispatch(
        self,
        *,
        dispatch_id: int,
        actor_id: int,
    ) -> DeliveryDispatch:
        scope = self._get_delivery_scope(actor_id=actor_id, require_active_provider=True)
        if scope.driver_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="رفض العرض المباشر متاح من حساب السائق فقط.",
            )
        driver = self._get_driver_or_404(driver_id=scope.driver_id)
        dispatch = self._db.execute(
            select(DeliveryDispatch)
            .options(joinedload(DeliveryDispatch.provider), joinedload(DeliveryDispatch.driver))
            .where(DeliveryDispatch.id == dispatch_id)
        ).scalar_one_or_none()
        if dispatch is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="عرض التوصيل غير موجود.")
        if dispatch.status != DeliveryDispatchStatus.OFFERED.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="هذا العرض لم يعد متاحًا.")

        matches_driver = dispatch.dispatch_scope == DeliveryDispatchScope.DRIVER.value and dispatch.driver_id == driver.id
        matches_provider = (
            dispatch.dispatch_scope == DeliveryDispatchScope.PROVIDER.value
            and dispatch.provider_id is not None
            and driver.provider_id == dispatch.provider_id
        )
        if not (matches_driver or matches_provider):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="هذا العرض غير موجه إلى هذا العنصر.")

        dispatch.status = DeliveryDispatchStatus.REJECTED.value
        dispatch.responded_at = datetime.now(UTC)
        if matches_provider and dispatch.driver_id is None:
            dispatch.driver_id = int(driver.id)
        return dispatch

    def reject_delivery_dispatch_by_driver_id(
        self,
        *,
        dispatch_id: int,
        driver_id: int,
    ) -> DeliveryDispatch:
        driver = self._get_driver_or_404(driver_id=driver_id)
        dispatch = self._db.execute(
            select(DeliveryDispatch)
            .options(joinedload(DeliveryDispatch.provider), joinedload(DeliveryDispatch.driver))
            .where(DeliveryDispatch.id == dispatch_id)
        ).scalar_one_or_none()
        if dispatch is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="عرض التوصيل غير موجود.")
        if dispatch.status != DeliveryDispatchStatus.OFFERED.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="هذا العرض لم يعد متاحًا.")

        matches_driver = dispatch.dispatch_scope == DeliveryDispatchScope.DRIVER.value and dispatch.driver_id == driver.id
        matches_provider = (
            dispatch.dispatch_scope == DeliveryDispatchScope.PROVIDER.value
            and dispatch.provider_id is not None
            and driver.provider_id == dispatch.provider_id
        )
        if not (matches_driver or matches_provider):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="هذا العرض غير موجه إلى هذا العنصر.")

        dispatch.status = DeliveryDispatchStatus.REJECTED.value
        dispatch.responded_at = datetime.now(UTC)
        if matches_provider and dispatch.driver_id is None:
            dispatch.driver_id = int(driver.id)
        return dispatch

    def assign_delivery_dispatch_to_driver(
        self,
        *,
        dispatch_id: int,
        driver_id: int,
        actor_id: int,
    ) -> DeliveryDispatch:
        scope = self._get_delivery_scope(actor_id=actor_id, require_active_provider=True)
        if scope.provider_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="حساب التوصيل الحالي غير مرتبط بجهة توصيل صالحة.",
            )

        dispatch = self._db.execute(
            select(DeliveryDispatch)
            .options(joinedload(DeliveryDispatch.provider), joinedload(DeliveryDispatch.driver))
            .where(DeliveryDispatch.id == dispatch_id)
        ).scalar_one_or_none()
        if dispatch is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="عرض التوصيل غير موجود.")
        if dispatch.status != DeliveryDispatchStatus.OFFERED.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="هذا العرض لم يعد متاحًا للتوزيع.")
        if dispatch.dispatch_scope != DeliveryDispatchScope.PROVIDER.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="هذا العرض ليس عرض جهة توصيل.")
        if dispatch.provider_id != scope.provider_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="هذا العرض لا يخص جهة التوصيل الحالية.")

        target_driver = self._db.execute(
            select(DeliveryDriver)
            .options(joinedload(DeliveryDriver.provider))
            .where(DeliveryDriver.id == driver_id)
        ).scalar_one_or_none()
        if target_driver is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="سائق التوصيل غير موجود.")
        if target_driver.provider_id != scope.provider_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="السائق المحدد لا يتبع هذه الجهة.")
        if not target_driver.active or target_driver.status == DriverStatus.INACTIVE.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="السائق المحدد غير متاح حاليًا.")

        now = datetime.now(UTC)
        dispatch.status = DeliveryDispatchStatus.ACCEPTED.value
        dispatch.responded_at = now

        driver_dispatch = self.create_delivery_dispatch(
            order_id=int(dispatch.order_id),
            actor_id=actor_id,
            provider_id=None,
            driver_id=int(target_driver.id),
        )
        record_system_audit(
            self._db,
            module="delivery",
            action="assign_delivery_dispatch_to_driver",
            entity_type="delivery_dispatch",
            entity_id=int(driver_dispatch.id),
            user_id=actor_id,
            description=(
                f"تم تمرير عرض جهة التوصيل للطلب #{dispatch.order_id} "
                f"إلى السائق {target_driver.name} من جهة {target_driver.provider_name or 'الفريق الداخلي'}."
            ),
        )
        return driver_dispatch

    def list_delivery_orders(
        self,
        *,
        actor_id: int,
        actor_role: str,
        offset: int,
        limit: int,
    ) -> list[Order]:
        active_statuses = [
            DeliveryAssignmentStatus.ASSIGNED.value,
            DeliveryAssignmentStatus.DEPARTED.value,
        ]
        active_assignment_exists = exists(
            select(DeliveryAssignment.id).where(
                DeliveryAssignment.order_id == Order.id,
                DeliveryAssignment.status.in_(active_statuses),
            )
        )
        any_dispatch_exists = exists(select(DeliveryDispatch.id).where(DeliveryDispatch.order_id == Order.id))
        pending_unassigned_condition = (
            Order.status.in_([OrderStatus.IN_PREPARATION.value, OrderStatus.READY.value])
            & Order.delivery_team_notified_at.is_not(None)
            & ~active_assignment_exists
        )

        if actor_role == UserRole.MANAGER.value:
            visibility_condition = (
                active_assignment_exists
                | pending_unassigned_condition
                | (
                    (Order.status == OrderStatus.DELIVERY_FAILED.value)
                    & Order.delivery_failure_resolution_status.is_(None)
                )
            )
        else:
            try:
                scope = self._get_delivery_scope(
                    actor_id=actor_id,
                    require_active_provider=False,
                )
            except HTTPException as error:
                if error.status_code == status.HTTP_400_BAD_REQUEST:
                    return []
                raise

            provider_active_assignment_exists = exists(
                select(DeliveryAssignment.id).where(
                    DeliveryAssignment.order_id == Order.id,
                    DeliveryAssignment.driver_id.in_(scope.driver_ids_statement),
                    DeliveryAssignment.status.in_(active_statuses),
                )
            )
            provider_targeted_dispatch_exists = exists(
                select(DeliveryDispatch.id).where(
                    DeliveryDispatch.order_id == Order.id,
                    DeliveryDispatch.status == DeliveryDispatchStatus.OFFERED.value,
                    and_(
                        DeliveryDispatch.dispatch_scope == DeliveryDispatchScope.PROVIDER.value,
                        DeliveryDispatch.provider_id == (scope.provider_id if scope.provider_id is not None else -1),
                    ),
                )
            )
            my_targeted_driver_dispatch_exists = exists(
                select(DeliveryDispatch.id).where(
                    DeliveryDispatch.order_id == Order.id,
                    DeliveryDispatch.status == DeliveryDispatchStatus.OFFERED.value,
                    DeliveryDispatch.dispatch_scope == DeliveryDispatchScope.DRIVER.value,
                    DeliveryDispatch.driver_id == (scope.driver_id if scope.driver_id is not None else -1),
                )
            )
            provider_failed_assignment_exists = exists(
                select(DeliveryAssignment.id).where(
                    DeliveryAssignment.order_id == Order.id,
                    DeliveryAssignment.driver_id.in_(scope.driver_ids_statement),
                    DeliveryAssignment.status == DeliveryAssignmentStatus.FAILED.value,
                )
            )
            legacy_open_claim_condition = (
                pending_unassigned_condition & ~any_dispatch_exists
                if scope.driver_id is not None
                else false()
            )
            visibility_condition = (
                provider_active_assignment_exists
                | provider_targeted_dispatch_exists
                | my_targeted_driver_dispatch_exists
                | legacy_open_claim_condition
                | (
                    (Order.status == OrderStatus.DELIVERY_FAILED.value)
                    & Order.delivery_failure_resolution_status.is_(None)
                    & provider_failed_assignment_exists
                )
            )

        orders = (
            self._db.execute(
                select(Order)
                .where(
                    Order.type == OrderType.DELIVERY.value,
                    visibility_condition,
                )
                .options(joinedload(Order.items))
                .order_by(Order.created_at.asc(), Order.id.asc())
                .offset(offset)
                .limit(limit)
            )
            .unique()
            .scalars()
            .all()
        )
        return app_attach_sent_to_kitchen_at(self._db, orders)

    def list_delivery_history(
        self,
        *,
        actor_id: int,
        offset: int,
        limit: int,
    ) -> list[DeliveryHistoryOut]:
        try:
            scope = self._get_delivery_scope(
                actor_id=actor_id,
                require_active_provider=False,
            )
        except HTTPException as error:
            if error.status_code == status.HTTP_400_BAD_REQUEST:
                return []
            raise

        rows = self._db.execute(
            select(DeliveryAssignment, Order)
            .join(Order, Order.id == DeliveryAssignment.order_id)
            .where(
                DeliveryAssignment.driver_id.in_(scope.driver_ids_statement),
                Order.status.in_(
                    [
                        OrderStatus.DELIVERED.value,
                        OrderStatus.DELIVERY_FAILED.value,
                    ]
                ),
                DeliveryAssignment.status.in_(
                    [
                        DeliveryAssignmentStatus.DELIVERED.value,
                        DeliveryAssignmentStatus.FAILED.value,
                    ]
                ),
            )
            .order_by(DeliveryAssignment.delivered_at.desc(), DeliveryAssignment.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()

        return [
            DeliveryHistoryOut(
                assignment_id=assignment.id,
                order_id=order.id,
                assignment_status=DeliveryAssignmentStatus(assignment.status),
                order_status=OrderStatus(order.status),
                assigned_at=assignment.assigned_at,
                departed_at=assignment.departed_at,
                delivered_at=assignment.delivered_at,
                order_subtotal=order.subtotal,
                delivery_fee=order.delivery_fee,
                order_total=order.total,
                phone=order.phone,
                address=order.delivery_location_label or order.address,
            )
            for assignment, order in rows
        ]

    def list_delivery_orders_for_driver(
        self,
        *,
        driver_id: int,
        offset: int,
        limit: int,
    ) -> list[Order]:
        active_statuses = [
            DeliveryAssignmentStatus.ASSIGNED.value,
            DeliveryAssignmentStatus.DEPARTED.value,
        ]
        visibility_condition = or_(
            exists(
                select(DeliveryAssignment.id).where(
                    DeliveryAssignment.order_id == Order.id,
                    DeliveryAssignment.driver_id == driver_id,
                    DeliveryAssignment.status.in_(active_statuses),
                )
            ),
            exists(
                select(DeliveryDispatch.id).where(
                    DeliveryDispatch.order_id == Order.id,
                    DeliveryDispatch.status == DeliveryDispatchStatus.OFFERED.value,
                    DeliveryDispatch.dispatch_scope == DeliveryDispatchScope.DRIVER.value,
                    DeliveryDispatch.driver_id == driver_id,
                )
            ),
        )
        orders = (
            self._db.execute(
                select(Order)
                .where(
                    Order.type == OrderType.DELIVERY.value,
                    visibility_condition,
                )
                .options(joinedload(Order.items))
                .order_by(Order.created_at.asc(), Order.id.asc())
                .offset(offset)
                .limit(limit)
            )
            .unique()
            .scalars()
            .all()
        )
        return app_attach_sent_to_kitchen_at(self._db, orders)

    def list_delivery_history_for_driver(
        self,
        *,
        driver_id: int,
        offset: int,
        limit: int,
    ) -> list[DeliveryHistoryOut]:
        rows = self._db.execute(
            select(DeliveryAssignment, Order)
            .join(Order, Order.id == DeliveryAssignment.order_id)
            .where(
                DeliveryAssignment.driver_id == driver_id,
                Order.status.in_(
                    [
                        OrderStatus.DELIVERED.value,
                        OrderStatus.DELIVERY_FAILED.value,
                    ]
                ),
                DeliveryAssignment.status.in_(
                    [
                        DeliveryAssignmentStatus.DELIVERED.value,
                        DeliveryAssignmentStatus.FAILED.value,
                    ]
                ),
            )
            .order_by(DeliveryAssignment.delivered_at.desc(), DeliveryAssignment.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return [
            DeliveryHistoryOut(
                assignment_id=assignment.id,
                order_id=order.id,
                assignment_status=DeliveryAssignmentStatus(assignment.status),
                order_status=OrderStatus(order.status),
                assigned_at=assignment.assigned_at,
                departed_at=assignment.departed_at,
                delivered_at=assignment.delivered_at,
                order_subtotal=order.subtotal,
                delivery_fee=order.delivery_fee,
                order_total=order.total,
                phone=order.phone,
                address=order.delivery_location_label or order.address,
            )
            for assignment, order in rows
        ]

    def list_provider_delivery_drivers(
        self,
        *,
        actor_id: int,
    ) -> list[DeliveryDriver]:
        scope = self._get_delivery_scope(
            actor_id=actor_id,
            require_active_provider=False,
        )
        drivers = (
            self._db.execute(
                select(DeliveryDriver)
                .options(joinedload(DeliveryDriver.provider))
                .where(DeliveryDriver.id.in_(scope.driver_ids_statement))
                .order_by(
                    DeliveryDriver.status.asc(),
                    DeliveryDriver.active.desc(),
                    DeliveryDriver.name.asc(),
                    DeliveryDriver.id.asc(),
                )
            )
            .scalars()
            .all()
        )
        self._attach_driver_management_state(drivers)
        return drivers

    def list_delivery_drivers(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[DeliveryDriver]:
        self._ensure_driver_provider_links()
        drivers = (
            self._db.execute(
                select(DeliveryDriver)
                .options(joinedload(DeliveryDriver.provider))
                .order_by(DeliveryDriver.id.desc())
                .offset(offset)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        self._attach_driver_management_state(drivers)
        return drivers

    def list_delivery_providers(self) -> list[DeliveryProvider]:
        self._ensure_internal_delivery_provider()
        providers = (
            self._db.execute(
                select(DeliveryProvider)
                .options(joinedload(DeliveryProvider.account_user))
                .order_by(DeliveryProvider.is_internal_default.desc(), DeliveryProvider.name.asc())
            )
            .scalars()
            .all()
        )
        self._attach_provider_management_state(providers)
        return providers

    def create_delivery_provider(
        self,
        *,
        account_user_id: int | None,
        name: str,
        provider_type: str,
        active: bool,
    ) -> DeliveryProvider:
        self._ensure_internal_delivery_provider()
        normalized_name = " ".join(name.strip().split())
        existing = self._db.execute(
            select(DeliveryProvider).where(DeliveryProvider.name == normalized_name)
        ).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="جهة التوصيل موجودة بالفعل.")

        validated_account_user_id = self._validate_provider_account_user(
            account_user_id=account_user_id,
            provider_type=provider_type,
        )
        provider = DeliveryProvider(
            name=normalized_name,
            provider_type=provider_type,
            active=active,
            is_internal_default=False,
            account_user_id=validated_account_user_id,
        )
        self._db.add(provider)
        self._db.flush()
        created = self._db.execute(
            select(DeliveryProvider)
            .options(joinedload(DeliveryProvider.account_user))
            .where(DeliveryProvider.id == provider.id)
        ).scalar_one()
        self._attach_provider_management_state([created])
        return created

    def update_delivery_provider(
        self,
        *,
        provider_id: int,
        account_user_id: int | None,
        name: str,
        provider_type: str,
        active: bool,
    ) -> DeliveryProvider:
        self._ensure_internal_delivery_provider()
        provider = self._db.execute(
            select(DeliveryProvider).where(DeliveryProvider.id == provider_id)
        ).scalar_one_or_none()
        if provider is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="جهة التوصيل غير موجودة.")
        if provider.is_internal_default:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="الجهة الداخلية الافتراضية ثابتة ولا يمكن تعديلها.",
            )

        normalized_name = " ".join(name.strip().split())
        duplicate = self._db.execute(
            select(DeliveryProvider).where(
                DeliveryProvider.name == normalized_name,
                DeliveryProvider.id != provider_id,
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اسم جهة التوصيل مستخدم بالفعل.")

        validated_account_user_id = self._validate_provider_account_user(
            account_user_id=account_user_id,
            provider_id=provider_id,
            provider_type=provider_type,
        )
        provider.name = normalized_name
        provider.provider_type = provider_type
        provider.active = active
        provider.account_user_id = validated_account_user_id
        self._db.flush()
        updated = self._db.execute(
            select(DeliveryProvider)
            .options(joinedload(DeliveryProvider.account_user))
            .where(DeliveryProvider.id == provider.id)
        ).scalar_one()
        self._attach_provider_management_state([updated])
        return updated

    def delete_delivery_provider(self, *, provider_id: int) -> None:
        provider = self._db.execute(
            select(DeliveryProvider).options(joinedload(DeliveryProvider.account_user)).where(DeliveryProvider.id == provider_id)
        ).scalar_one_or_none()
        if provider is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="جهة التوصيل غير موجودة.")
        can_delete, block_reason, _ = self._resolve_provider_delete_state(provider)
        if not can_delete:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=block_reason or "لا يمكن حذف جهة التوصيل.")
        account_user = provider.account_user
        self._db.delete(provider)
        self._db.flush()
        if account_user is not None:
            try:
                self._db.delete(account_user)
                self._db.flush()
            except IntegrityError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="لا يمكن حذف الجهة نهائيًا لأن حساب لوحتها دخل سجلات تشغيلية أو أمنية من قبل. الإجراء الصحيح هنا هو التعطيل بدل الحذف النهائي.",
                ) from exc

    def create_delivery_driver(
        self,
        *,
        user_id: int | None,
        name: str,
        provider_id: int | None,
        phone: str,
        vehicle: str | None,
        active: bool,
    ) -> DeliveryDriver:
        internal_provider = self._ensure_internal_delivery_provider()
        normalized_name = " ".join(name.strip().split())
        if len(normalized_name) < 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اسم السائق مطلوب.")
        linked_user_id: int | None = None
        user = self._db.execute(select(User).where(User.id == user_id)).scalar_one_or_none() if user_id is not None else None
        if user_id is not None and user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستخدم غير موجود.")
        if user is not None and user.role != UserRole.DELIVERY.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لا يمكن ربط السائق إلا بمستخدم دوره توصيل.",
            )
        existing = (
            self._db.execute(select(DeliveryDriver).where(DeliveryDriver.user_id == user_id)).scalar_one_or_none()
            if user_id is not None
            else None
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="هذا المستخدم مرتبط بالفعل بسائق توصيل.",
            )

        if user is not None:
            linked_user_id = int(user.id)
        assigned_provider_id = int(internal_provider.id)
        if provider_id is not None:
            provider = self._db.execute(
                select(DeliveryProvider).where(DeliveryProvider.id == provider_id)
            ).scalar_one_or_none()
            if provider is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="جهة التوصيل المحددة غير موجودة.",
                )
            if not provider.is_internal_default:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="إضافة السائق من لوحة الإدارة مخصصة للفريق الداخلي فقط.",
                )
            assigned_provider_id = int(provider.id)

        driver = DeliveryDriver(
            user_id=linked_user_id,
            provider_id=assigned_provider_id,
            name=normalized_name,
            phone=phone,
            vehicle=vehicle,
            active=active,
            status=DriverStatus.AVAILABLE.value if active else DriverStatus.INACTIVE.value,
        )
        self._db.add(driver)
        self._db.flush()
        created = self._db.execute(
            select(DeliveryDriver).options(joinedload(DeliveryDriver.provider)).where(DeliveryDriver.id == driver.id)
        ).scalar_one()
        self._attach_driver_management_state([created])
        return created

    def update_delivery_driver(
        self,
        *,
        driver_id: int,
        provider_id: int | None,
        name: str,
        phone: str,
        vehicle: str | None,
        active: bool,
        status: DriverStatus,
    ) -> DeliveryDriver:
        internal_provider = self._ensure_driver_provider_links()
        driver = self._db.execute(
            select(DeliveryDriver).options(joinedload(DeliveryDriver.provider)).where(DeliveryDriver.id == driver_id)
        ).scalar_one_or_none()
        if not driver:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="سائق التوصيل غير موجود.")

        old_counts_as_delivery = driver.active and str(driver.status) != DriverStatus.INACTIVE.value
        new_counts_as_delivery = active and status != DriverStatus.INACTIVE
        if old_counts_as_delivery and not new_counts_as_delivery:
            app_ensure_delivery_capacity_reduction_allowed(self._db)

        normalized_name = " ".join(name.strip().split())
        if len(normalized_name) < 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اسم السائق مطلوب.")
        driver.name = normalized_name
        driver.phone = phone
        driver.vehicle = vehicle
        driver.active = active
        driver.status = status.value
        assigned_provider_id = int(internal_provider.id)
        if provider_id is not None:
            provider = self._db.execute(
                select(DeliveryProvider).where(DeliveryProvider.id == provider_id)
            ).scalar_one_or_none()
            if provider is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="جهة التوصيل المحددة غير موجودة.",
                )
            assigned_provider_id = int(provider.id)
        driver.provider_id = assigned_provider_id
        self._db.flush()
        updated = self._db.execute(
            select(DeliveryDriver).options(joinedload(DeliveryDriver.provider)).where(DeliveryDriver.id == driver.id)
        ).scalar_one()
        self._attach_driver_management_state([updated])
        return updated

    def _attach_provider_management_state(self, providers: list[DeliveryProvider]) -> None:
        if not providers:
            return

        provider_ids = [int(provider.id) for provider in providers]
        driver_counts = {
            int(provider_id): int(total)
            for provider_id, total in self._db.execute(
                select(DeliveryDriver.provider_id, func.count(DeliveryDriver.id))
                .where(DeliveryDriver.provider_id.in_(provider_ids))
                .group_by(DeliveryDriver.provider_id)
            ).all()
            if provider_id is not None
        }
        dispatch_counts = {
            int(provider_id): int(total)
            for provider_id, total in self._db.execute(
                select(DeliveryDispatch.provider_id, func.count(DeliveryDispatch.id))
                .where(DeliveryDispatch.provider_id.in_(provider_ids))
                .group_by(DeliveryDispatch.provider_id)
            ).all()
            if provider_id is not None
        }

        for provider in providers:
            can_delete, block_reason, recommended_action = self._resolve_provider_delete_state(
                provider,
                driver_count=driver_counts.get(int(provider.id), 0),
                dispatch_count=dispatch_counts.get(int(provider.id), 0),
            )
            provider.can_delete = can_delete
            provider.delete_block_reason = block_reason
            provider.recommended_management_action = recommended_action

    def _resolve_provider_delete_state(
        self,
        provider: DeliveryProvider,
        *,
        driver_count: int | None = None,
        dispatch_count: int | None = None,
    ) -> tuple[bool, str | None, str]:
        resolved_driver_count = driver_count
        if resolved_driver_count is None:
            resolved_driver_count = int(
                self._db.execute(
                    select(func.count(DeliveryDriver.id)).where(DeliveryDriver.provider_id == provider.id)
                ).scalar_one()
                or 0
            )
        resolved_dispatch_count = dispatch_count
        if resolved_dispatch_count is None:
            resolved_dispatch_count = int(
                self._db.execute(
                    select(func.count(DeliveryDispatch.id)).where(DeliveryDispatch.provider_id == provider.id)
                ).scalar_one()
                or 0
            )

        if provider.is_internal_default:
            return False, "الجهة الداخلية الافتراضية ثابتة في النظام، لذا الإجراء الصحيح هنا هو الإبقاء عليها مفعلة أو ضبطها فقط.", "configure_only"
        if resolved_driver_count > 0:
            return False, "لا يمكن حذف الجهة ما دام هناك سائقون مرتبطون بها. انقل السائقين أو عطّل الجهة بدل الحذف.", "deactivate"
        if resolved_dispatch_count > 0:
            return False, "هذه الجهة دخلت دورة التوزيع من قبل. الإجراء الصحيح هنا هو التعطيل بدل الحذف النهائي.", "deactivate"
        return True, None, "delete"

    def _attach_driver_management_state(self, drivers: list[DeliveryDriver]) -> None:
        if not drivers:
            return

        driver_ids = [int(driver.id) for driver in drivers]
        assignment_counts = {
            int(driver_id): int(total)
            for driver_id, total in self._db.execute(
                select(DeliveryAssignment.driver_id, func.count(DeliveryAssignment.id))
                .where(DeliveryAssignment.driver_id.in_(driver_ids))
                .group_by(DeliveryAssignment.driver_id)
            ).all()
            if driver_id is not None
        }
        dispatch_counts = {
            int(driver_id): int(total)
            for driver_id, total in self._db.execute(
                select(DeliveryDispatch.driver_id, func.count(DeliveryDispatch.id))
                .where(DeliveryDispatch.driver_id.in_(driver_ids))
                .group_by(DeliveryDispatch.driver_id)
            ).all()
            if driver_id is not None
        }
        settlement_counts = {
            int(driver_id): int(total)
            for driver_id, total in self._db.execute(
                select(DeliverySettlement.driver_id, func.count(DeliverySettlement.id))
                .where(DeliverySettlement.driver_id.in_(driver_ids))
                .group_by(DeliverySettlement.driver_id)
            ).all()
            if driver_id is not None
        }

        for driver in drivers:
            can_delete, block_reason, recommended_action = self._resolve_driver_delete_state(
                driver,
                assignment_count=assignment_counts.get(int(driver.id), 0),
                dispatch_count=dispatch_counts.get(int(driver.id), 0),
                settlement_count=settlement_counts.get(int(driver.id), 0),
            )
            driver.can_delete = can_delete
            driver.delete_block_reason = block_reason
            driver.recommended_management_action = recommended_action

    def _resolve_driver_delete_state(
        self,
        driver: DeliveryDriver,
        *,
        assignment_count: int | None = None,
        dispatch_count: int | None = None,
        settlement_count: int | None = None,
    ) -> tuple[bool, str | None, str]:
        resolved_assignment_count = assignment_count
        if resolved_assignment_count is None:
            resolved_assignment_count = int(
                self._db.execute(
                    select(func.count(DeliveryAssignment.id)).where(DeliveryAssignment.driver_id == driver.id)
                ).scalar_one()
                or 0
            )
        resolved_dispatch_count = dispatch_count
        if resolved_dispatch_count is None:
            resolved_dispatch_count = int(
                self._db.execute(
                    select(func.count(DeliveryDispatch.id)).where(DeliveryDispatch.driver_id == driver.id)
                ).scalar_one()
                or 0
            )
        resolved_settlement_count = settlement_count
        if resolved_settlement_count is None:
            resolved_settlement_count = int(
                self._db.execute(
                    select(func.count(DeliverySettlement.id)).where(DeliverySettlement.driver_id == driver.id)
                ).scalar_one()
                or 0
            )

        if resolved_assignment_count > 0 or resolved_dispatch_count > 0 or resolved_settlement_count > 0:
            return False, "هذا السائق دخل دورة تشغيل أو محاسبة من قبل. الإجراء الصحيح هنا هو التعطيل بدل الحذف النهائي.", "deactivate"
        return True, None, "delete"

    def delete_delivery_driver(self, *, driver_id: int) -> None:
        driver = self._db.execute(
            select(DeliveryDriver).options(joinedload(DeliveryDriver.provider)).where(DeliveryDriver.id == driver_id)
        ).scalar_one_or_none()
        if not driver:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="سائق التوصيل غير موجود.")
        can_delete, block_reason, _ = self._resolve_driver_delete_state(driver)
        if not can_delete:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=block_reason or "لا يمكن حذف السائق.")
        self._db.delete(driver)
        self._db.flush()

