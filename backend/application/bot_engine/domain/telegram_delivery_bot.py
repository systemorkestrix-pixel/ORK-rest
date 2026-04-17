from __future__ import annotations

from datetime import UTC, datetime
import json
import logging
import threading
from urllib import error as urllib_error
from urllib.parse import parse_qs, urlparse
from urllib import request as urllib_request

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.enums import DeliveryDispatchStatus
from app.models import DeliveryDispatch, DeliveryDriver, Order
from application.core_engine.domain.settings import get_telegram_bot_settings
from application.delivery_engine.domain.driver_task_flow import (
    can_driver_accept_dispatch,
    can_driver_finish_delivery,
    can_driver_start_delivery,
    is_driver_waiting_for_ready,
)
from application.operations_engine.domain.order_status_presentation import resolve_driver_task_status_label
from infrastructure.repositories.delivery_repository import DeliveryRepository

logger = logging.getLogger(__name__)

MAIN_MENU_OFFERS = "📥 العروض الواردة"
MAIN_MENU_TASKS = "📦 مهامي الحالية"
MAIN_MENU_INCOME = "💰 دخل اليوم"
MAIN_MENU_HELP = "❓ مساعدة"
MAIN_MENU_HOME = "🏠 الرئيسية"
MAIN_MENU_BACK = "↩️ رجوع"
MAIN_MENU_REFRESH_OFFERS = "🔄 تحديث العروض"
MAIN_MENU_REFRESH_TASKS = "🔄 تحديث المهام"


def _extract_start_payload(text: str) -> str | None:
    parts = text.split(maxsplit=1)
    if len(parts) != 2:
        return None

    raw = parts[1].strip()
    if not raw:
        return None

    if raw.startswith(("http://", "https://")):
        parsed = urlparse(raw)
        payload = parse_qs(parsed.query).get("start", [])
        if payload and payload[0].strip():
            return payload[0].strip()

    if "t.me/" in raw and "start=" in raw:
        parsed = urlparse(raw if raw.startswith(("http://", "https://")) else f"https://{raw}")
        payload = parse_qs(parsed.query).get("start", [])
        if payload and payload[0].strip():
            return payload[0].strip()

    return raw


def _reply_keyboard(*, linked: bool, screen: str = "home") -> dict[str, object]:
    if not linked:
        keyboard = [
            [{"text": "🔗 ربط الحساب"}, {"text": MAIN_MENU_HELP}],
        ]
    elif screen == "offers":
        keyboard = [
            [{"text": MAIN_MENU_REFRESH_OFFERS}, {"text": MAIN_MENU_TASKS}],
            [{"text": MAIN_MENU_BACK}, {"text": MAIN_MENU_HOME}],
        ]
    elif screen == "tasks":
        keyboard = [
            [{"text": MAIN_MENU_REFRESH_TASKS}, {"text": MAIN_MENU_OFFERS}],
            [{"text": MAIN_MENU_BACK}, {"text": MAIN_MENU_HOME}],
        ]
    elif screen == "income":
        keyboard = [
            [{"text": MAIN_MENU_TASKS}, {"text": MAIN_MENU_OFFERS}],
            [{"text": MAIN_MENU_BACK}, {"text": MAIN_MENU_HOME}],
        ]
    elif screen == "help":
        keyboard = [
            [{"text": MAIN_MENU_OFFERS}, {"text": MAIN_MENU_TASKS}],
            [{"text": MAIN_MENU_BACK}, {"text": MAIN_MENU_HOME}],
        ]
    else:
        keyboard = [
            [{"text": MAIN_MENU_OFFERS}, {"text": MAIN_MENU_TASKS}],
            [{"text": MAIN_MENU_INCOME}, {"text": MAIN_MENU_HELP}],
        ]
    return {
        "keyboard": keyboard,
        "resize_keyboard": True,
        "is_persistent": True,
        "input_field_placeholder": "اختر الإجراء المناسب",
    }


def _telegram_api_call(token: str, method: str, payload: dict[str, object]) -> dict[str, object]:
    endpoint = f"https://api.telegram.org/bot{token}/{method}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8")
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Telegram API error on {method}: {detail or exc.reason}") from exc
    except urllib_error.URLError as exc:
        raise RuntimeError(f"Telegram API unreachable on {method}: {exc.reason}") from exc

    parsed = json.loads(raw)
    if not parsed.get("ok", False):
        raise RuntimeError(f"Telegram API rejected {method}: {parsed}")
    return parsed


def _send_message(
    *,
    token: str,
    chat_id: str,
    text: str,
    reply_markup: dict[str, object] | None = None,
) -> None:
    payload: dict[str, object] = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    _telegram_api_call(token, "sendMessage", payload)


