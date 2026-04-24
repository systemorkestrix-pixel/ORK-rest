from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from sqlalchemy import MetaData, Table, func, select, text
from sqlalchemy.engine import Connection, Engine

from app.database import Base
from app.master_tenant_runtime_contract import (
    MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA,
    MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE,
    build_master_tenant_runtime_schema_name,
)
from app.tenant_runtime_storage import (
    TenantRuntimeStorageTarget,
    create_tenant_runtime_engine,
    resolve_tenant_runtime_target,
    tenant_runtime_target_exists,
)

from .postgres_runtime_provisioning import (
    build_postgres_runtime_search_path,
    build_postgres_tenant_runtime_metadata,
    provision_postgres_tenant_runtime_schema,
)

TENANT_RUNTIME_MIGRATION_TABLE_ORDER: tuple[str, ...] = (
    "users",
    "restaurant_employees",
    "tables",
    "product_categories",
    "resources",
    "expense_cost_centers",
    "wh_suppliers",
    "wh_items",
    "products",
    "product_secondary_links",
    "product_consumption_components",
    "delivery_location_cache",
    "delivery_zone_pricing",
    "delivery_address_nodes",
    "system_settings",
    "orders",
    "order_items",
    "order_cost_entries",
    "resource_movements",
    "expenses",
    "expense_attachments",
    "delivery_providers",
    "delivery_drivers",
    "delivery_assignments",
    "delivery_dispatches",
    "delivery_settlements",
    "financial_transactions",
    "cashbox_movements",
    "shift_closures",
    "wh_supplier_items",
    "wh_stock_balances",
    "wh_inbound_vouchers",
    "wh_inbound_items",
    "wh_outbound_vouchers",
    "wh_outbound_items",
    "wh_stock_ledger",
    "wh_stock_counts",
    "wh_stock_count_lines",
    "wh_integration_events",
    "refresh_tokens",
    "order_transitions_log",
    "system_audit_log",
    "security_audit_events",
)


@dataclass(frozen=True)
class TenantRuntimeTableMigrationReport:
    table_name: str
    primary_key_columns: tuple[str, ...]
    source_row_count: int
    migrated_row_count: int
    failed_row_count: int
    status: str
    elapsed_ms: int


@dataclass(frozen=True)
class TenantRuntimeMigrationReport:
    database_name: str
    source_backend: str
    source_database_path: str
    target_backend: str
    target_schema_name: str
    dry_run: bool
    validation_passed: bool
    total_source_rows: int
    total_migrated_rows: int
    total_failed_rows: int
    elapsed_ms: int
    table_reports: tuple[TenantRuntimeTableMigrationReport, ...]


def build_sqlite_tenant_runtime_metadata() -> MetaData:
    import app.models  # noqa: F401

    metadata = MetaData()
    for table in Base.metadata.sorted_tables:
        if table.name.startswith("master_"):
            continue
        table.to_metadata(metadata)
    return metadata


def list_tenant_runtime_migration_tables() -> tuple[str, ...]:
    assert_sqlite_to_postgres_migration_contract()
    return TENANT_RUNTIME_MIGRATION_TABLE_ORDER


def assert_sqlite_to_postgres_migration_contract() -> None:
    if len(TENANT_RUNTIME_MIGRATION_TABLE_ORDER) != len(set(TENANT_RUNTIME_MIGRATION_TABLE_ORDER)):
        raise RuntimeError("Duplicate table names found in tenant runtime migration order.")

    expected = {table.name for table in build_sqlite_tenant_runtime_metadata().sorted_tables}
    declared = set(TENANT_RUNTIME_MIGRATION_TABLE_ORDER)
    missing = sorted(expected - declared)
    unexpected = sorted(declared - expected)
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing={missing}")
        if unexpected:
            details.append(f"unexpected={unexpected}")
        raise RuntimeError("Tenant runtime migration coverage is out of sync: " + ", ".join(details))


