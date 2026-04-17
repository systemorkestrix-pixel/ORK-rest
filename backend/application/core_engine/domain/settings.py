from __future__ import annotations

import json
import re
import secrets
from datetime import UTC, datetime
from urllib import error as urllib_error
from urllib import request as urllib_request

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SystemSetting
from application.core_engine.domain.constants import (
    DELIVERY_FEATURE_ENABLED_SETTING_KEY,
    DELIVERY_AUTO_NOTIFY_SETTING_KEY,
    DELIVERY_FEE_SETTING_KEY,
    DELIVERY_LOCATION_CACHE_TTL_HOURS_KEY,
    DELIVERY_LOCATION_COUNTRY_CODES_KEY,
    DELIVERY_LOCATION_ENABLED_KEY,
    DELIVERY_LOCATION_GEONAMES_USERNAME_KEY,
    DELIVERY_LOCATION_PROVIDER_KEY,
    DELIVERY_MIN_ORDER_SETTING_KEY,
    CURRENCY_CODE_SETTING_KEY,
    CURRENCY_DECIMAL_PLACES_SETTING_KEY,
    KITCHEN_FEATURE_ENABLED_SETTING_KEY,
    KITCHEN_METRICS_WINDOW_SETTING_KEY,
    WAREHOUSE_FEATURE_ENABLED_SETTING_KEY,
    CURRENCY_NAME_SETTING_KEY,
    CURRENCY_SYMBOL_SETTING_KEY,
    OPERATIONAL_SETTINGS_CATALOG,
    OPERATING_COUNTRY_CODE_SETTING_KEY,
    OPERATING_COUNTRY_NAME_SETTING_KEY,
    PUBLIC_STOREFRONT_ICON_SETTING_KEY,
    PUBLIC_STOREFRONT_MARK_SETTING_KEY,
    PUBLIC_STOREFRONT_NAME_SETTING_KEY,
    PUBLIC_STOREFRONT_SOCIAL_LINKS_SETTING_KEY,
    PUBLIC_STOREFRONT_TAGLINE_SETTING_KEY,
    TELEGRAM_BOT_ENABLED_SETTING_KEY,
    TELEGRAM_BOT_TOKEN_SETTING_KEY,
    TELEGRAM_BOT_USERNAME_SETTING_KEY,
    TELEGRAM_BOT_WEBHOOK_SECRET_SETTING_KEY,
)
from application.core_engine.domain.helpers import (
    normalize_offset_limit,
    parse_bool,
    parse_non_negative_float,
    normalize_optional_text,
    record_system_audit,
    require_setting_value,
)


_ARABIC_CHAR_REGEX = re.compile(r"[\u0600-\u06FF]")
_READABLE_CHAR_REGEX = re.compile(r"^[\u0600-\u06FFA-Za-z0-9\s:,.()\-_/]+$")
_MOJIBAKE_MARKER_REGEX = re.compile(r"(?:Ã.|Ø.|Ù.|ï¿½|Â.)|\uFFFD")
_EXTENDED_LATIN_REGEX = re.compile(r"[\u00C0-\u00FF]")


def _decode_utf8_from_latin1(value: str) -> str | None:
    try:
        decoded = value.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore").strip()
    except (UnicodeEncodeError, UnicodeDecodeError):
        return None
    return decoded or None


def _cleanup_to_readable_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\u0600-\u06FFA-Za-z0-9\s:,.()\-_/]", " ", value)).strip()


def _is_safe_display_text(value: str) -> bool:
    return bool(value and _READABLE_CHAR_REGEX.match(value) and re.search(r"[\u0600-\u06FFA-Za-z0-9]", value))


def _is_likely_corrupted_text(value: str) -> bool:
    raw = value.strip()
    if not raw:
        return False
    if "\uFFFD" in raw or _MOJIBAKE_MARKER_REGEX.search(raw):
        return True
    extended_count = len(_EXTENDED_LATIN_REGEX.findall(raw))
    if not _ARABIC_CHAR_REGEX.search(raw) and extended_count >= 2:
        return True
    return False


def _sanitize_storefront_text(value: str | None, fallback: str = "") -> str:
    raw = normalize_optional_text(value) or ""
    if not raw:
        return fallback
    if not _is_likely_corrupted_text(raw):
        return raw

    decoded = _decode_utf8_from_latin1(raw)
    if decoded and not _is_likely_corrupted_text(decoded) and _is_safe_display_text(decoded):
        return decoded

    if decoded:
        decoded_twice = _decode_utf8_from_latin1(decoded)
        if decoded_twice:
            decoded = decoded_twice
        cleaned_decoded = _cleanup_to_readable_text(decoded)
        if len(cleaned_decoded) >= 3 and not _is_likely_corrupted_text(cleaned_decoded) and _is_safe_display_text(cleaned_decoded):
            return cleaned_decoded

    cleaned_raw = _cleanup_to_readable_text(raw)
    if len(cleaned_raw) >= 3 and not _is_likely_corrupted_text(cleaned_raw) and _is_safe_display_text(cleaned_raw):
        return cleaned_raw

    return fallback or raw


