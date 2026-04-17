from __future__ import annotations

from typing import Literal


MasterMode = Literal["core", "runtime_hidden", "disabled"]
AddonStatus = Literal["locked", "passive", "active", "paused"]

MANAGER_CHANNEL_KEYS = ("operations", "kitchen", "delivery", "warehouse", "finance", "intelligence", "system")
MANAGER_SECTION_KEYS = (
    "orders",
    "tables",
    "alerts",
    "menu",
    "kitchenMonitor",
    "delivery",
    "deliverySettings",
    "warehouse",
    "warehouseOverview",
    "warehouseSuppliers",
    "warehouseItems",
    "warehouseBalances",
    "warehouseInbound",
    "warehouseOutbound",
    "warehouseCounts",
    "warehouseLedger",
    "financeOverview",
    "financeExpenses",
    "financeCashbox",
    "financeSettlements",
    "financeEntries",
    "financeClosures",
    "operationalHeart",
    "reports",
    "staff",
    "settings",
)

ADDON_SEQUENCE = ("base", "kitchen", "delivery", "warehouse", "finance", "intelligence", "reports")
PASSIVE_ADDON_IDS = {"finance", "intelligence", "reports"}
ALWAYS_ACTIVE_CAPABILITY_KEYS = {"operations", "menu", "system"}
CAPABILITY_LABELS = {
    "operations": "العمليات",
    "menu": "المنيو",
    "kitchen": "المطبخ",
    "delivery": "التوصيل",
    "warehouse": "المستودع",
    "finance": "المالية",
    "intelligence": "التحليلات",
    "reports": "التقارير",
    "system": "النظام",
}
LEGACY_STAGE_MAP = {
    "starter": "base",
    "growth": "delivery",
    "scale": "warehouse",
}


def normalize_stage_id(stage_id: str | None) -> str:
    normalized = (stage_id or "base").strip().lower()
    return LEGACY_STAGE_MAP.get(normalized, normalized or "base")


def _normalize_paused_addons(paused_addons: list[str] | tuple[str, ...] | set[str] | None) -> set[str]:
    if not paused_addons:
        return set()
    return {normalize_stage_id(addon_id) for addon_id in paused_addons if addon_id}


def addon_status_for_stage(stage_id: str, addon_id: str, paused_addons: list[str] | tuple[str, ...] | set[str] | None = None) -> AddonStatus:
    normalized_stage_id = normalize_stage_id(stage_id)
    normalized_addon_id = normalize_stage_id(addon_id)
    paused = _normalize_paused_addons(paused_addons)

    if normalized_addon_id in paused:
        return "paused"
    if normalized_addon_id == "base":
        return "active"

    if normalized_addon_id in PASSIVE_ADDON_IDS:
        return "active" if addon_sequence(normalized_stage_id) >= addon_sequence(normalized_addon_id) else "passive"

    return "active" if addon_sequence(normalized_stage_id) >= addon_sequence(normalized_addon_id) else "locked"


def capability_status_for_stage(
    stage_id: str,
    capability_key: str,
    paused_addons: list[str] | tuple[str, ...] | set[str] | None = None,
) -> AddonStatus:
    if capability_key in ALWAYS_ACTIVE_CAPABILITY_KEYS:
        return "active"
    return addon_status_for_stage(stage_id, capability_key, paused_addons)


def mode_from_addon_status(status: AddonStatus) -> MasterMode:
    if status == "active":
        return "core"
    if status == "passive":
        return "runtime_hidden"
    return "disabled"


