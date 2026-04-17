from __future__ import annotations

import secrets
import string
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import MetaData, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.database import BASE_DIR, Base, create_app_engine, engine as master_engine, run_startup_integrity_checks
from app.enums import TableStatus, UserRole
from app.models import ExpenseCostCenter, MasterTenant, RestaurantTable, SystemSetting, User
from app.security import hash_password
from app.tenant_runtime import dispose_tenant_runtime

TENANTS_DIR = BASE_DIR / "tenants"
DEFAULT_EXPENSE_COST_CENTER_CODE = "GENERAL"
DEFAULT_EXPENSE_COST_CENTER_NAME = "Ù…ØµØ±ÙˆÙ Ø¹Ø§Ù…"
DEFAULT_DELIVERY_FEE = "0.00"
KITCHEN_ACCESS_USERNAME = "kitchen"
KITCHEN_ACCESS_PASSWORD_KEY = "kitchen_access_password"
_TENANT_SCHEMA = MetaData()


for table in Base.metadata.sorted_tables:
    if table.name.startswith("master_"):
        continue
    table.to_metadata(_TENANT_SCHEMA)


def resolve_tenant_database_path(database_name: str) -> Path:
    normalized = str(database_name or "").strip()
    if not normalized:
        raise ValueError("database_name is required")
    return (TENANTS_DIR / f"{normalized}.sqlite3").resolve()


def build_tenant_table_public_path(*, tenant_code: str | None, table_id: int) -> str:
    normalized_code = str(tenant_code or "").strip().lower()
    if normalized_code:
        return f"/t/{normalized_code}/menu?table={table_id}"
    return f"/menu?table={table_id}"


def build_tenant_kitchen_login_path(*, tenant_code: str | None) -> str:
    normalized_code = str(tenant_code or "").strip().lower()
    if normalized_code:
        return f"/t/{normalized_code}/kitchen/login"
    return "/kitchen/login"


def _current_revision() -> str | None:
    with master_engine.connect() as connection:
        row = connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).first()
    if row is None or row[0] is None:
        return None
    return str(row[0]).strip() or None


def _stamp_revision(tenant_session: Session) -> None:
    revision = _current_revision()
    if not revision:
        return

    tenant_session.execute(
        text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
    )
    tenant_session.execute(text("DELETE FROM alembic_version"))
    tenant_session.execute(text("INSERT INTO alembic_version(version_num) VALUES (:revision)"), {"revision": revision})


def _generate_access_password(prefix: str) -> str:
    alphabet = string.ascii_letters + string.digits
    return f"{prefix}@{''.join(secrets.choice(alphabet) for _ in range(10))}"


def _ensure_role_user(
    tenant_session: Session,
    *,
    display_name: str,
    username: str,
    password: str,
    role: UserRole,
) -> User:
    account = tenant_session.execute(select(User).where(User.username == username)).scalar_one_or_none()
    hashed_password = hash_password(password)
    if account is None:
        account = User(
            name=display_name,
            username=username,
            password_hash=hashed_password,
            role=role.value,
            active=True,
        )
        tenant_session.add(account)
        tenant_session.flush()
        return account

    account.name = display_name
    account.password_hash = hashed_password
    account.role = role.value
    account.active = True
    tenant_session.flush()
    return account


def _ensure_manager_user(tenant_session: Session, *, manager_name: str, manager_username: str, manager_password: str) -> User:
    return _ensure_role_user(
        tenant_session,
        display_name=manager_name,
        username=manager_username,
        password=manager_password,
        role=UserRole.MANAGER,
    )


def _get_system_setting_value(tenant_session: Session, *, key: str) -> str | None:
    setting = tenant_session.execute(select(SystemSetting).where(SystemSetting.key == key)).scalar_one_or_none()
    if setting is None:
        return None
    normalized = str(setting.value or "").strip()
    return normalized or None


def _upsert_system_setting(
    tenant_session: Session,
    *,
    key: str,
    value: str,
    updated_by: int | None = None,
) -> None:
    setting = tenant_session.execute(select(SystemSetting).where(SystemSetting.key == key)).scalar_one_or_none()
    if setting is None:
        tenant_session.add(SystemSetting(key=key, value=value, updated_by=updated_by))
        tenant_session.flush()
        return

    setting.value = value
    setting.updated_by = updated_by
    tenant_session.flush()


def _ensure_default_tables(tenant_session: Session, *, tenant_code: str) -> None:
    existing = tenant_session.execute(select(RestaurantTable.id).limit(1)).scalar_one_or_none()
    if existing is not None:
        return
    tenant_session.add_all(
        [
            RestaurantTable(
                id=table_id,
                qr_code=build_tenant_table_public_path(tenant_code=tenant_code, table_id=table_id),
                status=TableStatus.AVAILABLE.value,
            )
            for table_id in range(1, 13)
        ]
    )


