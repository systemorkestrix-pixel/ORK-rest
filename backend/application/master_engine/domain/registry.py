from __future__ import annotations

import json
import re
import secrets
import string
from datetime import UTC, datetime
from urllib.parse import urlencode, urlsplit, urlunsplit

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import MasterClient, MasterTenant
from app.config import load_settings
from app.tenant_runtime import infer_tenant_database_name_from_session, infer_tenant_record_from_session

from .catalog import (
    available_addon_ids_up_to,
    addon_status_for_stage,
    addon_by_id,
    addon_catalog,
    addon_sequence,
    capability_status_for_stage,
    derive_stage_channels,
    manager_channel_modes,
    manager_section_modes,
    mode_from_addon_status,
    next_addon_id,
    normalize_stage_id,
)
from .provisioning import (
    cleanup_provisioned_database,
    ensure_tenant_kitchen_access,
    provision_tenant_database,
    regenerate_tenant_manager_password,
    resolve_tenant_database_path,
)

SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
DEFAULT_STAGE_ID = "base"
SETTINGS = load_settings()


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


def _slugify(value: str) -> str:
    normalized = value.strip().lower()
    normalized = SLUG_PATTERN.sub("_", normalized)
    normalized = normalized.strip("_")
    return normalized


def _generate_unique_code(db: Session, seed: str) -> str:
    base = _slugify(seed) or "tenant"
    candidate = base
    counter = 2
    while db.execute(select(MasterTenant.id).where(MasterTenant.code == candidate)).scalar_one_or_none() is not None:
        candidate = f"{base}_{counter}"
        counter += 1
    return candidate


def _generate_unique_database_name(db: Session, seed: str) -> str:
    base = _slugify(seed) or "tenant"
    candidate = f"tenant_{base}"
    counter = 2
    while db.execute(select(MasterTenant.id).where(MasterTenant.database_name == candidate)).scalar_one_or_none() is not None:
        candidate = f"tenant_{base}_{counter}"
        counter += 1
    return candidate


def _generate_unique_manager_username(db: Session, tenant_code: str) -> str:
    base = f"{_slugify(tenant_code) or 'tenant'}.manager"
    candidate = base
    counter = 2
    while db.execute(select(MasterTenant.id).where(MasterTenant.manager_username == candidate)).scalar_one_or_none() is not None:
        candidate = f"{base}.{counter}"
        counter += 1
    return candidate


def _generate_initial_password() -> str:
    alphabet = string.ascii_letters + string.digits
    core = "".join(secrets.choice(alphabet) for _ in range(10))
    return f"Tmp@{core}"


def _parse_paused_addons(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    normalized = [normalize_stage_id(str(item)) for item in parsed if str(item).strip()]
    return [addon_id for addon_id in normalized if addon_id != "base"]


def _serialize_paused_addons(addon_ids: list[str] | tuple[str, ...] | set[str] | None) -> str:
    normalized = sorted({normalize_stage_id(addon_id) for addon_id in (addon_ids or []) if addon_id and addon_id != "base"})
    return json.dumps(normalized, ensure_ascii=False)


def _append_query_to_url(url: str, params: dict[str, str]) -> str:
    parts = urlsplit(url)
    existing_params: list[tuple[str, str]] = []
    if parts.query:
        for segment in parts.query.split("&"):
            if not segment:
                continue
            if "=" in segment:
                key, value = segment.split("=", 1)
            else:
                key, value = segment, ""
            existing_params.append((key, value))
    existing_params.extend((key, value) for key, value in params.items() if value)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(existing_params), parts.fragment))


def _build_addon_checkout_links(*, tenant_code: str | None, addon_id: str, addon_name: str) -> tuple[str | None, str | None]:
    params = {
        "addon": addon_id,
        "tool": addon_id,
        "tenant": tenant_code or "",
    }
    paypal_url = _append_query_to_url(SETTINGS.sales_paypal_url, params) if SETTINGS.sales_paypal_url else None

    telegram_url = None
    if SETTINGS.sales_telegram_url:
        message = f"أرغب في فتح أداة {addon_name}" + (f" لنسخة {tenant_code}" if tenant_code else "")
        telegram_url = _append_query_to_url(SETTINGS.sales_telegram_url, {"text": message})

    return paypal_url, telegram_url


