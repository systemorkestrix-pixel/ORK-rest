from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..dependencies import get_db
from ..enums import OrderType
from ..models import Order
from ..schemas import (
    CreateOrderInput,
    DeliveryAddressNodeListOut,
    DeliveryLocationListOut,
    DeliveryLocationPricingQuoteOut,
    DeliverySettingsOut,
    OperationalCapabilitiesOut,
    OrderOut,
    PublicOrderJourneyBootstrapOut,
    PublicOrderTrackingOut,
    PublicProductOut,
    StorefrontSettingsOut,
    TenantEntryOut,
    TableOut,
    TableSessionOut,
)
from ..usecase_factory import build_core_repository, build_operations_repository, build_orders_repository, run_use_case
from application.master_engine.domain.registry import (
    build_tenant_manager_login_path,
    build_tenant_public_order_path,
    get_registry_tenant_by_code,
)
from application.core_engine.use_cases import get_storefront_settings as get_storefront_settings_usecase
from application.operations_engine.use_cases import create_order as create_order_usecase
from application.operations_engine.use_cases import get_operational_capabilities as get_operational_capabilities_usecase
from application.operations_engine.use_cases import list_delivery_address_nodes as list_delivery_address_nodes_usecase
from application.operations_engine.use_cases import list_public_delivery_location_children as list_public_delivery_location_children_usecase
from application.operations_engine.use_cases import list_public_delivery_location_countries as list_public_delivery_location_countries_usecase
from application.operations_engine.use_cases import quote_delivery_location_pricing as quote_delivery_location_pricing_usecase
from application.operations_engine.use_cases import get_public_delivery_settings as get_public_delivery_settings_usecase
from application.operations_engine.use_cases import get_public_order_journey_bootstrap as get_public_order_journey_bootstrap_usecase
from application.operations_engine.use_cases import get_public_order_tracking as get_public_order_tracking_usecase
from application.operations_engine.use_cases import get_public_table_session as get_public_table_session_usecase
from application.operations_engine.use_cases import list_public_products as list_public_products_usecase
from application.operations_engine.use_cases import list_public_tables as list_public_tables_usecase

router = APIRouter(prefix="/public", tags=["public"])
DEFAULT_PUBLIC_PAGE_SIZE = 24
MAX_PUBLIC_PAGE_SIZE = 100


@router.get("/tenant-entry", response_model=TenantEntryOut)
def get_public_tenant_entry(tenant: str = Query(min_length=2, max_length=80)) -> TenantEntryOut:
    master_db = SessionLocal()
    try:
        tenant_record = get_registry_tenant_by_code(master_db, tenant)
        if tenant_record is None or tenant_record.client is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="تعذر العثور على النسخة المطلوبة.")
        return TenantEntryOut(
            tenant_id=str(tenant_record.id),
            tenant_code=tenant_record.code,
            tenant_brand_name=tenant_record.brand_name,
            client_brand_name=tenant_record.client.brand_name,
            client_owner_name=tenant_record.client.owner_name,
            manager_login_path=build_tenant_manager_login_path(tenant_record.code),
            public_order_path=build_tenant_public_order_path(tenant_record.code),
            public_menu_path=f"/t/{tenant_record.code}/menu",
        )
    finally:
        master_db.close()


@router.get("/storefront-settings", response_model=StorefrontSettingsOut)
def get_public_storefront_settings(db: Session = Depends(get_db)) -> StorefrontSettingsOut:
    output = run_use_case(
        execute=get_storefront_settings_usecase.execute,
        data=get_storefront_settings_usecase.Input(),
        repo=build_core_repository(db),
        db=db,
    )
    return output.result


