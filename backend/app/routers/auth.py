import secrets
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import load_settings
from ..dependencies import get_current_user, get_db
from ..models import User
from ..schemas import AuthSessionOut, LoginInput, RefreshInput, UserOut
from ..security import ACCESS_TOKEN_TTL_MINUTES, REFRESH_TOKEN_TTL_DAYS
from ..tenant_runtime import (
    create_runtime_session,
    infer_tenant_database_name_from_session,
    resolve_tenant_database_name_for_code,
    resolve_tenant_database_name_for_login,
)
from ..usecase_factory import build_core_repository, run_use_case
from application.core_engine.use_cases import authenticate_user as authenticate_user_usecase
from application.core_engine.use_cases import record_security_event as record_security_event_usecase
from application.core_engine.use_cases import refresh_session as refresh_session_usecase
from application.core_engine.use_cases import revoke_session as revoke_session_usecase

router = APIRouter(prefix="/auth", tags=["auth"])
SETTINGS = load_settings()
COOKIE_SECURE = SETTINGS.is_production
COOKIE_SAMESITE = "none" if SETTINGS.is_production else "lax"
COOKIE_DOMAIN = SETTINGS.cookie_domain
ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"
CSRF_COOKIE_NAME = "csrf_token"
TENANT_DATABASE_COOKIE_NAME = "tenant_database"

RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)]
CsrfCookie = Annotated[str | None, Cookie(alias=CSRF_COOKIE_NAME)]
TenantCodeHeader = Annotated[str | None, Header(alias="X-Tenant-Code")]


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()[:64]
    if request.client and request.client.host:
        return str(request.client.host)[:64]
    return None


def _user_agent(request: Request) -> str | None:
    raw = request.headers.get("user-agent")
    if not raw:
        return None
    return raw.strip()[:255]


def _set_auth_cookies(response: Response, *, access_token: str, refresh_token: str, tenant_database: str | None = None) -> None:
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        max_age=ACCESS_TOKEN_TTL_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        max_age=REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60,
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        max_age=REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60,
        path="/",
    )
    if tenant_database:
        response.set_cookie(
            key=TENANT_DATABASE_COOKIE_NAME,
            value=tenant_database,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            domain=COOKIE_DOMAIN,
            max_age=REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60,
            path="/",
        )
    else:
        response.delete_cookie(TENANT_DATABASE_COOKIE_NAME, path="/", domain=COOKIE_DOMAIN)


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/", domain=COOKIE_DOMAIN)
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/", domain=COOKIE_DOMAIN)
    response.delete_cookie(CSRF_COOKIE_NAME, path="/", domain=COOKIE_DOMAIN)
    response.delete_cookie(TENANT_DATABASE_COOKIE_NAME, path="/", domain=COOKIE_DOMAIN)


def _validate_csrf(request: Request, *, csrf_cookie: str | None) -> None:
    csrf_header = request.headers.get("x-csrf-token")
    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")


@router.post("/login", response_model=AuthSessionOut)
def login(
    payload: LoginInput,
    request: Request,
    response: Response,
    tenant_code_header: TenantCodeHeader = None,
) -> AuthSessionOut:
    tenant_db = None
    db = None
    ip_address = _client_ip(request)
    user_agent = _user_agent(request)
    try:
        tenant_db = resolve_tenant_database_name_for_code(tenant_code=tenant_code_header)
        if tenant_db is None:
            tenant_db = resolve_tenant_database_name_for_login(username=payload.username)
        db = create_runtime_session(tenant_db)
        output = run_use_case(
            execute=authenticate_user_usecase.execute,
            data=authenticate_user_usecase.Input(payload=payload),
            repo=build_core_repository(db),
            db=db,
            request=request,
        )
        user = output.user
        access_token = output.access_token
        refresh_token = output.refresh_token
        _set_auth_cookies(
            response,
            access_token=access_token,
            refresh_token=refresh_token,
            tenant_database=infer_tenant_database_name_from_session(db),
        )
        run_use_case(
            execute=record_security_event_usecase.execute,
            data=record_security_event_usecase.Input(
                event_type="login_success",
                success=True,
                severity="info",
                username=user.username,
                role=user.role,
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                detail="Successful login.",
            ),
            repo=build_core_repository(db),
            db=db,
        )
        return AuthSessionOut(user=user)
    except HTTPException as error:
        log_db = db if db is not None else create_runtime_session(tenant_db)
        run_use_case(
            execute=record_security_event_usecase.execute,
            data=record_security_event_usecase.Input(
                event_type="login_failed",
                success=False,
                severity="warning",
                username=payload.username,
                role=payload.role.value,
                ip_address=ip_address,
                user_agent=user_agent,
                detail=str(error.detail),
            ),
            repo=build_core_repository(log_db),
            db=log_db,
        )
        if db is None and log_db is not None:
            log_db.close()
        raise
    except Exception:
        log_db = db if db is not None else create_runtime_session(tenant_db)
        run_use_case(
            execute=record_security_event_usecase.execute,
            data=record_security_event_usecase.Input(
                event_type="login_failed",
                success=False,
                severity="critical",
                username=payload.username,
                role=payload.role.value,
                ip_address=ip_address,
                user_agent=user_agent,
                detail="Unexpected login failure.",
            ),
            repo=build_core_repository(log_db),
            db=log_db,
        )
        if db is None and log_db is not None:
            log_db.close()
        raise
    finally:
        if db is not None:
            db.close()