def migrate_sqlite_tenant_runtime_to_postgres(
    *,
    database_name: str,
    target_engine: Engine | None = None,
    target_schema_name: str | None = None,
    batch_size: int = 500,
    dry_run: bool = False,
) -> TenantRuntimeMigrationReport:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")

    assert_sqlite_to_postgres_migration_contract()
    source_target = _resolve_sqlite_source_target(database_name)
    resolved_target_schema_name = build_master_tenant_runtime_schema_name(target_schema_name or source_target.database_name)

    source_engine = create_tenant_runtime_engine(source_target)
    started_at = perf_counter()
    try:
        source_metadata = build_sqlite_tenant_runtime_metadata()
        source_tables = {table.name: table for table in source_metadata.sorted_tables}

        with source_engine.connect() as source_connection:
            if dry_run:
                return _build_dry_run_report(
                    source_connection=source_connection,
                    source_target=source_target,
                    source_tables=source_tables,
                    target_schema_name=resolved_target_schema_name,
                    started_at=started_at,
                )

            if target_engine is None:
                raise ValueError("target_engine is required unless dry_run=True")
            if target_engine.dialect.name != "postgresql":
                raise ValueError("target_engine must use the PostgreSQL dialect")

            provisioned_schema_name = provision_postgres_tenant_runtime_schema(
                target_engine,
                schema_name=resolved_target_schema_name,
            )
            target_metadata = build_postgres_tenant_runtime_metadata(provisioned_schema_name)
            target_tables = {table.name: table for table in target_metadata.sorted_tables}

            with target_engine.begin() as target_connection:
                _apply_postgres_search_path(target_connection, provisioned_schema_name)
                _assert_empty_postgres_target_schema(target_connection, target_tables.values())

            table_reports = tuple(
                _migrate_runtime_table(
                    source_connection=source_connection,
                    target_engine=target_engine,
                    source_table=source_tables[table_name],
                    target_table=target_tables[table_name],
                    target_schema_name=provisioned_schema_name,
                    batch_size=batch_size,
                )
                for table_name in list_tenant_runtime_migration_tables()
            )
            validation_passed = _validate_target_row_counts(
                source_connection=source_connection,
                target_engine=target_engine,
                source_tables=source_tables,
                target_tables=target_tables,
                target_schema_name=provisioned_schema_name,
            )
    finally:
        source_engine.dispose()

    return _finalize_report(
        source_target=source_target,
        target_schema_name=provisioned_schema_name,
        dry_run=False,
        validation_passed=validation_passed,
        started_at=started_at,
        table_reports=table_reports,
    )


def _resolve_sqlite_source_target(database_name: str) -> TenantRuntimeStorageTarget:
    target = resolve_tenant_runtime_target(database_name)
    if target.backend != MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE:
        raise ValueError(
            "Phase 4 migrator only supports sqlite_file tenant sources. "
            f"Received backend={target.backend!r}."
        )
    if not tenant_runtime_target_exists(target):
        raise FileNotFoundError(f"Tenant runtime database not found: {target.database_path}")
    return target


def _build_dry_run_report(
    *,
    source_connection: Connection,
    source_target: TenantRuntimeStorageTarget,
    source_tables: dict[str, Table],
    target_schema_name: str,
    started_at: float,
) -> TenantRuntimeMigrationReport:
    table_reports = tuple(
        _dry_run_runtime_table(source_connection=source_connection, source_table=source_tables[table_name])
        for table_name in list_tenant_runtime_migration_tables()
    )
    return _finalize_report(
        source_target=source_target,
        target_schema_name=target_schema_name,
        dry_run=True,
        validation_passed=False,
        started_at=started_at,
        table_reports=table_reports,
    )


def _dry_run_runtime_table(
    *,
    source_connection: Connection,
    source_table: Table,
) -> TenantRuntimeTableMigrationReport:
    started_at = perf_counter()
    source_rows = _count_rows(source_connection, source_table)
    return TenantRuntimeTableMigrationReport(
        table_name=source_table.name,
        primary_key_columns=_primary_key_columns(source_table),
        source_row_count=source_rows,
        migrated_row_count=0,
        failed_row_count=0,
        status="dry_run" if source_rows else "dry_run_empty",
        elapsed_ms=_elapsed_ms(started_at),
    )