def _send_notice(
    *,
    token: str,
    chat_id: str,
    text: str,
    linked: bool,
    screen: str = "home",
) -> None:
    _send_message(
        token=token,
        chat_id=chat_id,
        text=text,
        reply_markup=_reply_keyboard(linked=linked, screen=screen),
    )


def _answer_callback_query(*, token: str, callback_query_id: str, text: str) -> None:
    _telegram_api_call(
        token,
        "answerCallbackQuery",
        {
            "callback_query_id": callback_query_id,
            "text": text,
        },
    )


def _clear_inline_actions(*, token: str, chat_id: str, message_id: int) -> None:
    _telegram_api_call(
        token,
        "editMessageReplyMarkup",
        {
            "chat_id": chat_id,
            "message_id": message_id,
            "reply_markup": {"inline_keyboard": []},
        },
    )


def _safe_clear_inline_actions(*, token: str, chat_id: str, message_id: int | None) -> None:
    if message_id is None:
        return
    try:
        _clear_inline_actions(token=token, chat_id=chat_id, message_id=message_id)
    except RuntimeError:
        logger.debug("Telegram bot could not clear inline actions for message %s.", message_id)


def _delivery_address(order: Order) -> str:
    return (
        order.delivery_location_label
        or order.address
        or "-"
    )


def _build_offer_text(order: Order) -> str:
    return (
        f"📥 عرض جديد | طلب #{order.id}\n"
        f"📍 الحالة: {resolve_driver_task_status_label(order_status=order.status, dispatch_status=order.delivery_dispatch_status)}\n"
        f"📞 العميل: {order.phone or '-'}\n"
        f"🧭 العنوان: {_delivery_address(order)}\n"
        f"🚚 رسوم التوصيل: {order.delivery_fee:.2f} د.ج\n"
        f"💵 الإجمالي: {order.total:.2f} د.ج"
    )


def _build_offer_actions(order: Order) -> dict[str, object]:
    if not can_driver_accept_dispatch(
        order_status=str(order.status),
        dispatch_status=order.delivery_dispatch_status,
        assignment_status=order.delivery_assignment_status,
    ):
        return {"inline_keyboard": []}

    rows = [[{"text": "✅ قبول العرض", "callback_data": f"offer_accept:{order.id}"}]]
    if order.delivery_dispatch_id:
        rows[0].append({"text": "✖️ رفض العرض", "callback_data": f"offer_reject:{order.delivery_dispatch_id}"})
    return {"inline_keyboard": rows}


def _build_task_text(order: Order) -> str:
    return (
        f"📦 مهمة حالية | طلب #{order.id}\n"
        f"📍 الحالة: {resolve_driver_task_status_label(order_status=order.status, assignment_status=order.delivery_assignment_status)}\n"
        f"📞 العميل: {order.phone or '-'}\n"
        f"🧭 العنوان: {_delivery_address(order)}\n"
        f"🚚 رسوم التوصيل: {order.delivery_fee:.2f} د.ج\n"
        f"💵 الإجمالي: {order.total:.2f} د.ج"
    )


def _build_task_actions(order: Order) -> dict[str, object]:
    buttons: list[dict[str, str]] = []
    if can_driver_start_delivery(order_status=str(order.status), assignment_status=order.delivery_assignment_status):
        buttons.append({"text": "🚚 بدء التوصيل", "callback_data": f"task_depart:{order.id}"})
    elif can_driver_finish_delivery(order_status=str(order.status), assignment_status=order.delivery_assignment_status):
        buttons.extend(
            [
                {"text": "✅ تم التسليم", "callback_data": f"task_done:{order.id}"},
                {"text": "⚠️ فشل التوصيل", "callback_data": f"task_fail:{order.id}"},
            ]
        )
    return {"inline_keyboard": [buttons]} if buttons else {"inline_keyboard": []}

def _send_link_prompt(*, token: str, chat_id: str) -> None:
    _send_notice(
        token=token,
        chat_id=chat_id,
        text="🔗 هذا الحساب غير مربوط بعد.\nاطلب من الإدارة إنشاء رابط ربط خاص بك ثم افتح البوت من ذلك الرابط.",
        linked=False,
    )


def _send_help(*, token: str, chat_id: str, linked: bool) -> None:
    text = (
        "❓ دليل سريع\n"
        "📥 العروض الواردة: العروض الجديدة المرسلة لك.\n"
        "📦 مهامي الحالية: الطلبات التي تعمل عليها الآن.\n"
        "💰 دخل اليوم: ملخص التنفيذ اليومي.\n"
        "🏠 الرئيسية: العودة إلى البداية في أي وقت."
    )
    _send_notice(token=token, chat_id=chat_id, text=text, linked=linked, screen="help")


