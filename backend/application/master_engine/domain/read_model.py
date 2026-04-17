from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import load_settings

from .catalog import addon_catalog
from .registry import (
    _serialize_manager_addon,
    list_registry_clients,
    list_registry_tenants,
    serialize_master_client,
    serialize_master_tenant,
)

SETTINGS = load_settings()


def list_master_addons(db: Session) -> list[dict[str, object]]:
    _ = db
    return [
        _serialize_manager_addon(
            addon,
            current_stage_id="base",
            paused_addons=[],
            tenant_code=None,
        )
        for addon in addon_catalog()
    ]


def list_master_clients(db: Session) -> list[dict[str, object]]:
    return [serialize_master_client(client) for client in list_registry_clients(db)]


def list_master_tenants(db: Session) -> list[dict[str, object]]:
    return [serialize_master_tenant(tenant) for tenant in list_registry_tenants(db)]


def get_master_overview(db: Session) -> dict[str, object]:
    clients = list_master_clients(db)
    tenants = list_master_tenants(db)
    addons = list_master_addons(db)

    pending_count = sum(1 for tenant in tenants if tenant["environment_state"] == "pending_activation")
    suspended_count = sum(1 for tenant in tenants if tenant["environment_state"] == "suspended")
    active_stage_ids = {client["current_stage_id"] for client in clients}

    addon_distribution = [
        f"{addon['name']}: {sum(1 for tenant in tenants if tenant['current_stage_name'] == addon['name'])}"
        for addon in addons
    ]

    latest_tenants = [
        {
            "tenant_id": tenant["id"],
            "brand_name": tenant["brand_name"],
            "code": tenant["code"],
            "activation_stage_name": tenant["current_stage_name"],
        }
        for tenant in tenants[:4]
    ]

    return {
        "stats": [
            {
                "id": "clients",
                "label": "العملاء",
                "value": str(len(clients)),
                "detail": "عدد أصحاب المطاعم المرتبطين باللوحة الأم.",
                "tone": "emerald",
                "icon_key": "clients",
            },
            {
                "id": "tenants",
                "label": "النسخ",
                "value": str(len(tenants)),
                "detail": "عدد النسخ التشغيلية المسجلة.",
                "tone": "cyan",
                "icon_key": "tenants",
            },
            {
                "id": "addons",
                "label": "الإضافات المفعلة",
                "value": str(len(active_stage_ids)),
                "detail": "عدد مستويات التفعيل المستخدمة فعليًا عبر النسخ الحالية.",
                "tone": "violet",
                "icon_key": "addons",
            },
            {
                "id": "pending",
                "label": "بانتظار التفعيل",
                "value": str(pending_count),
                "detail": "نسخ أُنشئت ولم تدخل حالة التشغيل الكامل بعد.",
                "tone": "amber",
                "icon_key": "disabled",
            },
        ],
        "signals": [
            {"label": "العملاء النشطون", "value": str(sum(1 for client in clients if client["subscription_state"] == "active"))},
            {"label": "النسخ الموقوفة", "value": str(suspended_count)},
            {"label": "توزيع الإضافات", "value": " | ".join(addon_distribution) if addon_distribution else "لا توجد بيانات بعد"},
        ],
        "operating_modes": [
            {
                "key": "visible",
                "label": "مفعّل داخل النسخة",
                "detail": "أدوات يراها صاحب المطعم مباشرة داخل نسخته ويعمل بها الآن.",
                "tone": "visible",
            },
            {
                "key": "hidden",
                "label": "يعمل بصمت",
                "detail": "أدوات تجمع البيانات في الخلفية وتبقى واجهتها مقفلة حتى فتحها تجاريًا.",
                "tone": "hidden",
            },
            {
                "key": "disabled",
                "label": "مغلق حتى التفعيل",
                "detail": "أدوات تشغيلية لا تدخل دورة المطعم قبل فتحها من اللوحة الأم.",
                "tone": "disabled",
            },
        ],
        "base_clients_count": sum(1 for client in clients if client["current_stage_id"] == "base"),
        "latest_tenants": latest_tenants,
    }


def authenticate_master(username: str, password: str) -> bool:
    normalized_username = username.strip().lower()
    return normalized_username == SETTINGS.master_admin_username.lower() and password.strip() == SETTINGS.master_admin_password