def addon_catalog() -> list[dict[str, object]]:
    return [
        {
            "id": "base",
            "sequence": 1,
            "name": "النسخة الأساسية",
            "description": "تشغيل المطعم عبر الطلبات والطاولات والمنيو من دون مطبخ رقمي أو توصيل أو مستودع.",
            "unlock_note": "مفعلة تلقائيًا مع كل نسخة جديدة.",
            "target": "قاعدة التشغيل اليومية التي يبدأ منها كل مطعم قبل فتح أي أداة إضافية.",
            "prerequisite_id": None,
            "prerequisite_label": None,
            "capabilities": [
                {"key": "operations", "label": "العمليات", "mode": "core", "detail": "إدارة الطلبات والطاولات والدورة اليومية."},
                {"key": "menu", "label": "المنيو", "mode": "core", "detail": "إدارة التصنيفات والمنتجات الأساسية والثانوية."},
                {"key": "kitchen", "label": "المطبخ", "mode": "disabled", "detail": "يبقى غير متاح حتى فتح أداة المطبخ."},
                {"key": "delivery", "label": "التوصيل", "mode": "disabled", "detail": "يبقى غير متاح حتى فتح أداة التوصيل."},
                {"key": "warehouse", "label": "المستودع", "mode": "disabled", "detail": "يبقى غير متاح حتى فتح أداة المستودع."},
                {"key": "finance", "label": "المالية", "mode": "disabled", "detail": "يبقى غير متاح حتى فتح الأداة المالية."},
                {"key": "intelligence", "label": "التحليلات", "mode": "disabled", "detail": "يبقى غير متاح حتى فتح أداة التحليلات."},
                {"key": "reports", "label": "التقارير", "mode": "disabled", "detail": "يبقى غير متاح حتى فتح أداة التقارير."},
            ],
        },
        {
            "id": "kitchen",
            "sequence": 2,
            "name": "إضافة المطبخ",
            "description": "فتح شاشة المطبخ الرقمية وربط الطلبات بمسار التنفيذ داخل المطبخ.",
            "unlock_note": "أول أداة بعد النسخة الأساسية.",
            "target": "للمطاعم التي تريد نقل التنفيذ من التذكرة اليدوية إلى شاشة مطبخ حية.",
            "prerequisite_id": "base",
            "prerequisite_label": "النسخة الأساسية",
            "capabilities": [
                {"key": "operations", "label": "العمليات", "mode": "core", "detail": "تبقى قناة التشغيل اليومية."},
                {"key": "menu", "label": "المنيو", "mode": "core", "detail": "يبقى جزءًا من العمليات."},
                {"key": "kitchen", "label": "المطبخ", "mode": "core", "detail": "قناة تنفيذ مستقلة لفريق المطبخ."},
                {"key": "delivery", "label": "التوصيل", "mode": "disabled", "detail": "لا يفتح قبل إنهاء مرحلة المطبخ."},
                {"key": "warehouse", "label": "المستودع", "mode": "disabled", "detail": "لا يفتح قبل التوصيل."},
                {"key": "finance", "label": "المالية", "mode": "disabled", "detail": "لا تفتح قبل استكمال الأدوات التشغيلية."},
                {"key": "intelligence", "label": "التحليلات", "mode": "disabled", "detail": "لا تفتح قبل المالية."},
                {"key": "reports", "label": "التقارير", "mode": "disabled", "detail": "لا تفتح قبل التحليلات."},
            ],
        },
        {
            "id": "delivery",
            "sequence": 3,
            "name": "إضافة التوصيل",
            "description": "فتح فريق التوصيل، المزودين، وسياسة التسعير وإسناد الطلبات.",
            "unlock_note": "تتطلب تفعيل المطبخ أولًا.",
            "target": "للمطاعم التي انتقلت من الاستلام فقط إلى دورة توصيل كاملة.",
            "prerequisite_id": "kitchen",
            "prerequisite_label": "إضافة المطبخ",
            "capabilities": [
                {"key": "operations", "label": "العمليات", "mode": "core", "detail": "تبقى قناة التشغيل اليومية."},
                {"key": "menu", "label": "المنيو", "mode": "core", "detail": "يبقى جزءًا من العمليات."},
                {"key": "kitchen", "label": "المطبخ", "mode": "core", "detail": "يبقى مفعّلًا كشرط سابق."},
                {"key": "delivery", "label": "التوصيل", "mode": "core", "detail": "قناة تشغيل مستقلة لفريق التوصيل."},
                {"key": "warehouse", "label": "المستودع", "mode": "disabled", "detail": "لا يفتح قبل التوصيل."},
                {"key": "finance", "label": "المالية", "mode": "disabled", "detail": "لا تفتح قبل المستودع."},
                {"key": "intelligence", "label": "التحليلات", "mode": "disabled", "detail": "لا تفتح قبل المالية."},
                {"key": "reports", "label": "التقارير", "mode": "disabled", "detail": "لا تفتح قبل التحليلات."},
            ],
        },
        {
            "id": "warehouse",
            "sequence": 4,
            "name": "إضافة المستودع",
            "description": "فتح الموردين، الأصناف، الأرصدة، والحركات المخزنية داخل نسخة المطعم.",
            "unlock_note": "تتطلب تفعيل التوصيل أولًا.",
            "target": "للمطاعم التي وصلت إلى حجم يتطلب تتبع المخزون وحركته.",
            "prerequisite_id": "delivery",
            "prerequisite_label": "إضافة التوصيل",
            "capabilities": [
                {"key": "operations", "label": "العمليات", "mode": "core", "detail": "تبقى قناة التشغيل اليومية."},
                {"key": "menu", "label": "المنيو", "mode": "core", "detail": "يبقى جزءًا من العمليات."},
                {"key": "kitchen", "label": "المطبخ", "mode": "core", "detail": "يبقى مفعّلًا."},
                {"key": "delivery", "label": "التوصيل", "mode": "core", "detail": "يبقى مفعّلًا."},
                {"key": "warehouse", "label": "المستودع", "mode": "core", "detail": "قناة مستقلة للمخزون والحركات."},
                {"key": "finance", "label": "المالية", "mode": "disabled", "detail": "لا تفتح قبل استكمال الطبقة التشغيلية."},
                {"key": "intelligence", "label": "التحليلات", "mode": "disabled", "detail": "لا تفتح قبل المالية."},
                {"key": "reports", "label": "التقارير", "mode": "disabled", "detail": "لا تفتح قبل التحليلات."},
            ],
        },
        {
            "id": "finance",
            "sequence": 5,
            "name": "إضافة المالية",
            "description": "فتح الصندوق والمصروفات والتسويات والإغلاقات داخل لوحة المطعم.",
            "unlock_note": "تتطلب تفعيل المستودع أولًا.",
            "target": "للمطاعم التي تريد إدارة مالية يومية كاملة من داخل النظام.",
            "prerequisite_id": "warehouse",
            "prerequisite_label": "إضافة المستودع",
            "capabilities": [
                {"key": "operations", "label": "العمليات", "mode": "core", "detail": "تبقى قناة التشغيل اليومية."},
                {"key": "menu", "label": "المنيو", "mode": "core", "detail": "يبقى جزءًا من العمليات."},
                {"key": "kitchen", "label": "المطبخ", "mode": "core", "detail": "يبقى مفعّلًا."},
                {"key": "delivery", "label": "التوصيل", "mode": "core", "detail": "يبقى مفعّلًا."},
                {"key": "warehouse", "label": "المستودع", "mode": "core", "detail": "يبقى مفعّلًا."},
                {"key": "finance", "label": "المالية", "mode": "core", "detail": "قناة مستقلة للمالية والتسويات."},
                {"key": "intelligence", "label": "التحليلات", "mode": "disabled", "detail": "لا تفتح قبل المالية."},
                {"key": "reports", "label": "التقارير", "mode": "disabled", "detail": "لا تفتح قبل التحليلات."},
            ],
        },
        {
            "id": "intelligence",
            "sequence": 6,
            "name": "إضافة التحليلات",
            "description": "فتح لوحة المؤشرات والنبض التشغيلي والتحليلات اليومية داخل النظام.",
            "unlock_note": "تتطلب تفعيل المالية أولًا.",
            "target": "للمطاعم التي تريد قراءة المؤشرات التشغيلية من داخل النظام.",
            "prerequisite_id": "finance",
            "prerequisite_label": "إضافة المالية",
            "capabilities": [
                {"key": "operations", "label": "العمليات", "mode": "core", "detail": "تبقى قناة التشغيل اليومية."},
                {"key": "menu", "label": "المنيو", "mode": "core", "detail": "يبقى جزءًا من العمليات."},
                {"key": "kitchen", "label": "المطبخ", "mode": "core", "detail": "يبقى مفعّلًا."},
                {"key": "delivery", "label": "التوصيل", "mode": "core", "detail": "يبقى مفعّلًا."},
                {"key": "warehouse", "label": "المستودع", "mode": "core", "detail": "يبقى مفعّلًا."},
                {"key": "finance", "label": "المالية", "mode": "core", "detail": "تبقى مفعّلة."},
                {"key": "intelligence", "label": "التحليلات", "mode": "core", "detail": "قناة مستقلة للمؤشرات والمتابعة."},
                {"key": "reports", "label": "التقارير", "mode": "disabled", "detail": "لا تفتح قبل التقارير."},
            ],
        },
        {
            "id": "reports",
            "sequence": 7,
            "name": "إضافة التقارير",
            "description": "فتح تقارير الأداء والفترات والمقارنة بشكل مباشر داخل النظام.",
            "unlock_note": "آخر أداة بعد اكتمال بقية الأدوات.",
            "target": "للمطاعم التي تريد طبقة تقارير كاملة فوق كل ما سبق.",
            "prerequisite_id": "intelligence",
            "prerequisite_label": "إضافة التحليلات",
            "capabilities": [
                {"key": "operations", "label": "العمليات", "mode": "core", "detail": "تبقى قناة التشغيل اليومية."},
                {"key": "menu", "label": "المنيو", "mode": "core", "detail": "يبقى جزءًا من العمليات."},
                {"key": "kitchen", "label": "المطبخ", "mode": "core", "detail": "يبقى مفعّلًا."},
                {"key": "delivery", "label": "التوصيل", "mode": "core", "detail": "يبقى مفعّلًا."},
                {"key": "warehouse", "label": "المستودع", "mode": "core", "detail": "يبقى مفعّلًا."},
                {"key": "finance", "label": "المالية", "mode": "core", "detail": "تبقى مفعّلة."},
                {"key": "intelligence", "label": "التحليلات", "mode": "core", "detail": "تبقى مفعّلة."},
                {"key": "reports", "label": "التقارير", "mode": "core", "detail": "قناة مستقلة للتقارير والتحليلات المقارنة."},
            ],
        },
    ]


