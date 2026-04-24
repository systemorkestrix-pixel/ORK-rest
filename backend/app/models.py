from datetime import UTC, date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .enums import (
    CashChannel,
    CashboxMovementDirection,
    CashboxMovementType,
    CollectionChannel,
    DeliveryAssignmentStatus,
    DeliveryDispatchScope,
    DeliveryDispatchStatus,
    DeliverySettlementStatus,
    DriverStatus,
    FinancialTransactionType,
    DriverShareModel,
    OrderStatus,
    ProductKind,
    ResourceScope,
    OrderType,
    PaymentStatus,
    ResourceMovementType,
    TableStatus,
    UserRole,
)
from .master_tenant_runtime_contract import (
    MASTER_TENANT_MEDIA_STORAGE_BACKEND_LOCAL_STATIC,
    MASTER_TENANT_RUNTIME_MIGRATION_STATE_NOT_STARTED,
    MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE,
    build_master_tenant_runtime_schema_name,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    username: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False, index=True, default=UserRole.MANAGER.value)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_failed_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    permission_overrides_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now)

    @property
    def permissions_effective(self) -> list[str]:
        from .permissions import effective_permissions

        return sorted(effective_permissions(self.role, self.permission_overrides_json))


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now)

    user: Mapped[User] = relationship()


class MasterClient(Base):
    __tablename__ = "master_clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_name: Mapped[str] = mapped_column(String(120), nullable=False)
    brand_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    active_plan_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True, default="base")
    subscription_state: Mapped[str] = mapped_column(String(20), nullable=False, index=True, default="active")
    next_billing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now)

    tenants: Mapped[list["MasterTenant"]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
        order_by="MasterTenant.created_at.desc(), MasterTenant.id.desc()",
    )


class MasterTenant(Base):
    __tablename__ = "master_tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("master_clients.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    brand_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    database_name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    manager_username: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    environment_state: Mapped[str] = mapped_column(String(24), nullable=False, index=True, default="pending_activation")
    plan_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True, default="base")
    paused_addons_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    runtime_storage_backend: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        default=MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE,
    )
    runtime_schema_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        default=lambda context: build_master_tenant_runtime_schema_name(
            str(context.get_current_parameters().get("database_name") or "")
        ),
    )
    runtime_migration_state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        default=MASTER_TENANT_RUNTIME_MIGRATION_STATE_NOT_STARTED,
    )
    runtime_migrated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    media_storage_backend: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        default=MASTER_TENANT_MEDIA_STORAGE_BACKEND_LOCAL_STATIC,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now)

    client: Mapped[MasterClient] = relationship(back_populates="tenants")


