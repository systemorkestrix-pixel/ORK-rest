from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_roles, require_route_capability
from ..enums import UserRole
from ..models import Order, User
from ..schemas import KitchenOrdersPageOut, KitchenRuntimeSettingsOut, OrderOut
from ..usecase_factory import build_orders_repository, run_use_case
from application.kitchen_engine.use_cases import get_kitchen_runtime_settings as get_kitchen_runtime_settings_usecase
from application.kitchen_engine.use_cases import list_kitchen_orders as list_kitchen_orders_usecase
from application.kitchen_engine.use_cases import list_kitchen_orders_paged as list_kitchen_orders_paged_usecase
from application.kitchen_engine.use_cases import mark_order_ready as mark_order_ready_usecase
from application.kitchen_engine.use_cases import start_preparation as start_preparation_usecase

router = APIRouter(
    prefix="/kitchen",
    tags=["kitchen"],
    dependencies=[Depends(require_route_capability)],
)
DEFAULT_KITCHEN_PAGE_SIZE = 24
MAX_KITCHEN_PAGE_SIZE = 100


@router.get("/orders", response_model=list[OrderOut])
def kitchen_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_KITCHEN_PAGE_SIZE, ge=1, le=MAX_KITCHEN_PAGE_SIZE),
    _: User = Depends(require_roles(UserRole.KITCHEN)),
    db: Session = Depends(get_db),
) -> list[Order]:
    output = run_use_case(
        execute=list_kitchen_orders_usecase.execute,
        data=list_kitchen_orders_usecase.Input(
            page=page,
            page_size=page_size,
            sort_direction="asc",
        ),
        repo=build_orders_repository(db),
        db=db,
    )
    return output.result


@router.get("/orders/paged", response_model=KitchenOrdersPageOut)
def kitchen_orders_paged(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    search: str | None = Query(default=None),
    scope: Literal["active", "history"] = "active",
    sort_by: Literal["created_at", "total", "status", "id"] = "created_at",
    sort_direction: Literal["asc", "desc"] = "asc",
    _: User = Depends(require_roles(UserRole.KITCHEN)),
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
        ),
        repo=build_orders_repository(db),
        db=db,
    )
    return output.result


@router.get("/runtime-settings", response_model=KitchenRuntimeSettingsOut)
def kitchen_runtime_settings(
    _: User = Depends(require_roles(UserRole.KITCHEN)),
    db: Session = Depends(get_db),
) -> dict[str, int | str]:
    output = run_use_case(
        execute=get_kitchen_runtime_settings_usecase.execute,
        data=get_kitchen_runtime_settings_usecase.Input(),
        repo=build_orders_repository(db),
        db=db,
    )
    return output.result


@router.post("/orders/{order_id}/start", response_model=OrderOut)
def start_preparation(
    order_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.KITCHEN)),
    db: Session = Depends(get_db),
) -> Order:
    output = run_use_case(
        execute=start_preparation_usecase.execute,
        data=start_preparation_usecase.Input(
            actor_id=current_user.id,
            order_id=order_id,
        ),
        repo=build_orders_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.post("/orders/{order_id}/ready", response_model=OrderOut)
def mark_ready(
    order_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.KITCHEN)),
    db: Session = Depends(get_db),
) -> Order:
    output = run_use_case(
        execute=mark_order_ready_usecase.execute,
        data=mark_order_ready_usecase.Input(
            actor_id=current_user.id,
            order_id=order_id,
        ),
        repo=build_orders_repository(db),
        db=db,
        request=request,
    )
    return output.result
