import secrets

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from application.master_engine.domain.read_model import (
    authenticate_master,
    get_master_overview,
    list_master_addons,
    list_master_clients,
    list_master_tenants,
)
from application.master_engine.domain.registry import (
    create_master_tenant,
    delete_master_tenant,
    reset_master_tenant_manager_password,
    set_master_tenant_addon_paused_state,
    toggle_master_tenant_suspension,
    update_master_tenant,
)

from ..config import load_settings
from ..dependencies import get_db
from ..master_dependencies import MasterCurrentUser
from ..schemas import (
    MasterAddonOut,
    MasterClientOut,
    MasterIdentityOut,
    MasterLoginInput,
    MasterOverviewOut,
    MasterSessionOut,
    MasterTenantAccessOut,
    MasterTenantCreateInput,
    MasterTenantCreateResultOut,
    MasterTenantOut,
    MasterTenantUpdateInput,
)
from ..security import ACCESS_TOKEN_TTL_MINUTES, create_access_token

SETTINGS = load_settings()
COOKIE_SECURE = SETTINGS.is_production
COOKIE_SAMESITE = "none" if SETTINGS.is_production else "lax"
COOKIE_DOMAIN = SETTINGS.cookie_domain
MASTER_ACCESS_COOKIE_NAME = "master_access_token"
MASTER_CSRF_COOKIE_NAME = "master_csrf_token"

router = APIRouter(prefix="/master", tags=["master"])
auth_router = APIRouter(prefix="/master-auth", tags=["master-auth"])


def _set_master_cookies(response: Response, *, access_token: str) -> None:
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        key=MASTER_ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        max_age=ACCESS_TOKEN_TTL_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key=MASTER_CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        max_age=ACCESS_TOKEN_TTL_MINUTES * 60,
        path="/",
    )


def _clear_master_cookies(response: Response) -> None:
    response.delete_cookie(MASTER_ACCESS_COOKIE_NAME, path="/", domain=COOKIE_DOMAIN)
    response.delete_cookie(MASTER_CSRF_COOKIE_NAME, path="/", domain=COOKIE_DOMAIN)


def _current_identity_out() -> MasterIdentityOut:
    return MasterIdentityOut(
        username=SETTINGS.master_admin_username,
        display_name=SETTINGS.master_admin_display_name,
        role_label="مشرف اللوحة الأم",
    )


@auth_router.post("/login", response_model=MasterSessionOut)
def master_login(payload: MasterLoginInput, response: Response) -> MasterSessionOut:
    if not authenticate_master(payload.username, payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="بيانات دخول اللوحة الأم غير صحيحة.")

    access_token = create_access_token(user_id=0, role="master", username=SETTINGS.master_admin_username)
    _set_master_cookies(response, access_token=access_token)
    return MasterSessionOut(identity=_current_identity_out())


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def master_logout(response: Response, _: MasterCurrentUser) -> Response:
    _clear_master_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@auth_router.get("/session", response_model=MasterSessionOut)
def master_session(_: MasterCurrentUser) -> MasterSessionOut:
    return MasterSessionOut(identity=_current_identity_out())


@router.get("/overview", response_model=MasterOverviewOut)
def master_overview(_: MasterCurrentUser, db: Session = Depends(get_db)) -> dict[str, object]:
    return get_master_overview(db)


@router.get("/clients", response_model=list[MasterClientOut])
def master_clients(_: MasterCurrentUser, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    return list_master_clients(db)


@router.get("/tenants", response_model=list[MasterTenantOut])
def master_tenants(_: MasterCurrentUser, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    return list_master_tenants(db)


@router.get("/addons", response_model=list[MasterAddonOut])
def master_addons(_: MasterCurrentUser, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    return list_master_addons(db)


@router.get("/plans", response_model=list[MasterAddonOut], include_in_schema=False)
def master_plans_legacy(_: MasterCurrentUser, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    return list_master_addons(db)


@router.post("/tenants", response_model=MasterTenantCreateResultOut, status_code=status.HTTP_201_CREATED)
def master_create_tenant(
    payload: MasterTenantCreateInput,
    _: MasterCurrentUser,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return create_master_tenant(
        db,
        client_mode=payload.client_mode,
        existing_client_id=payload.existing_client_id,
        client_owner_name=payload.client_owner_name,
        client_brand_name=payload.client_brand_name,
        client_phone=payload.client_phone,
        client_city=payload.client_city,
        tenant_brand_name=payload.tenant_brand_name,
        tenant_code=payload.tenant_code,
        database_name=payload.database_name,
    )


@router.put("/tenants/{tenant_id}", response_model=MasterTenantOut)
def master_update_tenant(
    tenant_id: int,
    payload: MasterTenantUpdateInput,
    _: MasterCurrentUser,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return update_master_tenant(
        db,
        tenant_id=tenant_id,
        client_owner_name=payload.client_owner_name,
        client_brand_name=payload.client_brand_name,
        client_phone=payload.client_phone,
        client_city=payload.client_city,
        brand_name=payload.brand_name,
        activation_stage_id=payload.activation_stage_id,
    )


@router.post("/tenants/{tenant_id}/toggle-suspension", response_model=MasterTenantOut)
def master_toggle_tenant_suspension(
    tenant_id: int,
    _: MasterCurrentUser,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return toggle_master_tenant_suspension(db, tenant_id=tenant_id)


@router.post("/tenants/{tenant_id}/regenerate-manager-password", response_model=MasterTenantAccessOut)
def master_regenerate_tenant_manager_password(
    tenant_id: int,
    _: MasterCurrentUser,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return reset_master_tenant_manager_password(db, tenant_id=tenant_id)


@router.post("/tenants/{tenant_id}/addons/{addon_id}/pause", response_model=MasterTenantOut)
def master_pause_tenant_addon(
    tenant_id: int,
    addon_id: str,
    _: MasterCurrentUser,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return set_master_tenant_addon_paused_state(db, tenant_id=tenant_id, addon_id=addon_id, paused=True)


@router.post("/tenants/{tenant_id}/addons/{addon_id}/resume", response_model=MasterTenantOut)
def master_resume_tenant_addon(
    tenant_id: int,
    addon_id: str,
    _: MasterCurrentUser,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return set_master_tenant_addon_paused_state(db, tenant_id=tenant_id, addon_id=addon_id, paused=False)


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def master_delete_tenant(
    tenant_id: int,
    _: MasterCurrentUser,
    db: Session = Depends(get_db),
) -> Response:
    delete_master_tenant(db, tenant_id=tenant_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