def _purchase_state_for_addon(*, addon_id: str, current_stage_id: str) -> str:
    normalized_addon_id = normalize_stage_id(addon_id)
    normalized_current_stage_id = normalize_stage_id(current_stage_id)
    if addon_sequence(normalized_addon_id) <= addon_sequence(normalized_current_stage_id):
        return "owned"
    if normalized_addon_id == (next_addon_id(normalized_current_stage_id) or ""):
        return "next"
    return "later"


def _active_unpaused_addon_ids(current_stage_id: str, paused_addons: list[str]) -> list[str]:
    unlocked_addons = [addon_id for addon_id in available_addon_ids_up_to(current_stage_id) if addon_id != "base"]
    return [addon_id for addon_id in unlocked_addons if addon_id not in paused_addons]


def _pauseable_addon_id(current_stage_id: str, paused_addons: list[str]) -> str | None:
    active_addons = _active_unpaused_addon_ids(current_stage_id, paused_addons)
    if not active_addons:
        return None
    return max(active_addons, key=addon_sequence)


def _resumable_addon_id(paused_addons: list[str]) -> str | None:
    if not paused_addons:
        return None
    return min(paused_addons, key=addon_sequence)


def _serialize_manager_addon(
    addon: dict[str, object],
    *,
    current_stage_id: str,
    paused_addons: list[str],
    tenant_code: str | None,
) -> dict[str, object]:
    addon_id = str(addon["id"])
    addon_name = str(addon["name"])
    addon_status = addon_status_for_stage(current_stage_id, addon_id, paused_addons)
    purchase_state = _purchase_state_for_addon(addon_id=addon_id, current_stage_id=current_stage_id)
    can_activate_now = purchase_state == "next" and addon_status != "paused"
    paypal_checkout_url, telegram_checkout_url = _build_addon_checkout_links(
        tenant_code=tenant_code,
        addon_id=addon_id,
        addon_name=addon_name,
    )

    capabilities = []
    for capability in addon.get("capabilities", []):
        capability_key = str(capability["key"])
        capability_status = capability_status_for_stage(current_stage_id, capability_key, paused_addons)
        capabilities.append(
            {
                **capability,
                "status": capability_status,
                "mode": mode_from_addon_status(capability_status),
            }
        )

    return {
        **addon,
        "status": addon_status,
        "can_activate_now": can_activate_now,
        "purchase_state": purchase_state,
        "paypal_checkout_url": paypal_checkout_url if can_activate_now else None,
        "telegram_checkout_url": telegram_checkout_url if can_activate_now else None,
        "capabilities": capabilities,
    }


def _validate_activation_stage_transition(current_stage_id: str, requested_stage_id: str) -> None:
    catalog_ids = {str(addon["id"]) for addon in addon_catalog()}
    normalized_requested_id = normalize_stage_id(requested_stage_id)
    if normalized_requested_id not in catalog_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="الأداة المطلوبة غير معروفة.")

    current_stage = addon_by_id(current_stage_id)
    requested_stage = addon_by_id(normalized_requested_id)
    current_id = str(current_stage["id"])
    requested_id = str(requested_stage["id"])

    if requested_id == current_id:
        return

    current_sequence = addon_sequence(current_id)
    requested_sequence = addon_sequence(requested_id)
    allowed_next_id = next_addon_id(current_id)

    if requested_sequence < current_sequence:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن الرجوع إلى أداة أدنى بعد تفعيلها. استخدم الإيقاف المؤقت إذا لزم الأمر.",
        )
    if requested_sequence > current_sequence + 1 or requested_id != allowed_next_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="فعّل الأداة التالية في الترتيب أولًا قبل الانتقال إلى أداة أعلى.",
        )


def build_tenant_manager_login_path(code: str) -> str:
    normalized = _slugify(code)
    return f"/t/{normalized}/manager/login" if normalized else "/manager/login"


def build_tenant_public_order_path(code: str) -> str:
    return f"/t/{code}/order"


def serialize_master_client(client: MasterClient) -> dict[str, object]:
    stage = addon_by_id(client.active_plan_id or DEFAULT_STAGE_ID)
    return {
        "id": str(client.id),
        "owner_name": client.owner_name,
        "brand_name": client.brand_name,
        "phone": client.phone,
        "city": client.city,
        "current_stage_id": str(stage["id"]),
        "current_stage_name": str(stage["name"]),
        "subscription_state": client.subscription_state,
        "next_billing_date": client.next_billing_date.isoformat() if client.next_billing_date else "غير محدد",
    }


