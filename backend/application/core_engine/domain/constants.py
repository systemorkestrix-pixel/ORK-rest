from __future__ import annotations

DELIVERY_FEE_SETTING_KEY = "delivery_fee"
DELIVERY_MIN_ORDER_SETTING_KEY = "delivery_min_order_amount"
DELIVERY_AUTO_NOTIFY_SETTING_KEY = "delivery_auto_notify_team"
DELIVERY_LOCATION_PROVIDER_KEY = "delivery_location_provider"
DELIVERY_LOCATION_GEONAMES_USERNAME_KEY = "delivery_location_geonames_username"
DELIVERY_LOCATION_COUNTRY_CODES_KEY = "delivery_location_country_codes"
DELIVERY_LOCATION_CACHE_TTL_HOURS_KEY = "delivery_location_cache_ttl_hours"
DELIVERY_LOCATION_ENABLED_KEY = "delivery_location_enabled"
OPERATING_COUNTRY_CODE_SETTING_KEY = "operating_country_code"
OPERATING_COUNTRY_NAME_SETTING_KEY = "operating_country_name"
CURRENCY_CODE_SETTING_KEY = "currency_code"
CURRENCY_NAME_SETTING_KEY = "currency_name"
CURRENCY_SYMBOL_SETTING_KEY = "currency_symbol"
CURRENCY_DECIMAL_PLACES_SETTING_KEY = "currency_decimal_places"
KITCHEN_FEATURE_ENABLED_SETTING_KEY = "kitchen_feature_enabled"
DELIVERY_FEATURE_ENABLED_SETTING_KEY = "delivery_feature_enabled"
WAREHOUSE_FEATURE_ENABLED_SETTING_KEY = "warehouse_feature_enabled"
KITCHEN_METRICS_WINDOW_SETTING_KEY = "kitchen_metrics_window"
PUBLIC_STOREFRONT_NAME_SETTING_KEY = "public_storefront_name"
PUBLIC_STOREFRONT_MARK_SETTING_KEY = "public_storefront_mark"
PUBLIC_STOREFRONT_ICON_SETTING_KEY = "public_storefront_icon"
PUBLIC_STOREFRONT_TAGLINE_SETTING_KEY = "public_storefront_tagline"
PUBLIC_STOREFRONT_SOCIAL_LINKS_SETTING_KEY = "public_storefront_social_links"
TELEGRAM_BOT_ENABLED_SETTING_KEY = "telegram_bot_enabled"
TELEGRAM_BOT_TOKEN_SETTING_KEY = "telegram_bot_token"
TELEGRAM_BOT_USERNAME_SETTING_KEY = "telegram_bot_username"
TELEGRAM_BOT_WEBHOOK_SECRET_SETTING_KEY = "telegram_bot_webhook_secret"

OPERATIONAL_SETTINGS_CATALOG: dict[str, dict[str, object]] = {
    "deployment_mode": {
        "default": "on-prem",
        "description": "وضع التشغيل الحالي للنظام المحلي.",
        "editable": False,
    },
    "payment_method": {
        "default": "cash_only",
        "description": "طريقة الدفع المعتمدة في النظام حاليًا.",
        "editable": False,
    },
    "order_polling_ms": {
        "default": "5000",
        "description": "فاصل تحديث الطلبات داخل الواجهات بالميلي ثانية.",
        "editable": True,
    },
    KITCHEN_METRICS_WINDOW_SETTING_KEY: {
        "default": "day",
        "description": "Kitchen metrics window: day / week / month.",
        "editable": True,
    },
    "audit_logs": {
        "default": "enabled",
        "description": "تسجيل العمليات الحساسة داخل سجل التدقيق.",
        "editable": True,
    },
    KITCHEN_FEATURE_ENABLED_SETTING_KEY: {
        "default": "enabled",
        "description": "تفعيل أو إيقاف وحدة المطبخ على مستوى النظام.",
        "editable": True,
    },
    DELIVERY_FEATURE_ENABLED_SETTING_KEY: {
        "default": "enabled",
        "description": "تفعيل أو إيقاف وحدة التوصيل على مستوى النظام.",
        "editable": True,
    },
    WAREHOUSE_FEATURE_ENABLED_SETTING_KEY: {
        "default": "enabled",
        "description": "تفعيل أو إيقاف وحدة المستودع على مستوى النظام.",
        "editable": True,
    },
}
