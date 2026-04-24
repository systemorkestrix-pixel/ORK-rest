from __future__ import annotations

from sqlalchemy import MetaData, text
from sqlalchemy.engine import Engine

from app.database import Base, engine as master_engine
from app.master_tenant_runtime_contract import build_master_tenant_runtime_schema_name


def _current_master_revision() -> str | None:
    with master_engine.connect() as connection:
        row = connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).first()
    if row is None or row[0] is None:
        return None
    return str(row[0]).strip() or None


def build_postgres_runtime_search_path(schema_name: str) -> str:
    normalized = build_master_tenant_runtime_schema_name(schema_name)
    return f"{normalized},public"


def build_postgres_tenant_runtime_metadata(schema_name: str) -> MetaData:
    import app.models  # noqa: F401

    normalized_schema_name = build_master_tenant_runtime_schema_name(schema_name)
    metadata = MetaData()
    for table in Base.metadata.sorted_tables:
        if table.name.startswith("master_"):
            continue
        table.to_metadata(metadata, schema=normalized_schema_name)
    return metadata


def provision_postgres_tenant_runtime_schema(engine: Engine, *, schema_name: str) -> str:
    if engine.dialect.name != "postgresql":
        raise ValueError("PostgreSQL engine is required for tenant schema provisioning.")

    normalized_schema_name = build_master_tenant_runtime_schema_name(schema_name)
    revision = _current_master_revision()
    metadata = build_postgres_tenant_runtime_metadata(normalized_schema_name)

    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{normalized_schema_name}"'))
        metadata.create_all(bind=connection)
        connection.execute(
            text(
                f'CREATE TABLE IF NOT EXISTS "{normalized_schema_name}".alembic_version '
                "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
        )
        if revision:
            connection.execute(text(f'DELETE FROM "{normalized_schema_name}".alembic_version'))
            connection.execute(
                text(f'INSERT INTO "{normalized_schema_name}".alembic_version(version_num) VALUES (:revision)'),
                {"revision": revision},
            )

    return normalized_schema_name
