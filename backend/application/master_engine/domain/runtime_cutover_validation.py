from __future__ import annotations

import json
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
from app.tenant_runtime_storage import create_tenant_runtime_engine, resolve_tenant_runtime_target, tenant_runtime_target_exists

from .postgres_runtime_provisioning import (
    build_postgres_runtime_search_path,
    build_postgres_tenant_runtime_metadata,
)

DUAL_VALIDATION_SAMPLE_TABLES: tuple[str, ...] = (
    "users",
    "products",
    "orders",
    "financial_transactions",
    "delivery_dispatches",
)

DUAL_VALIDATION_SMOKE_KEYS: tuple[str, ...] = (
    "manager_login",
    "public_order",
    "tracking",
    "operations_page",
    "settings_read_write",
)


@dataclass(frozen=True)
class TenantRuntimeParityReport:
    table_name: str
    source_row_count: int
    target_row_count: int | None
    parity_ok: bool


@dataclass(frozen=True)
class TenantRuntimeSampleReport:
    table_name: str
    sample_limit: int
    source_sample_rows: tuple[dict[str, object], ...]
    target_sample_rows: tuple[dict[str, object], ...]
    sample_match: bool | None


@dataclass(frozen=True)
class TenantRuntimeSmokeCheck:
    key: str
    path: str
    expectation: str
    status: str


@dataclass(frozen=True)
class TenantRuntimeDualValidationReport:
    database_name: str
    target_schema_name: str
    source_backend: str
    target_backend: str
    dry_run: bool
    validation_passed: bool
    parity_reports: tuple[TenantRuntimeParityReport, ...]
    sample_reports: tuple[TenantRuntimeSampleReport, ...]
    smoke_checks: tuple[TenantRuntimeSmokeCheck, ...]
    elapsed_ms: int


def build_dual_validation_runtime_metadata() -> MetaData:
    import app.models  # noqa: F401

    metadata = MetaData()
    for table in Base.metadata.sorted_tables:
        if table.name.startswith("master_"):
            continue
        table.to_metadata(metadata)
    return metadata


def build_dual_validation_smoke_checks(*, tenant_code: str | None) -> tuple[TenantRuntimeSmokeCheck, ...]:
    normalized = str(tenant_code or "").strip().lower()
    scoped_prefix = f"/t/{normalized}" if normalized else ""
    menu_path = f"{scoped_prefix}/menu" if scoped_prefix else "/menu"
    manager_login_path = f"{scoped_prefix}/manager/login" if scoped_prefix else "/manager/login"
    tracking_path = f"{scoped_prefix}/track" if scoped_prefix else "/track"
    operations_path = f"{scoped_prefix}/manager/operations/orders" if scoped_prefix else "/manager/operations/orders"
    settings_path = f"{scoped_prefix}/manager/settings" if scoped_prefix else "/manager/settings"
    return (
        TenantRuntimeSmokeCheck(
            key="manager_login",
            path=manager_login_path,
            expectation="manager credentials authenticate against the cutover runtime",
            status="contract_ready",
        ),
        TenantRuntimeSmokeCheck(
            key="public_order",
            path=menu_path,
            expectation="public scoped ordering reads catalog and creates orders successfully",
            status="contract_ready",
        ),
        TenantRuntimeSmokeCheck(
            key="tracking",
            path=tracking_path,
            expectation="public tracking resolves tenant orders and status timeline correctly",
            status="contract_ready",
        ),
        TenantRuntimeSmokeCheck(
            key="operations_page",
            path=operations_path,
            expectation="operations orders page loads and reflects migrated orders without parity drift",
            status="contract_ready",
        ),
        TenantRuntimeSmokeCheck(
            key="settings_read_write",
            path=settings_path,
            expectation="manager settings can be read and persisted against the cutover runtime",
            status="contract_ready",
        ),
    )