def serialize_master_tenant(tenant: MasterTenant) -> dict[str, object]:
    paused_addons = _parse_paused_addons(tenant.paused_addons_json)
    enabled_tools, hidden_tools, locked_tools = derive_stage_channels(tenant.plan_id or DEFAULT_STAGE_ID, paused_addons)
    stage = addon_by_id(tenant.plan_id or DEFAULT_STAGE_ID)
    client = tenant.client
    next_id = next_addon_id(str(stage["id"]))
    next_stage = addon_by_id(next_id) if next_id else None
    return {
        "id": str(tenant.id),
        "code": tenant.code,
        "brand_name": tenant.brand_name,
        "client_id": str(tenant.client_id),
        "client_owner_name": client.owner_name if client is not None else "غير محدد",
        "client_brand_name": client.brand_name if client is not None else "غير محدد",
        "database_name": tenant.database_name,
        "manager_username": tenant.manager_username,
        "environment_state": tenant.environment_state,
        "enabled_tools": enabled_tools,
        "hidden_tools": hidden_tools,
        "locked_tools": locked_tools,
        "paused_tools": paused_addons,
        "current_stage_id": str(stage["id"]),
        "current_stage_name": str(stage["name"]),
        "next_addon_id": str(next_stage["id"]) if next_stage is not None else None,
        "next_addon_name": str(next_stage["name"]) if next_stage is not None else None,
        "manager_login_path": build_tenant_manager_login_path(tenant.code),
        "public_order_path": build_tenant_public_order_path(tenant.code),
    }


def get_manager_tenant_context(db: Session) -> dict[str, object]:
    tenant = infer_tenant_record_from_session(db)
    if tenant is None:
        default_stage = addon_by_id(DEFAULT_STAGE_ID)
        stage_id = str(default_stage["id"])
        return {
            "tenant_id": None,
            "tenant_code": None,
            "tenant_brand_name": None,
            "database_name": infer_tenant_database_name_from_session(db),
            "activation_stage_id": stage_id,
            "activation_stage_name": str(default_stage["name"]),
            "channel_modes": manager_channel_modes(stage_id, []),
            "section_modes": manager_section_modes(stage_id, []),
        }

    stage = addon_by_id(tenant.plan_id or DEFAULT_STAGE_ID)
    stage_id = str(stage["id"])
    paused_addons = _parse_paused_addons(tenant.paused_addons_json)
    if addon_status_for_stage(stage_id, "kitchen", paused_addons) == "active":
        ensure_tenant_kitchen_access(
            database_name=tenant.database_name,
            tenant_code=tenant.code,
            tenant_brand_name=tenant.brand_name,
            regenerate_password=False,
        )
    return {
        "tenant_id": str(tenant.id),
        "tenant_code": tenant.code,
        "tenant_brand_name": tenant.brand_name,
        "database_name": tenant.database_name,
        "activation_stage_id": stage_id,
        "activation_stage_name": str(stage["name"]),
        "channel_modes": manager_channel_modes(stage_id, paused_addons),
        "section_modes": manager_section_modes(stage_id, paused_addons),
    }


def _require_manager_tenant(db: Session) -> MasterTenant:
    tenant = infer_tenant_record_from_session(db)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="تعذر تحديد النسخة الحالية.")
    return tenant


def _ensure_kitchen_addon_available(tenant: MasterTenant) -> None:
    paused_addons = _parse_paused_addons(tenant.paused_addons_json)
    if addon_status_for_stage(tenant.plan_id or DEFAULT_STAGE_ID, "kitchen", paused_addons) != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="أداة المطبخ غير مفعّلة في النسخة الحالية.",
        )


def get_manager_kitchen_access(db: Session) -> dict[str, object]:
    tenant = _require_manager_tenant(db)
    _ensure_kitchen_addon_available(tenant)
    access = ensure_tenant_kitchen_access(
        database_name=tenant.database_name,
        tenant_code=tenant.code,
        tenant_brand_name=tenant.brand_name,
        regenerate_password=False,
    )
    return {
        "login_path": str(access["login_path"]),
        "username": str(access["username"]),
        "password": str(access["password"]),
        "account_ready": bool(access["account_ready"]),
    }