def addon_by_id(addon_id: str) -> dict[str, object]:
    normalized_id = normalize_stage_id(addon_id)
    return next((addon for addon in addon_catalog() if addon["id"] == normalized_id), addon_catalog()[0])


def addon_sequence(addon_id: str) -> int:
    addon = addon_by_id(addon_id)
    return int(addon["sequence"])


def next_addon_id(addon_id: str) -> str | None:
    current_index = ADDON_SEQUENCE.index(str(addon_by_id(addon_id)["id"]))
    next_index = current_index + 1
    if next_index >= len(ADDON_SEQUENCE):
        return None
    return ADDON_SEQUENCE[next_index]


def available_addon_ids_up_to(addon_id: str) -> list[str]:
    current_index = ADDON_SEQUENCE.index(str(addon_by_id(addon_id)["id"]))
    return list(ADDON_SEQUENCE[: current_index + 1])


def capability_modes_for_stage(
    stage_id: str,
    paused_addons: list[str] | tuple[str, ...] | set[str] | None = None,
) -> dict[str, MasterMode]:
    capability_keys = ("operations", "menu", "kitchen", "delivery", "warehouse", "finance", "intelligence", "reports", "system")
    return {
        key: mode_from_addon_status(capability_status_for_stage(stage_id, key, paused_addons))
        for key in capability_keys
    }


