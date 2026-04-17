from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_roles, require_route_capability
from ..enums import UserRole
from ..models import DeliveryAssignment, Order, User
from ..schemas import (
    DeliveryAssignmentOut,
    DeliveryDispatchAssignDriverInput,
    DeliveryDispatchOut,
    DeliveryDriverOut,
    DeliveryHistoryOut,
    OrderOut,
    OrderTransitionInput,
)
from ..usecase_factory import build_delivery_repository, run_use_case
from application.delivery_engine.use_cases import assign_delivery_dispatch_to_driver as assign_delivery_dispatch_to_driver_usecase
from application.delivery_engine.use_cases import assign_driver as assign_driver_usecase
from application.delivery_engine.use_cases import list_delivery_dispatches as list_delivery_dispatches_usecase
from application.delivery_engine.use_cases import complete_delivery as complete_delivery_usecase
from application.delivery_engine.use_cases import depart_delivery as depart_delivery_usecase
from application.delivery_engine.use_cases import fail_delivery as fail_delivery_usecase
from application.delivery_engine.use_cases import list_delivery_assignments as list_delivery_assignments_usecase
from application.delivery_engine.use_cases import list_provider_delivery_drivers as list_provider_delivery_drivers_usecase
from application.delivery_engine.use_cases import list_delivery_history as list_delivery_history_usecase
from application.delivery_engine.use_cases import list_delivery_orders as list_delivery_orders_usecase
from application.delivery_engine.use_cases import reject_delivery_dispatch as reject_delivery_dispatch_usecase

router = APIRouter(
    prefix="/delivery",
    tags=["delivery"],
    dependencies=[Depends(require_route_capability)],
)
DEFAULT_DELIVERY_PAGE_SIZE = 30
MAX_DELIVERY_PAGE_SIZE = 500


@router.get("/assignments", response_model=list[DeliveryAssignmentOut])
def my_assignments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_DELIVERY_PAGE_SIZE, ge=1, le=MAX_DELIVERY_PAGE_SIZE),
    current_user: User = Depends(require_roles(UserRole.DELIVERY, UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[DeliveryAssignment]:
    output = run_use_case(
        execute=list_delivery_assignments_usecase.execute,
        data=list_delivery_assignments_usecase.Input(
            actor_id=current_user.id,
            actor_role=current_user.role,
            page=page,
            page_size=page_size,
        ),
        repo=build_delivery_repository(db),
        db=db,
    )
    return output.result


@router.get("/dispatches", response_model=list[DeliveryDispatchOut])
def my_dispatches(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_DELIVERY_PAGE_SIZE, ge=1, le=MAX_DELIVERY_PAGE_SIZE),
    current_user: User = Depends(require_roles(UserRole.DELIVERY, UserRole.MANAGER)),
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


@router.get("/team/drivers", response_model=list[DeliveryDriverOut])
def provider_team_drivers(
    current_user: User = Depends(require_roles(UserRole.DELIVERY)),
    db: Session = Depends(get_db),
) -> list[DeliveryDriverOut]:
    output = run_use_case(
        execute=list_provider_delivery_drivers_usecase.execute,
        data=list_provider_delivery_drivers_usecase.Input(actor_id=current_user.id),
        repo=build_delivery_repository(db),
        db=db,
    )
    return output.result


@router.get("/orders", response_model=list[OrderOut])
def delivery_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_DELIVERY_PAGE_SIZE, ge=1, le=MAX_DELIVERY_PAGE_SIZE),
    current_user: User = Depends(require_roles(UserRole.DELIVERY, UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> list[Order]:
    output = run_use_case(
        execute=list_delivery_orders_usecase.execute,
        data=list_delivery_orders_usecase.Input(
            actor_id=current_user.id,
            actor_role=current_user.role,
            page=page,
            page_size=page_size,
        ),
        repo=build_delivery_repository(db),
        db=db,
    )
    return output.result


@router.post("/dispatches/{dispatch_id}/assign-driver", response_model=DeliveryDispatchOut)
def assign_dispatch_to_driver(
    dispatch_id: int,
    payload: DeliveryDispatchAssignDriverInput,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.DELIVERY)),
    db: Session = Depends(get_db),
) -> DeliveryDispatchOut:
    output = run_use_case(
        execute=assign_delivery_dispatch_to_driver_usecase.execute,
        data=assign_delivery_dispatch_to_driver_usecase.Input(
            actor_id=current_user.id,
            dispatch_id=dispatch_id,
            driver_id=payload.driver_id,
        ),
        repo=build_delivery_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.post("/orders/{order_id}/claim", response_model=DeliveryAssignmentOut)
def claim_order(
    order_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.DELIVERY)),
    db: Session = Depends(get_db),
) -> DeliveryAssignment:
    output = run_use_case(
        execute=assign_driver_usecase.execute,
        data=assign_driver_usecase.Input(actor_id=current_user.id, order_id=order_id),
        repo=build_delivery_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.post("/dispatches/{dispatch_id}/reject", response_model=DeliveryDispatchOut)
def reject_dispatch(
    dispatch_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.DELIVERY)),
    db: Session = Depends(get_db),
) -> DeliveryDispatchOut:
    output = run_use_case(
        execute=reject_delivery_dispatch_usecase.execute,
        data=reject_delivery_dispatch_usecase.Input(actor_id=current_user.id, dispatch_id=dispatch_id),
        repo=build_delivery_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.post("/orders/{order_id}/depart", response_model=OrderOut)
def depart_order(
    order_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.DELIVERY)),
    db: Session = Depends(get_db),
) -> Order:
    output = run_use_case(
        execute=depart_delivery_usecase.execute,
        data=depart_delivery_usecase.Input(actor_id=current_user.id, order_id=order_id),
        repo=build_delivery_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.post("/orders/{order_id}/delivered", response_model=OrderOut)
def mark_delivered(
    order_id: int,
    payload: OrderTransitionInput,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.DELIVERY)),
    db: Session = Depends(get_db),
) -> Order:
    output = run_use_case(
        execute=complete_delivery_usecase.execute,
        data=complete_delivery_usecase.Input(
            actor_id=current_user.id,
            order_id=order_id,
            payload=payload,
        ),
        repo=build_delivery_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.post("/orders/{order_id}/failed", response_model=OrderOut)
def mark_failed(
    order_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.DELIVERY)),
    db: Session = Depends(get_db),
) -> Order:
    output = run_use_case(
        execute=fail_delivery_usecase.execute,
        data=fail_delivery_usecase.Input(actor_id=current_user.id, order_id=order_id),
        repo=build_delivery_repository(db),
        db=db,
        request=request,
    )
    return output.result


@router.get("/history", response_model=list[DeliveryHistoryOut])
def delivery_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_DELIVERY_PAGE_SIZE, ge=1, le=MAX_DELIVERY_PAGE_SIZE),
    current_user: User = Depends(require_roles(UserRole.DELIVERY)),
    db: Session = Depends(get_db),
) -> list[DeliveryHistoryOut]:
    output = run_use_case(
        execute=list_delivery_history_usecase.execute,
        data=list_delivery_history_usecase.Input(
            actor_id=current_user.id,
            page=page,
            page_size=page_size,
        ),
        repo=build_delivery_repository(db),
        db=db,
    )
    return output.result
