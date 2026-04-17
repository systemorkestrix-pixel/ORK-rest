from dataclasses import dataclass
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, status

from .config import load_settings
from .security import decode_access_token

SETTINGS = load_settings()
SAFE_HTTP_METHODS = {"GET", "HEAD", "OPTIONS"}
MasterAuthorizationHeader = Annotated[str | None, Header(alias="Authorization")]
MasterAccessTokenCookie = Annotated[str | None, Cookie(alias="master_access_token")]
MasterCsrfHeader = Annotated[str | None, Header(alias="X-Master-CSRF-Token")]
MasterCsrfCookie = Annotated[str | None, Cookie(alias="master_csrf_token")]


@dataclass(frozen=True)
class MasterIdentity:
    username: str
    display_name: str
    role_label: str = "مشرف اللوحة الأم"


def get_current_master_identity(
    request: Request,
    authorization: MasterAuthorizationHeader = None,
    access_token_cookie: MasterAccessTokenCookie = None,
    csrf_header: MasterCsrfHeader = None,
    csrf_cookie: MasterCsrfCookie = None,
) -> MasterIdentity:
    token: str | None = None
    using_cookie_auth = False

    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
    elif access_token_cookie:
        token = access_token_cookie.strip()
        using_cookie_auth = True

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="جلسة اللوحة الأم غير موجودة.")

    if using_cookie_auth and request.method.upper() not in SAFE_HTTP_METHODS:
        if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="فشل التحقق الأمني لجلسة اللوحة الأم.")

    try:
        payload = decode_access_token(token)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="جلسة اللوحة الأم غير صالحة.") from error

    token_role = str(payload.get("role") or "")
    token_username = str(payload.get("username") or "")
    if token_role != "master" or token_username.lower() != SETTINGS.master_admin_username.lower():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="جلسة اللوحة الأم لا تطابق هوية المنصة.")

    return MasterIdentity(
        username=SETTINGS.master_admin_username,
        display_name=SETTINGS.master_admin_display_name,
    )


MasterCurrentUser = Annotated[MasterIdentity, Depends(get_current_master_identity)]