def _send_home(*, token: str, chat_id: str, driver_name: str) -> None:
    _send_notice(
        token=token,
        chat_id=chat_id,
        text=(
            f"👋 مرحبًا {driver_name}.\n"
            "اختر من اللوحة السفلية ما تحتاجه الآن: العروض، المهام، أو دخل اليوم."
        ),
        linked=True,
        screen="home",
    )


def _load_driver_orders(repo: DeliveryRepository, *, driver: DeliveryDriver) -> list[Order]:
    return repo.list_delivery_orders_for_driver(
        driver_id=int(driver.id),
        offset=0,
        limit=30,
    )


def _send_offers(*, token: str, chat_id: str, repo: DeliveryRepository, driver: DeliveryDriver) -> None:
    orders = _load_driver_orders(repo, driver=driver)
    active_tasks = [
        order
        for order in orders
        if order.delivery_assignment_driver_id == driver.id
        and order.delivery_assignment_status in {"assigned", "departed"}
    ]
    if active_tasks:
        _send_notice(
            token=token,
            chat_id=chat_id,
            text="📦 لديك مهمة نشطة الآن.\nأكملها أولًا ثم راجع العروض الجديدة.",
            linked=True,
            screen="tasks",
        )
        return
    offers = [
        order
        for order in orders
        if order.delivery_dispatch_status == DeliveryDispatchStatus.OFFERED.value
        and order.delivery_dispatch_driver_id == driver.id
    ]
    if not offers:
        _send_notice(
            token=token,
            chat_id=chat_id,
            text="📭 لا توجد عروض مباشرة لك الآن.",
            linked=True,
            screen="offers",
        )
        return
    _send_notice(
        token=token,
        chat_id=chat_id,
        text=f"📥 العروض الواردة الآن: {len(offers)}",
        linked=True,
        screen="offers",
    )
    for order in offers:
        _send_message(
            token=token,
            chat_id=chat_id,
            text=_build_offer_text(order),
            reply_markup=_build_offer_actions(order),
        )


def _send_tasks(*, token: str, chat_id: str, repo: DeliveryRepository, driver: DeliveryDriver) -> None:
    orders = _load_driver_orders(repo, driver=driver)
    tasks = [
        order
        for order in orders
        if order.delivery_assignment_driver_id == driver.id
        and (
            order.delivery_assignment_status in {"assigned", "departed"}
            or order.status == "OUT_FOR_DELIVERY"
        )
    ]
    if not tasks:
        _send_notice(
            token=token,
            chat_id=chat_id,
            text="📭 لا توجد مهام جارية الآن.",
            linked=True,
            screen="tasks",
        )
        return
    _send_notice(
        token=token,
        chat_id=chat_id,
        text=f"📦 مهامك الحالية: {len(tasks)}",
        linked=True,
        screen="tasks",
    )
    for order in tasks:
        if is_driver_waiting_for_ready(order_status=str(order.status), assignment_status=order.delivery_assignment_status):
            _send_notice(
                token=token,
                chat_id=chat_id,
                text=f"⏳ طلب #{order.id} تم استلامه وهو الآن بانتظار الجاهزية للانطلاق.",
                linked=True,
                screen="tasks",
            )
        _send_message(
            token=token,
            chat_id=chat_id,
            text=_build_task_text(order),
            reply_markup=_build_task_actions(order),
        )


def _send_income_summary(*, token: str, chat_id: str, repo: DeliveryRepository, driver: DeliveryDriver) -> None:
    today = datetime.now(UTC).date()
    history = repo.list_delivery_history_for_driver(driver_id=int(driver.id), offset=0, limit=100)
    today_rows = [
        row
        for row in history
        if getattr(row.assignment_status, "value", row.assignment_status) == "delivered"
        and (row.delivered_at or row.assigned_at).date() == today
    ]
    completed_count = len(today_rows)
    today_delivery_fees = sum(float(row.delivery_fee) for row in today_rows)
    today_order_totals = sum(float(row.order_total) for row in today_rows)
    _send_notice(
        token=token,
        chat_id=chat_id,
        text=(
            "💰 ملخص اليوم\n"
            f"✅ الطلبات المسلّمة: {completed_count}\n"
            f"🚚 رسوم التوصيل المنفذة: {today_delivery_fees:.2f} د.ج\n"
            f"💵 إجمالي الطلبات المسلّمة: {today_order_totals:.2f} د.ج"
        ),
        linked=True,
        screen="income",
    )