class RestaurantEmployee(Base):
    __tablename__ = "restaurant_employees"
    __table_args__ = (
        Index("ix_restaurant_employees_type_active", "employee_type", "active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    employee_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    compensation_cycle: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    compensation_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    work_schedule: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now)


class RestaurantTable(Base):
    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    qr_code: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=TableStatus.AVAILABLE.value)

    orders: Mapped[list["Order"]] = relationship(back_populates="table")


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)

    products: Mapped[list["Product"]] = relationship(back_populates="category_ref")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default=ProductKind.PRIMARY.value, index=True)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("product_categories.id"), nullable=False, index=True)
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    category_ref: Mapped[ProductCategory] = relationship(back_populates="products")
    secondary_links: Mapped[list["ProductSecondaryLink"]] = relationship(
        back_populates="primary_product",
        foreign_keys="ProductSecondaryLink.primary_product_id",
        cascade="all, delete-orphan",
        order_by="ProductSecondaryLink.sort_order.asc(), ProductSecondaryLink.id.asc()",
    )
    parent_secondary_links: Mapped[list["ProductSecondaryLink"]] = relationship(
        back_populates="secondary_product",
        foreign_keys="ProductSecondaryLink.secondary_product_id",
    )
    consumption_components: Mapped[list["ProductConsumptionComponent"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductConsumptionComponent.id.asc()",
    )

    @property
    def legacy_kind(self) -> str:
        if self.kind == ProductKind.PRIMARY.value:
            return "sellable"
        if self.kind == ProductKind.SECONDARY.value:
            return "internal"
        return str(self.kind)


class ProductSecondaryLink(Base):
    __tablename__ = "product_secondary_links"
    __table_args__ = (
        UniqueConstraint("primary_product_id", "secondary_product_id", name="uq_product_secondary_link"),
        CheckConstraint("primary_product_id <> secondary_product_id", name="ck_product_secondary_link_not_self"),
        CheckConstraint("max_quantity >= 1", name="ck_product_secondary_link_max_quantity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    primary_product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    secondary_product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    max_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)

    primary_product: Mapped["Product"] = relationship(
        back_populates="secondary_links",
        foreign_keys=[primary_product_id],
    )
    secondary_product: Mapped["Product"] = relationship(
        back_populates="parent_secondary_links",
        foreign_keys=[secondary_product_id],
    )

    @property
    def secondary_product_name(self) -> str | None:
        if self.secondary_product is None:
            return None
        return self.secondary_product.name


class ProductConsumptionComponent(Base):
    __tablename__ = "product_consumption_components"
    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_item_id", name="uq_product_consumption_component"),
        CheckConstraint("quantity_per_unit > 0", name="ck_product_consumption_quantity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    warehouse_item_id: Mapped[int] = mapped_column(ForeignKey("wh_items.id"), nullable=False, index=True)
    quantity_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)

    product: Mapped["Product"] = relationship(back_populates="consumption_components")
    warehouse_item: Mapped["WarehouseItem"] = relationship(back_populates="product_components")

    @property
    def warehouse_item_name(self) -> str | None:
        if self.warehouse_item is None:
            return None
        return self.warehouse_item.name

    @property
    def warehouse_item_unit(self) -> str | None:
        if self.warehouse_item is None:
            return None
        return self.warehouse_item.unit


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    unit: Mapped[str] = mapped_column(String(32), nullable=False, default="unit")
    alert_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    scope: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ResourceScope.KITCHEN.value, index=True
    )

    movements: Mapped[list["ResourceMovement"]] = relationship(
        back_populates="resource", cascade="all, delete-orphan"
    )


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_status_created_at", "status", "created_at"),
        Index("ix_orders_table_status_created_at", "table_id", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=OrderStatus.CREATED.value, index=True)
    table_id: Mapped[int | None] = mapped_column(ForeignKey("tables.id"), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_location_key: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    delivery_location_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_location_level: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    delivery_location_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    delivery_fee: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    payment_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=PaymentStatus.UNPAID.value, index=True
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    paid_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    amount_received: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    payment_method: Mapped[str] = mapped_column(String(16), nullable=False, default="cash")
    collected_by_channel: Mapped[str] = mapped_column(
        String(24), nullable=False, default=CollectionChannel.CASHIER.value, index=True
    )
    collection_variance_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    collection_variance_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    accounting_recognized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    delivery_team_notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    delivery_team_notified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    delivery_failure_resolution_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    delivery_failure_resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_failure_resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    delivery_failure_resolved_by: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    table: Mapped[RestaurantTable | None] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    delivery_settlement: Mapped["DeliverySettlement | None"] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    cashbox_movements: Mapped[list["CashboxMovement"]] = relationship(back_populates="order")

    @property
    def tracking_code(self) -> str:
        from .tracking import encode_public_order_tracking_code

        return encode_public_order_tracking_code(self.id)


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    product_name: Mapped[str] = mapped_column(String(120), nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")


class OrderCostEntry(Base):
    __tablename__ = "order_cost_entries"
    __table_args__ = (
        UniqueConstraint("order_id", "order_item_id", name="uq_order_cost_entry_order_item"),
        Index("ix_order_cost_entries_order_created_at", "order_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    quantity_sold: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    cogs_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)


class ResourceMovement(Base):
    __tablename__ = "resource_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False, default=ResourceMovementType.ADJUST.value)
    # Keep legacy compatibility with old schema that requires signed delta.
    delta: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)

    resource: Mapped[Resource] = relationship(back_populates="movements")


class OrderTransitionLog(Base):
    __tablename__ = "order_transitions_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    from_status: Mapped[str] = mapped_column(String(40), nullable=False)
    to_status: Mapped[str] = mapped_column(String(40), nullable=False)
    performed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)


class SystemAuditLog(Base):
    __tablename__ = "system_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    module: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    performed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)


class SecurityAuditEvent(Base):
    __tablename__ = "security_audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info", index=True)
    username: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    role: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)


class FinancialTransaction(Base):
    __tablename__ = "financial_transactions"
    __table_args__ = (
        Index("ix_financial_transactions_type_created_at", "type", "created_at"),
        Index("ix_financial_transactions_reference_group", "reference_group"),
        Index("ix_financial_transactions_order_type_created_at", "order_id", "type", "created_at"),
        Index("ix_financial_transactions_settlement_type", "delivery_settlement_id", "type"),
        Index(
            "ux_financial_transactions_sale_order",
            "order_id",
            unique=True,
            sqlite_where=text("type = 'sale' AND order_id IS NOT NULL"),
        ),
        Index(
            "ux_financial_transactions_refund_order",
            "order_id",
            unique=True,
            sqlite_where=text("type = 'refund' AND order_id IS NOT NULL"),
        ),
        Index(
            "ux_financial_transactions_expense_expense",
            "expense_id",
            unique=True,
            sqlite_where=text("type = 'expense' AND expense_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    delivery_settlement_id: Mapped[int | None] = mapped_column(
        ForeignKey("delivery_settlements.id"), nullable=True, index=True
    )
    expense_id: Mapped[int | None] = mapped_column(ForeignKey("expenses.id"), nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default=FinancialTransactionType.SALE.value)
    direction: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    account_code: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    reference_group: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    delivery_settlement: Mapped["DeliverySettlement | None"] = relationship(back_populates="financial_transactions")


class ShiftClosure(Base):
    __tablename__ = "shift_closures"
    __table_args__ = (UniqueConstraint("business_date", name="uq_shift_closure_business_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    business_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    opening_cash: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sales_total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    refunds_total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expenses_total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expected_cash: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_cash: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    variance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    transactions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    closed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)


class ExpenseCostCenter(Base):
    __tablename__ = "expense_cost_centers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now)

    expenses: Mapped[list["Expense"]] = relationship(back_populates="cost_center")


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False, default="general")
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cost_center_id: Mapped[int] = mapped_column(ForeignKey("expense_cost_centers.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    review_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now)
    attachments: Mapped[list["ExpenseAttachment"]] = relationship(
        back_populates="expense",
        cascade="all, delete-orphan",
    )
    cost_center: Mapped["ExpenseCostCenter"] = relationship(back_populates="expenses")

    @property
    def cost_center_name(self) -> str | None:
        if self.cost_center is None:
            return None
        return self.cost_center.name


class ExpenseAttachment(Base):
    __tablename__ = "expense_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(180), nullable=False)
    file_url: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(80), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)

    expense: Mapped["Expense"] = relationship(back_populates="attachments")


class DeliveryProvider(Base):
    __tablename__ = "delivery_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False, default="internal_team", index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    is_internal_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)

    drivers: Mapped[list["DeliveryDriver"]] = relationship(back_populates="provider")
    account_user: Mapped["User | None"] = relationship(foreign_keys=[account_user_id])

    @property
    def account_user_name(self) -> str | None:
        return self.account_user.name if self.account_user is not None else None

    @property
    def account_username(self) -> str | None:
        return self.account_user.username if self.account_user is not None else None


class DeliveryDriver(Base):
    __tablename__ = "delivery_drivers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, unique=True, index=True)
    provider_id: Mapped[int | None] = mapped_column(ForeignKey("delivery_providers.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=DriverStatus.AVAILABLE.value, index=True)
    vehicle: Mapped[str | None] = mapped_column(String(120), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(40), nullable=True, unique=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(120), nullable=True)
    telegram_link_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    telegram_link_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    telegram_linked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    telegram_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    provider: Mapped["DeliveryProvider | None"] = relationship(back_populates="drivers")

    @property
    def provider_name(self) -> str | None:
        return self.provider.name if self.provider is not None else None

    @property
    def provider_type(self) -> str | None:
        return self.provider.provider_type if self.provider is not None else None


class DeliveryAssignment(Base):
    __tablename__ = "delivery_assignments"
    __table_args__ = (
        Index("ix_delivery_assignments_driver_status_id", "driver_id", "status", "id"),
        Index("ix_delivery_assignments_order_status_id", "order_id", "status", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("delivery_drivers.id"), nullable=False, index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    departed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=DeliveryAssignmentStatus.ASSIGNED.value, index=True
    )
    delivery_settlement: Mapped["DeliverySettlement | None"] = relationship(back_populates="assignment")


class DeliveryDispatch(Base):
    __tablename__ = "delivery_dispatches"
    __table_args__ = (
        Index("ix_delivery_dispatches_order_status_id", "order_id", "status", "id"),
        Index("ix_delivery_dispatches_driver_status_id", "driver_id", "status", "id"),
        Index("ix_delivery_dispatches_provider_status_id", "provider_id", "status", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    provider_id: Mapped[int | None] = mapped_column(ForeignKey("delivery_providers.id"), nullable=True, index=True)
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("delivery_drivers.id"), nullable=True, index=True)
    dispatch_scope: Mapped[str] = mapped_column(
        String(16), nullable=False, default=DeliveryDispatchScope.PROVIDER.value, index=True
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=DeliveryDispatchStatus.OFFERED.value, index=True
    )
    channel: Mapped[str] = mapped_column(String(16), nullable=False, default="console", index=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    provider: Mapped["DeliveryProvider | None"] = relationship()
    driver: Mapped["DeliveryDriver | None"] = relationship()

    @property
    def provider_name(self) -> str | None:
        return self.provider.name if self.provider is not None else None

    @property
    def driver_name(self) -> str | None:
        return self.driver.name if self.driver is not None else None


class DeliverySettlement(Base):
    __tablename__ = "delivery_settlements"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_delivery_settlements_order_id"),
        Index("ix_delivery_settlements_driver_status", "driver_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("delivery_assignments.id"), nullable=False, index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("delivery_drivers.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default=DeliverySettlementStatus.PENDING.value, index=True
    )
    driver_share_model: Mapped[str] = mapped_column(
        String(24), nullable=False, default=DriverShareModel.FULL_DELIVERY_FEE.value
    )
    driver_share_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expected_customer_total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_collected_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    food_revenue_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    delivery_revenue_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    driver_due_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    store_due_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    remitted_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    remaining_store_due_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    variance_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    variance_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recognized_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    settled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    order: Mapped[Order] = relationship(back_populates="delivery_settlement")
    assignment: Mapped[DeliveryAssignment] = relationship(back_populates="delivery_settlement")
    financial_transactions: Mapped[list[FinancialTransaction]] = relationship(back_populates="delivery_settlement")


class CashboxMovement(Base):
    __tablename__ = "cashbox_movements"
    __table_args__ = (
        Index("ix_cashbox_movements_type_created_at", "type", "created_at"),
        Index("ix_cashbox_movements_direction_created_at", "direction", "created_at"),
        Index("ix_cashbox_movements_settlement_created_at", "delivery_settlement_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    delivery_settlement_id: Mapped[int | None] = mapped_column(
        ForeignKey("delivery_settlements.id"), nullable=True, index=True
    )
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(
        String(32), nullable=False, default=CashboxMovementType.DRIVER_REMITTANCE.value, index=True
    )
    direction: Mapped[str] = mapped_column(
        String(8), nullable=False, default=CashboxMovementDirection.IN.value, index=True
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    cash_channel: Mapped[str] = mapped_column(
        String(24), nullable=False, default=CashChannel.CASH_DRAWER.value, index=True
    )
    performed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    order: Mapped[Order | None] = relationship(back_populates="cashbox_movements")
    delivery_settlement: Mapped[DeliverySettlement | None] = relationship()


class DeliveryLocationCache(Base):
    __tablename__ = "delivery_location_cache"
    __table_args__ = (
        Index("ix_delivery_location_cache_provider_parent_level", "provider", "parent_key", "level"),
        Index("ix_delivery_location_cache_provider_expires_at", "provider", "expires_at"),
        Index("ix_delivery_location_cache_country_level", "country_code", "level"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    node_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    parent_key: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    level: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    country_code: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    refreshed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)


class DeliveryZonePricing(Base):
    __tablename__ = "delivery_zone_pricing"
    __table_args__ = (
        UniqueConstraint("location_key", name="uq_delivery_zone_pricing_location_key"),
        Index("ix_delivery_zone_pricing_provider_active", "provider", "active"),
        Index("ix_delivery_zone_pricing_country_level", "country_code", "level"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    location_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    parent_key: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    level: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    country_code: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    delivery_fee: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)


class DeliveryAddressNode(Base):
    __tablename__ = "delivery_address_nodes"
    __table_args__ = (
        UniqueConstraint("parent_id", "code", name="uq_delivery_address_node_parent_code"),
        Index("ix_delivery_address_nodes_parent_sort", "parent_id", "sort_order"),
        Index("ix_delivery_address_nodes_country_level", "country_code", "level"),
        Index("ix_delivery_address_nodes_active_public", "active", "visible_in_public"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("delivery_address_nodes.id"), nullable=True, index=True)
    level: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    country_code: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    visible_in_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    parent: Mapped["DeliveryAddressNode | None"] = relationship(
        "DeliveryAddressNode",
        remote_side=[id],
        back_populates="children",
    )
    children: Mapped[list["DeliveryAddressNode"]] = relationship(
        "DeliveryAddressNode",
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="DeliveryAddressNode.sort_order.asc(), DeliveryAddressNode.id.asc()",
    )


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)


class WarehouseSupplier(Base):
    __tablename__ = "wh_suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_term_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    credit_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_rating: Mapped[float] = mapped_column(Float, nullable=False, default=3)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now)
    supplied_items: Mapped[list["WarehouseSupplierItem"]] = relationship(
        back_populates="supplier",
        cascade="all, delete-orphan",
    )


class WarehouseItem(Base):
    __tablename__ = "wh_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    unit: Mapped[str] = mapped_column(String(32), nullable=False, default="unit")
    alert_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now)
    supplier_links: Mapped[list["WarehouseSupplierItem"]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
    )
    product_components: Mapped[list["ProductConsumptionComponent"]] = relationship(
        back_populates="warehouse_item",
    )


class WarehouseSupplierItem(Base):
    __tablename__ = "wh_supplier_items"
    __table_args__ = (
        UniqueConstraint("supplier_id", "item_id", name="uq_wh_supplier_item"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("wh_suppliers.id"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("wh_items.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)

    supplier: Mapped[WarehouseSupplier] = relationship(back_populates="supplied_items")
    item: Mapped[WarehouseItem] = relationship(back_populates="supplier_links")


class WarehouseStockBalance(Base):
    __tablename__ = "wh_stock_balances"
    __table_args__ = (UniqueConstraint("item_id", name="uq_wh_stock_balance_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("wh_items.id"), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    avg_unit_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)


class WarehouseInboundVoucher(Base):
    __tablename__ = "wh_inbound_vouchers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    voucher_no: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("wh_suppliers.id"), nullable=False, index=True)
    reference_no: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True, index=True)
    received_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)

    items: Mapped[list["WarehouseInboundItem"]] = relationship(
        back_populates="voucher", cascade="all, delete-orphan"
    )


class WarehouseInboundItem(Base):
    __tablename__ = "wh_inbound_items"
    __table_args__ = (UniqueConstraint("voucher_id", "item_id", name="uq_wh_inbound_voucher_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    voucher_id: Mapped[int] = mapped_column(ForeignKey("wh_inbound_vouchers.id"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("wh_items.id"), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    voucher: Mapped[WarehouseInboundVoucher] = relationship(back_populates="items")


class WarehouseOutboundVoucher(Base):
    __tablename__ = "wh_outbound_vouchers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    voucher_no: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False, default="operational_use", index=True)
    reason: Mapped[str] = mapped_column(String(160), nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True, index=True)
    issued_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)

    items: Mapped[list["WarehouseOutboundItem"]] = relationship(
        back_populates="voucher", cascade="all, delete-orphan"
    )


class WarehouseOutboundItem(Base):
    __tablename__ = "wh_outbound_items"
    __table_args__ = (UniqueConstraint("voucher_id", "item_id", name="uq_wh_outbound_voucher_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    voucher_id: Mapped[int] = mapped_column(ForeignKey("wh_outbound_vouchers.id"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("wh_items.id"), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)

    voucher: Mapped[WarehouseOutboundVoucher] = relationship(back_populates="items")


class WarehouseStockLedger(Base):
    __tablename__ = "wh_stock_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("wh_items.id"), nullable=False, index=True)
    movement_kind: Mapped[str] = mapped_column(String(24), nullable=False, index=True)  # inbound | outbound
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    line_value: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    running_avg_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    balance_before: Mapped[float] = mapped_column(Float, nullable=False)
    balance_after: Mapped[float] = mapped_column(Float, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)


class WarehouseStockCount(Base):
    __tablename__ = "wh_stock_counts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    count_no: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    counted_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    counted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    settled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    items: Mapped[list["WarehouseStockCountLine"]] = relationship(
        back_populates="count", cascade="all, delete-orphan"
    )


class WarehouseStockCountLine(Base):
    __tablename__ = "wh_stock_count_lines"
    __table_args__ = (UniqueConstraint("count_id", "item_id", name="uq_wh_stock_count_line_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    count_id: Mapped[int] = mapped_column(ForeignKey("wh_stock_counts.id"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("wh_items.id"), nullable=False, index=True)
    system_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    counted_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    variance_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    variance_value: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    count: Mapped[WarehouseStockCount] = relationship(back_populates="items")


class WarehouseIntegrationEvent(Base):
    __tablename__ = "wh_integration_events"
    __table_args__ = (
        Index("ix_wh_integration_events_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now, index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(255), nullable=True)