def get_delivery_fee_setting(db: Session) -> float:
    setting = db.execute(
        select(SystemSetting).where(SystemSetting.key == DELIVERY_FEE_SETTING_KEY)
    ).scalar_one_or_none()
    if not setting:
        return 0.0
    return parse_non_negative_float(setting.value, default=0.0)


def get_system_context_settings(db: Session) -> dict[str, object]:
    rows = db.execute(
        select(SystemSetting).where(
            SystemSetting.key.in_(
                [
                    OPERATING_COUNTRY_CODE_SETTING_KEY,
                    OPERATING_COUNTRY_NAME_SETTING_KEY,
                    CURRENCY_CODE_SETTING_KEY,
                    CURRENCY_NAME_SETTING_KEY,
                    CURRENCY_SYMBOL_SETTING_KEY,
                    CURRENCY_DECIMAL_PLACES_SETTING_KEY,
                ]
            )
        )
    ).scalars().all()
    values = {row.key: row.value for row in rows}

    country_code = (normalize_optional_text(values.get(OPERATING_COUNTRY_CODE_SETTING_KEY)) or "DZ").upper()
    country_name = normalize_optional_text(values.get(OPERATING_COUNTRY_NAME_SETTING_KEY)) or "الجزائر"
    currency_code = (normalize_optional_text(values.get(CURRENCY_CODE_SETTING_KEY)) or "DZD").upper()
    currency_name = normalize_optional_text(values.get(CURRENCY_NAME_SETTING_KEY)) or "الدينار الجزائري"
    currency_symbol = normalize_optional_text(values.get(CURRENCY_SYMBOL_SETTING_KEY)) or "د.ج"

    currency_decimal_places = 2
    raw_decimal_places = normalize_optional_text(values.get(CURRENCY_DECIMAL_PLACES_SETTING_KEY))
    if raw_decimal_places:
        try:
            candidate = int(raw_decimal_places)
            if 0 <= candidate <= 4:
                currency_decimal_places = candidate
        except (TypeError, ValueError):
            pass

    return {
        "country_code": country_code,
        "country_name": country_name,
        "currency_code": currency_code,
        "currency_name": currency_name,
        "currency_symbol": currency_symbol,
        "currency_decimal_places": currency_decimal_places,
    }


def get_operational_feature_flags(db: Session) -> dict[str, bool]:
    rows = db.execute(
        select(SystemSetting).where(
            SystemSetting.key.in_(
                [
                    KITCHEN_FEATURE_ENABLED_SETTING_KEY,
                    DELIVERY_FEATURE_ENABLED_SETTING_KEY,
                    WAREHOUSE_FEATURE_ENABLED_SETTING_KEY,
                ]
            )
        )
    ).scalars().all()
    values = {row.key: row.value for row in rows}
    return {
        "kitchen_feature_enabled": parse_bool(
            values.get(KITCHEN_FEATURE_ENABLED_SETTING_KEY, "enabled"),
            default=True,
        ),
        "delivery_feature_enabled": parse_bool(
            values.get(DELIVERY_FEATURE_ENABLED_SETTING_KEY, "enabled"),
            default=True,
        ),
        "warehouse_feature_enabled": parse_bool(
            values.get(WAREHOUSE_FEATURE_ENABLED_SETTING_KEY, "enabled"),
            default=True,
        ),
    }


def _default_storefront_socials() -> list[dict[str, object]]:
    return [
        {"platform": "website", "url": None, "enabled": False},
        {"platform": "whatsapp", "url": None, "enabled": False},
        {"platform": "instagram", "url": None, "enabled": False},
        {"platform": "facebook", "url": None, "enabled": False},
    ]


