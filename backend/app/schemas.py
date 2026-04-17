import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .enums import (
    DeliveryAssignmentStatus,
    DeliveryDispatchStatus,
    DriverStatus,
    FinancialTransactionType,
    OrderStatus,
    OrderType,
    PaymentStatus,
    ProductKind,
    CashChannel,
    TableStatus,
    UserRole,
)

PHONE_PATTERN = re.compile(r"^[0-9\u0660-\u0669+\-()\s]{6,40}$")


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    return normalized or None


def _validate_phone_format(phone: str) -> None:
    if not PHONE_PATTERN.fullmatch(phone):
        raise ValueError("صيغة رقم الهاتف غير صحيحة.")
    digit_count = sum(1 for char in phone if char.isdigit())
    if digit_count < 6:
        raise ValueError("رقم الهاتف يجب أن يحتوي 6 أرقام على الأقل.")


def _normalize_product_kind_value(value: object) -> object:
    if isinstance(value, ProductKind):
        return value
    if not isinstance(value, str):
        return value
    normalized = value.strip().lower()
    if normalized in {"sellable", "primary"}:
        return ProductKind.PRIMARY
    if normalized in {"internal", "secondary"}:
        return ProductKind.SECONDARY
    return value


class UserOut(BaseModel):
    id: int
    name: str
    username: str
    role: UserRole
    active: bool
    permissions_effective: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class LoginInput(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=4, max_length=120)
    role: UserRole


class RefreshInput(BaseModel):
    refresh_token: str = Field(min_length=20)


class TokenPairOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class AuthSessionOut(BaseModel):
    user: UserOut
    token_type: str = "cookie"


class MasterLoginInput(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=8, max_length=120)


class MasterIdentityOut(BaseModel):
    username: str
    display_name: str
    role_label: str


class MasterSessionOut(BaseModel):
    identity: MasterIdentityOut
    token_type: str = "cookie"


class MasterOverviewStatOut(BaseModel):
    id: str
    label: str
    value: str
    detail: str
    tone: Literal["emerald", "cyan", "amber", "violet"]
    icon_key: str


class MasterSignalOut(BaseModel):
    label: str
    value: str


class MasterOperatingModeOut(BaseModel):
    key: str
    label: str
    detail: str
    tone: Literal["visible", "hidden", "disabled"]


class MasterLatestTenantOut(BaseModel):
    tenant_id: str
    brand_name: str
    code: str
    activation_stage_name: str


class MasterOverviewOut(BaseModel):
    stats: list[MasterOverviewStatOut] = Field(default_factory=list)
    signals: list[MasterSignalOut] = Field(default_factory=list)
    operating_modes: list[MasterOperatingModeOut] = Field(default_factory=list)
    base_clients_count: int = 0
    latest_tenants: list[MasterLatestTenantOut] = Field(default_factory=list)


class MasterAddonCapabilityOut(BaseModel):
    key: str
    label: str
    status: Literal["locked", "passive", "active", "paused"] = "locked"
    mode: Literal["core", "runtime_hidden", "disabled"]
    detail: str


class MasterAddonOut(BaseModel):
    id: str
    sequence: int
    name: str
    description: str
    unlock_note: str
    target: str
    prerequisite_id: str | None = None
    prerequisite_label: str | None = None
    status: Literal["locked", "passive", "active", "paused"] = "locked"
    can_activate_now: bool = False
    purchase_state: Literal["owned", "next", "later"] = "later"
    paypal_checkout_url: str | None = None
    telegram_checkout_url: str | None = None
    capabilities: list[MasterAddonCapabilityOut] = Field(default_factory=list)


class MasterClientOut(BaseModel):
    id: str
    owner_name: str
    brand_name: str
    phone: str
    city: str
    current_stage_id: str
    current_stage_name: str
    subscription_state: Literal["active", "trial", "paused"]
    next_billing_date: str


class MasterTenantOut(BaseModel):
    id: str
    code: str
    brand_name: str
    client_id: str
    client_owner_name: str
    client_brand_name: str
    database_name: str
    manager_username: str
    environment_state: Literal["ready", "pending_activation", "suspended"]
    enabled_tools: list[str] = Field(default_factory=list)
    hidden_tools: list[str] = Field(default_factory=list)
    locked_tools: list[str] = Field(default_factory=list)
    paused_tools: list[str] = Field(default_factory=list)
    current_stage_id: str
    current_stage_name: str
    next_addon_id: str | None = None
    next_addon_name: str | None = None
    manager_login_path: str
    public_order_path: str


class MasterTenantCreateInput(BaseModel):
    client_mode: Literal["existing", "new"] = "new"
    existing_client_id: str | None = None
    client_owner_name: str | None = Field(default=None, max_length=120)
    client_brand_name: str | None = Field(default=None, max_length=120)
    client_phone: str | None = Field(default=None, max_length=40)
    client_city: str | None = Field(default=None, max_length=120)
    tenant_brand_name: str = Field(min_length=2, max_length=120)
    tenant_code: str | None = Field(default=None, max_length=80)
    database_name: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_client_mode(self) -> "MasterTenantCreateInput":
        if self.client_mode == "existing":
            if not _normalize_optional_text(self.existing_client_id):
                raise ValueError("اختر العميل الذي ستربط به النسخة.")
            return self
        if not _normalize_optional_text(self.client_owner_name):
            raise ValueError("اسم العميل مطلوب.")
        if not _normalize_optional_text(self.client_brand_name):
            raise ValueError("اسم العلامة مطلوب.")
        if not _normalize_optional_text(self.client_phone):
            raise ValueError("رقم الهاتف مطلوب.")
        _validate_phone_format(str(self.client_phone))
        if not _normalize_optional_text(self.client_city):
            raise ValueError("المدينة مطلوبة.")
        return self


class MasterTenantUpdateInput(BaseModel):
    client_owner_name: str = Field(min_length=2, max_length=120)
    client_brand_name: str = Field(min_length=2, max_length=120)
    client_phone: str = Field(min_length=8, max_length=40)
    client_city: str = Field(min_length=2, max_length=120)
    brand_name: str = Field(min_length=2, max_length=120)
    activation_stage_id: str = Field(min_length=2, max_length=40)

    @model_validator(mode="after")
    def validate_client_fields(self) -> "MasterTenantUpdateInput":
        _validate_phone_format(str(self.client_phone))
        return self


RestaurantEmployeeType = Literal[
    "cook",
    "kitchen_assistant",
    "delivery_staff",
    "courier",
    "warehouse_keeper",
    "cashier",
    "service_staff",
    "admin_staff",
]
RestaurantEmployeeCompensationCycle = Literal["monthly", "weekly", "daily", "hourly"]


class RestaurantEmployeeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    employee_type: RestaurantEmployeeType
    phone: str | None = Field(default=None, max_length=40)
    compensation_cycle: RestaurantEmployeeCompensationCycle = "monthly"
    compensation_amount: float = Field(ge=0, default=0)
    work_schedule: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=1000)
    active: bool = True

    @model_validator(mode="after")
    def normalize_employee_fields(self) -> "RestaurantEmployeeCreate":
        self.phone = _normalize_optional_text(self.phone)
        self.work_schedule = _normalize_optional_text(self.work_schedule)
        self.notes = _normalize_optional_text(self.notes)
        if self.phone is not None:
            _validate_phone_format(self.phone)
        return self


class RestaurantEmployeeUpdate(RestaurantEmployeeCreate):
    pass


class RestaurantEmployeeOut(BaseModel):
    id: int
    name: str
    employee_type: RestaurantEmployeeType
    phone: str | None
    compensation_cycle: RestaurantEmployeeCompensationCycle
    compensation_amount: float
    work_schedule: str | None
    notes: str | None
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TenantEntryOut(BaseModel):
    tenant_id: str
    tenant_code: str
    tenant_brand_name: str
    client_brand_name: str
    client_owner_name: str
    manager_login_path: str
    public_order_path: str
    public_menu_path: str


class ManagerTenantContextOut(BaseModel):
    tenant_id: str | None = None
    tenant_code: str | None = None
    tenant_brand_name: str | None = None
    database_name: str | None = None
    activation_stage_id: str
    activation_stage_name: str
    channel_modes: dict[str, Literal["core", "runtime_hidden", "disabled"]] = Field(default_factory=dict)
    section_modes: dict[str, Literal["core", "runtime_hidden", "disabled"]] = Field(default_factory=dict)


class MasterTenantAccessOut(BaseModel):
    login_path: str
    manager_username: str
    manager_password: str


class ManagerKitchenAccessOut(BaseModel):
    login_path: str
    username: str
    password: str
    account_ready: bool = True


class MasterTenantCreateResultOut(BaseModel):
    client: MasterClientOut
    tenant: MasterTenantOut
    activation_stage: MasterAddonOut
    access: MasterTenantAccessOut


class ProductSecondaryLinkInput(BaseModel):
    secondary_product_id: int = Field(gt=0)
    sort_order: int = Field(default=0, ge=0)
    is_default: bool = False
    max_quantity: int = Field(default=1, ge=1)


class ProductConsumptionComponentInput(BaseModel):
    warehouse_item_id: int = Field(gt=0)
    quantity_per_unit: float = Field(gt=0)


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    price: float = Field(gt=0)
    kind: ProductKind = ProductKind.PRIMARY
    available: bool = True
    category_id: int | None = Field(default=None, gt=0)
    secondary_links: list[ProductSecondaryLinkInput] = Field(default_factory=list)
    consumption_components: list[ProductConsumptionComponentInput] = Field(default_factory=list)

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_kind(cls, value: object) -> object:
        return _normalize_product_kind_value(value)

    @model_validator(mode="after")
    def validate_category_requirement(self) -> "ProductCreate":
        if self.kind == ProductKind.PRIMARY and (self.category_id is None or self.category_id <= 0):
            raise ValueError("اختر تصنيفًا صالحًا للمنتج الأساسي.")
        return self


class ProductUpdate(ProductCreate):
    secondary_links: list[ProductSecondaryLinkInput] | None = None
    consumption_components: list[ProductConsumptionComponentInput] | None = None
    is_archived: bool | None = None


class ProductSecondaryLinkOut(BaseModel):
    id: int
    secondary_product_id: int
    secondary_product_name: str | None
    sort_order: int
    is_default: bool
    max_quantity: int

    model_config = {"from_attributes": True}


class ProductConsumptionComponentOut(BaseModel):
    id: int
    warehouse_item_id: int
    warehouse_item_name: str | None
    warehouse_item_unit: str | None
    quantity_per_unit: float

    model_config = {"from_attributes": True}


class ProductOut(BaseModel):
    id: int
    name: str
    description: str | None
    price: float
    kind: str = Field(validation_alias="legacy_kind")
    normalized_kind: ProductKind = Field(validation_alias="kind")
    available: bool
    category: str
    category_id: int
    image_path: str | None
    is_archived: bool
    secondary_links: list[ProductSecondaryLinkOut] = Field(default_factory=list)
    consumption_components: list[ProductConsumptionComponentOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PublicProductOut(BaseModel):
    id: int
    name: str
    description: str | None
    price: float
    category: str
    image_path: str | None

    model_config = {"from_attributes": True}


class PublicSecondaryOptionOut(BaseModel):
    product_id: int
    name: str
    description: str | None
    price: float
    image_path: str | None
    sort_order: int
    is_default: bool
    max_quantity: int


class PublicJourneyProductOut(BaseModel):
    id: int
    name: str
    description: str | None
    price: float
    category: str
    image_path: str | None
    secondary_options: list[PublicSecondaryOptionOut] = Field(default_factory=list)


class PublicJourneyCategoryOut(BaseModel):
    name: str
    products: list[PublicJourneyProductOut] = Field(default_factory=list)


class PublicJourneyCatalogOut(BaseModel):
    categories: list[PublicJourneyCategoryOut] = Field(default_factory=list)
    secondary_products: list[PublicSecondaryOptionOut] = Field(default_factory=list)


class PublicOrderJourneyMetaOut(BaseModel):
    journey_version: str = Field(default="v1", min_length=1, max_length=16)
    generated_at: datetime


class PublicJourneyDeliveryOut(BaseModel):
    delivery_fee: float
    min_order_amount: float
    pricing_mode: str = "fixed"
    structured_locations_enabled: bool = False
    zones_configured: bool = False


class PublicJourneyTableContextOut(BaseModel):
    table_id: int | None = None
    has_table_context: bool = False
    has_active_session: bool = False
    table_status: TableStatus | None = None
    total_orders: int = 0
    active_orders_count: int = 0
    unsettled_orders_count: int = 0
    unpaid_total: float = 0.0
    latest_order_status: OrderStatus | None = None


class PublicJourneyRulesOut(BaseModel):
    allowed_order_types: list[OrderType] = Field(default_factory=list)
    default_order_type: OrderType = OrderType.TAKEAWAY
    workflow_profile: str = "kitchen_managed"
    require_phone_for_takeaway: bool = True
    require_phone_for_delivery: bool = True
    require_address_for_delivery: bool = True
    allow_manual_table_selection: bool = True


class PublicOrderJourneyBootstrapOut(BaseModel):
    meta: PublicOrderJourneyMetaOut
    catalog: PublicJourneyCatalogOut
    capabilities: "OperationalCapabilitiesOut"
    delivery: PublicJourneyDeliveryOut
    table_context: PublicJourneyTableContextOut
    journey_rules: PublicJourneyRulesOut


class PublicOrderTrackingOut(BaseModel):
    tracking_code: str
    type: OrderType
    status: OrderStatus
    workflow_profile: str = "kitchen_managed"
    payment_status: PaymentStatus
    created_at: datetime
    subtotal: float
    delivery_fee: float
    total: float
    notes: str | None
    items: list["OrderItemOut"] = Field(default_factory=list)


class ProductsPageOut(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    page_size: int


class ProductCategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    active: bool = True
    sort_order: int = Field(default=0, ge=0)


class ProductCategoryUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    active: bool
    sort_order: int = Field(default=0, ge=0)


class ProductCategoryOut(BaseModel):
    id: int
    name: str
    active: bool
    sort_order: int

    model_config = {"from_attributes": True}


class ProductImageInput(BaseModel):
    mime_type: str
    data_base64: str = Field(min_length=20)


class TableOut(BaseModel):
    id: int
    qr_code: str
    status: TableStatus

    model_config = {"from_attributes": True}


class ManagerTableOut(TableOut):
    total_orders_count: int
    has_active_session: bool
    active_orders_count: int
    unsettled_orders_count: int
    unpaid_total: float


class TableCreateInput(BaseModel):
    status: TableStatus = TableStatus.AVAILABLE


class TableUpdateInput(BaseModel):
    status: TableStatus


class TableSessionSettlementInput(BaseModel):
    amount_received: float | None = Field(default=None, gt=0)


class CreateOrderItemInput(BaseModel):
    product_id: int
    quantity: int = Field(ge=1)


class CreateOrderInput(BaseModel):
    type: OrderType
    table_id: int | None = Field(default=None, gt=0)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=255)
    delivery_location_key: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=255)
    items: list[CreateOrderItemInput] = Field(min_length=1)

    @model_validator(mode="after")
    def check_required_fields(self) -> "CreateOrderInput":
        self.phone = _normalize_optional_text(self.phone)
        self.address = _normalize_optional_text(self.address)
        self.delivery_location_key = _normalize_optional_text(self.delivery_location_key)
        self.notes = _normalize_optional_text(self.notes)

        if self.phone is not None:
            _validate_phone_format(self.phone)

        if self.type == OrderType.DINE_IN and not self.table_id:
            raise ValueError("رقم الطاولة مطلوب للطلبات الداخلية.")
        if self.type == OrderType.DELIVERY and not self.phone:
            raise ValueError("رقم الهاتف مطلوب لطلبات التوصيل.")
        if self.type == OrderType.DELIVERY and not self.address:
            raise ValueError("عنوان التوصيل مطلوب.")
        if self.type == OrderType.DELIVERY and self.address is not None and len(self.address) < 5:
            raise ValueError("عنوان التوصيل يجب أن يكون 5 أحرف على الأقل.")
        return self