def backfill_tenant_table_qr_codes(*, database_name: str, tenant_code: str) -> int:
    database_path = resolve_tenant_database_path(database_name)
    if not database_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ù‚Ø§Ø¹Ø¯Ø© Ø§Ù„Ù†Ø³Ø®Ø© ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯Ø© Ù„ØªÙ†ÙÙŠØ° Ù…Ø²Ø§Ù…Ù†Ø© Ø±ÙˆØ§Ø¨Ø· Ø§Ù„Ø·Ø§ÙˆÙ„Ø§Øª.",
        )

    dispose_tenant_runtime(database_name)
    tenant_engine = create_app_engine(f"sqlite:///{database_path.as_posix()}")
    tenant_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=tenant_engine)
    updated = 0

    try:
        tenant_session = tenant_session_factory()
        try:
            tables = tenant_session.execute(select(RestaurantTable).order_by(RestaurantTable.id.asc())).scalars().all()
            for table in tables:
                expected = build_tenant_table_public_path(tenant_code=tenant_code, table_id=int(table.id))
                if table.qr_code != expected:
                    table.qr_code = expected
                    updated += 1
            tenant_session.commit()
        except Exception:
            tenant_session.rollback()
            raise
        finally:
            tenant_session.close()
    finally:
        tenant_engine.dispose()
        dispose_tenant_runtime(database_name)

    return updated


def backfill_all_tenant_qr_codes(master_db: Session) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    tenants = master_db.execute(select(MasterTenant).order_by(MasterTenant.id.asc())).scalars().all()
    for tenant in tenants:
        updated = backfill_tenant_table_qr_codes(database_name=tenant.database_name, tenant_code=tenant.code)
        rows.append(
            {
                "tenant_id": int(tenant.id),
                "tenant_code": tenant.code,
                "database_name": tenant.database_name,
                "updated_tables": updated,
            }
        )
    return rows


def sync_all_tenant_tables(master_db: Session, *, table_names: list[str]) -> list[str]:
    if not table_names:
        return []

    resolved_tables = [table for name, table in _TENANT_SCHEMA.tables.items() if name in set(table_names)]
    if not resolved_tables:
        return []

    synced_databases: list[str] = []
    tenants = master_db.execute(select(MasterTenant).order_by(MasterTenant.id.asc())).scalars().all()
    for tenant in tenants:
        database_path = resolve_tenant_database_path(tenant.database_name)
        if not database_path.exists():
            continue

        dispose_tenant_runtime(tenant.database_name)
        tenant_engine = create_app_engine(f"sqlite:///{database_path.as_posix()}")
        try:
            _TENANT_SCHEMA.create_all(bind=tenant_engine, tables=resolved_tables)
            synced_databases.append(tenant.database_name)
        finally:
            tenant_engine.dispose()
            dispose_tenant_runtime(tenant.database_name)

    return synced_databases


def _ensure_default_settings(tenant_session: Session, *, manager_id: int) -> None:
    delivery_fee_setting = tenant_session.execute(
        select(SystemSetting).where(SystemSetting.key == "delivery_fee")
    ).scalar_one_or_none()
    if delivery_fee_setting is None:
        tenant_session.add(
            SystemSetting(
                key="delivery_fee",
                value=DEFAULT_DELIVERY_FEE,
                updated_by=manager_id,
            )
        )

    expense_center = tenant_session.execute(
        select(ExpenseCostCenter).where(ExpenseCostCenter.code == DEFAULT_EXPENSE_COST_CENTER_CODE)
    ).scalar_one_or_none()
    if expense_center is None:
        tenant_session.add(
            ExpenseCostCenter(
                code=DEFAULT_EXPENSE_COST_CENTER_CODE,
                name=DEFAULT_EXPENSE_COST_CENTER_NAME,
                active=True,
            )
        )


def cleanup_provisioned_database(database_path: Path) -> None:
    dispose_tenant_runtime(database_path.stem)
    if database_path.exists():
        database_path.unlink()