def get_storefront_settings(db: Session) -> dict[str, object]:
    rows = db.execute(
        select(SystemSetting).where(
            SystemSetting.key.in_(
                [
                    PUBLIC_STOREFRONT_NAME_SETTING_KEY,
                    PUBLIC_STOREFRONT_MARK_SETTING_KEY,
                    PUBLIC_STOREFRONT_ICON_SETTING_KEY,
                    PUBLIC_STOREFRONT_TAGLINE_SETTING_KEY,
                    PUBLIC_STOREFRONT_SOCIAL_LINKS_SETTING_KEY,
                ]
            )
        )
    ).scalars().all()
    values = {row.key: row.value for row in rows}

    socials = _default_storefront_socials()
    raw_socials = normalize_optional_text(values.get(PUBLIC_STOREFRONT_SOCIAL_LINKS_SETTING_KEY))
    normalized_socials_setting = None
    if raw_socials:
        try:
            parsed = json.loads(raw_socials)
            if isinstance(parsed, list):
                normalized_rows: list[dict[str, object]] = []
                seen: set[str] = set()
                for row in parsed:
                    if not isinstance(row, dict):
                        continue
                    platform = normalize_optional_text(str(row.get("platform") or "")) or ""
                    if platform not in {"website", "whatsapp", "instagram", "facebook"} or platform in seen:
                        continue
                    seen.add(platform)
                    normalized_rows.append(
                        {
                            "platform": platform,
                            "url": normalize_optional_text(str(row.get("url"))) if row.get("url") is not None else None,
                            "enabled": bool(row.get("enabled")),
                        }
                    )
                if normalized_rows:
                    socials = normalized_rows
                    normalized_socials_setting = json.dumps(normalized_rows, ensure_ascii=False)
        except (TypeError, ValueError, json.JSONDecodeError):
            pass

    normalized_name = _sanitize_storefront_text(values.get(PUBLIC_STOREFRONT_NAME_SETTING_KEY), "sPeeD SyS")
    normalized_mark = _sanitize_storefront_text(values.get(PUBLIC_STOREFRONT_MARK_SETTING_KEY), "sPeeD SyS")
    normalized_icon = normalize_optional_text(values.get(PUBLIC_STOREFRONT_ICON_SETTING_KEY)) or "utensils"
    normalized_tagline = _sanitize_storefront_text(
        values.get(PUBLIC_STOREFRONT_TAGLINE_SETTING_KEY),
        "وجباتك جاهزة بخطوات أوضح.",
    )

    healed_values = {
        PUBLIC_STOREFRONT_NAME_SETTING_KEY: normalized_name,
        PUBLIC_STOREFRONT_MARK_SETTING_KEY: normalized_mark,
        PUBLIC_STOREFRONT_TAGLINE_SETTING_KEY: normalized_tagline,
    }
    if normalized_socials_setting is not None:
        healed_values[PUBLIC_STOREFRONT_SOCIAL_LINKS_SETTING_KEY] = normalized_socials_setting
    for key, healed_value in healed_values.items():
        current_value = normalize_optional_text(values.get(key))
        if current_value and current_value != healed_value:
            setting = next((row for row in rows if row.key == key), None)
            if setting:
                setting.value = healed_value
    if any(normalize_optional_text(values.get(key)) and normalize_optional_text(values.get(key)) != healed_values.get(key, normalize_optional_text(values.get(key))) for key in healed_values):
        db.flush()

    return {
        "brand_name": normalized_name,
        "brand_mark": normalized_mark,
        "brand_icon": normalized_icon,
        "brand_tagline": normalized_tagline,
        "socials": socials,
    }


def update_storefront_settings(
    db: Session,
    *,
    brand_name: str,
    brand_mark: str,
    brand_icon: str,
    brand_tagline: str | None,
    socials: list[dict[str, object]],
    actor_id: int,
) -> dict[str, object]:
    normalized_name = _sanitize_storefront_text(brand_name)
    normalized_mark = _sanitize_storefront_text(brand_mark)
    normalized_icon = normalize_optional_text(brand_icon) or ""
    normalized_tagline = _sanitize_storefront_text(brand_tagline)

    if len(normalized_name) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اسم الواجهة العامة يجب أن يكون حرفين على الأقل.")
    if len(normalized_mark) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="شارة الواجهة العامة يجب أن تكون حرفين على الأقل.")
    if normalized_icon not in {"utensils", "chef_hat", "shopping_bag", "bike"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="أيقونة الواجهة العامة غير مدعومة.")

    serialized_socials: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in socials:
        platform = normalize_optional_text(str(row.get("platform") or "")) or ""
        if platform not in {"website", "whatsapp", "instagram", "facebook"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="منصة التواصل غير مدعومة.")
        if platform in seen:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يمكن تكرار نفس منصة التواصل أكثر من مرة.")
        seen.add(platform)
        serialized_socials.append(
            {
                "platform": platform,
                "url": normalize_optional_text(str(row.get("url"))) if row.get("url") is not None else None,
                "enabled": bool(row.get("enabled")),
            }
        )

    previous = get_storefront_settings(db)
    settings_map = {
        PUBLIC_STOREFRONT_NAME_SETTING_KEY: normalized_name,
        PUBLIC_STOREFRONT_MARK_SETTING_KEY: normalized_mark,
        PUBLIC_STOREFRONT_ICON_SETTING_KEY: normalized_icon,
        PUBLIC_STOREFRONT_TAGLINE_SETTING_KEY: normalized_tagline or "",
        PUBLIC_STOREFRONT_SOCIAL_LINKS_SETTING_KEY: json.dumps(serialized_socials, ensure_ascii=False),
    }
    for key, value in settings_map.items():
        setting = db.execute(select(SystemSetting).where(SystemSetting.key == key)).scalar_one_or_none()
        if setting:
            setting.value = value
            setting.updated_by = actor_id
        else:
            db.add(SystemSetting(key=key, value=value, updated_by=actor_id))

    enabled_socials = sum(1 for row in serialized_socials if row.get("enabled") and row.get("url"))
    record_system_audit(
        db,
        module="settings",
        action="update_storefront_settings",
        entity_type="system_setting",
        entity_id=None,
        user_id=actor_id,
        description=(
            "تحديث هوية الواجهة العامة | "
            f"الاسم: {previous['brand_name']} -> {normalized_name} | "
            f"الأيقونة: {previous['brand_icon']} -> {normalized_icon} | "
            f"روابط مفعلة: {enabled_socials}"
        ),
    )
    return {
        "brand_name": normalized_name,
        "brand_mark": normalized_mark,
        "brand_icon": normalized_icon,
        "brand_tagline": normalized_tagline,
        "socials": serialized_socials,
    }