def _aggregate_modes(modes: list[MasterMode]) -> MasterMode:
    if any(mode == "core" for mode in modes):
        return "core"
    if any(mode == "runtime_hidden" for mode in modes):
        return "runtime_hidden"
    return "disabled"


def manager_channel_mode(
    stage_id: str,
    channel_key: str,
    paused_addons: list[str] | tuple[str, ...] | set[str] | None = None,
) -> MasterMode:
    capability_modes = capability_modes_for_stage(stage_id, paused_addons)
    if channel_key == "operations":
        return _aggregate_modes(
            [capability_modes.get("operations", "disabled"), capability_modes.get("menu", "disabled")]
        )
    if channel_key == "kitchen":
        return capability_modes.get("kitchen", "disabled")
    if channel_key == "delivery":
        return capability_modes.get("delivery", "disabled")
    if channel_key == "warehouse":
        return capability_modes.get("warehouse", "disabled")
    if channel_key == "finance":
        return capability_modes.get("finance", "disabled")
    if channel_key == "reports":
        return capability_modes.get("reports", "disabled")
    if channel_key == "intelligence":
        return _aggregate_modes(
            [capability_modes.get("intelligence", "disabled"), capability_modes.get("reports", "disabled")]
        )
    if channel_key == "system":
        return capability_modes.get("system", "core")
    return "disabled"


