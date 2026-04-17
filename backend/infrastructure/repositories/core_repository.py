from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.schemas import UserPermissionsOut
from app.orchestration.service_bridge import (
    app_create_system_backup,
    app_create_user,
    app_get_telegram_bot_health,
    app_get_storefront_settings,
    app_get_telegram_bot_settings,
    app_delete_user_permanently,
    app_get_system_context_settings,
    app_get_user_permissions_profile,
    app_list_operational_settings,
    app_list_permissions_catalog,
    app_list_system_backups,
    app_list_user_refresh_sessions,
    app_login_user,
    app_record_security_event,
    app_refresh_user_tokens,
    app_restore_system_backup,
    app_revoke_refresh_token,
    app_revoke_user_refresh_sessions,
    app_update_operational_setting,
    app_update_storefront_settings,
    app_update_telegram_bot_settings,
    app_update_system_context_settings,
    app_update_user,
    app_update_user_permissions_profile,
)
from app.orchestration.service_bridge import get_system_order_actor_prefix


class CoreRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_user(
        self,
        *,
        name: str,
        username: str,
        password: str,
        role: str,
        active: bool,
        delivery_phone: str | None,
        delivery_vehicle: str | None,
        actor_id: int,
    ) -> User:
        return app_create_user(
            self._db,
            name=name,
            username=username,
            password=password,
            role=role,
            active=active,
            delivery_phone=delivery_phone,
            delivery_vehicle=delivery_vehicle,
            actor_id=actor_id,
        )

    def update_user(
        self,
        *,
        user_id: int,
        name: str,
        role: str,
        active: bool,
        password: str | None,
        delivery_phone: str | None,
        delivery_vehicle: str | None,
        actor_id: int,
        allow_manager_self_update: bool = False,
    ) -> User:
        return app_update_user(
            self._db,
            user_id=user_id,
            name=name,
            role=role,
            active=active,
            password=password,
            delivery_phone=delivery_phone,
            delivery_vehicle=delivery_vehicle,
            actor_id=actor_id,
            allow_manager_self_update=allow_manager_self_update,
        )

    def delete_user_permanently(self, *, user_id: int, actor_id: int) -> None:
        app_delete_user_permanently(self._db, user_id=user_id, actor_id=actor_id)

    def update_user_permissions(
        self,
        *,
        user_id: int,
        allow: list[str] | None,
        deny: list[str] | None,
        actor_id: int,
    ) -> UserPermissionsOut:
        return app_update_user_permissions_profile(
            self._db,
            user_id=user_id,
            allow=allow,
            deny=deny,
            actor_id=actor_id,
        )

    def authenticate(self, *, username: str, password: str, role: str) -> tuple[User, str, str]:
        return app_login_user(self._db, username=username, password=password, role=role)

    def refresh(self, *, refresh_token: str) -> tuple[User, str, str]:
        return app_refresh_user_tokens(self._db, refresh_token=refresh_token)

    def revoke_refresh_token(self, *, refresh_token: str) -> tuple[int | None, bool]:
        return app_revoke_refresh_token(self._db, refresh_token=refresh_token)

    def revoke_user_refresh_sessions(self, *, user_id: int, actor_id: int) -> int:
        return app_revoke_user_refresh_sessions(self._db, user_id=user_id, actor_id=actor_id)

    def update_operational_setting(
        self,
        *,
        key: str,
        value: str,
        actor_id: int,
    ) -> dict[str, object]:
        return app_update_operational_setting(
            self._db,
            key=key,
            value=value,
            actor_id=actor_id,
        )

    def create_system_backup(self, *, actor_id: int) -> dict[str, object]:
        return app_create_system_backup(self._db, actor_id=actor_id)

    def restore_system_backup(
        self,
        *,
        filename: str,
        confirm_phrase: str,
        actor_id: int,
    ) -> dict[str, object]:
        return app_restore_system_backup(
            self._db,
            filename=filename,
            confirm_phrase=confirm_phrase,
            actor_id=actor_id,
        )

    def list_users(self, *, offset: int, limit: int) -> list[User]:
        prefix = get_system_order_actor_prefix()
        return (
            self._db.execute(
                select(User)
                .where(~User.username.like(f"{prefix}%"))
                .order_by(User.id.asc())
                .offset(offset)
                .limit(limit)
            )
            .scalars()
            .all()
        )

    def list_permissions_catalog(self, *, role: str | None) -> list[dict[str, object]]:
        return app_list_permissions_catalog(role=role)

    def get_user_permissions(self, *, user_id: int) -> dict[str, object]:
        return app_get_user_permissions_profile(self._db, user_id=user_id)

    def list_account_sessions(
        self,
        *,
        user_id: int,
        offset: int,
        limit: int,
    ) -> list[dict[str, object]]:
        return app_list_user_refresh_sessions(
            self._db,
            user_id=user_id,
            offset=offset,
            limit=limit,
        )

    def list_operational_settings(self, *, offset: int, limit: int) -> list[dict[str, object]]:
        return app_list_operational_settings(self._db, offset=offset, limit=limit)

    def get_system_context_settings(self) -> dict[str, object]:
        return app_get_system_context_settings(self._db)

    def get_storefront_settings(self) -> dict[str, object]:
        return app_get_storefront_settings(self._db)

    def get_telegram_bot_settings(self) -> dict[str, object]:
        return app_get_telegram_bot_settings(self._db)

    def get_telegram_bot_health(self) -> dict[str, object]:
        return app_get_telegram_bot_health(self._db)

    def update_system_context_settings(
        self,
        *,
        country_code: str,
        country_name: str,
        currency_code: str,
        currency_name: str,
        currency_symbol: str,
        currency_decimal_places: int,
        actor_id: int,
    ) -> dict[str, object]:
        return app_update_system_context_settings(
            self._db,
            country_code=country_code,
            country_name=country_name,
            currency_code=currency_code,
            currency_name=currency_name,
            currency_symbol=currency_symbol,
            currency_decimal_places=currency_decimal_places,
            actor_id=actor_id,
        )

    def update_storefront_settings(
        self,
        *,
        brand_name: str,
        brand_mark: str,
        brand_icon: str,
        brand_tagline: str | None,
        socials: list[dict[str, object]],
        actor_id: int,
    ) -> dict[str, object]:
        return app_update_storefront_settings(
            self._db,
            brand_name=brand_name,
            brand_mark=brand_mark,
            brand_icon=brand_icon,
            brand_tagline=brand_tagline,
            socials=socials,
            actor_id=actor_id,
        )

    def update_telegram_bot_settings(
        self,
        *,
        enabled: bool,
        bot_token: str | None,
        bot_username: str | None,
        actor_id: int,
    ) -> dict[str, object]:
        return app_update_telegram_bot_settings(
            self._db,
            enabled=enabled,
            bot_token=bot_token,
            bot_username=bot_username,
            actor_id=actor_id,
        )

    def list_system_backups(self, *, offset: int, limit: int) -> list[dict[str, object]]:
        return app_list_system_backups(offset=offset, limit=limit)

    def record_security_event(
        self,
        *,
        event_type: str,
        success: bool,
        severity: str,
        username: str | None,
        role: str | None,
        user_id: int | None,
        ip_address: str | None,
        user_agent: str | None,
        detail: str | None,
    ) -> None:
        app_record_security_event(
            self._db,
            event_type=event_type,
            success=success,
            severity=severity,
            username=username,
            role=role,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            detail=detail,
        )