def get_telegram_bot_settings(db: Session) -> dict[str, object]:
    rows = db.execute(
        select(SystemSetting).where(
            SystemSetting.key.in_(
                [
                    TELEGRAM_BOT_ENABLED_SETTING_KEY,
                    TELEGRAM_BOT_TOKEN_SETTING_KEY,
                    TELEGRAM_BOT_USERNAME_SETTING_KEY,
                    TELEGRAM_BOT_WEBHOOK_SECRET_SETTING_KEY,
                ]
            )
        )
    ).scalars().all()
    values = {row.key: row.value for row in rows}
    webhook_secret = normalize_optional_text(values.get(TELEGRAM_BOT_WEBHOOK_SECRET_SETTING_KEY)) or secrets.token_urlsafe(24)
    existing_secret = next((row for row in rows if row.key == TELEGRAM_BOT_WEBHOOK_SECRET_SETTING_KEY), None)
    if existing_secret is None:
        db.add(SystemSetting(key=TELEGRAM_BOT_WEBHOOK_SECRET_SETTING_KEY, value=webhook_secret))
        db.flush()
    return {
        "enabled": parse_bool(values.get(TELEGRAM_BOT_ENABLED_SETTING_KEY, "disabled"), default=False),
        "bot_token": normalize_optional_text(values.get(TELEGRAM_BOT_TOKEN_SETTING_KEY)),
        "bot_username": normalize_optional_text(values.get(TELEGRAM_BOT_USERNAME_SETTING_KEY)),
        "webhook_secret": webhook_secret,
    }


def update_telegram_bot_settings(
    db: Session,
    *,
    enabled: bool,
    bot_token: str | None,
    bot_username: str | None,
    actor_id: int,
) -> dict[str, object]:
    normalized_token = normalize_optional_text(bot_token)
    normalized_username = normalize_optional_text(bot_username)
    if normalized_username and normalized_username.startswith("@"):
        normalized_username = normalized_username[1:]

    previous = get_telegram_bot_settings(db)
    current_secret = str(previous["webhook_secret"])

    if enabled and not normalized_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="توكن بوت Telegram مطلوب عند التفعيل.")
    if normalized_token and not re.fullmatch(r"\d{6,}:[A-Za-z0-9_-]{20,}", normalized_token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="صيغة توكن Telegram غير صحيحة. استخدم التوكن كما وصلك من BotFather مباشرة.",
        )
    if normalized_username and len(normalized_username) < 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اسم مستخدم البوت غير صالح.")

    settings_map = {
        TELEGRAM_BOT_ENABLED_SETTING_KEY: "enabled" if enabled else "disabled",
        TELEGRAM_BOT_TOKEN_SETTING_KEY: normalized_token or "",
        TELEGRAM_BOT_USERNAME_SETTING_KEY: normalized_username or "",
        TELEGRAM_BOT_WEBHOOK_SECRET_SETTING_KEY: current_secret,
    }
    for key, value in settings_map.items():
        setting = db.execute(select(SystemSetting).where(SystemSetting.key == key)).scalar_one_or_none()
        if setting:
            setting.value = value
            setting.updated_by = actor_id
        else:
            db.add(SystemSetting(key=key, value=value, updated_by=actor_id))

    record_system_audit(
        db,
        module="settings",
        action="update_telegram_bot_settings",
        entity_type="system_setting",
        entity_id=None,
        user_id=actor_id,
        description=(
            "تحديث إعدادات بوت Telegram | "
            f"التفعيل: {'مفعّل' if enabled else 'متوقف'} | "
            f"المستخدم: {(normalized_username or 'غير محدد')}"
        ),
    )
    return {
        "enabled": enabled,
        "bot_token": normalized_token,
        "bot_username": normalized_username,
        "webhook_secret": current_secret,
    }


def _telegram_api_read(token: str, method: str) -> dict[str, object]:
    endpoint = f"https://api.telegram.org/bot{token}/{method}"
    req = urllib_request.Request(endpoint, method="GET")
    try:
        with urllib_request.urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8")
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(detail or str(exc.reason)) from exc
    except urllib_error.URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc

    parsed = json.loads(raw)
    if not parsed.get("ok", False):
        raise RuntimeError(str(parsed.get("description") or parsed))
    return parsed.get("result", {})