class ManagerCreateOrderInput(BaseModel):
    type: OrderType
    table_id: int | None = Field(default=None, gt=0)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=255)
    delivery_location_key: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=255)
    items: list[CreateOrderItemInput] = Field(min_length=1)

    @model_validator(mode="after")
    def check_required_fields(self) -> "ManagerCreateOrderInput":
        self.phone = _normalize_optional_text(self.phone)
        self.address = _normalize_optional_text(self.address)
        self.delivery_location_key = _normalize_optional_text(self.delivery_location_key)
        self.notes = _normalize_optional_text(self.notes)

        if self.phone is not None:
            _validate_phone_format(self.phone)

        if self.type == OrderType.DINE_IN and not self.table_id:
            raise ValueError("رقم الطاولة مطلوب للطلبات الداخلية.")
        if self.type == OrderType.DELIVERY and not self.phone:
            raise ValueError("رقم الهاتف مطلوب لطلبات التوصيل.")
        if self.type == OrderType.DELIVERY and not self.address:
            raise ValueError("عنوان التوصيل مطلوب.")
        if self.type == OrderType.DELIVERY and self.address is not None and len(self.address) < 5:
            raise ValueError("عنوان التوصيل يجب أن يكون 5 أحرف على الأقل.")
        return self


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    price: float
    product_name: str

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    tracking_code: str
    type: OrderType
    status: OrderStatus
    table_id: int | None
    phone: str | None
    address: str | None
    delivery_location_key: str | None = None
    delivery_location_label: str | None = None
    delivery_location_level: str | None = None
    subtotal: float
    delivery_fee: float
    total: float
    created_at: datetime
    notes: str | None
    payment_status: PaymentStatus
    paid_at: datetime | None
    paid_by: int | None
    amount_received: float | None
    change_amount: float | None
    payment_method: str
    delivery_team_notified_at: datetime | None
    delivery_team_notified_by: int | None
    delivery_failure_resolution_status: str | None = None
    delivery_failure_resolution_note: str | None = None
    delivery_failure_resolved_at: datetime | None = None
    delivery_failure_resolved_by: int | None = None
    sent_to_kitchen_at: datetime | None = None
    delivery_settlement_id: int | None = None
    delivery_settlement_status: str | None = None
    delivery_settlement_remaining_store_due_amount: float | None = None
    delivery_assignment_status: str | None = None
    delivery_assignment_driver_id: int | None = None
    delivery_assignment_driver_name: str | None = None
    delivery_assignment_assigned_at: datetime | None = None
    delivery_assignment_departed_at: datetime | None = None
    delivery_assignment_delivered_at: datetime | None = None
    delivery_dispatch_id: int | None = None
    delivery_dispatch_status: str | None = None
    delivery_dispatch_scope: str | None = None
    delivery_dispatch_provider_id: int | None = None
    delivery_dispatch_provider_name: str | None = None
    delivery_dispatch_driver_id: int | None = None
    delivery_dispatch_driver_name: str | None = None
    delivery_dispatch_sent_at: datetime | None = None
    delivery_dispatch_responded_at: datetime | None = None
    items: list[OrderItemOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class TableSessionOut(BaseModel):
    table: TableOut
    has_active_session: bool
    total_orders: int
    active_orders_count: int
    unsettled_orders_count: int
    unpaid_total: float
    latest_order_status: OrderStatus | None
    orders: list[OrderOut] = Field(default_factory=list)


class TableSessionSettlementOut(BaseModel):
    table_id: int
    settled_order_ids: list[int]
    settled_total: float
    amount_received: float
    change_amount: float
    table_status: TableStatus


class OrderTransitionInput(BaseModel):
    target_status: OrderStatus
    amount_received: float | None = Field(default=None, gt=0)
    collect_payment: bool = True
    reason_code: str | None = Field(default=None, min_length=2, max_length=80)
    reason_note: str | None = Field(default=None, max_length=255)


class OrderCancelInput(BaseModel):
    reason_code: str = Field(min_length=2, max_length=80)
    reason_note: str | None = Field(default=None, max_length=255)


class EmergencyDeliveryFailInput(BaseModel):
    reason_code: str = Field(min_length=2, max_length=80)
    reason_note: str | None = Field(default=None, max_length=255)


class DeliveryFailureResolutionInput(BaseModel):
    resolution_action: Literal["retry_delivery", "convert_to_takeaway", "close_failure"]
    resolution_note: str | None = Field(default=None, max_length=255)


class OrderPaymentCollectionInput(BaseModel):
    amount_received: float | None = Field(default=None, gt=0)


class OrderRefundInput(BaseModel):
    note: str | None = Field(default=None, max_length=255)


class OrdersPageOut(BaseModel):
    items: list[OrderOut]
    total: int
    page: int
    page_size: int


class KitchenMonitorSummaryOut(BaseModel):
    sent_to_kitchen: int
    in_preparation: int
    ready: int
    oldest_order_wait_seconds: int
    metrics_window: Literal["day", "week", "month"] = "day"
    avg_prep_minutes_today: float
    warehouse_issued_quantity_today: float = 0.0
    warehouse_issue_vouchers_today: int = 0
    warehouse_issued_items_today: int = 0


class KitchenOrdersPageOut(BaseModel):
    items: list[OrderOut]
    total: int
    page: int
    page_size: int
    scope: Literal["active", "history"] = "active"
    summary: KitchenMonitorSummaryOut


class DashboardOut(BaseModel):
    created: int
    confirmed: int
    sent_to_kitchen: int
    in_preparation: int
    ready: int
    out_for_delivery: int
    delivered: int
    delivery_failed: int
    canceled: int
    active_orders: int
    today_sales: float
    today_expenses: float
    today_net: float


class OperationalHeartMetaOut(BaseModel):
    generated_at: datetime
    local_business_date: date
    refresh_recommended_ms: int = Field(ge=1000, le=30000)
    contract_version: str = Field(default="2.1", min_length=1, max_length=16)


class OperationalHeartCapabilitiesOut(BaseModel):
    kitchen_feature_enabled: bool = True
    delivery_feature_enabled: bool = True
    kitchen_runtime_enabled: bool = True
    delivery_runtime_enabled: bool = True
    kitchen_enabled: bool
    delivery_enabled: bool
    kitchen_active_users: int
    delivery_active_users: int
    kitchen_block_reason: str | None
    delivery_block_reason: str | None


class OperationalHeartKpisOut(BaseModel):
    active_orders: int
    kitchen_active_orders: int
    delivery_active_orders: int
    ready_orders: int
    today_sales: float
    today_expenses: float
    today_net: float
    avg_prep_minutes_today: float
    oldest_kitchen_wait_seconds: int


class OperationalHeartQueueOut(BaseModel):
    key: str
    label: str
    count: int
    oldest_age_seconds: int
    aged_over_sla_count: int
    sla_seconds: int
    action_route: str


class OperationalHeartIncidentOut(BaseModel):
    code: str
    severity: str
    title: str
    message: str
    count: int
    oldest_age_seconds: int | None = None
    action_route: str


class OperationalHeartTimelineItemOut(BaseModel):
    timestamp: datetime
    domain: str
    title: str
    description: str
    action_route: str | None = None
    order_id: int | None = None
    entity_id: int | None = None


class OperationalHeartFinancialControlOut(BaseModel):
    severity: str = "info"
    action_route: str = "/manager/financial"
    shift_closed_today: bool = False
    latest_shift_variance: float = 0.0
    sales_transactions_today: int = 0
    expense_transactions_today: int = 0
    today_net: float = 0.0


class OperationalHeartWarehouseControlOut(BaseModel):
    severity: str = "info"
    action_route: str = "/manager/warehouse"
    active_items: int = 0
    low_stock_items: int = 0
    pending_stock_counts: int = 0
    inbound_today: float = 0.0
    outbound_today: float = 0.0


class OperationalHeartTablesControlOut(BaseModel):
    severity: str = "info"
    action_route: str = "/manager/tables"
    active_sessions: int = 0
    blocked_settlement_tables: int = 0
    unpaid_orders: int = 0
    unpaid_total: float = 0.0


class OperationalHeartExpensesControlOut(BaseModel):
    severity: str = "info"
    action_route: str = "/manager/expenses"
    pending_approvals: int = 0
    pending_amount: float = 0.0
    rejected_today: int = 0
    high_value_pending_amount: float = 0.0


class OperationalHeartReconciliationOut(BaseModel):
    key: str
    label: str
    ok: bool
    severity: str = "info"
    detail: str
    action_route: str


class OperationalHeartOut(BaseModel):
    meta: OperationalHeartMetaOut
    capabilities: OperationalHeartCapabilitiesOut
    kpis: OperationalHeartKpisOut
    queues: list[OperationalHeartQueueOut]
    incidents: list[OperationalHeartIncidentOut]
    timeline: list[OperationalHeartTimelineItemOut]
    financial_control: OperationalHeartFinancialControlOut = Field(default_factory=OperationalHeartFinancialControlOut)
    warehouse_control: OperationalHeartWarehouseControlOut = Field(default_factory=OperationalHeartWarehouseControlOut)
    tables_control: OperationalHeartTablesControlOut = Field(default_factory=OperationalHeartTablesControlOut)
    expenses_control: OperationalHeartExpensesControlOut = Field(default_factory=OperationalHeartExpensesControlOut)
    reconciliations: list[OperationalHeartReconciliationOut] = Field(default_factory=list)


class FinancialTransactionOut(BaseModel):
    id: int
    order_id: int | None
    delivery_settlement_id: int | None
    expense_id: int | None
    amount: float
    type: str
    direction: str | None
    account_code: str | None
    reference_group: str | None
    created_by: int
    created_at: datetime
    note: str | None

    model_config = {"from_attributes": True}


class DeliverySettlementOut(BaseModel):
    id: int
    order_id: int
    assignment_id: int
    driver_id: int
    status: str
    driver_share_model: str
    driver_share_value: float
    expected_customer_total: float
    actual_collected_amount: float
    food_revenue_amount: float
    delivery_revenue_amount: float
    driver_due_amount: float
    store_due_amount: float
    remitted_amount: float
    remaining_store_due_amount: float
    variance_amount: float
    variance_reason: str | None
    recognized_at: datetime
    settled_at: datetime | None
    settled_by: int | None
    note: str | None

    model_config = {"from_attributes": True}


class CashboxMovementOut(BaseModel):
    id: int
    delivery_settlement_id: int | None
    order_id: int | None
    type: str
    direction: str
    amount: float
    cash_channel: str
    performed_by: int
    created_at: datetime
    note: str | None
    model_config = {"from_attributes": True}


class CashboxMovementCreate(BaseModel):
    settlement_id: int = Field(gt=0)
    amount: float = Field(gt=0)
    movement_type: Literal["remittance", "payout"]
    cash_channel: CashChannel = CashChannel.CASH_DRAWER
    note: str | None = Field(default=None, max_length=255)


class DeliveryAccountingMigrationStatusOut(BaseModel):
    legacy_candidates: int
    pending_migratable: int
    blocked_missing_assignment: int
    blocked_missing_driver: int
    backfilled_orders: int
    assumed_amount_received_orders: int
    cutover_ready: bool
    cutover_completed_at: datetime | None
    last_backfill_at: datetime | None
    last_backfill_by: int | None
    pending_order_ids: list[int] = Field(default_factory=list)
    blocked_missing_assignment_order_ids: list[int] = Field(default_factory=list)
    blocked_missing_driver_order_ids: list[int] = Field(default_factory=list)


class DeliveryAccountingBackfillInput(BaseModel):
    limit: int = Field(default=100, ge=1, le=500)
    dry_run: bool = False


class DeliveryAccountingBackfillOut(BaseModel):
    processed_orders: int
    migrated_orders: int
    blocked_missing_assignment: int
    blocked_missing_driver: int
    assumed_amount_received_orders: int
    dry_run: bool
    migrated_order_ids: list[int] = Field(default_factory=list)
    skipped_missing_assignment_order_ids: list[int] = Field(default_factory=list)
    skipped_missing_driver_order_ids: list[int] = Field(default_factory=list)
    status: DeliveryAccountingMigrationStatusOut


class ShiftClosureCreate(BaseModel):
    opening_cash: float = Field(ge=0, default=0)
    actual_cash: float = Field(ge=0)
    note: str | None = Field(default=None, max_length=255)


class ShiftClosureOut(BaseModel):
    id: int
    business_date: date
    opening_cash: float
    sales_total: float
    refunds_total: float
    expenses_total: float
    expected_cash: float
    actual_cash: float
    variance: float
    transactions_count: int
    note: str | None
    closed_by: int
    closed_at: datetime

    model_config = {"from_attributes": True}


class ExpenseCostCenterCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=120)
    active: bool = True