def _load_order_for_driver(
    repo: DeliveryRepository,
    *,
    driver: DeliveryDriver,
    order_id: int,
) -> Order | None:
    orders = _load_driver_orders(repo, driver=driver)
    for order in orders:
        if int(order.id) == int(order_id):
            return order
    return None


def _send_driver_assignment_snapshot(
    *,
    token: str,
    chat_id: str,
    repo: DeliveryRepository,
    driver: DeliveryDriver,
    order_id: int,
    intro_text: str,
) -> None:
    order = _load_order_for_driver(repo, driver=driver, order_id=order_id)
    if order is None:
        _send_notice(
            token=token,
            chat_id=chat_id,
            text=intro_text,
            linked=True,
            screen="tasks",
        )
        return
    _send_notice(
        token=token,
        chat_id=chat_id,
        text=intro_text,
        linked=True,
        screen="tasks",
    )
    _send_message(
        token=token,
        chat_id=chat_id,
        text=_build_task_text(order),
        reply_markup=_build_task_actions(order),
    )


def _run_push_safely(action_name: str, operation) -> None:
    try:
        operation()
    except HTTPException:
        logger.exception("Telegram delivery bot push skipped during %s due to business rule.", action_name)
    except RuntimeError as exc:
        logger.exception("Telegram delivery bot push failed during %s: %s", action_name, exc)
    except Exception:
        logger.exception("Telegram delivery bot push failed during %s.", action_name)


def _run_followup_async(action_name: str, operation) -> None:
    def _runner() -> None:
        try:
            operation()
        except Exception:
            logger.exception("Telegram delivery bot follow-up failed during %s.", action_name)

    threading.Thread(target=_runner, name=f"tg-bot-{action_name}", daemon=True).start()


def _schedule_notice(
    *,
    token: str,
    chat_id: str,
    text: str,
    linked: bool,
    screen: str = "home",
) -> None:
    _run_followup_async(
        "notice",
        lambda: _send_notice(
            token=token,
            chat_id=chat_id,
            text=text,
            linked=linked,
            screen=screen,
        ),
    )


def _run_driver_followup(action_name: str, *, driver_id: int, operation) -> None:
    def _runner() -> None:
        db = SessionLocal()
        try:
            repo = DeliveryRepository(db)
            driver = db.execute(
                select(DeliveryDriver).where(DeliveryDriver.id == driver_id)
            ).scalar_one_or_none()
            if driver is None or not driver.telegram_enabled or not driver.telegram_chat_id:
                return
            operation(repo, driver)
        except Exception:
            logger.exception("Telegram delivery bot driver follow-up failed during %s.", action_name)
        finally:
            db.close()

    threading.Thread(target=_runner, name=f"tg-bot-driver-{action_name}", daemon=True).start()


def _schedule_offers(*, token: str, chat_id: str, driver_id: int) -> None:
    _run_driver_followup(
        "offers",
        driver_id=driver_id,
        operation=lambda repo, driver: _send_offers(
            token=token,
            chat_id=chat_id,
            repo=repo,
            driver=driver,
        ),
    )


def _schedule_tasks(*, token: str, chat_id: str, driver_id: int) -> None:
    _run_driver_followup(
        "tasks",
        driver_id=driver_id,
        operation=lambda repo, driver: _send_tasks(
            token=token,
            chat_id=chat_id,
            repo=repo,
            driver=driver,
        ),
    )


def _schedule_income_summary(*, token: str, chat_id: str, driver_id: int) -> None:
    _run_driver_followup(
        "income",
        driver_id=driver_id,
        operation=lambda repo, driver: _send_income_summary(
            token=token,
            chat_id=chat_id,
            repo=repo,
            driver=driver,
        ),
    )


def _schedule_driver_assignment_snapshot(
    *,
    token: str,
    chat_id: str,
    driver_id: int,
    order_id: int,
    intro_text: str,
) -> None:
    _run_driver_followup(
        "assignment_snapshot",
        driver_id=driver_id,
        operation=lambda repo, driver: _send_driver_assignment_snapshot(
            token=token,
            chat_id=chat_id,
            repo=repo,
            driver=driver,
            order_id=order_id,
            intro_text=intro_text,
        ),
    )