def regenerate_manager_kitchen_access_password(db: Session) -> dict[str, object]:
    tenant = _require_manager_tenant(db)
    _ensure_kitchen_addon_available(tenant)
    access = ensure_tenant_kitchen_access(
        database_name=tenant.database_name,
        tenant_code=tenant.code,
        tenant_brand_name=tenant.brand_name,
        regenerate_password=True,
    )
    return {
        "login_path": str(access["login_path"]),
        "username": str(access["username"]),
        "password": str(access["password"]),
        "account_ready": bool(access["account_ready"]),
    }


def list_registry_clients(db: Session) -> list[MasterClient]:
    statement = select(MasterClient).order_by(MasterClient.created_at.desc(), MasterClient.id.desc())
    return list(db.execute(statement).scalars())


def list_registry_tenants(db: Session) -> list[MasterTenant]:
    statement = (
        select(MasterTenant)
        .options(selectinload(MasterTenant.client))
        .order_by(MasterTenant.created_at.desc(), MasterTenant.id.desc())
    )
    return list(db.execute(statement).scalars())


def list_manager_addons(db: Session) -> list[dict[str, object]]:
    tenant = infer_tenant_record_from_session(db)
    current_stage_id = normalize_stage_id(tenant.plan_id if tenant is not None else DEFAULT_STAGE_ID)
    paused_addons = _parse_paused_addons(tenant.paused_addons_json if tenant is not None else None)
    tenant_code = tenant.code if tenant is not None else None
    return [
        _serialize_manager_addon(
            addon,
            current_stage_id=current_stage_id,
            paused_addons=paused_addons,
            tenant_code=tenant_code,
        )
        for addon in addon_catalog()
    ]


def set_master_tenant_addon_paused_state(
    db: Session,
    *,
    tenant_id: int,
    addon_id: str,
    paused: bool,
) -> dict[str, object]:
    tenant = get_registry_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="النسخة المطلوبة غير موجودة.")

    normalized_addon_id = normalize_stage_id(addon_id)
    if normalized_addon_id == "base":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يمكن إيقاف النسخة الأساسية.")

    unlocked_addons = available_addon_ids_up_to(tenant.plan_id or DEFAULT_STAGE_ID)
    if normalized_addon_id not in unlocked_addons:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن التحكم في أداة غير مفتوحة بعد داخل هذه النسخة.",
        )

    paused_addons = _parse_paused_addons(tenant.paused_addons_json)

    if paused:
        if normalized_addon_id in paused_addons:
            return serialize_master_tenant(tenant)
        pauseable_addon_id = _pauseable_addon_id(tenant.plan_id or DEFAULT_STAGE_ID, paused_addons)
        if normalized_addon_id != pauseable_addon_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="أوقف آخر أداة مفتوحة أولًا قبل الرجوع إلى أداة أقدم.",
            )
        paused_addons.append(normalized_addon_id)
    else:
        if normalized_addon_id not in paused_addons:
            return serialize_master_tenant(tenant)
        resumable_addon_id = _resumable_addon_id(paused_addons)
        if normalized_addon_id != resumable_addon_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="أعد تفعيل الأداة الأقرب أولًا قبل فتح الأدوات الأعلى منها.",
            )
        paused_addons = [current_addon_id for current_addon_id in paused_addons if current_addon_id != normalized_addon_id]

    tenant.paused_addons_json = _serialize_paused_addons(paused_addons)
    tenant.updated_at = _utc_now()
    db.commit()
    db.refresh(tenant)

    if addon_status_for_stage(tenant.plan_id or DEFAULT_STAGE_ID, "kitchen", paused_addons) == "active":
        ensure_tenant_kitchen_access(
            database_name=tenant.database_name,
            tenant_code=tenant.code,
            tenant_brand_name=tenant.brand_name,
            regenerate_password=False,
        )

    refreshed = get_registry_tenant(db, tenant.id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="تعذر إعادة تحميل النسخة.")
    return serialize_master_tenant(refreshed)


def get_registry_tenant(db: Session, tenant_id: int) -> MasterTenant | None:
    statement = select(MasterTenant).options(selectinload(MasterTenant.client)).where(MasterTenant.id == tenant_id)
    return db.execute(statement).scalar_one_or_none()