class ExpenseCostCenterUpdate(ExpenseCostCenterCreate):
    pass


class ExpenseCostCenterOut(BaseModel):
    id: int
    code: str
    name: str
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExpenseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=60)
    cost_center_id: int = Field(gt=0)
    amount: float = Field(gt=0)
    note: str | None = Field(default=None, max_length=255)


class ExpenseUpdate(ExpenseCreate):
    pass


class ExpenseReviewInput(BaseModel):
    note: str | None = Field(default=None, max_length=255)


class ExpenseAttachmentCreate(BaseModel):
    file_name: str | None = Field(default=None, max_length=180)
    mime_type: str = Field(min_length=8, max_length=80)
    data_base64: str = Field(min_length=20)


class ExpenseAttachmentOut(BaseModel):
    id: int
    expense_id: int
    file_name: str
    file_url: str
    mime_type: str
    size_bytes: int
    uploaded_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ExpenseOut(BaseModel):
    id: int
    title: str
    category: str
    cost_center_id: int
    cost_center_name: str | None
    amount: float
    note: str | None
    status: str
    reviewed_by: int | None
    reviewed_at: datetime | None
    review_note: str | None
    attachments: list[ExpenseAttachmentOut] = Field(default_factory=list)
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeliveryDriverCreate(BaseModel):
    user_id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=2, max_length=120)
    provider_id: int | None = Field(default=None, gt=0)
    phone: str = Field(min_length=5, max_length=40)
    vehicle: str | None = Field(default=None, max_length=120)
    active: bool = True