def push_delivery_dispatch_offer(*, db: Session, dispatch_id: int) -> None:
    settings = get_telegram_bot_settings(db)
    if not bool(settings.get("enabled")):
        return
    token = str(settings.get("bot_token") or "").strip()
    if not token:
        return

    def _push() -> None:
        dispatch = db.execute(
            select(DeliveryDispatch)
            .where(DeliveryDispatch.id == dispatch_id)
        ).scalar_one_or_none()
        if dispatch is None:
            return
        if dispatch.status != DeliveryDispatchStatus.OFFERED.value or dispatch.driver_id is None:
            return

        repo = DeliveryRepository(db)
        driver = db.execute(
            select(DeliveryDriver).where(DeliveryDriver.id == dispatch.driver_id)
        ).scalar_one_or_none()
        if driver is None or not driver.telegram_enabled or not driver.telegram_chat_id:
            return

        order = _load_order_for_driver(repo, driver=driver, order_id=int(dispatch.order_id))
        if order is None:
            return

        _send_message(
            token=token,
            chat_id=str(driver.telegram_chat_id),
            text="📥 وصلك عرض توصيل جديد.",
            reply_markup=_reply_keyboard(linked=True, screen="offers"),
        )
        _send_message(
            token=token,
            chat_id=str(driver.telegram_chat_id),
            text=_build_offer_text(order),
            reply_markup=_build_offer_actions(order),
        )

    _run_push_safely("push_delivery_dispatch_offer", _push)


def push_driver_assignment_update(*, db: Session, driver_id: int, order_id: int, event: str) -> None:
    settings = get_telegram_bot_settings(db)
    if not bool(settings.get("enabled")):
        return
    token = str(settings.get("bot_token") or "").strip()
    if not token:
        return

    event_messages = {
        "assigned": "📦 تم إسناد الطلب لك. ابدأ المهمة عندما تصبح جاهزًا.",
        "ready": "🔔 الطلب أصبح جاهزًا في المطبخ. يمكنك الانطلاق الآن.",
        "departed": "🚚 تم تسجيل خروجك للتوصيل. أكمل المهمة من نفس البطاقة.",
        "delivered": "✅ تم تأكيد التسليم بنجاح.",
        "failed": "⚠️ تم تسجيل فشل التوصيل لهذا الطلب.\nأزيلت المهمة من مهامك الحالية.\nالمعالجة التالية أصبحت عند الإدارة.",
        "dispatch_canceled": "ℹ️ تم سحب هذا العرض ولم يعد متاحًا لك.",
    }

    def _push() -> None:
        driver = db.execute(
            select(DeliveryDriver).where(DeliveryDriver.id == driver_id)
        ).scalar_one_or_none()
        if driver is None or not driver.telegram_enabled or not driver.telegram_chat_id:
            return

        repo = DeliveryRepository(db)
        chat_id = str(driver.telegram_chat_id)
        intro_text = event_messages.get(event)
        if not intro_text:
            return

        if event in {"assigned", "ready", "departed"}:
            _send_driver_assignment_snapshot(
                token=token,
                chat_id=chat_id,
                repo=repo,
                driver=driver,
                order_id=order_id,
                intro_text=intro_text,
            )
            return

        _send_notice(
            token=token,
            chat_id=chat_id,
            text=intro_text,
            linked=True,
            screen="home",
        )
        if event == "delivered":
            _send_income_summary(token=token, chat_id=chat_id, repo=repo, driver=driver)
        if event == "failed":
            _send_tasks(token=token, chat_id=chat_id, repo=repo, driver=driver)

    _run_push_safely(f"push_driver_assignment_update:{event}", _push)


def send_driver_support_test_message(*, db: Session, driver_id: int) -> str:
    settings = get_telegram_bot_settings(db)
    if not bool(settings.get("enabled")):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="بوت Telegram غير مفعل الآن.")
    token = str(settings.get("bot_token") or "").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="توكن بوت Telegram غير مضبوط.")

    driver = db.execute(select(DeliveryDriver).where(DeliveryDriver.id == driver_id)).scalar_one_or_none()
    if driver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="سائق التوصيل غير موجود.")
    if not driver.telegram_enabled or not driver.telegram_chat_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="هذا السائق غير مربوط على Telegram بعد.")

    _send_notice(
        token=token,
        chat_id=str(driver.telegram_chat_id),
        text=(
            "🧪 رسالة اختبار من لوحة الإدارة\n"
            "الاتصال مع البوت يعمل، ويمكنك متابعة العروض والمهام من هذه المحادثة."
        ),
        linked=True,
        screen="home",
    )
    return "تم إرسال رسالة اختبار إلى Telegram بنجاح."