@router.post("/refresh", response_model=AuthSessionOut)
def refresh(
    request: Request,
    response: Response,
    payload: RefreshInput | None = None,
    refresh_cookie: RefreshCookie = None,
    csrf_cookie: CsrfCookie = None,
    db: Session = Depends(get_db),
) -> AuthSessionOut:
    ip_address = _client_ip(request)
    user_agent = _user_agent(request)
    token = payload.refresh_token if payload is not None else None
    if not token and refresh_cookie:
        _validate_csrf(request, csrf_cookie=csrf_cookie)
        token = refresh_cookie
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is required")

    try:
        output = run_use_case(
            execute=refresh_session_usecase.execute,
            data=refresh_session_usecase.Input(refresh_token=token),
            repo=build_core_repository(db),
            db=db,
            request=request,
        )
        user = output.user
        access_token = output.access_token
        refresh_token = output.refresh_token
        _set_auth_cookies(
            response,
            access_token=access_token,
            refresh_token=refresh_token,
            tenant_database=infer_tenant_database_name_from_session(db),
        )
        run_use_case(
            execute=record_security_event_usecase.execute,
            data=record_security_event_usecase.Input(
                event_type="refresh_success",
                success=True,
                severity="info",
                username=user.username,
                role=user.role,
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                detail="Session refresh succeeded.",
            ),
            repo=build_core_repository(db),
            db=db,
        )
        return AuthSessionOut(user=user)
    except HTTPException as error:
        run_use_case(
            execute=record_security_event_usecase.execute,
            data=record_security_event_usecase.Input(
                event_type="refresh_failed",
                success=False,
                severity="warning",
                ip_address=ip_address,
                user_agent=user_agent,
                detail=str(error.detail),
            ),
            repo=build_core_repository(db),
            db=db,
        )
        raise
    except Exception:
        run_use_case(
            execute=record_security_event_usecase.execute,
            data=record_security_event_usecase.Input(
                event_type="refresh_failed",
                success=False,
                severity="critical",
                ip_address=ip_address,
                user_agent=user_agent,
                detail="Unexpected refresh failure.",
            ),
            repo=build_core_repository(db),
            db=db,
        )
        raise


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    payload: RefreshInput | None = None,
    refresh_cookie: RefreshCookie = None,
    csrf_cookie: CsrfCookie = None,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    ip_address = _client_ip(request)
    user_agent = _user_agent(request)
    token = payload.refresh_token if payload is not None else None
    if not token and refresh_cookie:
        _validate_csrf(request, csrf_cookie=csrf_cookie)
        token = refresh_cookie

    user_id = None
    revoked = False
    if token:
        output = run_use_case(
            execute=revoke_session_usecase.execute,
            data=revoke_session_usecase.Input(refresh_token=token),
            repo=build_core_repository(db),
            db=db,
            request=request,
        )
        user_id, revoked = output.user_id, output.revoked
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none() if user_id else None

    _clear_auth_cookies(response)
    run_use_case(
        execute=record_security_event_usecase.execute,
        data=record_security_event_usecase.Input(
            event_type="logout",
            success=bool(revoked),
            severity="info" if revoked else "warning",
            username=user.username if user else None,
            role=user.role if user else None,
            user_id=user.id if user else None,
            ip_address=ip_address,
            user_agent=user_agent,
            detail="Session terminated." if revoked else "Session token missing/invalid during logout.",
        ),
        repo=build_core_repository(db),
        db=db,
    )
    return {"status": "ok"}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