class DeliveryDriverUpdate(BaseModel):
    provider_id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=5, max_length=40)
    vehicle: str | None = Field(default=None, max_length=120)
    active: bool
    status: DriverStatus


class DeliveryDriverOut(BaseModel):
    id: int
    user_id: int | None = None
    provider_id: int | None = None
    provider_name: str | None = None
    provider_type: str | None = None
    name: str
    phone: str
    status: DriverStatus
    vehicle: str | None
    active: bool
    telegram_chat_id: str | None = None
    telegram_username: str | None = None
    telegram_link_code: str | None = None
    telegram_link_expires_at: datetime | None = None
    telegram_linked_at: datetime | None = None
    telegram_enabled: bool = False
    can_delete: bool = False
    delete_block_reason: str | None = None
    recommended_management_action: str | None = None

    model_config = {"from_attributes": True}


class DeliveryTeamNotifyInput(BaseModel):
    order_id: int


class DeliveryAssignmentOut(BaseModel):
    id: int
    order_id: int
    driver_id: int
    assigned_at: datetime
    departed_at: datetime | None
    delivered_at: datetime | None
    status: DeliveryAssignmentStatus

    model_config = {"from_attributes": True}


class DeliveryDispatchCreate(BaseModel):
    order_id: int = Field(gt=0)
    provider_id: int | None = Field(default=None, gt=0)
    driver_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_target(self) -> "DeliveryDispatchCreate":
        if (self.provider_id is None and self.driver_id is None) or (
            self.provider_id is not None and self.driver_id is not None
        ):
            raise ValueError("اختر جهة توصيل واحدة فقط: جهة أو سائق.")
        return self


class DeliveryDispatchDecisionInput(BaseModel):
    dispatch_id: int = Field(gt=0)


class DeliveryDispatchAssignDriverInput(BaseModel):
    driver_id: int = Field(gt=0)


class DeliveryDispatchOut(BaseModel):
    id: int
    order_id: int
    provider_id: int | None
    provider_name: str | None = None
    driver_id: int | None
    driver_name: str | None = None
    dispatch_scope: str
    status: DeliveryDispatchStatus
    channel: str
    sent_at: datetime
    responded_at: datetime | None
    expires_at: datetime | None
    created_by: int | None

    model_config = {"from_attributes": True}


class DeliveryProviderCreate(BaseModel):
    account_user_id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=2, max_length=120)
    provider_type: Literal["internal_team", "partner_company"] = "partner_company"
    active: bool = True

    @model_validator(mode="after")
    def validate_account_user(self) -> "DeliveryProviderCreate":
        if self.provider_type == "partner_company" and self.account_user_id is None:
            raise ValueError("حساب لوحة جهة التوصيل مطلوب عند إنشاء جهة خارجية.")
        return self


class DeliveryProviderUpdate(BaseModel):
    account_user_id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=2, max_length=120)
    provider_type: Literal["internal_team", "partner_company"]
    active: bool

    @model_validator(mode="after")
    def validate_account_user(self) -> "DeliveryProviderUpdate":
        if self.provider_type == "partner_company" and self.account_user_id is None:
            raise ValueError("حساب لوحة جهة التوصيل مطلوب عند تحديث جهة خارجية.")
        return self


