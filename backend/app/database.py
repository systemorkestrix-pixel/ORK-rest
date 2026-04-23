import os
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .env_loader import load_local_env_file
from .enums import OrderStatus, PaymentStatus

load_local_env_file()

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
DEFAULT_DATABASE_PATH = BASE_DIR / "restaurant.db"


def _resolve_database_path(raw_value: str | None) -> Path:
    if not raw_value:
        return DEFAULT_DATABASE_PATH

    raw_path = Path(raw_value).expanduser()
    if raw_path.is_absolute():
        return raw_path.resolve()

    # Support both:
    # - DATABASE_PATH=local.sqlite3          -> relative to backend/
    # - DATABASE_PATH=backend/local.sqlite3  -> relative to project root/
    if raw_path.parts and raw_path.parts[0] == BASE_DIR.name:
        return (PROJECT_ROOT / raw_path).resolve()
    return (BASE_DIR / raw_path).resolve()


def normalize_database_url(raw_value: str) -> str:
    normalized = str(raw_value or "").strip()
    if not normalized:
        raise RuntimeError("DATABASE_URL must not be empty.")
    if normalized.startswith("postgres://"):
        return f"postgresql+psycopg://{normalized.removeprefix('postgres://')}"
    if normalized.startswith("postgresql://") and "+psycopg" not in normalized.split("://", 1)[0]:
        return f"postgresql+psycopg://{normalized.removeprefix('postgresql://')}"
    return normalized


def resolve_database_url(database_url_raw: str | None = None, database_path_raw: str | None = None) -> str:
    if database_url_raw and database_url_raw.strip():
        return normalize_database_url(database_url_raw)

    database_path = _resolve_database_path(database_path_raw)
    return f"sqlite:///{database_path.as_posix()}"


DATABASE_URL = resolve_database_url(os.getenv("DATABASE_URL"), os.getenv("DATABASE_PATH"))


def is_sqlite_database_url(database_url: str) -> bool:
    return str(database_url or "").strip().startswith("sqlite")


def resolve_sqlite_database_path(app_engine: Engine) -> Path | None:
    if app_engine.dialect.name != "sqlite":
        return None
    database = getattr(app_engine.url, "database", None)
    if not database:
        return None
    return Path(str(database)).expanduser().resolve()


def _register_sqlite_datetime_adapter() -> None:
    if getattr(sqlite3, "_restaurant_datetime_adapter_registered", False):
        return
    sqlite3.register_adapter(datetime, lambda value: value.isoformat(sep=" "))
    sqlite3.register_adapter(date, lambda value: value.isoformat())
    setattr(sqlite3, "_restaurant_datetime_adapter_registered", True)


def _apply_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_app_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if is_sqlite_database_url(database_url) else {}
    app_engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
    if is_sqlite_database_url(database_url):
        _register_sqlite_datetime_adapter()
        event.listen(app_engine, "connect", _apply_sqlite_pragmas)
    return app_engine


def assert_production_migration_state(
    app_engine: Engine,
    *,
    version_table: str = "alembic_version",
    expected_revision: str | None = None,
) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", version_table):
        raise RuntimeError(f"Invalid migration version table name: {version_table!r}")

    inspector = inspect(app_engine)
    if version_table not in set(inspector.get_table_names()):
        raise RuntimeError(
            f"Production startup blocked: migration version table {version_table!r} is missing. "
            "Apply schema migrations before boot."
        )

    with app_engine.connect() as connection:
        row = connection.execute(text(f"SELECT version_num FROM {version_table} LIMIT 1")).first()
    if row is None or row[0] is None or not str(row[0]).strip():
        raise RuntimeError(
            f"Production startup blocked: migration version table {version_table!r} has no revision stamp."
        )

    current_revision = str(row[0]).strip()
    if expected_revision and current_revision != expected_revision:
        raise RuntimeError(
            "Production startup blocked: schema revision mismatch. "
            f"expected={expected_revision!r}, current={current_revision!r}."
        )
    return current_revision


def run_startup_integrity_checks(app_engine: Engine) -> None:
    with app_engine.connect() as connection:
        if app_engine.dialect.name == "sqlite":
            fk_violations = connection.execute(text("PRAGMA foreign_key_check")).fetchall()
            if fk_violations:
                raise RuntimeError(f"Startup blocked: foreign key violations detected ({len(fk_violations)} row(s)).")

        orphan_payments = int(
            connection.execute(
                text(
                    """
                    SELECT COUNT(*) FROM financial_transactions ft
                    LEFT JOIN orders o ON o.id = ft.order_id
                    LEFT JOIN expenses e ON e.id = ft.expense_id
                    WHERE (ft.order_id IS NOT NULL AND o.id IS NULL)
                       OR (ft.expense_id IS NOT NULL AND e.id IS NULL)
                    """
                )
            ).scalar_one()
            or 0
        )
        if orphan_payments:
            raise RuntimeError(f"Startup blocked: orphan financial records detected ({orphan_payments}).")

        orphan_delivery_drivers = int(
            connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM delivery_drivers dd
                    LEFT JOIN users u ON u.id = dd.user_id
                    WHERE dd.user_id IS NOT NULL
                      AND (u.id IS NULL OR u.role <> 'delivery')
                    """
                )
            ).scalar_one()
            or 0
        )
        if orphan_delivery_drivers:
            raise RuntimeError(
                f"Startup blocked: delivery drivers without valid delivery user linkage detected ({orphan_delivery_drivers})."
            )

        invalid_provider_accounts = int(
            connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM delivery_providers dp
                    LEFT JOIN users u ON u.id = dp.account_user_id
                    WHERE dp.account_user_id IS NOT NULL
                      AND (u.id IS NULL OR u.role <> 'delivery')
                    """
                )
            ).scalar_one()
            or 0
        )
        if invalid_provider_accounts:
            raise RuntimeError(
                f"Startup blocked: delivery providers with invalid delivery account linkage detected ({invalid_provider_accounts})."
            )

        negative_stock = int(
            connection.execute(text("SELECT COUNT(*) FROM wh_stock_balances WHERE quantity < 0")).scalar_one() or 0
        )
        if negative_stock:
            raise RuntimeError(f"Startup blocked: negative stock rows detected ({negative_stock}).")

        valid_statuses_sql = ", ".join(f"'{status.value}'" for status in OrderStatus)
        valid_payment_statuses_sql = ", ".join(f"'{status.value}'" for status in PaymentStatus)
        invalid_orders = int(
            connection.execute(
                text(
                    f"""
                    SELECT COUNT(*) FROM orders
                    WHERE status NOT IN ({valid_statuses_sql})
                       OR payment_status NOT IN ({valid_payment_statuses_sql})
                    """
                )
            ).scalar_one()
            or 0
        )
        if invalid_orders:
            raise RuntimeError(f"Startup blocked: orders with invalid status/payment_status detected ({invalid_orders}).")


engine = create_app_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