def get_registry_tenant_by_code(db: Session, code: str) -> MasterTenant | None:
    normalized = _slugify(code)
    if not normalized:
        return None
    statement = select(MasterTenant).options(selectinload(MasterTenant.client)).where(MasterTenant.code == normalized)
    return db.execute(statement).scalar_one_or_none()


def create_master_tenant(
    db: Session,
    *,
    client_mode: str,
    existing_client_id: str | None,
    client_owner_name: str | None,
    client_brand_name: str | None,
    client_phone: str | None,
    client_city: str | None,
    tenant_brand_name: str,
    tenant_code: str | None,
    database_name: str | None,
) -> dict[str, object]:
    provisioned_database_path = None
    stage = addon_by_id(DEFAULT_STAGE_ID)

    if client_mode == "existing":
        raw_client_id = (existing_client_id or "").strip()
        if not raw_client_id.isdigit():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اختر العميل الذي سترتبط به النسخة.")
        client = db.get(MasterClient, int(raw_client_id))
        if client is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="العميل المطلوب غير موجود.")
    else:
        owner_name = _normalize_text(client_owner_name or "")
        brand_name = _normalize_text(client_brand_name or tenant_brand_name or "")
        phone = _normalize_text(client_phone or "")
        city = _normalize_text(client_city or "")
        if not owner_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="أدخل اسم العميل.")
        if not brand_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="أدخل اسم العلامة.")
        if not phone:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="أدخل رقم الهاتف.")
        if not city:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="أدخل المدينة.")

        client = MasterClient(
            owner_name=owner_name,
            brand_name=brand_name,
            phone=phone,
            city=city,
            active_plan_id=DEFAULT_STAGE_ID,
            subscription_state="active",
            updated_at=_utc_now(),
        )
        db.add(client)
        db.flush()

    normalized_brand_name = _normalize_text(tenant_brand_name)
    if not normalized_brand_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="أدخل اسم النسخة.")

    normalized_code = _slugify(tenant_code or normalized_brand_name)
    if not normalized_code:
        normalized_code = _generate_unique_code(db, normalized_brand_name)
    elif db.execute(select(MasterTenant.id).where(MasterTenant.code == normalized_code)).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="كود النسخة مستخدم من قبل.")

    normalized_database_name = _slugify(database_name or "")
    if normalized_database_name:
        if normalized_database_name.startswith("tenant_"):
            normalized_database_name = normalized_database_name.removeprefix("tenant_")
        normalized_database_name = f"tenant_{normalized_database_name}"
        if (
            db.execute(select(MasterTenant.id).where(MasterTenant.database_name == normalized_database_name)).scalar_one_or_none()
            is not None
        ):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="اسم قاعدة البيانات مستخدم من قبل.")
    else:
        normalized_database_name = _generate_unique_database_name(db, normalized_code)

    manager_username = _generate_unique_manager_username(db, normalized_code)
    manager_password = _generate_initial_password()

    try:
        tenant = MasterTenant(
            client_id=client.id,
            code=normalized_code,
            brand_name=normalized_brand_name,
            database_name=normalized_database_name,
            manager_username=manager_username,
            environment_state="pending_activation",
            plan_id=DEFAULT_STAGE_ID,
            paused_addons_json=_serialize_paused_addons([]),
            updated_at=_utc_now(),
        )
        client.active_plan_id = DEFAULT_STAGE_ID
        client.updated_at = _utc_now()

        db.add(tenant)
        db.flush()

        provisioned_database_path = provision_tenant_database(
            database_name=normalized_database_name,
            tenant_code=normalized_code,
            tenant_brand_name=normalized_brand_name,
            manager_username=manager_username,
            manager_password=manager_password,
            manager_name=client.owner_name,
        )

        tenant.environment_state = "ready"
        tenant.updated_at = _utc_now()

        db.commit()
        db.refresh(client)
        db.refresh(tenant)
    except HTTPException:
        db.rollback()
        if provisioned_database_path is not None:
            cleanup_provisioned_database(provisioned_database_path)
        raise
    except Exception as error:
        db.rollback()
        if provisioned_database_path is not None:
            cleanup_provisioned_database(provisioned_database_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="تعذر تجهيز قاعدة Tenant الجديدة.",
        ) from error

    return {
        "client": serialize_master_client(client),
        "tenant": serialize_master_tenant(tenant),
        "activation_stage": stage,
        "access": {
            "login_path": build_tenant_manager_login_path(tenant.code),
            "manager_username": manager_username,
            "manager_password": manager_password,
        },
    }