class DeliveryProviderOut(BaseModel):
    id: int
    account_user_id: int | None = None
    account_user_name: str | None = None
    account_username: str | None = None
    name: str
    provider_type: str
    active: bool
    is_internal_default: bool
    created_at: datetime
    can_delete: bool = False
    delete_block_reason: str | None = None
    recommended_management_action: str | None = None

    model_config = {"from_attributes": True}


class TelegramBotSettingsOut(BaseModel):
    enabled: bool
    bot_token: str | None = None
    bot_username: str | None = None
    webhook_secret: str


class TelegramBotSettingsUpdate(BaseModel):
    enabled: bool
    bot_token: str | None = Field(default=None, max_length=255)
    bot_username: str | None = Field(default=None, max_length=120)


class TelegramBotHealthOut(BaseModel):
    enabled: bool
    token_configured: bool
    username_configured: bool
    webhook_secret_configured: bool
    bot_api_ok: bool
    bot_id: int | None = None
    bot_username: str | None = None
    webhook_ok: bool
    webhook_url: str | None = None
    webhook_expected_path: str | None = None
    webhook_path_matches: bool
    pending_update_count: int = 0
    last_error_message: str | None = None
    last_error_at: datetime | None = None
    issues: list[str] = Field(default_factory=list)
    status: Literal["healthy", "warning", "error"]


class DeliveryDriverTelegramLinkOut(BaseModel):
    driver_id: int
    driver_name: str
    linked: bool
    telegram_enabled: bool
    provider_name: str | None = None
    telegram_username: str | None = None
    telegram_chat_id: str | None = None
    telegram_linked_at: datetime | None = None
    link_code: str | None = None
    link_expires_at: datetime | None = None
    bot_username: str | None = None
    deep_link: str | None = None
    has_active_task: bool = False
    active_order_id: int | None = None
    active_order_status: str | None = None
    has_open_offer: bool = False
    offered_order_id: int | None = None
    offered_order_status: str | None = None
    recovery_hint: str | None = None
    action_message: str | None = None


class SystemContextOut(BaseModel):
    country_code: str
    country_name: str
    currency_code: str
    currency_name: str
    currency_symbol: str
    currency_decimal_places: int


class SystemContextUpdate(BaseModel):
    country_code: str = Field(min_length=2, max_length=3)
    country_name: str = Field(min_length=2, max_length=80)
    currency_code: str = Field(min_length=3, max_length=3)
    currency_name: str = Field(min_length=2, max_length=80)
    currency_symbol: str = Field(min_length=1, max_length=12)
    currency_decimal_places: int = Field(default=2, ge=0, le=4)


StorefrontIconKey = Literal["utensils", "chef_hat", "shopping_bag", "bike"]
StorefrontSocialPlatform = Literal["website", "whatsapp", "instagram", "facebook"]


class StorefrontSocialLink(BaseModel):
    platform: StorefrontSocialPlatform
    url: str | None = Field(default=None, max_length=500)
    enabled: bool = False

    @field_validator("url", mode="before")
    @classmethod
    def normalize_url(cls, value: object) -> object:
        if isinstance(value, str):
            return _normalize_optional_text(value)
        return value


class StorefrontSettingsOut(BaseModel):
    brand_name: str
    brand_mark: str
    brand_icon: StorefrontIconKey
    brand_tagline: str | None = None
    socials: list[StorefrontSocialLink] = Field(default_factory=list)


class StorefrontSettingsUpdate(BaseModel):
    brand_name: str = Field(min_length=2, max_length=120)
    brand_mark: str = Field(min_length=2, max_length=32)
    brand_icon: StorefrontIconKey
    brand_tagline: str | None = Field(default=None, max_length=180)
    socials: list[StorefrontSocialLink] = Field(default_factory=list)

    @field_validator("brand_name", "brand_mark", "brand_tagline", mode="before")
    @classmethod
    def normalize_storefront_text(cls, value: object) -> object:
        if isinstance(value, str):
            return _normalize_optional_text(value)
        return value

    @field_validator("socials")
    @classmethod
    def ensure_unique_social_platforms(cls, value: list[StorefrontSocialLink]) -> list[StorefrontSocialLink]:
        seen: set[str] = set()
        normalized: list[StorefrontSocialLink] = []
        for row in value:
            if row.platform in seen:
                raise ValueError("لا يمكن تكرار نفس منصة التواصل أكثر من مرة.")
            seen.add(row.platform)
            normalized.append(row)
        return normalized


class DeliverySettingsOut(BaseModel):
    delivery_fee: float
    pricing_mode: str = "fixed"
    structured_locations_enabled: bool = False
    active_zones_count: int = 0
    system_context: SystemContextOut


class DeliverySettingsUpdate(BaseModel):
    delivery_fee: float = Field(ge=0)


class DeliveryLocationNodeOut(BaseModel):
    key: str
    parent_key: str | None = None
    level: str
    external_id: str | None = None
    country_code: str | None = None
    name: str
    display_name: str
    can_expand: bool


class DeliveryLocationListOut(BaseModel):
    provider: str
    parent_key: str | None = None
    items: list[DeliveryLocationNodeOut] = Field(default_factory=list)


class DeliveryLocationProviderSettingsOut(BaseModel):
    provider: str
    enabled: bool
    geonames_username_configured: bool
    country_codes: list[str] = Field(default_factory=list)
    cache_ttl_hours: int


class DeliveryLocationProviderSettingsUpdate(BaseModel):
    provider: str = Field(default="geonames", min_length=2, max_length=32)
    enabled: bool = False
    geonames_username: str | None = Field(default=None, max_length=80)
    country_codes: list[str] = Field(default_factory=list)
    cache_ttl_hours: int = Field(default=720, ge=1, le=8760)


class DeliveryAddressNodeCreate(BaseModel):
    parent_id: int | None = Field(default=None, gt=0)
    level: str = Field(min_length=4, max_length=32)
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=2, max_length=160)
    display_name: str = Field(min_length=2, max_length=255)
    postal_code: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=255)
    active: bool = True
    visible_in_public: bool = True
    sort_order: int = Field(default=0, ge=0)


class DeliveryAddressNodeUpdate(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=2, max_length=160)
    display_name: str = Field(min_length=2, max_length=255)
    postal_code: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=255)
    active: bool
    visible_in_public: bool
    sort_order: int = Field(default=0, ge=0)


class DeliveryAddressNodeOut(BaseModel):
    id: int
    parent_id: int | None = None
    level: str
    country_code: str
    code: str
    name: str
    display_name: str
    postal_code: str | None = None
    notes: str | None = None
    active: bool
    visible_in_public: bool
    sort_order: int
    child_count: int = 0
    can_expand: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeliveryAddressNodeListOut(BaseModel):
    parent_id: int | None = None
    items: list[DeliveryAddressNodeOut] = Field(default_factory=list)
    total: int