def manager_section_mode(
    stage_id: str,
    section_key: str,
    paused_addons: list[str] | tuple[str, ...] | set[str] | None = None,
) -> MasterMode:
    if section_key in {"orders", "tables", "alerts"}:
        return manager_channel_mode(stage_id, "operations", paused_addons)
    if section_key == "menu":
        return capability_modes_for_stage(stage_id, paused_addons).get("menu", "disabled")
    if section_key == "kitchenMonitor":
        return manager_channel_mode(stage_id, "kitchen", paused_addons)
    if section_key in {"delivery", "deliverySettings"}:
        return manager_channel_mode(stage_id, "delivery", paused_addons)
    if section_key in {
        "warehouse",
        "warehouseOverview",
        "warehouseSuppliers",
        "warehouseItems",
        "warehouseBalances",
        "warehouseInbound",
        "warehouseOutbound",
        "warehouseCounts",
        "warehouseLedger",
    }:
        return manager_channel_mode(stage_id, "warehouse", paused_addons)
    if section_key in {
        "financeOverview",
        "financeExpenses",
        "financeCashbox",
        "financeSettlements",
        "financeEntries",
        "financeClosures",
    }:
        return manager_channel_mode(stage_id, "finance", paused_addons)
    if section_key == "operationalHeart":
        return capability_modes_for_stage(stage_id, paused_addons).get("intelligence", "disabled")
    if section_key == "reports":
        return capability_modes_for_stage(stage_id, paused_addons).get("reports", "disabled")
    if section_key in {"staff", "settings"}:
        return manager_channel_mode(stage_id, "system", paused_addons)
    return "disabled"


def manager_channel_modes(
    stage_id: str,
    paused_addons: list[str] | tuple[str, ...] | set[str] | None = None,
) -> dict[str, MasterMode]:
    return {key: manager_channel_mode(stage_id, key, paused_addons) for key in MANAGER_CHANNEL_KEYS}


def manager_section_modes(
    stage_id: str,
    paused_addons: list[str] | tuple[str, ...] | set[str] | None = None,
) -> dict[str, MasterMode]:
    return {key: manager_section_mode(stage_id, key, paused_addons) for key in MANAGER_SECTION_KEYS}


def derive_stage_channels(
    stage_id: str,
    paused_addons: list[str] | tuple[str, ...] | set[str] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    addon = addon_by_id(stage_id)
    visible: list[str] = []
    hidden: list[str] = []
    disabled: list[str] = []
    for capability in addon["capabilities"]:
        label = str(capability["label"])
        mode = mode_from_addon_status(capability_status_for_stage(stage_id, str(capability["key"]), paused_addons))
        if mode == "core":
            visible.append(label)
        elif mode == "runtime_hidden":
            hidden.append(label)
        else:
            disabled.append(label)
    return visible, hidden, disabled