def provision_tenant_database(
    *,
    database_name: str,
    tenant_code: str,
    tenant_brand_name: str,
    manager_username: str,
    manager_password: str,
    manager_name: str,
) -> Path:
    database_path = resolve_tenant_database_path(database_name)
    TENANTS_DIR.mkdir(parents=True, exist_ok=True)

    if database_path.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ù…Ù„Ù Ù‚Ø§Ø¹Ø¯Ø© Ø§Ù„Ù†Ø³Ø®Ø© Ù…ÙˆØ¬ÙˆØ¯ Ø¨Ø§Ù„ÙØ¹Ù„. Ø§Ø³ØªØ®Ø¯Ù… Ø§Ø³Ù… Ù‚Ø§Ø¹Ø¯Ø© Ù…Ø®ØªÙ„ÙÙ‹Ø§ Ø£Ùˆ Ù†Ø¸Ù Ø§Ù„Ù†Ø³Ø®Ø© Ø§Ù„Ù‚Ø¯ÙŠÙ…Ø©.",
        )

    tenant_engine = create_app_engine(f"sqlite:///{database_path.as_posix()}")
    tenant_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=tenant_engine)

    try:
        _TENANT_SCHEMA.create_all(bind=tenant_engine)
        tenant_session = tenant_session_factory()
        try:
            _stamp_revision(tenant_session)
            manager = _ensure_manager_user(
                tenant_session,
                manager_name=manager_name or f"Ù…Ø¯ÙŠØ± {tenant_brand_name}",
                manager_username=manager_username,
                manager_password=manager_password,
            )
            _ensure_default_tables(tenant_session, tenant_code=tenant_code)
            _ensure_default_settings(tenant_session, manager_id=int(manager.id))
            tenant_session.commit()
        except Exception:
            tenant_session.rollback()
            raise
        finally:
            tenant_session.close()

        run_startup_integrity_checks(tenant_engine)
        return database_path
    except Exception:
        tenant_engine.dispose()
        cleanup_provisioned_database(database_path)
        raise
    finally:
        tenant_engine.dispose()


def ensure_tenant_kitchen_access(
    *,
    database_name: str,
    tenant_code: str,
    tenant_brand_name: str,
    regenerate_password: bool = False,
    updated_by: int | None = None,
) -> dict[str, object]:
    database_path = resolve_tenant_database_path(database_name)
    if not database_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ù‚Ø§Ø¹Ø¯Ø© Ø§Ù„Ù†Ø³Ø®Ø© ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯Ø© Ù„ØªØ¬Ù‡ÙŠØ² ÙˆØµÙˆÙ„ Ø§Ù„Ù…Ø·Ø¨Ø®.",
        )

    dispose_tenant_runtime(database_name)
    tenant_engine = create_app_engine(f"sqlite:///{database_path.as_posix()}")
    tenant_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=tenant_engine)

    try:
        tenant_session = tenant_session_factory()
        try:
            password = _get_system_setting_value(tenant_session, key=KITCHEN_ACCESS_PASSWORD_KEY)
            if regenerate_password or not password:
                password = _generate_access_password("Kitchen")

            _ensure_role_user(
                tenant_session,
                display_name=f"Ù…Ø·Ø¨Ø® {tenant_brand_name}".strip(),
                username=KITCHEN_ACCESS_USERNAME,
                password=password,
                role=UserRole.KITCHEN,
            )
            _upsert_system_setting(
                tenant_session,
                key=KITCHEN_ACCESS_PASSWORD_KEY,
                value=password,
                updated_by=updated_by,
            )
            tenant_session.commit()
            return {
                "login_path": build_tenant_kitchen_login_path(tenant_code=tenant_code),
                "username": KITCHEN_ACCESS_USERNAME,
                "password": password,
                "account_ready": True,
            }
        except Exception:
            tenant_session.rollback()
            raise
        finally:
            tenant_session.close()
    finally:
        tenant_engine.dispose()
        dispose_tenant_runtime(database_name)


def regenerate_tenant_manager_password(
    *,
    database_name: str,
    manager_username: str,
    manager_password: str,
    manager_name: str,
) -> None:
    database_path = resolve_tenant_database_path(database_name)
    if not database_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ù‚Ø§Ø¹Ø¯Ø© Ø§Ù„Ù†Ø³Ø®Ø© ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯Ø© Ù„ØªØ­Ø¯ÙŠØ« ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ±.",
        )

    dispose_tenant_runtime(database_name)
    tenant_engine = create_app_engine(f"sqlite:///{database_path.as_posix()}")
    tenant_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=tenant_engine)

    try:
        tenant_session = tenant_session_factory()
        try:
            _ensure_manager_user(
                tenant_session,
                manager_name=manager_name,
                manager_username=manager_username,
                manager_password=manager_password,
            )
            tenant_session.commit()
        except Exception:
            tenant_session.rollback()
            raise
        finally:
            tenant_session.close()
    finally:
        tenant_engine.dispose()
        dispose_tenant_runtime(database_name)