class DeliveryZonePricingUpsert(BaseModel):
    node_id: int = Field(gt=0)
    delivery_fee: float = Field(ge=0)
    active: bool = True
    sort_order: int = Field(default=0, ge=0)


class DeliveryZonePricingOut(BaseModel):
    id: int
    node_id: int
    provider: str
    location_key: str
    parent_key: str | None = None
    parent_id: int | None = None
    level: str
    external_id: str | None = None
    country_code: str | None = None
    code: str | None = None
    name: str
    display_name: str
    delivery_fee: float
    active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeliveryZonePricingListOut(BaseModel):
    items: list[DeliveryZonePricingOut] = Field(default_factory=list)
    total: int


class DeliveryLocationPricingQuoteOut(BaseModel):
    selected_node_id: int | None = None
    location_key: str | None = None
    location_label: str | None = None
    location_level: str | None = None
    resolved_node_id: int | None = None
    resolved_node_label: str | None = None
    resolved_node_level: str | None = None
    available: bool
    pricing_source: str
    delivery_fee: float | None = None
    active_zones_count: int = 0
    message: str | None = None


class DeliveryPolicySettingsOut(BaseModel):
    min_order_amount: float
    auto_notify_team: bool


class DeliveryPolicySettingsUpdate(BaseModel):
    min_order_amount: float = Field(ge=0)
    auto_notify_team: bool


class OperationalSettingOut(BaseModel):
    key: str
    value: str
    description: str
    editable: bool


class OperationalSettingUpdate(BaseModel):
    key: str = Field(min_length=2, max_length=64)
    value: str = Field(min_length=1, max_length=255)

class OperationalCapabilitiesOut(BaseModel):
    activation_stage_id: str = "base"
    workflow_profile: str = "base_direct"
    kitchen_feature_enabled: bool = True
    delivery_feature_enabled: bool = True
    warehouse_feature_enabled: bool = True
    kitchen_runtime_enabled: bool = True
    delivery_runtime_enabled: bool = True
    warehouse_runtime_enabled: bool = True
    kitchen_enabled: bool
    delivery_enabled: bool
    warehouse_enabled: bool
    kitchen_active_users: int
    delivery_active_users: int
    warehouse_active_suppliers: int = 0
    warehouse_active_items: int = 0
    kitchen_block_reason: str | None = None
    delivery_block_reason: str | None = None
    warehouse_block_reason: str | None = None


class KitchenRuntimeSettingsOut(BaseModel):
    order_polling_ms: int = Field(ge=3000, le=60000)
    kitchen_metrics_window: Literal["day", "week", "month"] = "day"


class DeliveryHistoryOut(BaseModel):
    assignment_id: int
    order_id: int
    assignment_status: DeliveryAssignmentStatus
    order_status: OrderStatus
    assigned_at: datetime
    departed_at: datetime | None
    delivered_at: datetime | None
    order_subtotal: float
    delivery_fee: float
    order_total: float
    phone: str | None
    address: str | None


class ReportDailyRow(BaseModel):
    day: str
    food_sales: float = 0.0
    delivery_revenue: float = 0.0
    driver_cost: float = 0.0
    refunds: float = 0.0
    cash_in: float = 0.0
    cash_out: float = 0.0
    sales: float
    expenses: float
    net: float


class ReportMonthlyRow(BaseModel):
    month: str
    food_sales: float = 0.0
    delivery_revenue: float = 0.0
    driver_cost: float = 0.0
    refunds: float = 0.0
    cash_in: float = 0.0
    cash_out: float = 0.0
    sales: float
    expenses: float
    net: float


class ReportByTypeRow(BaseModel):
    order_type: OrderType
    orders_count: int
    food_sales: float = 0.0
    delivery_revenue: float = 0.0
    sales: float


class ReportPerformance(BaseModel):
    avg_prep_minutes: float


class ReportProfitabilityProductRow(BaseModel):
    product_id: int
    product_name: str
    category_name: str
    quantity_sold: int
    revenue: float
    estimated_unit_cost: float
    estimated_cost: float
    gross_profit: float
    margin_percent: float


class ReportProfitabilityCategoryRow(BaseModel):
    category_name: str
    quantity_sold: int
    revenue: float
    estimated_cost: float
    gross_profit: float
    margin_percent: float


class ReportProfitabilityOut(BaseModel):
    start_date: date | None
    end_date: date | None
    total_quantity_sold: int
    total_revenue: float
    total_estimated_cost: float
    total_gross_profit: float
    total_margin_percent: float
    by_products: list[ReportProfitabilityProductRow] = Field(default_factory=list)
    by_categories: list[ReportProfitabilityCategoryRow] = Field(default_factory=list)


class ReportPeriodMetrics(BaseModel):
    label: str
    start_date: date
    end_date: date
    days_count: int
    food_sales: float = 0.0
    delivery_revenue: float = 0.0
    driver_cost: float = 0.0
    refunds: float = 0.0
    cash_in: float = 0.0
    cash_out: float = 0.0
    sales: float
    expenses: float
    net: float
    delivered_orders_count: int
    avg_order_value: float


class ReportPeriodDeltaRow(BaseModel):
    metric: str
    current_value: float
    previous_value: float
    absolute_change: float
    change_percent: float | None


class ReportPeriodComparisonOut(BaseModel):
    current_period: ReportPeriodMetrics
    previous_period: ReportPeriodMetrics
    deltas: list[ReportPeriodDeltaRow] = Field(default_factory=list)


class ReportPeakHourRow(BaseModel):
    hour_label: str
    orders_count: int
    food_sales: float = 0.0
    delivery_revenue: float = 0.0
    sales: float
    avg_order_value: float
    avg_prep_minutes: float


class ReportPeakHoursPerformanceOut(BaseModel):
    start_date: date
    end_date: date
    days_count: int
    peak_hour: str | None
    peak_orders_count: int
    peak_sales: float
    overall_avg_prep_minutes: float
    by_hours: list[ReportPeakHourRow] = Field(default_factory=list)


class OrderTransitionLogOut(BaseModel):
    id: int
    order_id: int
    from_status: OrderStatus
    to_status: OrderStatus
    performed_by: int
    timestamp: datetime

    model_config = {"from_attributes": True}


class SystemAuditLogOut(BaseModel):
    id: int
    module: str
    action: str
    entity_type: str
    entity_id: int | None
    description: str
    performed_by: int
    timestamp: datetime

    model_config = {"from_attributes": True}