@router.get("/order-journey/bootstrap", response_model=PublicOrderJourneyBootstrapOut)
def get_public_order_journey_bootstrap(
    table_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
) -> PublicOrderJourneyBootstrapOut:
    output = run_use_case(
        execute=get_public_order_journey_bootstrap_usecase.execute,
        data=get_public_order_journey_bootstrap_usecase.Input(table_id=table_id),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.get("/delivery/locations/countries", response_model=DeliveryLocationListOut)
def list_public_delivery_location_countries(db: Session = Depends(get_db)) -> DeliveryLocationListOut:
    output = run_use_case(
        execute=list_public_delivery_location_countries_usecase.execute,
        data=list_public_delivery_location_countries_usecase.Input(),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.get("/delivery/locations/children", response_model=DeliveryLocationListOut)
def list_public_delivery_location_children(
    parent_key: str = Query(min_length=4, max_length=160),
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
def list_public_delivery_address_nodes(
    parent_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
) -> DeliveryAddressNodeListOut:
    output = run_use_case(
        execute=list_delivery_address_nodes_usecase.execute,
        data=list_delivery_address_nodes_usecase.Input(parent_id=parent_id, public_only=True),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.get("/delivery/pricing/quote", response_model=DeliveryLocationPricingQuoteOut)
def quote_public_delivery_location_pricing(
    node_id: int | None = Query(default=None, gt=0),
    location_key: str | None = Query(default=None, min_length=1, max_length=160),
    db: Session = Depends(get_db),
) -> DeliveryLocationPricingQuoteOut:
    selected_location_key = str(node_id) if node_id is not None else location_key
    output = run_use_case(
        execute=quote_delivery_location_pricing_usecase.execute,
        data=quote_delivery_location_pricing_usecase.Input(location_key=selected_location_key),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.get("/orders/track", response_model=PublicOrderTrackingOut)
def get_public_order_tracking(
    code: str = Query(min_length=8, max_length=32),
    db: Session = Depends(get_db),
) -> PublicOrderTrackingOut:
    output = run_use_case(
        execute=get_public_order_tracking_usecase.execute,
        data=get_public_order_tracking_usecase.Input(tracking_code=code),
        repo=build_operations_repository(db),
        db=db,
    )
    if output.result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="تعذر العثور على طلب مطابق لهذا الكود.",
        )
    return output.result


@router.get("/products", response_model=list[PublicProductOut])
def list_public_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PUBLIC_PAGE_SIZE, ge=1, le=MAX_PUBLIC_PAGE_SIZE),
    db: Session = Depends(get_db),
) -> list[PublicProductOut]:
    output = run_use_case(
        execute=list_public_products_usecase.execute,
        data=list_public_products_usecase.Input(page=page, page_size=page_size),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.get("/tables", response_model=list[TableOut])
def list_tables(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PUBLIC_PAGE_SIZE, ge=1, le=MAX_PUBLIC_PAGE_SIZE),
    db: Session = Depends(get_db),
) -> list[TableOut]:
    output = run_use_case(
        execute=list_public_tables_usecase.execute,
        data=list_public_tables_usecase.Input(page=page, page_size=page_size),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.get("/tables/{table_id}/session", response_model=TableSessionOut)
def get_public_table_session(table_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    output = run_use_case(
        execute=get_public_table_session_usecase.execute,
        data=get_public_table_session_usecase.Input(table_id=table_id),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.post("/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: CreateOrderInput,
    request: Request,
    db: Session = Depends(get_db),
) -> Order:
    capabilities = run_use_case(
        execute=get_operational_capabilities_usecase.execute,
        data=get_operational_capabilities_usecase.Input(),
        repo=build_operations_repository(db),
        db=db,
    ).result
    kitchen_feature_enabled = bool(capabilities.get("kitchen_feature_enabled", True))
    if kitchen_feature_enabled and not capabilities["kitchen_enabled"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="استقبال الطلبات غير متاح مؤقتًا. حاول مرة أخرى بعد قليل.",
        )
    if payload.type == OrderType.DELIVERY and (
        not capabilities.get("delivery_feature_enabled", False) or not capabilities.get("delivery_enabled", False)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="خدمة التوصيل غير متاحة حاليًا. اختر الاستلام من المطعم أو الطلب من الطاولة.",
        )
    output = run_use_case(
        execute=create_order_usecase.execute,
        data=create_order_usecase.Input(actor_id=None, payload=payload, source_actor="public"),
        repo=build_orders_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/delivery/settings", response_model=DeliverySettingsOut)
def public_delivery_settings(db: Session = Depends(get_db)) -> DeliverySettingsOut:
    output = run_use_case(
        execute=get_public_delivery_settings_usecase.execute,
        data=get_public_delivery_settings_usecase.Input(),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result


@router.get("/operational-capabilities", response_model=OperationalCapabilitiesOut)
def public_operational_capabilities(db: Session = Depends(get_db)) -> dict[str, object]:
    output = run_use_case(
        execute=get_operational_capabilities_usecase.execute,
        data=get_operational_capabilities_usecase.Input(),
        repo=build_operations_repository(db),
        db=db,
    )
    return output.result