def validate_tenant_runtime_dual_state(
    *,
    database_name: str,
    target_engine: Engine | None = None,
    target_schema_name: str | None = None,
    tenant_code: str | None = None,
    sample_limit: int = 5,
    dry_run: bool = False,
) -> TenantRuntimeDualValidationReport:
    if sample_limit <= 0:
        raise ValueError("sample_limit must be greater than zero")

    source_target = resolve_tenant_runtime_target(database_name)
    if source_target.backend != MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE:
        raise ValueError(
            "Phase 6 validation expects sqlite_file as the source runtime backend. "
            f"Received backend={source_target.backend!r}."
        )
    if not tenant_runtime_target_exists(source_target):
        raise FileNotFoundError(f"Tenant runtime database not found: {source_target.database_path}")

    resolved_schema_name = build_master_tenant_runtime_schema_name(target_schema_name or database_name)
    smoke_checks = build_dual_validation_smoke_checks(tenant_code=tenant_code)
    started_at = perf_counter()
    source_engine = create_tenant_runtime_engine(source_target)
    try:
        source_metadata = build_dual_validation_runtime_metadata()
        source_tables = {table.name: table for table in source_metadata.sorted_tables}

        with source_engine.connect() as source_connection:
            if dry_run:
                parity_reports = tuple(
                    TenantRuntimeParityReport(
                        table_name=table_name,
                        source_row_count=_count_rows(source_connection, source_tables[table_name]),
                        target_row_count=None,
                        parity_ok=False,
                    )
                    for table_name in _validation_table_order(source_tables)
                )
                sample_reports = tuple(
                    TenantRuntimeSampleReport(
                        table_name=table_name,
                        sample_limit=sample_limit,
                        source_sample_rows=_sample_rows(source_connection, source_tables[table_name], sample_limit),
                        target_sample_rows=tuple(),
                        sample_match=None,
                    )
                    for table_name in DUAL_VALIDATION_SAMPLE_TABLES
                )
                return TenantRuntimeDualValidationReport(
                    database_name=database_name,
                    target_schema_name=resolved_schema_name,
                    source_backend=MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE,
                    target_backend=MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA,
                    dry_run=True,
                    validation_passed=False,
                    parity_reports=parity_reports,
                    sample_reports=sample_reports,
                    smoke_checks=smoke_checks,
                    elapsed_ms=_elapsed_ms(started_at),
                )

            if target_engine is None:
                raise ValueError("target_engine is required unless dry_run=True")
            if target_engine.dialect.name != "postgresql":
                raise ValueError("target_engine must use the PostgreSQL dialect")

            target_metadata = build_postgres_tenant_runtime_metadata(resolved_schema_name)
            target_tables = {table.name: table for table in target_metadata.sorted_tables}
            parity_reports, sample_reports = _validate_source_vs_target(
                source_connection=source_connection,
                target_engine=target_engine,
                source_tables=source_tables,
                target_tables=target_tables,
                target_schema_name=resolved_schema_name,
                sample_limit=sample_limit,
            )
    finally:
        source_engine.dispose()

    return TenantRuntimeDualValidationReport(
        database_name=database_name,
        target_schema_name=resolved_schema_name,
        source_backend=MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE,
        target_backend=MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA,
        dry_run=False,
        validation_passed=all(row.parity_ok for row in parity_reports) and all(
            row.sample_match is True for row in sample_reports
        ),
        parity_reports=parity_reports,
        sample_reports=sample_reports,
        smoke_checks=smoke_checks,
        elapsed_ms=_elapsed_ms(started_at),
    )


def _validate_source_vs_target(
    *,
    source_connection: Connection,
    target_engine: Engine,
    source_tables: dict[str, Table],
    target_tables: dict[str, Table],
    target_schema_name: str,
    sample_limit: int,
) -> tuple[tuple[TenantRuntimeParityReport, ...], tuple[TenantRuntimeSampleReport, ...]]:
    parity_reports: list[TenantRuntimeParityReport] = []
    sample_reports: list[TenantRuntimeSampleReport] = []
    with target_engine.connect() as target_connection:
        _apply_postgres_search_path(target_connection, target_schema_name)
        for table_name in _validation_table_order(source_tables):
            source_count = _count_rows(source_connection, source_tables[table_name])
            target_count = _count_rows(target_connection, target_tables[table_name])
            parity_reports.append(
                TenantRuntimeParityReport(
                    table_name=table_name,
                    source_row_count=source_count,
                    target_row_count=target_count,
                    parity_ok=source_count == target_count,
                )
            )

        for table_name in DUAL_VALIDATION_SAMPLE_TABLES:
            source_sample_rows = _sample_rows(source_connection, source_tables[table_name], sample_limit)
            target_sample_rows = _sample_rows(target_connection, target_tables[table_name], sample_limit)
            sample_reports.append(
                TenantRuntimeSampleReport(
                    table_name=table_name,
                    sample_limit=sample_limit,
                    source_sample_rows=source_sample_rows,
                    target_sample_rows=target_sample_rows,
                    sample_match=source_sample_rows == target_sample_rows,
                )
            )

    failed_counts = [row.table_name for row in parity_reports if not row.parity_ok]
    failed_samples = [row.table_name for row in sample_reports if row.sample_match is not True]
    if failed_counts or failed_samples:
        failures: list[str] = []
        if failed_counts:
            failures.append("row_count_mismatch=" + ",".join(failed_counts))
        if failed_samples:
            failures.append("sample_mismatch=" + ",".join(failed_samples))
        raise RuntimeError("Phase 6 dual validation failed: " + "; ".join(failures))

    return tuple(parity_reports), tuple(sample_reports)


def _validation_table_order(source_tables: dict[str, Table]) -> tuple[str, ...]:
    return tuple(table.name for table in build_dual_validation_runtime_metadata().sorted_tables if table.name in source_tables)


def _sample_rows(connection: Connection, table: Table, sample_limit: int) -> tuple[dict[str, object], ...]:
    statement = select(table)
    if table.primary_key.columns:
        statement = statement.order_by(*table.primary_key.columns)
    statement = statement.limit(sample_limit)
    rows = connection.execute(statement).mappings().all()
    return tuple(_normalize_row(dict(row)) for row in rows)


def _normalize_row(row: dict[str, object]) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key, value in row.items():
        if hasattr(value, "isoformat"):
            normalized[key] = value.isoformat()
        elif isinstance(value, (dict, list, tuple)):
            normalized[key] = json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True))
        else:
            normalized[key] = value
    return normalized


def _apply_postgres_search_path(connection: Connection, schema_name: str) -> None:
    connection.execute(text(f"SET search_path TO {build_postgres_runtime_search_path(schema_name)}"))


def _count_rows(connection: Connection, table: Table) -> int:
    return int(connection.execute(select(func.count()).select_from(table)).scalar_one())


def _elapsed_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)