def get_telegram_bot_health(db: Session) -> dict[str, object]:
    settings = get_telegram_bot_settings(db)
    enabled = bool(settings["enabled"])
    token = normalize_optional_text(settings.get("bot_token"))
    configured_username = normalize_optional_text(settings.get("bot_username"))
    webhook_secret = normalize_optional_text(settings.get("webhook_secret"))
    expected_path = f"/api/bot/telegram/{webhook_secret}" if webhook_secret else None

    issues: list[str] = []
    bot_api_ok = False
    bot_id: int | None = None
    bot_username: str | None = None
    webhook_ok = False
    webhook_url: str | None = None
    webhook_path_matches = False
    pending_update_count = 0
    last_error_message: str | None = None
    last_error_at: datetime | None = None

    token_configured = bool(token)
    username_configured = bool(configured_username)
    webhook_secret_configured = bool(webhook_secret)

    if enabled and not token_configured:
        issues.append("التوكن غير مضبوط رغم أن البوت مفعّل.")
    if enabled and not username_configured:
        issues.append("اسم مستخدم البوت غير مضبوط رغم أن البوت مفعّل.")
    if not webhook_secret_configured:
        issues.append("سر الويبهوك غير متوفر.")

    if token_configured:
        try:
            me_payload = _telegram_api_read(token, "getMe")
            bot_api_ok = True
            bot_id = int(me_payload.get("id")) if me_payload.get("id") is not None else None
            bot_username = normalize_optional_text(me_payload.get("username"))
            if configured_username and bot_username and configured_username != bot_username:
                issues.append("اسم المستخدم المحفوظ لا يطابق اسم البوت الفعلي في Telegram.")
        except RuntimeError as exc:
            issues.append(f"تعذر التحقق من هوية البوت: {exc}")

        try:
            webhook_payload = _telegram_api_read(token, "getWebhookInfo")
            webhook_url = normalize_optional_text(webhook_payload.get("url"))
            pending_update_count = int(webhook_payload.get("pending_update_count") or 0)
            last_error_message = normalize_optional_text(webhook_payload.get("last_error_message"))
            last_error_date = webhook_payload.get("last_error_date")
            if isinstance(last_error_date, (int, float)) and last_error_date > 0:
                last_error_at = datetime.fromtimestamp(float(last_error_date), tz=UTC)

            if webhook_url and expected_path:
                webhook_path_matches = webhook_url.endswith(expected_path)
            webhook_ok = bool(webhook_url and webhook_path_matches)

            if enabled and not webhook_url:
                issues.append("الويبهوك غير مضبوط على Telegram.")
            elif webhook_url and not webhook_path_matches:
                issues.append("مسار الويبهوك الحالي لا يطابق المسار المتوقع داخل النظام.")
            if last_error_message:
                issues.append(f"آخر خطأ من Telegram: {last_error_message}")
            if pending_update_count > 0:
                issues.append(f"توجد {pending_update_count} تحديثات معلقة في صف Telegram.")
        except RuntimeError as exc:
            issues.append(f"تعذر فحص الويبهوك: {exc}")

    if enabled:
        health_status = "healthy" if bot_api_ok and webhook_ok and not last_error_message and pending_update_count == 0 else "warning"
        if not bot_api_ok or not webhook_ok:
            health_status = "error"
    else:
        health_status = "warning" if token_configured or username_configured else "healthy"

    return {
        "enabled": enabled,
        "token_configured": token_configured,
        "username_configured": username_configured,
        "webhook_secret_configured": webhook_secret_configured,
        "bot_api_ok": bot_api_ok,
        "bot_id": bot_id,
        "bot_username": bot_username,
        "webhook_ok": webhook_ok,
        "webhook_url": webhook_url,
        "webhook_expected_path": expected_path,
        "webhook_path_matches": webhook_path_matches,
        "pending_update_count": pending_update_count,
        "last_error_message": last_error_message,
        "last_error_at": last_error_at,
        "issues": issues,
        "status": health_status,
    }