def _migrate_runtime_table(
    *,
    source_connection: Connection,
    target_engine: Engine,
    source_table: Table,
    target_table: Table,
    target_schema_name: str,
    batch_size: int,
) -> TenantRuntimeTableMigrationReport:
    started_at = perf_counter()
    payload = _read_table_payload(source_connection, source_table)
    source_row_count = len(payload)
    if not payload:
        return TenantRuntimeTableMigrationReport(
            table_name=source_table.name,
            primary_key_columns=_primary_key_columns(source_table),
            source_row_count=0,
            migrated_row_count=0,
            failed_row_count=0,
            status="skipped_empty",
            elapsed_ms=_elapsed_ms(started_at),
        )

    try:
        with target_engine.begin() as target_connection:
            _apply_postgres_search_path(target_connection, target_schema_name)
            for batch in _chunked(payload, batch_size):
                target_connection.execute(target_table.insert(), batch)
    except Exception as exc:
        raise RuntimeError(f"Tenant runtime migration failed while importing table {source_table.name!r}") from exc

    return TenantRuntimeTableMigrationReport(
        table_name=source_table.name,
        primary_key_columns=_primary_key_columns(source_table),
        source_row_count=source_row_count,
        migrated_row_count=source_row_count,
        failed_row_count=0,
        status="migrated",
        elapsed_ms=_elapsed_ms(started_at),
    )


def _validate_target_row_counts(
    *,
    source_connection: Connection,
    target_engine: Engine,
    source_tables: dict[str, Table],
    target_tables: dict[str, Table],
    target_schema_name: str,
) -> bool:
    mismatches: list[str] = []
    with target_engine.connect() as target_connection:
        _apply_postgres_search_path(target_connection, target_schema_name)
        for table_name in list_tenant_runtime_migration_tables():
            source_count = _count_rows(source_connection, source_tables[table_name])
            target_count = _count_rows(target_connection, target_tables[table_name])
            if source_count != target_count:
                mismatches.append(f"{table_name}: source={source_count}, target={target_count}")

    if mismatches:
        raise RuntimeError("Tenant runtime migration validation failed: " + "; ".join(mismatches))
    return True


def _apply_postgres_search_path(connection: Connection, schema_name: str) -> None:
    search_path = build_postgres_runtime_search_path(schema_name)
    connection.execute(text(f"SET search_path TO {search_path}"))


def _assert_empty_postgres_target_schema(connection: Connection, tables: Sequence[Table]) -> None:
    non_empty_tables: list[str] = []
    for table in tables:
        if _count_rows(connection, table) > 0:
            non_empty_tables.append(table.name)
    if non_empty_tables:
        raise RuntimeError(
            "Target PostgreSQL tenant schema must be empty before phase 4 import: "
            + ", ".join(sorted(non_empty_tables))
        )


def _read_table_payload(connection: Connection, table: Table) -> list[dict[str, object]]:
    statement = select(table)
    if table.primary_key.columns:
        statement = statement.order_by(*table.primary_key.columns)
    rows = connection.execute(statement).mappings().all()
    return [dict(row) for row in rows]


def _count_rows(connection: Connection, table: Table) -> int:
    return int(connection.execute(select(func.count()).select_from(table)).scalar_one())


def _primary_key_columns(table: Table) -> tuple[str, ...]:
    return tuple(column.name for column in table.primary_key.columns)


def _chunked(payload: Sequence[dict[str, object]], batch_size: int) -> Iterator[list[dict[str, object]]]:
    for start in range(0, len(payload), batch_size):
        yield list(payload[start : start + batch_size])


def _elapsed_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)


def _finalize_report(
    *,
    source_target: TenantRuntimeStorageTarget,
    target_schema_name: str,
    dry_run: bool,
    validation_passed: bool,
    started_at: float,
    table_reports: tuple[TenantRuntimeTableMigrationReport, ...],
) -> TenantRuntimeMigrationReport:
    total_source_rows = sum(report.source_row_count for report in table_reports)
    total_migrated_rows = sum(report.migrated_row_count for report in table_reports)
    total_failed_rows = sum(report.failed_row_count for report in table_reports)
    return TenantRuntimeMigrationReport(
        database_name=source_target.database_name,
        source_backend=source_target.backend,
        source_database_path=str(Path(source_target.database_path)),
        target_backend=MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA,
        target_schema_name=target_schema_name,
        dry_run=dry_run,
        validation_passed=validation_passed,
        total_source_rows=total_source_rows,
        total_migrated_rows=total_migrated_rows,
        total_failed_rows=total_failed_rows,
        elapsed_ms=_elapsed_ms(started_at),
        table_reports=table_reports,
    )