def resend_driver_latest_flow(*, db: Session, driver_id: int) -> str:
    settings = get_telegram_bot_settings(db)
    if not bool(settings.get("enabled")):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="بوت Telegram غير مفعل الآن.")
    token = str(settings.get("bot_token") or "").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="توكن بوت Telegram غير مضبوط.")

    repo = DeliveryRepository(db)
    driver = db.execute(select(DeliveryDriver).where(DeliveryDriver.id == driver_id)).scalar_one_or_none()
    if driver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="سائق التوصيل غير موجود.")
    if not driver.telegram_enabled or not driver.telegram_chat_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="هذا السائق غير مربوط على Telegram بعد.")

    chat_id = str(driver.telegram_chat_id)
    orders = _load_driver_orders(repo, driver=driver)
    active_task = next(
        (
            order
            for order in orders
            if order.delivery_assignment_driver_id == driver.id
            and order.delivery_assignment_status in {"assigned", "departed"}
        ),
        None,
    )
    if active_task is not None:
        _send_driver_assignment_snapshot(
            token=token,
            chat_id=chat_id,
            repo=repo,
            driver=driver,
            order_id=int(active_task.id),
            intro_text="🔁 تمت إعادة إرسال المهمة الحالية إلى السائق.",
        )
        return f"تمت إعادة إرسال المهمة الحالية للطلب #{active_task.id}."

    active_offer = next(
        (
            order
            for order in orders
            if order.delivery_dispatch_status == DeliveryDispatchStatus.OFFERED.value
            and order.delivery_dispatch_driver_id == driver.id
        ),
        None,
    )
    if active_offer is not None:
        _send_notice(
            token=token,
            chat_id=chat_id,
            text="🔁 تمت إعادة إرسال آخر عرض مفتوح إلى السائق.",
            linked=True,
            screen="offers",
        )
        _send_message(
            token=token,
            chat_id=chat_id,
            text=_build_offer_text(active_offer),
            reply_markup=_build_offer_actions(active_offer),
        )
        return f"تمت إعادة إرسال العرض المفتوح للطلب #{active_offer.id}."

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="لا توجد مهمة جارية أو عرض مفتوح لإعادة إرساله لهذا السائق.",
    )


def _handle_message(*, db: Session, token: str, message: dict[str, object]) -> dict[str, object]:
    chat = message.get("chat") or {}
    chat_id = str((chat or {}).get("id") or "")
    if not chat_id:
        return {"handled": False, "reason": "missing_chat_id"}

    text = str((message.get("text") or "")).strip()
    username = None
    from_user = message.get("from")
    if isinstance(from_user, dict):
        username_value = from_user.get("username")
        username = str(username_value).strip() if username_value else None

    repo = DeliveryRepository(db)
    linked_driver = repo.get_driver_by_telegram_chat(chat_id=chat_id)

    if text.startswith("/start"):
        start_payload = _extract_start_payload(text)
        if start_payload:
            driver = repo.link_driver_to_telegram_chat(
                link_code=start_payload,
                chat_id=chat_id,
                telegram_username=username,
            )
            db.commit()
            _send_message(
                token=token,
                chat_id=chat_id,
                text=f"تم ربط حسابك بنجاح، {driver.name}. يمكنك الآن استلام العروض ومتابعة مهامك من البوت.",
                reply_markup=_reply_keyboard(linked=True, screen="home"),
            )
            return {"handled": True, "action": "linked"}
        if linked_driver is not None:
            _send_home(token=token, chat_id=chat_id, driver_name=linked_driver.name)
            return {"handled": True, "action": "welcome_back"}
        _send_link_prompt(token=token, chat_id=chat_id)
        return {"handled": True, "action": "need_link"}

    if linked_driver is None:
        _send_link_prompt(token=token, chat_id=chat_id)
        return {"handled": True, "action": "blocked_unlinked"}

    if text in {MAIN_MENU_HOME, MAIN_MENU_BACK}:
        _send_home(token=token, chat_id=chat_id, driver_name=linked_driver.name)
        return {"handled": True, "action": "home"}

    if text in {MAIN_MENU_OFFERS, MAIN_MENU_REFRESH_OFFERS}:
        _send_offers(token=token, chat_id=chat_id, repo=repo, driver=linked_driver)
        return {"handled": True, "action": "offers"}
    if text in {MAIN_MENU_TASKS, MAIN_MENU_REFRESH_TASKS}:
        _send_tasks(token=token, chat_id=chat_id, repo=repo, driver=linked_driver)
        return {"handled": True, "action": "tasks"}
    if text == MAIN_MENU_INCOME:
        _send_income_summary(token=token, chat_id=chat_id, repo=repo, driver=linked_driver)
        return {"handled": True, "action": "income"}

    _send_help(token=token, chat_id=chat_id, linked=True)
    return {"handled": True, "action": "help"}


