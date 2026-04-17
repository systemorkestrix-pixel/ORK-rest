from datetime import date, datetime

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import String, asc, cast, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..dependencies import get_db, require_roles, require_route_capability
from ..enums import FinancialTransactionType, OrderStatus, OrderType, ProductKind, UserRole
from ..models import (
    CashboxMovement,
    DeliverySettlement,
    DeliveryDriver,
    Expense,
    ExpenseCostCenter,
    FinancialTransaction,
    Order,
    OrderTransitionLog,
    Product,
    ProductCategory,
    RestaurantEmployee,
    ShiftClosure,
    SecurityAuditEvent,
    SystemAuditLog,
    User,
)
from ..schemas import (
    AccountProfileUpdate,
    AccountSessionOut,
    AccountSessionsRevokeOut,
    DashboardOut,
    CreateOrderInput,
    ManagerCreateOrderInput,
    DeliveryDriverCreate,
    DeliveryDriverOut,
    DeliveryDriverTelegramLinkOut,
    DeliveryDriverUpdate,
    DeliveryDispatchCreate,
    DeliveryDispatchOut,
    DeliveryProviderCreate,
    DeliveryProviderOut,
    DeliveryProviderUpdate,
    DeliveryFailureResolutionInput,
    DeliveryAccountingBackfillInput,
    DeliveryAccountingBackfillOut,
    DeliveryAccountingMigrationStatusOut,
    DeliveryAddressNodeCreate,
    DeliveryAddressNodeListOut,
    DeliveryAddressNodeOut,
    DeliveryAddressNodeUpdate,
    DeliveryLocationListOut,
    DeliveryLocationPricingQuoteOut,
    DeliveryLocationProviderSettingsOut,
    DeliveryLocationProviderSettingsUpdate,
    DeliveryPolicySettingsOut,
    DeliveryPolicySettingsUpdate,
    DeliverySettlementOut,
    DeliverySettingsOut,
    DeliverySettingsUpdate,
    DeliveryZonePricingListOut,
    DeliveryZonePricingOut,
    DeliveryZonePricingUpsert,
    DeliveryTeamNotifyInput,
    EmergencyDeliveryFailInput,
    OrderCancelInput,
    OperationalSettingOut,
    OperationalSettingUpdate,
    OperationalCapabilitiesOut,
    ExpenseAttachmentCreate,
    ExpenseAttachmentOut,
    ExpenseCostCenterCreate,
    ExpenseCostCenterOut,
    ExpenseCostCenterUpdate,
    ExpenseCreate,
    ExpenseOut,
    ExpenseReviewInput,
    ExpenseUpdate,
    CashboxMovementCreate,
    CashboxMovementOut,
    FinancialTransactionOut,
    KitchenOrdersPageOut,
    OrderOut,
    OperationalHeartOut,
    OrderPaymentCollectionInput,
    OrderRefundInput,
    OrdersPageOut,
    OrderTransitionInput,
    OrderTransitionLogOut,
    ProductCategoryCreate,
    ProductCategoryOut,
    ProductCategoryUpdate,
    ProductCreate,
    PermissionCatalogItemOut,
    ProductOut,
    ProductImageInput,
    ProductsPageOut,
    ProductUpdate,
    ReportByTypeRow,
    ReportDailyRow,
    ReportMonthlyRow,
    ReportPeakHoursPerformanceOut,
    ReportPeriodComparisonOut,
    ReportPerformance,
    ReportProfitabilityOut,
    ShiftClosureCreate,
    ShiftClosureOut,
    StorefrontSettingsOut,
    StorefrontSettingsUpdate,
    TelegramBotSettingsOut,
    TelegramBotSettingsUpdate,
    TelegramBotHealthOut,
    SecurityAuditEventOut,
    SystemBackupOut,
    SystemBackupRestoreInput,
    SystemContextOut,
    SystemContextUpdate,
    SystemAuditLogOut,
    ManagerTableOut,
    ManagerTenantContextOut,
    ManagerKitchenAccessOut,
    MasterAddonOut,
    TableCreateInput,
    TableUpdateInput,
    TableSessionOut,
    TableSessionSettlementInput,
    TableSessionSettlementOut,
    RestaurantEmployeeCreate,
    RestaurantEmployeeOut,
    RestaurantEmployeeUpdate,
    UserCreate,
    UserPermissionsOut,
    UserPermissionsUpdate,
    UserOut,
    UserUpdate,
)
from ..usecase_factory import (
    build_core_repository,
    build_delivery_repository,
    build_financial_repository,
    build_intelligence_repository,
    build_operations_repository,
    build_orders_repository,
    run_use_case,
)
from application.core_engine.use_cases import create_system_backup as create_system_backup_usecase
from application.core_engine.use_cases import create_user as create_user_usecase
from application.core_engine.use_cases import delete_user as delete_user_usecase
from application.core_engine.use_cases import get_user_permissions as get_user_permissions_usecase
from application.core_engine.use_cases import get_system_context_settings as get_system_context_settings_usecase
from application.core_engine.use_cases import get_storefront_settings as get_storefront_settings_usecase
from application.core_engine.use_cases import get_telegram_bot_settings as get_telegram_bot_settings_usecase
from application.core_engine.use_cases import get_telegram_bot_health as get_telegram_bot_health_usecase
from application.core_engine.use_cases import list_account_sessions as list_account_sessions_usecase
from application.core_engine.use_cases import list_operational_settings as list_operational_settings_usecase
from application.core_engine.use_cases import list_permissions_catalog as list_permissions_catalog_usecase
from application.core_engine.use_cases import list_system_backups as list_system_backups_usecase
from application.core_engine.use_cases import list_users as list_users_usecase
from application.core_engine.use_cases import restore_system_backup as restore_system_backup_usecase
from application.core_engine.use_cases import revoke_all_account_sessions as revoke_all_account_sessions_usecase
from application.core_engine.use_cases import update_account_profile as update_account_profile_usecase
from application.core_engine.use_cases import update_operational_setting as update_operational_setting_usecase
from application.core_engine.use_cases import update_storefront_settings as update_storefront_settings_usecase
from application.core_engine.use_cases import update_system_context_settings as update_system_context_settings_usecase
from application.core_engine.use_cases import update_telegram_bot_settings as update_telegram_bot_settings_usecase
from application.core_engine.use_cases import update_user as update_user_usecase
from application.master_engine.domain.registry import (
    get_manager_kitchen_access,
    list_manager_addons,
    get_manager_tenant_context,
    regenerate_manager_kitchen_access_password,
)
from application.core_engine.use_cases import update_user_permissions as update_user_permissions_usecase
from application.delivery_engine.use_cases import emergency_fail_delivery_order as emergency_fail_delivery_order_usecase
from application.delivery_engine.use_cases import cancel_delivery_dispatch as cancel_delivery_dispatch_usecase
from application.delivery_engine.use_cases import create_delivery_driver as create_delivery_driver_usecase
from application.delivery_engine.use_cases import create_delivery_dispatch as create_delivery_dispatch_usecase
from application.delivery_engine.use_cases import create_delivery_provider as create_delivery_provider_usecase
from application.delivery_engine.use_cases import delete_delivery_driver as delete_delivery_driver_usecase
from application.delivery_engine.use_cases import delete_delivery_provider as delete_delivery_provider_usecase
from application.delivery_engine.use_cases import list_delivery_drivers as list_delivery_drivers_usecase
from application.delivery_engine.use_cases import list_delivery_dispatches as list_delivery_dispatches_usecase
from application.delivery_engine.use_cases import list_delivery_providers as list_delivery_providers_usecase
from application.delivery_engine.use_cases import notify_delivery_team as notify_delivery_team_usecase
from application.delivery_engine.use_cases import resolve_delivery_failure as resolve_delivery_failure_usecase
from application.delivery_engine.use_cases import settle_delivery_order as settle_delivery_order_usecase
from application.delivery_engine.use_cases import update_delivery_driver as update_delivery_driver_usecase
from application.delivery_engine.use_cases import update_delivery_provider as update_delivery_provider_usecase
from application.financial_engine.use_cases import approve_expense as approve_expense_usecase
from application.financial_engine.use_cases import collect_order_payment as collect_order_payment_usecase
from application.financial_engine.use_cases import close_shift as close_shift_usecase
from application.financial_engine.use_cases import create_expense as create_expense_usecase
from application.financial_engine.use_cases import create_expense_attachment as create_expense_attachment_usecase
from application.financial_engine.use_cases import create_expense_cost_center as create_expense_cost_center_usecase
from application.financial_engine.use_cases import delete_expense as delete_expense_usecase
from application.financial_engine.use_cases import delete_expense_attachment as delete_expense_attachment_usecase
from application.financial_engine.use_cases import get_delivery_accounting_migration_status as get_delivery_accounting_migration_status_usecase
from application.financial_engine.use_cases import list_cashbox_movements as list_cashbox_movements_usecase
from application.financial_engine.use_cases import list_delivery_settlements as list_delivery_settlements_usecase
from application.financial_engine.use_cases import list_expense_cost_centers as list_expense_cost_centers_usecase
from application.financial_engine.use_cases import list_expenses as list_expenses_usecase
from application.financial_engine.use_cases import list_financial_transactions as list_financial_transactions_usecase
from application.financial_engine.use_cases import list_shift_closures as list_shift_closures_usecase
from application.financial_engine.use_cases import record_cashbox_movement as record_cashbox_movement_usecase
from application.financial_engine.use_cases import refund_order as refund_order_usecase
from application.financial_engine.use_cases import reject_expense as reject_expense_usecase
from application.financial_engine.use_cases import run_delivery_accounting_backfill as run_delivery_accounting_backfill_usecase
from application.financial_engine.use_cases import update_expense_cost_center as update_expense_cost_center_usecase
from application.financial_engine.use_cases import update_expense as update_expense_usecase
from application.intelligence_engine.use_cases import get_dashboard as get_dashboard_usecase
from application.intelligence_engine.use_cases import get_operational_heart as get_operational_heart_usecase
from application.intelligence_engine.use_cases import list_order_audit as list_order_audit_usecase
from application.intelligence_engine.use_cases import list_security_audit as list_security_audit_usecase
from application.intelligence_engine.use_cases import list_system_audit as list_system_audit_usecase
from application.intelligence_engine.use_cases import report_by_order_type as report_by_order_type_usecase
from application.intelligence_engine.use_cases import report_daily as report_daily_usecase
from application.intelligence_engine.use_cases import report_monthly as report_monthly_usecase
from application.intelligence_engine.use_cases import report_peak_hours_performance as report_peak_hours_performance_usecase
from application.intelligence_engine.use_cases import report_performance as report_performance_usecase
from application.intelligence_engine.use_cases import report_period_comparison as report_period_comparison_usecase
from application.intelligence_engine.use_cases import report_profitability as report_profitability_usecase
from application.operations_engine.use_cases import create_table as create_table_usecase
from application.operations_engine.use_cases import create_order as create_order_usecase
from application.operations_engine.use_cases import create_delivery_address_node as create_delivery_address_node_usecase
from application.operations_engine.use_cases import cancel_order as cancel_order_usecase
from application.operations_engine.use_cases import create_category as create_category_usecase
from application.operations_engine.use_cases import create_product as create_product_usecase
from application.operations_engine.use_cases import delete_table as delete_table_usecase
from application.operations_engine.use_cases import delete_category as delete_category_usecase
from application.operations_engine.use_cases import delete_product_permanently as delete_product_permanently_usecase
from application.operations_engine.use_cases import delete_delivery_address_node as delete_delivery_address_node_usecase
from application.operations_engine.use_cases import delete_delivery_zone_pricing as delete_delivery_zone_pricing_usecase
from application.operations_engine.use_cases import get_delivery_location_provider_settings as get_delivery_location_provider_settings_usecase
from application.operations_engine.use_cases import get_delivery_policies as get_delivery_policies_usecase
from application.operations_engine.use_cases import get_delivery_settings as get_delivery_settings_usecase
from application.operations_engine.use_cases import get_operational_capabilities as get_operational_capabilities_usecase
from application.operations_engine.use_cases import get_table_session as get_table_session_usecase
from application.operations_engine.use_cases import list_active_orders as list_active_orders_usecase
from application.operations_engine.use_cases import list_categories as list_categories_usecase
from application.operations_engine.use_cases import list_delivery_address_nodes as list_delivery_address_nodes_usecase
from application.operations_engine.use_cases import list_delivery_zone_pricing as list_delivery_zone_pricing_usecase
from application.operations_engine.use_cases import list_public_delivery_location_children as list_public_delivery_location_children_usecase
from application.operations_engine.use_cases import list_public_delivery_location_countries as list_public_delivery_location_countries_usecase
from application.operations_engine.use_cases import list_orders as list_orders_usecase
from application.operations_engine.use_cases import list_orders_paged as list_orders_paged_usecase
from application.operations_engine.use_cases import list_products as list_products_usecase
from application.operations_engine.use_cases import list_products_paged as list_products_paged_usecase
from application.operations_engine.use_cases import list_table_sessions as list_table_sessions_usecase
from application.operations_engine.use_cases import list_tables as list_tables_usecase
from application.operations_engine.use_cases import settle_table_session as settle_table_session_usecase
from application.operations_engine.use_cases import transition_order as transition_order_usecase
from application.operations_engine.use_cases import update_table as update_table_usecase
from application.operations_engine.use_cases import update_category as update_category_usecase
from application.operations_engine.use_cases import update_delivery_address_node as update_delivery_address_node_usecase
from application.operations_engine.use_cases import update_delivery_location_provider_settings as update_delivery_location_provider_settings_usecase
from application.operations_engine.use_cases import update_delivery_policies as update_delivery_policies_usecase
from application.operations_engine.use_cases import update_delivery_settings as update_delivery_settings_usecase
from application.operations_engine.use_cases import update_product as update_product_usecase
from application.operations_engine.use_cases import upsert_delivery_zone_pricing as upsert_delivery_zone_pricing_usecase
from application.operations_engine.use_cases import quote_delivery_location_pricing as quote_delivery_location_pricing_usecase
from application.operations_engine.use_cases import upload_product_image as upload_product_image_usecase
from application.operations_engine.use_cases import archive_product as archive_product_usecase
from application.kitchen_engine.use_cases import list_kitchen_orders as list_kitchen_orders_usecase
from application.kitchen_engine.use_cases import list_kitchen_orders_paged as list_kitchen_orders_paged_usecase