def update_master_tenant(
    db: Session,
    *,
    tenant_id: int,
    client_owner_name: str,
    client_brand_name: str,
    client_phone: str,
    client_city: str,
    brand_name: str,
    activation_stage_id: str,
) -> dict[str, object]:
    tenant = get_registry_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="النسخة المطلوبة غير موجودة.")

    normalized_client_owner_name = _normalize_text(client_owner_name)
    normalized_client_brand_name = _normalize_text(client_brand_name)
    normalized_client_phone = _normalize_text(client_phone)
    normalized_client_city = _normalize_text(client_city)
    normalized_brand_name = _normalize_text(brand_name)

    if not normalized_client_owner_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اسم العميل مطلوب.")
    if not normalized_client_brand_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اسم العلامة مطلوب.")
    if not normalized_client_phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="رقم الهاتف مطلوب.")
    if not normalized_client_city:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="المدينة مطلوبة.")
    if not normalized_brand_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اسم النسخة مطلوب.")

    normalized_stage_id = normalize_stage_id(activation_stage_id)
    _validate_activation_stage_transition(tenant.plan_id or DEFAULT_STAGE_ID, normalized_stage_id)
    paused_addons = _parse_paused_addons(tenant.paused_addons_json)

    tenant.brand_name = normalized_brand_name
    tenant.plan_id = normalized_stage_id
    tenant.paused_addons_json = _serialize_paused_addons(
        [addon_id for addon_id in paused_addons if addon_id != normalized_stage_id]
    )
    tenant.updated_at = _utc_now()

    if tenant.client is not None:
        tenant.client.owner_name = normalized_client_owner_name
        tenant.client.brand_name = normalized_client_brand_name
        tenant.client.phone = normalized_client_phone
        tenant.client.city = normalized_client_city
        tenant.client.active_plan_id = normalized_stage_id
        tenant.client.updated_at = _utc_now()

    db.commit()

    if addon_status_for_stage(normalized_stage_id, "kitchen", _parse_paused_addons(tenant.paused_addons_json)) == "active":
        ensure_tenant_kitchen_access(
            database_name=tenant.database_name,
            tenant_code=tenant.code,
            tenant_brand_name=tenant.brand_name,
            regenerate_password=False,
        )

    db.refresh(tenant)
    refreshed = get_registry_tenant(db, tenant.id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="تعذر إعادة تحميل النسخة.")
    return serialize_master_tenant(refreshed)


def reset_master_tenant_manager_password(db: Session, *, tenant_id: int) -> dict[str, object]:
    tenant = get_registry_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="النسخة المطلوبة غير موجودة.")

    manager_password = _generate_initial_password()
    manager_name = tenant.client.owner_name if tenant.client is not None else tenant.brand_name
    regenerate_tenant_manager_password(
        database_name=tenant.database_name,
        manager_username=tenant.manager_username,
        manager_password=manager_password,
        manager_name=manager_name,
    )

    return {
        "login_path": build_tenant_manager_login_path(tenant.code),
        "manager_username": tenant.manager_username,
        "manager_password": manager_password,
    }


def toggle_master_tenant_suspension(db: Session, *, tenant_id: int) -> dict[str, object]:
    tenant = get_registry_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="النسخة المطلوبة غير موجودة.")

    tenant.environment_state = "ready" if tenant.environment_state == "suspended" else "suspended"
    tenant.updated_at = _utc_now()
    db.commit()
    db.refresh(tenant)
    refreshed = get_registry_tenant(db, tenant.id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="تعذر إعادة تحميل النسخة.")
    return serialize_master_tenant(refreshed)


def delete_master_tenant(db: Session, *, tenant_id: int) -> None:
    tenant = get_registry_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="النسخة المطلوبة غير موجودة.")

    database_path = resolve_tenant_database_path(tenant.database_name)
    db.delete(tenant)
    db.commit()
    cleanup_provisioned_database(database_path)