def _handle_callback(*, db: Session, token: str, callback_query: dict[str, object]) -> dict[str, object]:
    callback_query_id = str(callback_query.get("id") or "")
    message = callback_query.get("message") or {}
    chat = (message if isinstance(message, dict) else {}).get("chat") or {}
    chat_id = str((chat if isinstance(chat, dict) else {}).get("id") or "")
    message_id_raw = (message if isinstance(message, dict) else {}).get("message_id")
    message_id = int(message_id_raw) if isinstance(message_id_raw, int) else None
    data = str(callback_query.get("data") or "")
    if not callback_query_id or not chat_id or not data:
        return {"handled": False, "reason": "invalid_callback"}

    repo = DeliveryRepository(db)
    driver = repo.get_driver_by_telegram_chat(chat_id=chat_id)
    if driver is None:
        _answer_callback_query(token=token, callback_query_id=callback_query_id, text="هذا الحساب غير مربوط بسائق.")
        _send_notice(
            token=token,
            chat_id=chat_id,
            text="هذا الحساب غير مربوط بسائق داخل النظام.",
            linked=False,
        )
        return {"handled": True, "action": "blocked_unlinked"}

    try:
        action, raw_id = data.split(":", 1)
        target_id = int(raw_id)
    except (ValueError, TypeError):
        _answer_callback_query(token=token, callback_query_id=callback_query_id, text="الإجراء غير صالح.")
        _send_notice(
            token=token,
            chat_id=chat_id,
            text="تعذر قراءة الإجراء المطلوب. أعد فتح آخر عرض أو مهمة.",
            linked=True,
            screen="home",
        )
        return {"handled": True, "action": "invalid_callback"}

    try:
        if action == "offer_accept":
            _answer_callback_query(token=token, callback_query_id=callback_query_id, text="جارٍ قبول العرض...")
            _safe_clear_inline_actions(token=token, chat_id=chat_id, message_id=message_id)
            order = _load_order_for_driver(repo, driver=driver, order_id=target_id)
            if order is None or not can_driver_accept_dispatch(
                order_status=str(order.status),
                dispatch_status=order.delivery_dispatch_status,
                assignment_status=order.delivery_assignment_status,
            ):
                _send_notice(
                    token=token,
                    chat_id=chat_id,
                    text="ℹ️ هذا العرض لم يعد متاحًا أو انتقل إلى مرحلة أخرى.",
                    linked=True,
                    screen="offers",
                )
                return {"handled": True, "action": "offer_accept_stale"}
            repo.assign_driver_by_driver_id(order_id=target_id, driver_id=int(driver.id), notify_bot=False)
            db.commit()
            _schedule_driver_assignment_snapshot(
                token=token,
                chat_id=chat_id,
                driver_id=int(driver.id),
                order_id=target_id,
                intro_text="✅ تم قبول العرض وإسناد الطلب لك.\nإذا كان الطلب ما زال في التحضير فسيصلك تنبيه عند الجاهزية.",
            )
            return {"handled": True, "action": "offer_accept"}
        if action == "offer_reject":
            _answer_callback_query(token=token, callback_query_id=callback_query_id, text="جارٍ رفض العرض...")
            _safe_clear_inline_actions(token=token, chat_id=chat_id, message_id=message_id)
            repo.reject_delivery_dispatch_by_driver_id(dispatch_id=target_id, driver_id=int(driver.id))
            db.commit()
            _schedule_notice(
                token=token,
                chat_id=chat_id,
                text="✖️ تم رفض العرض.",
                linked=True,
                screen="offers",
            )
            _schedule_offers(token=token, chat_id=chat_id, driver_id=int(driver.id))
            return {"handled": True, "action": "offer_reject"}
        if action == "task_depart":
            _answer_callback_query(token=token, callback_query_id=callback_query_id, text="جارٍ تسجيل بدء التوصيل...")
            _safe_clear_inline_actions(token=token, chat_id=chat_id, message_id=message_id)
            order = _load_order_for_driver(repo, driver=driver, order_id=target_id)
            if order is None or not can_driver_start_delivery(
                order_status=str(order.status),
                assignment_status=order.delivery_assignment_status,
            ):
                _send_notice(
                    token=token,
                    chat_id=chat_id,
                    text="ℹ️ لا يمكن بدء التوصيل الآن. الطلب لم يصل بعد إلى مرحلة الجاهزية.",
                    linked=True,
                    screen="tasks",
                )
                return {"handled": True, "action": "task_depart_blocked"}
            repo.depart_delivery_by_driver_id(order_id=target_id, driver_id=int(driver.id), notify_bot=False)
            db.commit()
            _schedule_driver_assignment_snapshot(
                token=token,
                chat_id=chat_id,
                driver_id=int(driver.id),
                order_id=target_id,
                intro_text="🚚 تم تسجيل خروجك للتوصيل. أكمل المهمة من البطاقة المحدثة.",
            )
            return {"handled": True, "action": "task_depart"}
        if action == "task_done":
            _answer_callback_query(token=token, callback_query_id=callback_query_id, text="جارٍ تأكيد التسليم...")
            _safe_clear_inline_actions(token=token, chat_id=chat_id, message_id=message_id)
            order = _load_order_for_driver(repo, driver=driver, order_id=target_id)
            if order is None or not can_driver_finish_delivery(
                order_status=str(order.status),
                assignment_status=order.delivery_assignment_status,
            ):
                _send_notice(
                    token=token,
                    chat_id=chat_id,
                    text="ℹ️ لا يمكن إنهاء هذه المهمة الآن لأنها ليست في مرحلة خرج للتوصيل.",
                    linked=True,
                    screen="tasks",
                )
                return {"handled": True, "action": "task_done_blocked"}
            repo.complete_delivery_by_driver_id(
                order_id=target_id,
                driver_id=int(driver.id),
                success=True,
                notify_bot=False,
            )
            db.commit()
            _schedule_notice(
                token=token,
                chat_id=chat_id,
                text="✅ تم تأكيد التسليم بنجاح.",
                linked=True,
                screen="home",
            )
            _schedule_income_summary(token=token, chat_id=chat_id, driver_id=int(driver.id))
            return {"handled": True, "action": "task_done"}
        if action == "task_fail":
            _answer_callback_query(token=token, callback_query_id=callback_query_id, text="جارٍ تسجيل فشل التوصيل...")
            _safe_clear_inline_actions(token=token, chat_id=chat_id, message_id=message_id)
            order = _load_order_for_driver(repo, driver=driver, order_id=target_id)
            if order is None or not can_driver_finish_delivery(
                order_status=str(order.status),
                assignment_status=order.delivery_assignment_status,
            ):
                _send_notice(
                    token=token,
                    chat_id=chat_id,
                    text="ℹ️ لا يمكن تسجيل فشل التوصيل الآن لأن المهمة لم تصل إلى مرحلة خرج للتوصيل.",
                    linked=True,
                    screen="tasks",
                )
                return {"handled": True, "action": "task_fail_blocked"}
            repo.complete_delivery_by_driver_id(
                order_id=target_id,
                driver_id=int(driver.id),
                success=False,
                notify_bot=False,
            )
            db.commit()
            _schedule_notice(
                token=token,
                chat_id=chat_id,
                text="⚠️ تم تسجيل فشل التوصيل.\nأزيلت المهمة من مهامك الحالية.\nالمعالجة التالية أصبحت عند الإدارة.",
                linked=True,
                screen="home",
            )
            _schedule_tasks(token=token, chat_id=chat_id, driver_id=int(driver.id))
            return {"handled": True, "action": "task_fail"}
    except HTTPException as exc:
        db.rollback()
        _answer_callback_query(token=token, callback_query_id=callback_query_id, text="تعذر التنفيذ")
        _send_notice(
            token=token,
            chat_id=chat_id,
            text=str(exc.detail),
            linked=True,
            screen="home",
        )
        return {"handled": True, "action": "business_error"}

    _answer_callback_query(token=token, callback_query_id=callback_query_id, text="الإجراء غير مدعوم.")
    _send_notice(
        token=token,
        chat_id=chat_id,
        text="هذا الإجراء غير متاح في هذه المرحلة.",
        linked=True,
        screen="home",
    )
    return {"handled": True, "action": "unsupported_callback"}


def process_delivery_bot_update(*, db: Session, update: dict[str, object]) -> dict[str, object]:
    settings = get_telegram_bot_settings(db)
    if not bool(settings.get("enabled")):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Telegram bot is disabled.")
    token = str(settings.get("bot_token") or "").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Telegram bot token is missing.")

    try:
        if isinstance(update.get("callback_query"), dict):
            return _handle_callback(db=db, token=token, callback_query=update["callback_query"])
        if isinstance(update.get("message"), dict):
            return _handle_message(db=db, token=token, message=update["message"])
        return {"handled": False, "reason": "ignored_update_type"}
    except RuntimeError as exc:
        logger.exception("Telegram delivery bot runtime failure: %s", exc)
        return {"handled": False, "reason": "telegram_runtime_failure"}