router = APIRouter(prefix="/manager", tags=["manager"], dependencies=[Depends(require_route_capability)])
DEFAULT_LIST_PAGE_SIZE = 50
MAX_LIST_PAGE_SIZE = 200
MAX_AUDIT_PAGE_SIZE = 500
def _extract_order_id_search(value: str) -> int | None:
    digits_only = "".join(char for char in value if char.isdigit())
    if not digits_only:
        return None
    return int(digits_only.lstrip("0") or "0")


def _manager_table_row_or_404(db: Session, table_id: int) -> dict[str, object]:
    output = run_use_case(
        execute=list_tables_usecase.execute,
        data=list_tables_usecase.Input(table_ids=[table_id], page=1, page_size=1),
        repo=build_operations_repository(db),
        db=db,
    )
    for row in output.result:
        if int(row["id"]) == table_id:
            return row
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الطاولة غير موجودة")


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DashboardOut:
    output = run_use_case(
        execute=get_dashboard_usecase.execute,
        data=get_dashboard_usecase.Input(),
        repo=build_intelligence_repository(db),
        db=db,
    )
    return output.result


@router.get("/dashboard/operational-heart", response_model=OperationalHeartOut)
def dashboard_operational_heart(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=get_operational_heart_usecase.execute,
        data=get_operational_heart_usecase.Input(),
        repo=build_intelligence_repository(db),
        db=db,
    )
    return output.result