def update_system_context_settings(
    db: Session,
    *,
    country_code: str,
    country_name: str,
    currency_code: str,
    currency_name: str,
    currency_symbol: str,
    currency_decimal_places: int,
    actor_id: int,
) -> dict[str, object]:
    normalized_country_code = (normalize_optional_text(country_code) or "").upper()
    normalized_country_name = normalize_optional_text(country_name) or ""
    normalized_currency_code = (normalize_optional_text(currency_code) or "").upper()
    normalized_currency_name = normalize_optional_text(currency_name) or ""
    normalized_currency_symbol = normalize_optional_text(currency_symbol) or ""
    safe_currency_decimal_places = int(currency_decimal_places)

    if len(normalized_country_code) not in {2, 3}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="رمز الدولة يجب أن يكون من حرفين أو ثلاثة.")
    if len(normalized_currency_code) != 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="رمز العملة يجب أن يكون من 3 أحرف.")
    if safe_currency_decimal_places < 0 or safe_currency_decimal_places > 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="عدد الخانات العشرية يجب أن يكون بين 0 و 4.")

    previous = get_system_context_settings(db)
    settings_map = {
        OPERATING_COUNTRY_CODE_SETTING_KEY: normalized_country_code,
        OPERATING_COUNTRY_NAME_SETTING_KEY: normalized_country_name,
        CURRENCY_CODE_SETTING_KEY: normalized_currency_code,
        CURRENCY_NAME_SETTING_KEY: normalized_currency_name,
        CURRENCY_SYMBOL_SETTING_KEY: normalized_currency_symbol,
        CURRENCY_DECIMAL_PLACES_SETTING_KEY: str(safe_currency_decimal_places),
    }
    for key, value in settings_map.items():
        setting = db.execute(select(SystemSetting).where(SystemSetting.key == key)).scalar_one_or_none()
        if setting:
            setting.value = value
            setting.updated_by = actor_id
        else:
            db.add(SystemSetting(key=key, value=value, updated_by=actor_id))

    record_system_audit(
        db,
        module="settings",
        action="update_system_context",
        entity_type="system_setting",
        entity_id=None,
        user_id=actor_id,
        description=(
            "تحديث سياق النظام المركزي | "
            f"country: {previous['country_code']} -> {normalized_country_code} | "
            f"currency: {previous['currency_code']} -> {normalized_currency_code} | "
            f"symbol: {previous['currency_symbol']} -> {normalized_currency_symbol}"
        ),
    )
    return {
        "country_code": normalized_country_code,
        "country_name": normalized_country_name,
        "currency_code": normalized_currency_code,
        "currency_name": normalized_currency_name,
        "currency_symbol": normalized_currency_symbol,
        "currency_decimal_places": safe_currency_decimal_places,
    }


def update_delivery_fee_setting(db: Session, *, delivery_fee: float, actor_id: int) -> float:
    value = max(0.0, float(delivery_fee))
    previous_value = get_delivery_fee_setting(db)
    setting = db.execute(
        select(SystemSetting).where(SystemSetting.key == DELIVERY_FEE_SETTING_KEY)
    ).scalar_one_or_none()
    if setting:
        setting.value = f"{value:.2f}"
        setting.updated_by = actor_id
    else:
        db.add(
            SystemSetting(
                key=DELIVERY_FEE_SETTING_KEY,
                value=f"{value:.2f}",
                updated_by=actor_id,
            )
        )
    record_system_audit(
        db,
        module="settings",
        action="update_delivery_fee",
        entity_type="system_setting",
        entity_id=None,
        user_id=actor_id,
        description=f"تحديث رسوم التوصيل من {previous_value:.2f} إلى {value:.2f} د.ج.",
    )
    return value


def get_delivery_policy_settings(db: Session) -> dict[str, object]:
    rows = db.execute(
        select(SystemSetting).where(
            SystemSetting.key.in_(
                [
                    DELIVERY_MIN_ORDER_SETTING_KEY,
                    DELIVERY_AUTO_NOTIFY_SETTING_KEY,
                ]
            )
        )
    ).scalars().all()
    values = {row.key: row.value for row in rows}
    return {
        "min_order_amount": parse_non_negative_float(values.get(DELIVERY_MIN_ORDER_SETTING_KEY, "0"), default=0.0),
        "auto_notify_team": parse_bool(values.get(DELIVERY_AUTO_NOTIFY_SETTING_KEY, "false"), default=False),
    }


def update_delivery_policy_settings(
    db: Session,
    *,
    min_order_amount: float,
    auto_notify_team: bool,
    actor_id: int,
) -> dict[str, object]:
    safe_min_order = max(0.0, float(min_order_amount))
    safe_auto_notify = bool(auto_notify_team)
    previous = get_delivery_policy_settings(db)
    settings_map = {
        DELIVERY_MIN_ORDER_SETTING_KEY: f"{safe_min_order:.2f}",
        DELIVERY_AUTO_NOTIFY_SETTING_KEY: "true" if safe_auto_notify else "false",
    }
    for key, value in settings_map.items():
        setting = db.execute(select(SystemSetting).where(SystemSetting.key == key)).scalar_one_or_none()
        if setting:
            setting.value = value
            setting.updated_by = actor_id
        else:
            db.add(
                SystemSetting(
                    key=key,
                    value=value,
                    updated_by=actor_id,
                )
            )
    record_system_audit(
        db,
        module="settings",
        action="update_delivery_policy",
        entity_type="system_setting",
        entity_id=None,
        user_id=actor_id,
        description=(
            "تحديث سياسات التوصيل | "
            f"الحد الأدنى: {previous['min_order_amount']:.2f} -> {safe_min_order:.2f} د.ج | "
            f"التبليغ التلقائي: {'مفعل' if previous['auto_notify_team'] else 'غير مفعل'} -> "
            f"{'مفعل' if safe_auto_notify else 'غير مفعل'}"
        ),
    )
    return {
        "min_order_amount": safe_min_order,
        "auto_notify_team": safe_auto_notify,
    }