class SecurityAuditEventOut(BaseModel):
    id: int
    event_type: str
    success: bool
    severity: str
    username: str | None
    role: UserRole | None = None
    user_id: int | None
    ip_address: str | None
    user_agent: str | None
    detail: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    password: str | None = Field(default=None, min_length=8, max_length=120)


class AccountSessionOut(BaseModel):
    id: int
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    is_active: bool


class AccountSessionsRevokeOut(BaseModel):
    revoked_count: int


class SystemBackupOut(BaseModel):
    filename: str
    size_bytes: int
    created_at: datetime


class SystemBackupRestoreInput(BaseModel):
    filename: str = Field(min_length=4, max_length=255)
    confirm_phrase: str = Field(min_length=3, max_length=32)


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=8, max_length=120)
    role: UserRole
    active: bool = True
    delivery_phone: str | None = Field(default=None, min_length=5, max_length=40)
    delivery_vehicle: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_delivery_fields(self) -> "UserCreate":
        return self


class UserUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    role: UserRole
    active: bool
    password: str | None = Field(default=None, min_length=8, max_length=120)
    delivery_phone: str | None = Field(default=None, min_length=5, max_length=40)
    delivery_vehicle: str | None = Field(default=None, max_length=120)


class PermissionCatalogItemOut(BaseModel):
    code: str
    label: str
    description: str
    roles: list[UserRole] = Field(default_factory=list)
    default_enabled: bool


class UserPermissionsOut(BaseModel):
    user_id: int
    username: str
    role: UserRole
    default_permissions: list[str] = Field(default_factory=list)
    allow_overrides: list[str] = Field(default_factory=list)
    deny_overrides: list[str] = Field(default_factory=list)
    effective_permissions: list[str] = Field(default_factory=list)


class UserPermissionsUpdate(BaseModel):
    allow: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)


class WarehouseSupplierCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=255)
    payment_term_days: int = Field(ge=0, le=365, default=0)
    credit_limit: float | None = Field(default=None, ge=0)
    quality_rating: float = Field(ge=0, le=5, default=3)
    lead_time_days: int = Field(ge=0, le=365, default=0)
    notes: str | None = Field(default=None, max_length=255)
    active: bool = True
    supplied_item_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def ensure_unique_supplied_item_ids(self) -> "WarehouseSupplierCreate":
        normalized_ids = [int(item_id) for item_id in self.supplied_item_ids]
        if any(item_id <= 0 for item_id in normalized_ids):
            raise ValueError("معرف الصنف يجب أن يكون أكبر من صفر.")
        if len(normalized_ids) != len(set(normalized_ids)):
            raise ValueError("لا يمكن تكرار نفس الصنف في قائمة التوريد.")
        self.supplied_item_ids = normalized_ids
        return self


class WarehouseSupplierUpdate(WarehouseSupplierCreate):
    pass


class WarehouseSupplierOut(BaseModel):
    id: int
    name: str
    phone: str | None
    email: str | None
    address: str | None
    payment_term_days: int
    credit_limit: float | None
    quality_rating: float
    lead_time_days: int
    notes: str | None
    active: bool
    supplied_item_ids: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WarehouseItemCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    unit: str = Field(min_length=1, max_length=32)
    alert_threshold: float = Field(ge=0, default=0)
    active: bool = True


class WarehouseItemUpdate(WarehouseItemCreate):
    pass


class WarehouseItemOut(BaseModel):
    id: int
    name: str
    unit: str
    alert_threshold: float
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WarehouseStockBalanceOut(BaseModel):
    item_id: int
    item_name: str
    unit: str
    alert_threshold: float
    active: bool
    quantity: float
    is_low: bool


class WarehouseInboundItemInput(BaseModel):
    item_id: int
    quantity: float = Field(gt=0)
    unit_cost: float = Field(ge=0, default=0)


class WarehouseOutboundItemInput(BaseModel):
    item_id: int
    quantity: float = Field(gt=0)


class WarehouseInboundVoucherCreate(BaseModel):
    supplier_id: int
    reference_no: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=255)
    idempotency_key: str | None = Field(default=None, max_length=80)
    items: list[WarehouseInboundItemInput] = Field(min_length=1)


class WarehouseOutboundVoucherCreate(BaseModel):
    reason_code: str = Field(min_length=2, max_length=64)
    reason_note: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=255)
    idempotency_key: str | None = Field(default=None, max_length=80)
    items: list[WarehouseOutboundItemInput] = Field(min_length=1)


class WarehouseOutboundReasonOut(BaseModel):
    code: str
    label: str


class WarehouseInboundVoucherItemOut(BaseModel):
    item_id: int
    item_name: str
    quantity: float
    unit_cost: float
    line_total: float


class WarehouseOutboundVoucherItemOut(BaseModel):
    item_id: int
    item_name: str
    quantity: float
    unit_cost: float
    line_total: float


class WarehouseInboundVoucherOut(BaseModel):
    id: int
    voucher_no: str
    supplier_id: int
    supplier_name: str
    reference_no: str | None
    note: str | None
    posted_at: datetime
    received_by: int
    total_quantity: float
    total_cost: float
    items: list[WarehouseInboundVoucherItemOut]


class WarehouseOutboundVoucherOut(BaseModel):
    id: int
    voucher_no: str
    reason_code: str
    reason: str
    note: str | None
    posted_at: datetime
    issued_by: int
    total_quantity: float
    total_cost: float
    items: list[WarehouseOutboundVoucherItemOut]


class WarehouseLedgerOut(BaseModel):
    id: int
    item_id: int
    item_name: str
    movement_kind: str
    source_type: str
    source_id: int
    quantity: float
    unit_cost: float
    line_value: float
    running_avg_cost: float
    balance_before: float
    balance_after: float
    note: str | None
    created_by: int
    created_at: datetime


class WarehouseStockCountItemInput(BaseModel):
    item_id: int
    counted_quantity: float = Field(ge=0)


class WarehouseStockCountCreate(BaseModel):
    note: str | None = Field(default=None, max_length=255)
    idempotency_key: str | None = Field(default=None, max_length=80)
    items: list[WarehouseStockCountItemInput] = Field(min_length=1)


class WarehouseStockCountItemOut(BaseModel):
    item_id: int
    item_name: str
    unit: str
    system_quantity: float
    counted_quantity: float
    variance_quantity: float
    unit_cost: float
    variance_value: float


class WarehouseStockCountOut(BaseModel):
    id: int
    count_no: str
    note: str | None
    status: str
    counted_by: int
    counted_at: datetime
    settled_by: int | None
    settled_at: datetime | None
    total_variance_quantity: float
    total_variance_value: float
    items: list[WarehouseStockCountItemOut]


class WarehouseDashboardOut(BaseModel):
    active_items: int
    active_suppliers: int
    low_stock_items: int
    inbound_today: float
    outbound_today: float