@router.get("/operational-capabilities", response_model=OperationalCapabilitiesOut)
def manager_operational_capabilities(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=get_operational_capabilities_usecase.execute,
        data=get_operational_capabilities_usecase.Input(),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.get("/tenant-context", response_model=ManagerTenantContextOut)
def manager_tenant_context(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return get_manager_tenant_context(db)


@router.get("/addons", response_model=list[MasterAddonOut])
def manager_addons(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return list_manager_addons(db)


@router.get("/plans", response_model=list[MasterAddonOut], include_in_schema=False)
def manager_plans_legacy(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return list_manager_addons(db)


@router.get("/kitchen/access", response_model=ManagerKitchenAccessOut)
def manager_kitchen_access(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return get_manager_kitchen_access(db)


@router.post("/kitchen/access/regenerate-password", response_model=ManagerKitchenAccessOut)
def manager_kitchen_access_regenerate_password(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return regenerate_manager_kitchen_access_password(db)


@router.get("/staff", response_model=list[RestaurantEmployeeOut])
def list_restaurant_staff(
    search: str | None = Query(default=None, max_length=120),
    employee_type: str | None = Query(default=None, max_length=40),
    active_only: bool = Query(default=False),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[RestaurantEmployee]:
    statement = select(RestaurantEmployee).order_by(
        desc(RestaurantEmployee.active),
        asc(RestaurantEmployee.employee_type),
        asc(RestaurantEmployee.name),
        asc(RestaurantEmployee.id),
    )

    normalized_search = (search or "").strip()
    if normalized_search:
        search_term = f"%{normalized_search}%"
        statement = statement.where(
            or_(
                RestaurantEmployee.name.ilike(search_term),
                RestaurantEmployee.phone.ilike(search_term),
                RestaurantEmployee.work_schedule.ilike(search_term),
            )
        )

    normalized_type = (employee_type or "").strip()
    if normalized_type:
        statement = statement.where(RestaurantEmployee.employee_type == normalized_type)

    if active_only:
        statement = statement.where(RestaurantEmployee.active.is_(True))

    return list(db.execute(statement).scalars())


@router.post("/staff", response_model=RestaurantEmployeeOut, status_code=status.HTTP_201_CREATED)
def create_restaurant_staff(
    payload: RestaurantEmployeeCreate,
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> RestaurantEmployee:
    employee = RestaurantEmployee(
        name=payload.name,
        employee_type=payload.employee_type,
        phone=payload.phone,
        compensation_cycle=payload.compensation_cycle,
        compensation_amount=payload.compensation_amount,
        work_schedule=payload.work_schedule,
        notes=payload.notes,
        active=payload.active,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.put("/staff/{employee_id}", response_model=RestaurantEmployeeOut)
def update_restaurant_staff(
    employee_id: int,
    payload: RestaurantEmployeeUpdate,
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> RestaurantEmployee:
    employee = db.get(RestaurantEmployee, employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الموظف غير موجود.")

    employee.name = payload.name
    employee.employee_type = payload.employee_type
    employee.phone = payload.phone
    employee.compensation_cycle = payload.compensation_cycle
    employee.compensation_amount = payload.compensation_amount
    employee.work_schedule = payload.work_schedule
    employee.notes = payload.notes
    employee.active = payload.active
    employee.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(employee)
    return employee


@router.delete("/staff/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_restaurant_staff(
    employee_id: int,
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> None:
    employee = db.get(RestaurantEmployee, employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الموظف غير موجود.")
    db.delete(employee)
    db.commit()


@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[Order]:
    output = run_use_case(
        execute=list_orders_usecase.execute,
        data=list_orders_usecase.Input(page=page, page_size=page_size),
        repo=build_orders_repository(db),
        db=db,
    )
    return output.result


@router.get("/orders/active", response_model=list[OrderOut])
def list_active_orders(
    limit: int = Query(default=200, ge=1, le=500),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[Order]:
    output = run_use_case(
        execute=list_active_orders_usecase.execute,
        data=list_active_orders_usecase.Input(limit=limit),
        repo=build_orders_repository(db),
        db=db,
    )
    return output.result


@router.get("/tables", response_model=list[ManagerTableOut])
def manager_list_tables(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    output = run_use_case(
        execute=list_tables_usecase.execute,
        data=list_tables_usecase.Input(page=page, page_size=page_size),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.post("/tables", response_model=ManagerTableOut, status_code=status.HTTP_201_CREATED)
def manager_create_table(
    payload: TableCreateInput,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=create_table_usecase.execute,
        data=create_table_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_operations_repository(db),
        db=db,
        request=request,
    )
    return _manager_table_row_or_404(db, output.result.id)


@router.put("/tables/{table_id}", response_model=ManagerTableOut)
def manager_update_table(
    table_id: int,
    payload: TableUpdateInput,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=update_table_usecase.execute,
        data=update_table_usecase.Input(actor_id=current_user.id, table_id=table_id, payload=payload),
        repo=build_operations_repository(db),
        db=db,
        request=request,
    )
    return _manager_table_row_or_404(db, output.result.id)


@router.delete("/tables/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
def manager_delete_table(
    table_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> None:
    run_use_case(
        execute=delete_table_usecase.execute,
        data=delete_table_usecase.Input(actor_id=current_user.id, table_id=table_id),
        repo=build_operations_repository(db),
        db=db,
        request=request,
    )


@router.post("/orders/manual", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def manager_create_manual_order(
    payload: ManagerCreateOrderInput,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Order:
    output = run_use_case(
        execute=create_order_usecase.execute,
        data=create_order_usecase.Input(
            actor_id=current_user.id,
            payload=payload,
            source_actor="manager",
        ),
        repo=build_orders_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/orders/paged", response_model=OrdersPageOut)
def list_orders_paged(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
    search: str | None = Query(default=None),
    sort_by: Literal["created_at", "total", "status", "id"] = "created_at",
    sort_direction: Literal["asc", "desc"] = "desc",
    status_filter: OrderStatus | None = Query(default=None, alias="status"),
    order_type: OrderType | None = Query(default=None),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> OrdersPageOut:
    output = run_use_case(
        execute=list_orders_paged_usecase.execute,
        data=list_orders_paged_usecase.Input(
            page=page,
            page_size=page_size,
            search=search,
            sort_by=sort_by,
            sort_direction=sort_direction,
            status_filter=status_filter,
            order_type=order_type,
        ),
        repo=build_orders_repository(db),
        db=db,
    )
    return output.result


@router.get("/kitchen/orders", response_model=list[OrderOut])
def manager_kitchen_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[Order]:
    output = run_use_case(
        execute=list_kitchen_orders_usecase.execute,
        data=list_kitchen_orders_usecase.Input(
            page=page,
            page_size=page_size,
            sort_direction="desc",
        ),
        repo=build_orders_repository(db),
        db=db,
    )
    return output.result


@router.get("/kitchen/orders/paged", response_model=KitchenOrdersPageOut)
def manager_kitchen_orders_paged(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    search: str | None = Query(default=None),
    scope: Literal["active", "history"] = "active",
    sort_by: Literal["created_at", "total", "status", "id"] = "created_at",
    sort_direction: Literal["asc", "desc"] = "desc",
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> KitchenOrdersPageOut:
    output = run_use_case(
        execute=list_kitchen_orders_paged_usecase.execute,
        data=list_kitchen_orders_paged_usecase.Input(
            page=page,
            page_size=page_size,
            search=search,
            scope=scope,
            sort_by=sort_by,
            sort_direction=sort_direction,
            tie_break_direction="desc",
        ),
        repo=build_orders_repository(db),
        db=db,
    )
    return output.result


@router.post("/orders/{order_id}/transition", response_model=OrderOut)
def manager_transition_order(
    order_id: int,
    payload: OrderTransitionInput,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Order:
    manager_allowed_targets = {
        OrderStatus.CONFIRMED,
        OrderStatus.SENT_TO_KITCHEN,
        OrderStatus.READY,
        OrderStatus.CANCELED,
        OrderStatus.DELIVERED,
    }
    if payload.target_status not in manager_allowed_targets:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="لا تملك صلاحية تنفيذ هذا الانتقال")

    if payload.target_status == OrderStatus.DELIVERED:
        order_type_value = db.execute(select(Order.type).where(Order.id == order_id)).scalar_one_or_none()
        if order_type_value == OrderType.DELIVERY.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="لا يمكن للمدير إنهاء طلب توصيل مباشرة من هذه الشاشة",
            )

    output = run_use_case(
        execute=transition_order_usecase.execute,
        data=transition_order_usecase.Input(
            actor_id=current_user.id,
            order_id=order_id,
            payload=payload,
        ),
        repo=build_orders_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.post("/orders/{order_id}/cancel", response_model=OrderOut)
def manager_cancel_order(
    order_id: int,
    payload: OrderCancelInput,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Order:
    output = run_use_case(
        execute=cancel_order_usecase.execute,
        data=cancel_order_usecase.Input(
            actor_id=current_user.id,
            order_id=order_id,
            reason_code=payload.reason_code,
            reason_note=payload.reason_note,
        ),
        repo=build_orders_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.post("/orders/{order_id}/collect-payment", response_model=OrderOut)
def manager_collect_payment(
    order_id: int,
    payload: OrderPaymentCollectionInput,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Order:
    output = run_use_case(
        execute=collect_order_payment_usecase.execute,
        data=collect_order_payment_usecase.Input(
            actor_id=current_user.id,
            order_id=order_id,
            payload=payload,
        ),
        repo=build_financial_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.post("/orders/{order_id}/settle-delivery", response_model=DeliverySettlementOut)
def manager_settle_delivery_order(
    order_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliverySettlement:
    output = run_use_case(
        execute=settle_delivery_order_usecase.execute,
        data=settle_delivery_order_usecase.Input(
            actor_id=current_user.id,
            order_id=order_id,
        ),
        repo=build_financial_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.post("/orders/{order_id}/refund", response_model=OrderOut)
def manager_refund_order(
    order_id: int,
    payload: OrderRefundInput,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Order:
    output = run_use_case(
        execute=refund_order_usecase.execute,
        data=refund_order_usecase.Input(
            actor_id=current_user.id,
            order_id=order_id,
            payload=payload,
        ),
        repo=build_financial_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.post("/orders/{order_id}/emergency-delivery-fail", response_model=OrderOut)
def manager_emergency_delivery_fail(
    order_id: int,
    payload: EmergencyDeliveryFailInput,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Order:
    output = run_use_case(
        execute=emergency_fail_delivery_order_usecase.execute,
        data=emergency_fail_delivery_order_usecase.Input(
            actor_id=current_user.id,
            order_id=order_id,
            payload=payload,
        ),
        repo=build_delivery_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/table-sessions", response_model=list[TableSessionOut])
def manager_list_table_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    output = run_use_case(
        execute=list_table_sessions_usecase.execute,
        data=list_table_sessions_usecase.Input(page=page, page_size=page_size),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.post("/orders/{order_id}/resolve-delivery-failure", response_model=OrderOut)
def manager_resolve_delivery_failure(
    order_id: int,
    payload: DeliveryFailureResolutionInput,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Order:
    output = run_use_case(
        execute=resolve_delivery_failure_usecase.execute,
        data=resolve_delivery_failure_usecase.Input(
            actor_id=current_user.id,
            order_id=order_id,
            payload=payload,
        ),
        repo=build_delivery_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/tables/{table_id}/session", response_model=TableSessionOut)
def manager_get_table_session(
    table_id: int,
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=get_table_session_usecase.execute,
        data=get_table_session_usecase.Input(table_id=table_id),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.post("/tables/{table_id}/settle-session", response_model=TableSessionSettlementOut)
def manager_settle_session(
    table_id: int,
    payload: TableSessionSettlementInput,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=settle_table_session_usecase.execute,
        data=settle_table_session_usecase.Input(
            actor_id=current_user.id,
            table_id=table_id,
            payload=payload,
        ),
        repo=build_operations_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/products", response_model=list[ProductOut])
def list_products(
    kind: Literal["all", "sellable", "internal", "primary", "secondary"] = Query(default="all"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[Product]:
    output = run_use_case(
        execute=list_products_usecase.execute,
        data=list_products_usecase.Input(
            kind=kind,
            page=page,
            page_size=page_size,
        ),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.get("/categories", response_model=list[ProductCategoryOut])
def list_categories(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[ProductCategory]:
    output = run_use_case(
        execute=list_categories_usecase.execute,
        data=list_categories_usecase.Input(page=page, page_size=page_size),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.post("/categories", response_model=ProductCategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: ProductCategoryCreate,
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> ProductCategory:
    output = run_use_case(
        execute=create_category_usecase.execute,
        data=create_category_usecase.Input(payload=payload),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.put("/categories/{category_id}", response_model=ProductCategoryOut)
def update_category(
    category_id: int,
    payload: ProductCategoryUpdate,
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> ProductCategory:
    output = run_use_case(
        execute=update_category_usecase.execute,
        data=update_category_usecase.Input(category_id=category_id, payload=payload),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> None:
    run_use_case(
        execute=delete_category_usecase.execute,
        data=delete_category_usecase.Input(category_id=category_id),
        repo=build_operations_repository(db),
        db=db,
    )


@router.get("/products/paged", response_model=ProductsPageOut)
def list_products_paged(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
    search: str | None = Query(default=None),
    sort_by: Literal["id", "name", "category", "price", "available"] = "id",
    sort_direction: Literal["asc", "desc"] = "desc",
    archive_state: Literal["all", "active", "archived"] = Query(default="all"),
    kind: Literal["all", "sellable", "internal", "primary", "secondary"] = Query(default="all"),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> ProductsPageOut:
    output = run_use_case(
        execute=list_products_paged_usecase.execute,
        data=list_products_paged_usecase.Input(
            page=page,
            page_size=page_size,
            search=search,
            sort_by=sort_by,
            sort_direction=sort_direction,
            archive_state=archive_state,
            kind=kind,
        ),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Product:
    output = run_use_case(
        execute=create_product_usecase.execute,
        data=create_product_usecase.Input(payload=payload),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Product:
    output = run_use_case(
        execute=update_product_usecase.execute,
        data=update_product_usecase.Input(product_id=product_id, payload=payload),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.post("/products/{product_id}/image", response_model=ProductOut)
def upload_product_image(
    product_id: int,
    payload: ProductImageInput,
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Product:
    output = run_use_case(
        execute=upload_product_image_usecase.execute,
        data=upload_product_image_usecase.Input(product_id=product_id, payload=payload),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_product(
    product_id: int,
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> None:
    run_use_case(
        execute=archive_product_usecase.execute,
        data=archive_product_usecase.Input(product_id=product_id),
        repo=build_operations_repository(db),
        db=db,
    )


@router.delete("/products/{product_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_permanently(
    product_id: int,
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> None:
    run_use_case(
        execute=delete_product_permanently_usecase.execute,
        data=delete_product_permanently_usecase.Input(product_id=product_id),
        repo=build_operations_repository(db),
        db=db,
    )



@router.get("/drivers", response_model=list[DeliveryDriverOut])
def list_drivers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[DeliveryDriver]:
    output = run_use_case(
        execute=list_delivery_drivers_usecase.execute,
        data=list_delivery_drivers_usecase.Input(page=page, page_size=page_size),
        repo=build_delivery_repository(db),
        db=db,
    )
    return output.result


@router.get("/delivery/providers", response_model=list[DeliveryProviderOut])
def list_delivery_providers(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[DeliveryProviderOut]:
    output = run_use_case(
        execute=list_delivery_providers_usecase.execute,
        data=list_delivery_providers_usecase.Input(),
        repo=build_delivery_repository(db),
        db=db,
    )
    return output.result


@router.post("/delivery/providers", response_model=DeliveryProviderOut, status_code=status.HTTP_201_CREATED)
def create_delivery_provider(
    payload: DeliveryProviderCreate,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryProviderOut:
    output = run_use_case(
        execute=create_delivery_provider_usecase.execute,
        data=create_delivery_provider_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_delivery_repository(db),
        db=db,
    )
    return output.result


@router.put("/delivery/providers/{provider_id}", response_model=DeliveryProviderOut)
def update_delivery_provider(
    provider_id: int,
    payload: DeliveryProviderUpdate,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryProviderOut:
    output = run_use_case(
        execute=update_delivery_provider_usecase.execute,
        data=update_delivery_provider_usecase.Input(
            actor_id=current_user.id,
            provider_id=provider_id,
            payload=payload,
        ),
        repo=build_delivery_repository(db),
        db=db,
    )
    return output.result


@router.delete("/delivery/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_delivery_provider(
    provider_id: int,
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> None:
    run_use_case(
        execute=delete_delivery_provider_usecase.execute,
        data=delete_delivery_provider_usecase.Input(provider_id=provider_id),
        repo=build_delivery_repository(db),
        db=db,
    )


@router.get("/delivery/dispatches", response_model=list[DeliveryDispatchOut])
def list_delivery_dispatches(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[DeliveryDispatchOut]:
    output = run_use_case(
        execute=list_delivery_dispatches_usecase.execute,
        data=list_delivery_dispatches_usecase.Input(
            actor_id=current_user.id,
            actor_role=current_user.role,
            page=page,
            page_size=page_size,
        ),
        repo=build_delivery_repository(db),
        db=db,
    )
    return output.result


@router.post("/delivery/dispatches", response_model=DeliveryDispatchOut, status_code=status.HTTP_201_CREATED)
def create_delivery_dispatch(
    payload: DeliveryDispatchCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryDispatchOut:
    output = run_use_case(
        execute=create_delivery_dispatch_usecase.execute,
        data=create_delivery_dispatch_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_delivery_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.post("/delivery/dispatches/{dispatch_id}/cancel", response_model=DeliveryDispatchOut)
def cancel_delivery_dispatch(
    dispatch_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryDispatchOut:
    output = run_use_case(
        execute=cancel_delivery_dispatch_usecase.execute,
        data=cancel_delivery_dispatch_usecase.Input(actor_id=current_user.id, dispatch_id=dispatch_id),
        repo=build_delivery_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.post("/drivers", response_model=DeliveryDriverOut, status_code=status.HTTP_201_CREATED)
def create_driver(
    payload: DeliveryDriverCreate,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryDriver:
    output = run_use_case(
        execute=create_delivery_driver_usecase.execute,
        data=create_delivery_driver_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_delivery_repository(db),
        db=db,
    )
    return output.result


@router.put("/drivers/{driver_id}", response_model=DeliveryDriverOut)
def update_driver(
    driver_id: int,
    payload: DeliveryDriverUpdate,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryDriver:
    output = run_use_case(
        execute=update_delivery_driver_usecase.execute,
        data=update_delivery_driver_usecase.Input(
            actor_id=current_user.id,
            driver_id=driver_id,
            payload=payload,
        ),
        repo=build_delivery_repository(db),
        db=db,
    )
    return output.result


@router.delete("/drivers/{driver_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_driver(
    driver_id: int,
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> None:
    run_use_case(
        execute=delete_delivery_driver_usecase.execute,
        data=delete_delivery_driver_usecase.Input(driver_id=driver_id),
        repo=build_delivery_repository(db),
        db=db,
    )


@router.get("/drivers/{driver_id}/telegram-link", response_model=DeliveryDriverTelegramLinkOut)
def get_driver_telegram_link(
    driver_id: int,
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryDriverTelegramLinkOut:
    bot_settings = build_core_repository(db).get_telegram_bot_settings()
    db.commit()
    result = build_delivery_repository(db).get_driver_telegram_link_status(
        driver_id=driver_id,
        bot_username=str(bot_settings.get("bot_username") or "").strip() or None,
    )
    return DeliveryDriverTelegramLinkOut(**result)


@router.post("/drivers/{driver_id}/telegram-link", response_model=DeliveryDriverTelegramLinkOut)
def create_driver_telegram_link(
    driver_id: int,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryDriverTelegramLinkOut:
    bot_settings = build_core_repository(db).get_telegram_bot_settings()
    result = build_delivery_repository(db).create_driver_telegram_link(
        driver_id=driver_id,
        actor_id=current_user.id,
        bot_username=str(bot_settings.get("bot_username") or "").strip() or None,
    )
    db.commit()
    return DeliveryDriverTelegramLinkOut(**result)


@router.delete("/drivers/{driver_id}/telegram-link", response_model=DeliveryDriverTelegramLinkOut)
def clear_driver_telegram_link(
    driver_id: int,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryDriverTelegramLinkOut:
    bot_settings = build_core_repository(db).get_telegram_bot_settings()
    result = build_delivery_repository(db).clear_driver_telegram_link(
        driver_id=driver_id,
        actor_id=current_user.id,
        bot_username=str(bot_settings.get("bot_username") or "").strip() or None,
    )
    db.commit()
    return DeliveryDriverTelegramLinkOut(**result)


@router.post("/drivers/{driver_id}/telegram-link/test-message", response_model=DeliveryDriverTelegramLinkOut)
def send_driver_telegram_test_message(
    driver_id: int,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryDriverTelegramLinkOut:
    bot_settings = build_core_repository(db).get_telegram_bot_settings()
    result = build_delivery_repository(db).send_driver_telegram_test_message(
        driver_id=driver_id,
        actor_id=current_user.id,
        bot_username=str(bot_settings.get("bot_username") or "").strip() or None,
    )
    db.commit()
    return DeliveryDriverTelegramLinkOut(**result)


@router.post("/drivers/{driver_id}/telegram-link/resend-latest", response_model=DeliveryDriverTelegramLinkOut)
def resend_driver_telegram_flow(
    driver_id: int,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryDriverTelegramLinkOut:
    bot_settings = build_core_repository(db).get_telegram_bot_settings()
    result = build_delivery_repository(db).resend_driver_telegram_flow(
        driver_id=driver_id,
        actor_id=current_user.id,
        bot_username=str(bot_settings.get("bot_username") or "").strip() or None,
    )
    db.commit()
    return DeliveryDriverTelegramLinkOut(**result)


@router.post("/delivery/team-notify", response_model=OrderOut)
def notify_team(
    payload: DeliveryTeamNotifyInput,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Order:
    output = run_use_case(
        execute=notify_delivery_team_usecase.execute,
        data=notify_delivery_team_usecase.Input(
            actor_id=current_user.id,
            order_id=payload.order_id,
        ),
        repo=build_delivery_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/delivery/settings", response_model=DeliverySettingsOut)
def get_delivery_settings(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliverySettingsOut:
    output = run_use_case(
        execute=get_delivery_settings_usecase.execute,
        data=get_delivery_settings_usecase.Input(),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.put("/delivery/settings", response_model=DeliverySettingsOut)
def update_delivery_settings(
    payload: DeliverySettingsUpdate,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliverySettingsOut:
    output = run_use_case(
        execute=update_delivery_settings_usecase.execute,
        data=update_delivery_settings_usecase.Input(
            actor_id=current_user.id,
            payload=payload,
        ),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.get("/delivery/location-provider", response_model=DeliveryLocationProviderSettingsOut)
def get_delivery_location_provider_settings(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryLocationProviderSettingsOut:
    output = run_use_case(
        execute=get_delivery_location_provider_settings_usecase.execute,
        data=get_delivery_location_provider_settings_usecase.Input(),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.put("/delivery/location-provider", response_model=DeliveryLocationProviderSettingsOut)
def update_delivery_location_provider_settings(
    payload: DeliveryLocationProviderSettingsUpdate,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryLocationProviderSettingsOut:
    output = run_use_case(
        execute=update_delivery_location_provider_settings_usecase.execute,
        data=update_delivery_location_provider_settings_usecase.Input(
            actor_id=current_user.id,
            payload=payload,
        ),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.get("/delivery/locations/countries", response_model=DeliveryLocationListOut)
def manager_delivery_location_countries(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryLocationListOut:
    output = run_use_case(
        execute=list_public_delivery_location_countries_usecase.execute,
        data=list_public_delivery_location_countries_usecase.Input(),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.get("/delivery/locations/children", response_model=DeliveryLocationListOut)
def manager_delivery_location_children(
    parent_key: str = Query(min_length=4, max_length=160),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryLocationListOut:
    output = run_use_case(
        execute=list_public_delivery_location_children_usecase.execute,
        data=list_public_delivery_location_children_usecase.Input(parent_key=parent_key),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.get("/delivery/address-nodes", response_model=DeliveryAddressNodeListOut)
def manager_delivery_address_nodes(
    parent_id: int | None = Query(default=None, gt=0),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryAddressNodeListOut:
    output = run_use_case(
        execute=list_delivery_address_nodes_usecase.execute,
        data=list_delivery_address_nodes_usecase.Input(parent_id=parent_id, public_only=False),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.post("/delivery/address-nodes", response_model=DeliveryAddressNodeOut, status_code=status.HTTP_201_CREATED)
def create_delivery_address_node(
    payload: DeliveryAddressNodeCreate,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryAddressNodeOut:
    output = run_use_case(
        execute=create_delivery_address_node_usecase.execute,
        data=create_delivery_address_node_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.put("/delivery/address-nodes/{node_id}", response_model=DeliveryAddressNodeOut)
def update_delivery_address_node(
    node_id: int,
    payload: DeliveryAddressNodeUpdate,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryAddressNodeOut:
    output = run_use_case(
        execute=update_delivery_address_node_usecase.execute,
        data=update_delivery_address_node_usecase.Input(
            actor_id=current_user.id,
            node_id=node_id,
            payload=payload,
        ),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.delete("/delivery/address-nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_delivery_address_node(
    node_id: int,
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> None:
    run_use_case(
        execute=delete_delivery_address_node_usecase.execute,
        data=delete_delivery_address_node_usecase.Input(node_id=node_id),
        repo=build_operations_repository(db),
        db=db,
    )


@router.get("/delivery/address-pricing", response_model=DeliveryZonePricingListOut)
def list_delivery_address_pricing(
    search: str | None = Query(default=None),
    active_only: bool | None = Query(default=None),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryZonePricingListOut:
    output = run_use_case(
        execute=list_delivery_zone_pricing_usecase.execute,
        data=list_delivery_zone_pricing_usecase.Input(search=search, active_only=active_only),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.put("/delivery/address-pricing", response_model=DeliveryZonePricingOut)
def upsert_delivery_address_pricing(
    payload: DeliveryZonePricingUpsert,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryZonePricingOut:
    output = run_use_case(
        execute=upsert_delivery_zone_pricing_usecase.execute,
        data=upsert_delivery_zone_pricing_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.get("/delivery/address-pricing/quote", response_model=DeliveryLocationPricingQuoteOut)
def manager_quote_delivery_address_pricing(
    node_id: int = Query(gt=0),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryLocationPricingQuoteOut:
    output = run_use_case(
        execute=quote_delivery_location_pricing_usecase.execute,
        data=quote_delivery_location_pricing_usecase.Input(location_key=str(node_id)),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.delete("/delivery/address-pricing/{pricing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_delivery_address_pricing(
    pricing_id: int,
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> None:
    run_use_case(
        execute=delete_delivery_zone_pricing_usecase.execute,
        data=delete_delivery_zone_pricing_usecase.Input(zone_id=pricing_id),
        repo=build_operations_repository(db),
        db=db,
    )


@router.get("/delivery/policies", response_model=DeliveryPolicySettingsOut)
def get_delivery_policies(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryPolicySettingsOut:
    output = run_use_case(
        execute=get_delivery_policies_usecase.execute,
        data=get_delivery_policies_usecase.Input(),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.put("/delivery/policies", response_model=DeliveryPolicySettingsOut)
def update_delivery_policies(
    payload: DeliveryPolicySettingsUpdate,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliveryPolicySettingsOut:
    output = run_use_case(
        execute=update_delivery_policies_usecase.execute,
        data=update_delivery_policies_usecase.Input(
            actor_id=current_user.id,
            payload=payload,
        ),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.put("/account/profile", response_model=UserOut)
def update_manager_account_profile(
    payload: AccountProfileUpdate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> User:
    output = run_use_case(
        execute=update_account_profile_usecase.execute,
        data=update_account_profile_usecase.Input(
            actor_id=current_user.id,
            current_role=current_user.role,
            current_active=current_user.active,
            payload=payload,
        ),
        repo=build_core_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/account/sessions", response_model=list[AccountSessionOut])
def list_manager_account_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    output = run_use_case(
        execute=list_account_sessions_usecase.execute,
        data=list_account_sessions_usecase.Input(
            user_id=current_user.id,
            page=page,
            page_size=page_size,
        ),
        repo=build_core_repository(db),
        db=db,
    )
    return output.result


@router.post("/account/sessions/revoke-all", response_model=AccountSessionsRevokeOut)
def revoke_manager_account_sessions(
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> AccountSessionsRevokeOut:
    output = run_use_case(
        execute=revoke_all_account_sessions_usecase.execute,
        data=revoke_all_account_sessions_usecase.Input(
            actor_id=current_user.id,
            user_id=current_user.id,
        ),
        repo=build_core_repository(db),
        db=db,
        request=request,
    )
    return AccountSessionsRevokeOut(revoked_count=output.revoked_count)


@router.get("/settings/operational", response_model=list[OperationalSettingOut])
def get_operational_settings(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    output = run_use_case(
        execute=list_operational_settings_usecase.execute,
        data=list_operational_settings_usecase.Input(page=page, page_size=page_size),
        repo=build_core_repository(db),
        db=db,
    )
    return output.result


@router.put("/settings/operational", response_model=OperationalSettingOut)
def update_operational_settings(
    payload: OperationalSettingUpdate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=update_operational_setting_usecase.execute,
        data=update_operational_setting_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_core_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/settings/system-context", response_model=SystemContextOut)
def get_system_context_settings(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> SystemContextOut:
    output = run_use_case(
        execute=get_system_context_settings_usecase.execute,
        data=get_system_context_settings_usecase.Input(),
        repo=build_core_repository(db),
        db=db,
    )
    return output.result


@router.put("/settings/system-context", response_model=SystemContextOut)
def update_system_context_settings(
    payload: SystemContextUpdate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> SystemContextOut:
    output = run_use_case(
        execute=update_system_context_settings_usecase.execute,
        data=update_system_context_settings_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_core_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/settings/storefront", response_model=StorefrontSettingsOut)
def get_storefront_settings(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> StorefrontSettingsOut:
    output = run_use_case(
        execute=get_storefront_settings_usecase.execute,
        data=get_storefront_settings_usecase.Input(),
        repo=build_core_repository(db),
        db=db,
    )
    return output.result


@router.put("/settings/storefront", response_model=StorefrontSettingsOut)
def update_storefront_settings(
    payload: StorefrontSettingsUpdate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> StorefrontSettingsOut:
    output = run_use_case(
        execute=update_storefront_settings_usecase.execute,
        data=update_storefront_settings_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_core_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/settings/telegram-bot", response_model=TelegramBotSettingsOut)
def get_telegram_bot_settings(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> TelegramBotSettingsOut:
    output = run_use_case(
        execute=get_telegram_bot_settings_usecase.execute,
        data=get_telegram_bot_settings_usecase.Input(),
        repo=build_core_repository(db),
        db=db,
    )
    db.commit()
    return output.result


@router.get("/settings/telegram-bot/health", response_model=TelegramBotHealthOut)
def get_telegram_bot_health(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> TelegramBotHealthOut:
    output = run_use_case(
        execute=get_telegram_bot_health_usecase.execute,
        data=get_telegram_bot_health_usecase.Input(),
        repo=build_core_repository(db),
        db=db,
    )
    db.commit()
    return output.result


@router.put("/settings/telegram-bot", response_model=TelegramBotSettingsOut)
def update_telegram_bot_settings(
    payload: TelegramBotSettingsUpdate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> TelegramBotSettingsOut:
    output = run_use_case(
        execute=update_telegram_bot_settings_usecase.execute,
        data=update_telegram_bot_settings_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_core_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/system/backups", response_model=list[SystemBackupOut])
def get_system_backups(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    output = run_use_case(
        execute=list_system_backups_usecase.execute,
        data=list_system_backups_usecase.Input(page=page, page_size=page_size),
        repo=build_core_repository(db),
        db=db,
    )
    return output.result


@router.post("/system/backups/create", response_model=SystemBackupOut)
def create_backup(
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=create_system_backup_usecase.execute,
        data=create_system_backup_usecase.Input(actor_id=current_user.id),
        repo=build_core_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.post("/system/backups/restore", response_model=SystemBackupOut)
def restore_backup(
    payload: SystemBackupRestoreInput,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=restore_system_backup_usecase.execute,
        data=restore_system_backup_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_core_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/financial/transactions", response_model=list[FinancialTransactionOut])
def list_financial_transactions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[FinancialTransaction]:
    output = run_use_case(
        execute=list_financial_transactions_usecase.execute,
        data=list_financial_transactions_usecase.Input(page=page, page_size=page_size),
        repo=build_financial_repository(db),
        db=db,
    )
    return output.result


@router.get("/financial/delivery-settlements", response_model=list[DeliverySettlementOut])
def list_financial_delivery_settlements(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[DeliverySettlement]:
    output = run_use_case(
        execute=list_delivery_settlements_usecase.execute,
        data=list_delivery_settlements_usecase.Input(page=page, page_size=page_size),
        repo=build_financial_repository(db),
        db=db,
    )
    return output.result


@router.get("/financial/cashbox-movements", response_model=list[CashboxMovementOut])
def list_financial_cashbox_movements(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[CashboxMovement]:
    output = run_use_case(
        execute=list_cashbox_movements_usecase.execute,
        data=list_cashbox_movements_usecase.Input(page=page, page_size=page_size),
        repo=build_financial_repository(db),
        db=db,
    )
    return output.result


@router.post("/financial/cashbox-movements", response_model=DeliverySettlementOut)
def record_financial_cashbox_movement(
    payload: CashboxMovementCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> DeliverySettlement:
    output = run_use_case(
        execute=record_cashbox_movement_usecase.execute,
        data=record_cashbox_movement_usecase.Input(
            actor_id=current_user.id,
            settlement_id=payload.settlement_id,
            amount=payload.amount,
            movement_type=payload.movement_type,
            cash_channel=payload.cash_channel.value,
            note=payload.note,
        ),
        repo=build_financial_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/financial/migration-status", response_model=DeliveryAccountingMigrationStatusOut)
def get_financial_migration_status(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=get_delivery_accounting_migration_status_usecase.execute,
        data=get_delivery_accounting_migration_status_usecase.Input(),
        repo=build_financial_repository(db),
        db=db,
    )
    return output.result


@router.post("/financial/delivery-accounting-backfill", response_model=DeliveryAccountingBackfillOut)
def run_financial_delivery_accounting_backfill(
    payload: DeliveryAccountingBackfillInput,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=run_delivery_accounting_backfill_usecase.execute,
        data=run_delivery_accounting_backfill_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_financial_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/financial/shift-closures", response_model=list[ShiftClosureOut])
def list_financial_shift_closures(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[ShiftClosure]:
    output = run_use_case(
        execute=list_shift_closures_usecase.execute,
        data=list_shift_closures_usecase.Input(page=page, page_size=page_size),
        repo=build_financial_repository(db),
        db=db,
    )
    return output.result


@router.post("/financial/shift-closures", response_model=ShiftClosureOut, status_code=status.HTTP_201_CREATED)
def create_financial_shift_closure(
    payload: ShiftClosureCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> ShiftClosure:
    output = run_use_case(
        execute=close_shift_usecase.execute,
        data=close_shift_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_financial_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/expenses/cost-centers", response_model=list[ExpenseCostCenterOut])
def list_expense_cost_centers_endpoint(
    include_inactive: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[ExpenseCostCenter]:
    output = run_use_case(
        execute=list_expense_cost_centers_usecase.execute,
        data=list_expense_cost_centers_usecase.Input(
            include_inactive=include_inactive,
            page=page,
            page_size=page_size,
        ),
        repo=build_financial_repository(db),
        db=db,
    )
    return output.result


@router.post("/expenses/cost-centers", response_model=ExpenseCostCenterOut, status_code=status.HTTP_201_CREATED)
def create_expense_cost_center_endpoint(
    payload: ExpenseCostCenterCreate,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> ExpenseCostCenter:
    output = run_use_case(
        execute=create_expense_cost_center_usecase.execute,
        data=create_expense_cost_center_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_financial_repository(db),
        db=db,
    )
    return output.result


@router.put("/expenses/cost-centers/{center_id}", response_model=ExpenseCostCenterOut)
def update_expense_cost_center_endpoint(
    center_id: int,
    payload: ExpenseCostCenterUpdate,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> ExpenseCostCenter:
    output = run_use_case(
        execute=update_expense_cost_center_usecase.execute,
        data=update_expense_cost_center_usecase.Input(
            actor_id=current_user.id,
            center_id=center_id,
            payload=payload,
        ),
        repo=build_financial_repository(db),
        db=db,
    )
    return output.result


@router.get("/expenses", response_model=list[ExpenseOut])
def list_expenses(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[Expense]:
    output = run_use_case(
        execute=list_expenses_usecase.execute,
        data=list_expenses_usecase.Input(page=page, page_size=page_size),
        repo=build_financial_repository(db),
        db=db,
    )
    return output.result


@router.post("/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense_endpoint(
    payload: ExpenseCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Expense:
    output = run_use_case(
        execute=create_expense_usecase.execute,
        data=create_expense_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_financial_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.put("/expenses/{expense_id}", response_model=ExpenseOut)
def update_expense_endpoint(
    expense_id: int,
    payload: ExpenseUpdate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Expense:
    output = run_use_case(
        execute=update_expense_usecase.execute,
        data=update_expense_usecase.Input(
            actor_id=current_user.id,
            expense_id=expense_id,
            payload=payload,
        ),
        repo=build_financial_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.post("/expenses/{expense_id}/approve", response_model=ExpenseOut)
def approve_expense_endpoint(
    expense_id: int,
    payload: ExpenseReviewInput,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Expense:
    output = run_use_case(
        execute=approve_expense_usecase.execute,
        data=approve_expense_usecase.Input(
            actor_id=current_user.id,
            expense_id=expense_id,
            payload=payload,
        ),
        repo=build_financial_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.post("/expenses/{expense_id}/reject", response_model=ExpenseOut)
def reject_expense_endpoint(
    expense_id: int,
    payload: ExpenseReviewInput,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> Expense:
    output = run_use_case(
        execute=reject_expense_usecase.execute,
        data=reject_expense_usecase.Input(
            actor_id=current_user.id,
            expense_id=expense_id,
            payload=payload,
        ),
        repo=build_financial_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.post("/expenses/{expense_id}/attachments", response_model=ExpenseAttachmentOut, status_code=status.HTTP_201_CREATED)
def create_expense_attachment_endpoint(
    expense_id: int,
    payload: ExpenseAttachmentCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> ExpenseAttachmentOut:
    output = run_use_case(
        execute=create_expense_attachment_usecase.execute,
        data=create_expense_attachment_usecase.Input(
            actor_id=current_user.id,
            expense_id=expense_id,
            payload=payload,
        ),
        repo=build_financial_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.delete("/expenses/{expense_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense_attachment_endpoint(
    expense_id: int,
    attachment_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> None:
    run_use_case(
        execute=delete_expense_attachment_usecase.execute,
        data=delete_expense_attachment_usecase.Input(
            actor_id=current_user.id,
            expense_id=expense_id,
            attachment_id=attachment_id,
        ),
        repo=build_financial_repository(db),
        db=db,
        request=request,
    )


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense_endpoint(
    expense_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> None:
    run_use_case(
        execute=delete_expense_usecase.execute,
        data=delete_expense_usecase.Input(expense_id=expense_id, actor_id=current_user.id),
        repo=build_financial_repository(db),
        db=db,
        request=request,
    )


@router.get("/reports/daily", response_model=list[ReportDailyRow])
def report_daily(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_AUDIT_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[dict[str, float | str]]:
    output = run_use_case(
        execute=report_daily_usecase.execute,
        data=report_daily_usecase.Input(page=page, page_size=page_size),
        repo=build_intelligence_repository(db),
        db=db,
    )
    return output.result


@router.get("/reports/monthly", response_model=list[ReportMonthlyRow])
def report_monthly(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_AUDIT_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[dict[str, float | str]]:
    output = run_use_case(
        execute=report_monthly_usecase.execute,
        data=report_monthly_usecase.Input(page=page, page_size=page_size),
        repo=build_intelligence_repository(db),
        db=db,
    )
    return output.result


@router.get("/reports/by-order-type", response_model=list[ReportByTypeRow])
def report_order_type(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_AUDIT_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[dict[str, float | str | int]]:
    output = run_use_case(
        execute=report_by_order_type_usecase.execute,
        data=report_by_order_type_usecase.Input(page=page, page_size=page_size),
        repo=build_intelligence_repository(db),
        db=db,
    )
    return output.result


@router.get("/reports/performance", response_model=ReportPerformance)
def report_performance(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> ReportPerformance:
    output = run_use_case(
        execute=report_performance_usecase.execute,
        data=report_performance_usecase.Input(),
        repo=build_intelligence_repository(db),
        db=db,
    )
    return output.result


@router.get("/reports/profitability", response_model=ReportProfitabilityOut)
def report_profitability(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=report_profitability_usecase.execute,
        data=report_profitability_usecase.Input(start_date=start_date, end_date=end_date),
        repo=build_intelligence_repository(db),
        db=db,
    )
    return output.result


@router.get("/reports/period-comparison", response_model=ReportPeriodComparisonOut)
def report_period_comparison(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=report_period_comparison_usecase.execute,
        data=report_period_comparison_usecase.Input(start_date=start_date, end_date=end_date),
        repo=build_intelligence_repository(db),
        db=db,
    )
    return output.result


@router.get("/reports/peak-hours-performance", response_model=ReportPeakHoursPerformanceOut)
def report_peak_hours_performance(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=report_peak_hours_performance_usecase.execute,
        data=report_peak_hours_performance_usecase.Input(start_date=start_date, end_date=end_date),
        repo=build_intelligence_repository(db),
        db=db,
    )
    return output.result


@router.get("/users", response_model=list[UserOut])
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[User]:
    output = run_use_case(
        execute=list_users_usecase.execute,
        data=list_users_usecase.Input(page=page, page_size=page_size),
        repo=build_core_repository(db),
        db=db,
    )
    return output.result


@router.get("/users/permissions/catalog", response_model=list[PermissionCatalogItemOut])
def list_users_permissions_catalog(
    role: UserRole | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    output = run_use_case(
        execute=list_permissions_catalog_usecase.execute,
        data=list_permissions_catalog_usecase.Input(
            role=role.value if role else None,
            page=page,
            page_size=page_size,
        ),
        repo=build_core_repository(db),
        db=db,
    )
    return output.result


@router.get("/users/{user_id}/permissions", response_model=UserPermissionsOut)
def get_user_permissions_endpoint(
    user_id: int,
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=get_user_permissions_usecase.execute,
        data=get_user_permissions_usecase.Input(user_id=user_id),
        repo=build_core_repository(db),
        db=db,
    )
    return output.result


@router.put("/users/{user_id}/permissions", response_model=UserPermissionsOut)
def update_user_permissions_endpoint(
    user_id: int,
    payload: UserPermissionsUpdate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=update_user_permissions_usecase.execute,
        data=update_user_permissions_usecase.Input(
            actor_id=current_user.id,
            user_id=user_id,
            payload=payload,
        ),
        repo=build_core_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    payload: UserCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> User:
    output = run_use_case(
        execute=create_user_usecase.execute,
        data=create_user_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_core_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.put("/users/{user_id}", response_model=UserOut)
def update_user_endpoint(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> User:
    output = run_use_case(
        execute=update_user_usecase.execute,
        data=update_user_usecase.Input(
            actor_id=current_user.id,
            user_id=user_id,
            payload=payload,
        ),
        repo=build_core_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_endpoint(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> None:
    try:
        run_use_case(
            execute=delete_user_usecase.execute,
            data=delete_user_usecase.Input(actor_id=current_user.id, user_id=user_id),
            repo=build_core_repository(db),
            db=db,
            request=request,
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="تعذر حذف المستخدم لارتباطه بسجلات تشغيلية أخرى.",
        ) from exc


@router.get("/audit/orders", response_model=list[OrderTransitionLogOut])
def order_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_AUDIT_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[OrderTransitionLog]:
    output = run_use_case(
        execute=list_order_audit_usecase.execute,
        data=list_order_audit_usecase.Input(page=page, page_size=page_size),
        repo=build_intelligence_repository(db),
        db=db,
    )
    return output.result


@router.get("/audit/system", response_model=list[SystemAuditLogOut])
def system_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_AUDIT_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[SystemAuditLog]:
    output = run_use_case(
        execute=list_system_audit_usecase.execute,
        data=list_system_audit_usecase.Input(page=page, page_size=page_size),
        repo=build_intelligence_repository(db),
        db=db,
    )
    return output.result


@router.get("/audit/security", response_model=list[SecurityAuditEventOut])
def security_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LIST_PAGE_SIZE, ge=1, le=MAX_AUDIT_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[SecurityAuditEvent]:
    output = run_use_case(
        execute=list_security_audit_usecase.execute,
        data=list_security_audit_usecase.Input(page=page, page_size=page_size),
        repo=build_intelligence_repository(db),
        db=db,
    )
    return output.result