def get_delivery_location_provider_settings(db: Session) -> dict[str, object]:
    rows = db.execute(
        select(SystemSetting).where(
            SystemSetting.key.in_(
                [
                    DELIVERY_LOCATION_PROVIDER_KEY,
                    DELIVERY_LOCATION_GEONAMES_USERNAME_KEY,
                    DELIVERY_LOCATION_COUNTRY_CODES_KEY,
                    DELIVERY_LOCATION_CACHE_TTL_HOURS_KEY,
                    DELIVERY_LOCATION_ENABLED_KEY,
                ]
            )
        )
    ).scalars().all()
    values = {row.key: row.value for row in rows}
    raw_country_codes = normalize_optional_text(values.get(DELIVERY_LOCATION_COUNTRY_CODES_KEY))
    country_codes = (
        sorted({part.strip().upper() for part in raw_country_codes.split(",") if part.strip()})
        if raw_country_codes
        else []
    )
    ttl_hours = 720
    try:
        ttl_candidate = int(str(values.get(DELIVERY_LOCATION_CACHE_TTL_HOURS_KEY, ttl_hours)).strip())
        if 1 <= ttl_candidate <= 24 * 365:
            ttl_hours = ttl_candidate
    except (TypeError, ValueError):
        pass
    geonames_username = normalize_optional_text(values.get(DELIVERY_LOCATION_GEONAMES_USERNAME_KEY))
    enabled = parse_bool(values.get(DELIVERY_LOCATION_ENABLED_KEY, "false"), default=False)
    provider = normalize_optional_text(values.get(DELIVERY_LOCATION_PROVIDER_KEY)) or "geonames"
    return {
        "provider": provider,
        "enabled": enabled,
        "geonames_username": geonames_username,
        "geonames_username_configured": bool(geonames_username),
        "country_codes": country_codes,
        "cache_ttl_hours": ttl_hours,
    }


def update_delivery_location_provider_settings(
    db: Session,
    *,
    provider: str,
    enabled: bool,
    geonames_username: str | None,
    country_codes: list[str],
    cache_ttl_hours: int,
    actor_id: int,
) -> dict[str, object]:
    normalized_provider = (normalize_optional_text(provider) or "geonames").strip().lower()
    if normalized_provider != "geonames":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="المزود المدعوم حاليًا هو GeoNames فقط.")
    normalized_username = normalize_optional_text(geonames_username)
    normalized_country_codes = sorted({code.strip().upper() for code in country_codes if code.strip()})
    if cache_ttl_hours < 1 or cache_ttl_hours > 24 * 365:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="مدة cache يجب أن تكون بين 1 و 8760 ساعة.")

    previous = get_delivery_location_provider_settings(db)
    settings_map = {
        DELIVERY_LOCATION_PROVIDER_KEY: normalized_provider,
        DELIVERY_LOCATION_ENABLED_KEY: "true" if enabled else "false",
        DELIVERY_LOCATION_GEONAMES_USERNAME_KEY: normalized_username or "",
        DELIVERY_LOCATION_COUNTRY_CODES_KEY: ",".join(normalized_country_codes),
        DELIVERY_LOCATION_CACHE_TTL_HOURS_KEY: str(int(cache_ttl_hours)),
    }
    for key, value in settings_map.items():
        setting = db.execute(select(SystemSetting).where(SystemSetting.key == key)).scalar_one_or_none()
        if setting:
            setting.value = value
            setting.updated_by = actor_id
        else:
            db.add(SystemSetting(key=key, value=value, updated_by=actor_id))

    record_system_audit(
        db,
        module="settings",
        action="update_delivery_location_provider",
        entity_type="system_setting",
        entity_id=None,
        user_id=actor_id,
        description=(
            "تحديث مزود مواقع التوصيل | "
            f"provider: {previous['provider']} -> {normalized_provider} | "
            f"enabled: {'مفعل' if previous['enabled'] else 'غير مفعل'} -> {'مفعل' if enabled else 'غير مفعل'} | "
            f"countries: {len(previous['country_codes'])} -> {len(normalized_country_codes)} | "
            f"cache_ttl_hours: {previous['cache_ttl_hours']} -> {int(cache_ttl_hours)}"
        ),
    )
    return {
        "provider": normalized_provider,
        "enabled": enabled,
        "geonames_username": normalized_username,
        "geonames_username_configured": bool(normalized_username),
        "country_codes": normalized_country_codes,
        "cache_ttl_hours": int(cache_ttl_hours),
    }


