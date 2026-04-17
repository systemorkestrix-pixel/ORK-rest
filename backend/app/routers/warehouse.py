from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_roles, require_route_capability
from ..enums import UserRole
from ..models import User, WarehouseItem
from ..schemas import (
    WarehouseDashboardOut,
    WarehouseInboundVoucherCreate,
    WarehouseInboundVoucherOut,
    WarehouseItemCreate,
    WarehouseItemOut,
    WarehouseItemUpdate,
    WarehouseLedgerOut,
    WarehouseOutboundReasonOut,
    WarehouseOutboundVoucherCreate,
    WarehouseOutboundVoucherOut,
    WarehouseStockCountCreate,
    WarehouseStockCountOut,
    WarehouseStockBalanceOut,
    WarehouseSupplierCreate,
    WarehouseSupplierOut,
    WarehouseSupplierUpdate,
)
from ..usecase_factory import build_warehouse_repository, run_use_case
from application.inventory_engine.use_cases import create_inbound_voucher as create_inbound_voucher_usecase
from application.inventory_engine.use_cases import create_item as create_item_usecase
from application.inventory_engine.use_cases import create_outbound_voucher as create_outbound_voucher_usecase
from application.inventory_engine.use_cases import create_stock_count as create_stock_count_usecase
from application.inventory_engine.use_cases import create_supplier as create_supplier_usecase
from application.inventory_engine.use_cases import list_balances as list_balances_usecase
from application.inventory_engine.use_cases import list_inbound_vouchers as list_inbound_vouchers_usecase
from application.inventory_engine.use_cases import list_items as list_items_usecase
from application.inventory_engine.use_cases import list_ledger as list_ledger_usecase
from application.inventory_engine.use_cases import list_outbound_reasons as list_outbound_reasons_usecase
from application.inventory_engine.use_cases import list_outbound_vouchers as list_outbound_vouchers_usecase
from application.inventory_engine.use_cases import list_stock_counts as list_stock_counts_usecase
from application.inventory_engine.use_cases import list_suppliers as list_suppliers_usecase
from application.inventory_engine.use_cases import settle_stock_count as settle_stock_count_usecase
from application.inventory_engine.use_cases import update_item as update_item_usecase
from application.inventory_engine.use_cases import update_supplier as update_supplier_usecase
from application.inventory_engine.use_cases import warehouse_dashboard as warehouse_dashboard_usecase

router = APIRouter(
    prefix="/manager/warehouse",
    tags=["manager-warehouse"],
    dependencies=[Depends(require_route_capability)],
)
DEFAULT_WAREHOUSE_PAGE_SIZE = 50
MAX_WAREHOUSE_PAGE_SIZE = 200


@router.get("/dashboard", response_model=WarehouseDashboardOut)
def get_warehouse_dashboard(
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=warehouse_dashboard_usecase.execute,
        data=warehouse_dashboard_usecase.Input(),
        repo=build_warehouse_repository(db),
        db=db,
    )
    return output.result


@router.get("/suppliers", response_model=list[WarehouseSupplierOut])
def get_warehouse_suppliers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_WAREHOUSE_PAGE_SIZE, ge=1, le=MAX_WAREHOUSE_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
 ) -> list[dict[str, object]]:
    output = run_use_case(
        execute=list_suppliers_usecase.execute,
        data=list_suppliers_usecase.Input(page=page, page_size=page_size),
        repo=build_warehouse_repository(db),
        db=db,
    )
    return output.result