def list_operational_settings(
    db: Session,
    *,
    offset: int = 0,
    limit: int | None = None,
) -> list[dict[str, object]]:
    keys = list(OPERATIONAL_SETTINGS_CATALOG.keys())
    rows = db.execute(select(SystemSetting).where(SystemSetting.key.in_(keys))).scalars().all()
    values = {row.key: row.value for row in rows}
    output: list[dict[str, object]] = []
    for key, meta in OPERATIONAL_SETTINGS_CATALOG.items():
        output.append(
            {
                "key": key,
                "value": values.get(key, str(meta["default"])),
                "description": str(meta["description"]),
                "editable": bool(meta["editable"]),
            }
        )
    safe_offset, safe_limit = normalize_offset_limit(offset=offset, limit=limit, max_limit=200)
    if safe_offset <= 0 and safe_limit is None:
        return output
    if safe_limit is None:
        return output[safe_offset:]
    return output[safe_offset : safe_offset + safe_limit]


def get_order_polling_ms(db: Session) -> int:
    default_raw = str(OPERATIONAL_SETTINGS_CATALOG["order_polling_ms"]["default"])
    try:
        default_value = int(default_raw)
    except (TypeError, ValueError):
        default_value = 5000

    setting = db.execute(select(SystemSetting).where(SystemSetting.key == "order_polling_ms")).scalar_one_or_none()
    raw_value = setting.value if setting is not None else default_raw
    try:
        parsed = int(str(raw_value).strip())
    except (TypeError, ValueError):
        return default_value
    if parsed < 3000 or parsed > 60000:
        return default_value
    return parsed


def get_kitchen_metrics_window(db: Session) -> str:
    default_value = str(OPERATIONAL_SETTINGS_CATALOG[KITCHEN_METRICS_WINDOW_SETTING_KEY]["default"])
    setting = db.execute(
        select(SystemSetting).where(SystemSetting.key == KITCHEN_METRICS_WINDOW_SETTING_KEY)
    ).scalar_one_or_none()
    raw_value = normalize_optional_text(setting.value if setting is not None else default_value) or default_value
    normalized = raw_value.strip().lower()
    if normalized not in {"day", "week", "month"}:
        return default_value
    return normalized


def update_operational_setting(
    db: Session,
    *,
    key: str,
    value: str,
    actor_id: int,
) -> dict[str, object]:
    config = OPERATIONAL_SETTINGS_CATALOG.get(key)
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الإعداد غير موجود.")
    if not bool(config["editable"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="هذا الإعداد للقراءة فقط.")

    normalized_value = _normalize_operational_setting_value(key=key, value=value)
    setting = db.execute(select(SystemSetting).where(SystemSetting.key == key)).scalar_one_or_none()
    previous_value = setting.value if setting else str(config["default"])
    if setting:
        setting.value = normalized_value
        setting.updated_by = actor_id
    else:
        db.add(
            SystemSetting(
                key=key,
                value=normalized_value,
                updated_by=actor_id,
            )
        )
    record_system_audit(
        db,
        module="settings",
        action="update_operational_setting",
        entity_type="system_setting",
        entity_id=None,
        user_id=actor_id,
        description=f"تحديث الإعداد {key} من {previous_value} إلى {normalized_value}",
    )
    return {
        "key": key,
        "value": normalized_value,
        "description": str(config["description"]),
        "editable": bool(config["editable"]),
    }


def _normalize_operational_setting_value(*, key: str, value: str) -> str:
    normalized_value = require_setting_value(value)

    if key == "order_polling_ms":
        try:
            polling_ms = int(normalized_value)
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="قيمة فاصل التحديث غير صالحة.") from error
        if polling_ms < 3000 or polling_ms > 60000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="فاصل التحديث يجب أن يكون بين 3000 و 60000 مللي ثانية.",
            )
        return str(polling_ms)

    if key == KITCHEN_METRICS_WINDOW_SETTING_KEY:
        normalized_window = (normalize_optional_text(normalized_value) or "").strip().lower()
        if normalized_window not in {"day", "week", "month"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ù†Ø§ÙØ°Ø© Ø¥Ø­ØµØ§Ø¦ÙŠØ§Øª Ø§Ù„Ù…Ø·Ø¨Ø® ÙŠØ¬Ø¨ Ø£Ù† ØªÙƒÙˆÙ† day Ø£Ùˆ week Ø£Ùˆ month.",
            )
        return normalized_window

    if key in {
        "audit_logs",
        KITCHEN_FEATURE_ENABLED_SETTING_KEY,
        DELIVERY_FEATURE_ENABLED_SETTING_KEY,
    }:
        allowed = {"enabled", "disabled"}
        lowered = normalize_optional_text(normalized_value)
        lowered = lowered.lower() if lowered else ""
        if lowered not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="قيمة سجل التدقيق يجب أن تكون enabled أو disabled.",
            )
        return lowered

    return normalized_value