@router.post("/suppliers", response_model=WarehouseSupplierOut, status_code=201)
def post_warehouse_supplier(
    payload: WarehouseSupplierCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=create_supplier_usecase.execute,
        data=create_supplier_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_warehouse_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.put("/suppliers/{supplier_id}", response_model=WarehouseSupplierOut)
def put_warehouse_supplier(
    supplier_id: int,
    payload: WarehouseSupplierUpdate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=update_supplier_usecase.execute,
        data=update_supplier_usecase.Input(
            actor_id=current_user.id,
            supplier_id=supplier_id,
            payload=payload,
        ),
        repo=build_warehouse_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/items", response_model=list[WarehouseItemOut])
def get_warehouse_items(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_WAREHOUSE_PAGE_SIZE, ge=1, le=MAX_WAREHOUSE_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[WarehouseItem]:
    output = run_use_case(
        execute=list_items_usecase.execute,
        data=list_items_usecase.Input(page=page, page_size=page_size),
        repo=build_warehouse_repository(db),
        db=db,
    )
    return output.result


@router.post("/items", response_model=WarehouseItemOut, status_code=201)
def post_warehouse_item(
    payload: WarehouseItemCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> WarehouseItem:
    output = run_use_case(
        execute=create_item_usecase.execute,
        data=create_item_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_warehouse_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.put("/items/{item_id}", response_model=WarehouseItemOut)
def put_warehouse_item(
    item_id: int,
    payload: WarehouseItemUpdate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> WarehouseItem:
    output = run_use_case(
        execute=update_item_usecase.execute,
        data=update_item_usecase.Input(
            actor_id=current_user.id,
            item_id=item_id,
            payload=payload,
        ),
        repo=build_warehouse_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/balances", response_model=list[WarehouseStockBalanceOut])
def get_warehouse_balances(
    only_low: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_WAREHOUSE_PAGE_SIZE, ge=1, le=MAX_WAREHOUSE_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    output = run_use_case(
        execute=list_balances_usecase.execute,
        data=list_balances_usecase.Input(
            only_low=only_low,
            page=page,
            page_size=page_size,
        ),
        repo=build_warehouse_repository(db),
        db=db,
    )
    return output.result


@router.get("/ledger", response_model=list[WarehouseLedgerOut])
def get_warehouse_ledger(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_WAREHOUSE_PAGE_SIZE, ge=1, le=1000),
    item_id: int | None = Query(default=None),
    movement_kind: str | None = Query(default=None),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    output = run_use_case(
        execute=list_ledger_usecase.execute,
        data=list_ledger_usecase.Input(
            page=page,
            page_size=page_size,
            item_id=item_id,
            movement_kind=movement_kind,
        ),
        repo=build_warehouse_repository(db),
        db=db,
    )
    return output.result


@router.get("/inbound-vouchers", response_model=list[WarehouseInboundVoucherOut])
def get_inbound_vouchers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_WAREHOUSE_PAGE_SIZE, ge=1, le=500),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    output = run_use_case(
        execute=list_inbound_vouchers_usecase.execute,
        data=list_inbound_vouchers_usecase.Input(page=page, page_size=page_size),
        repo=build_warehouse_repository(db),
        db=db,
    )
    return output.result


@router.post("/inbound-vouchers", response_model=WarehouseInboundVoucherOut, status_code=201)
def post_inbound_voucher(
    payload: WarehouseInboundVoucherCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=create_inbound_voucher_usecase.execute,
        data=create_inbound_voucher_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_warehouse_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/outbound-vouchers", response_model=list[WarehouseOutboundVoucherOut])
def get_outbound_vouchers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_WAREHOUSE_PAGE_SIZE, ge=1, le=500),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    output = run_use_case(
        execute=list_outbound_vouchers_usecase.execute,
        data=list_outbound_vouchers_usecase.Input(page=page, page_size=page_size),
        repo=build_warehouse_repository(db),
        db=db,
    )
    return output.result


@router.get("/outbound-reasons", response_model=list[WarehouseOutboundReasonOut])
def get_outbound_reasons(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_WAREHOUSE_PAGE_SIZE, ge=1, le=MAX_WAREHOUSE_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[dict[str, str]]:
    output = run_use_case(
        execute=list_outbound_reasons_usecase.execute,
        data=list_outbound_reasons_usecase.Input(page=page, page_size=page_size),
        repo=build_warehouse_repository(db),
        db=db,
    )
    return output.result


@router.post("/outbound-vouchers", response_model=WarehouseOutboundVoucherOut, status_code=201)
def post_outbound_voucher(
    payload: WarehouseOutboundVoucherCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=create_outbound_voucher_usecase.execute,
        data=create_outbound_voucher_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_warehouse_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/stock-counts", response_model=list[WarehouseStockCountOut])
def get_stock_counts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_WAREHOUSE_PAGE_SIZE, ge=1, le=500),
    _: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    output = run_use_case(
        execute=list_stock_counts_usecase.execute,
        data=list_stock_counts_usecase.Input(page=page, page_size=page_size),
        repo=build_warehouse_repository(db),
        db=db,
    )
    return output.result


@router.post("/stock-counts", response_model=WarehouseStockCountOut, status_code=201)
def post_stock_count(
    payload: WarehouseStockCountCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=create_stock_count_usecase.execute,
        data=create_stock_count_usecase.Input(actor_id=current_user.id, payload=payload),
        repo=build_warehouse_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.post("/stock-counts/{count_id}/settle", response_model=WarehouseStockCountOut)
def post_settle_stock_count(
    count_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    output = run_use_case(
        execute=settle_stock_count_usecase.execute,
        data=settle_stock_count_usecase.Input(actor_id=current_user.id, count_id=count_id),
        repo=build_warehouse_repository(db),
        db=db,
        request=request,
    )
    return output.result
