from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import load_settings
from app.master_tenant_runtime_contract import (
    MASTER_TENANT_MEDIA_STORAGE_BACKEND_LOCAL_STATIC,
    MASTER_TENANT_MEDIA_STORAGE_BACKEND_SUPABASE_STORAGE,
)
from app.models import ExpenseAttachment, Product
from app.tenant_runtime import infer_tenant_record_from_session

APP_ROOT = Path(__file__).resolve().parents[3] / "app"
PRODUCT_UPLOAD_DIR = APP_ROOT / "static" / "uploads" / "products"
EXPENSE_ATTACHMENT_UPLOAD_DIR = APP_ROOT / "static" / "uploads" / "expenses"

MediaNamespace = Literal["products", "expenses"]


@dataclass(frozen=True)
class MediaStorageTarget:
    backend: str
    tenant_code: str
    bucket: str | None
    project_url: str | None
    public_base_url: str | None


@dataclass(frozen=True)
class StoredMediaObject:
    file_url: str
    storage_backend: str
    object_key: str | None
    size_bytes: int


def build_media_object_key(*, tenant_code: str, namespace: MediaNamespace, file_name: str) -> str:
    normalized_code = _normalize_tenant_code(tenant_code)
    safe_name = Path(file_name).name.strip()
    if not safe_name:
        raise ValueError("file_name is required")
    return f"tenants/{normalized_code}/{namespace}/{safe_name}"


def resolve_media_storage_target(
    db: Session | None = None,
    *,
    backend_override: str | None = None,
    tenant_code_override: str | None = None,
) -> MediaStorageTarget:
    settings = load_settings()
    tenant_code = _normalize_tenant_code(tenant_code_override)
    backend = (backend_override or "").strip() or settings.media_storage_backend

    if db is not None:
        tenant = infer_tenant_record_from_session(db)
        if tenant is not None:
            tenant_code = _normalize_tenant_code(tenant.code)
            if not backend_override:
                backend = str(tenant.media_storage_backend or "").strip() or settings.media_storage_backend

    if backend == MASTER_TENANT_MEDIA_STORAGE_BACKEND_LOCAL_STATIC:
        return MediaStorageTarget(
            backend=backend,
            tenant_code=tenant_code,
            bucket=None,
            project_url=None,
            public_base_url=None,
        )

    if backend == MASTER_TENANT_MEDIA_STORAGE_BACKEND_SUPABASE_STORAGE:
        if not settings.media_storage_bucket or not settings.media_storage_project_url or not settings.media_storage_public_base_url:
            raise RuntimeError("Supabase media storage backend is missing required storage settings.")
        return MediaStorageTarget(
            backend=backend,
            tenant_code=tenant_code,
            bucket=settings.media_storage_bucket,
            project_url=settings.media_storage_project_url,
            public_base_url=settings.media_storage_public_base_url,
        )

    raise RuntimeError(f"Unsupported media storage backend: {backend!r}")


def store_media_bytes(
    *,
    db: Session | None,
    namespace: MediaNamespace,
    file_name: str,
    content_type: str,
    data: bytes,
    old_file_url: str | None = None,
    backend_override: str | None = None,
    tenant_code_override: str | None = None,
) -> StoredMediaObject:
    target = resolve_media_storage_target(
        db,
        backend_override=backend_override,
        tenant_code_override=tenant_code_override,
    )
    if target.backend == MASTER_TENANT_MEDIA_STORAGE_BACKEND_LOCAL_STATIC:
        stored = _store_media_bytes_locally(namespace=namespace, file_name=file_name, data=data)
    elif target.backend == MASTER_TENANT_MEDIA_STORAGE_BACKEND_SUPABASE_STORAGE:
        stored = _store_media_bytes_in_supabase(
            target=target,
            namespace=namespace,
            file_name=file_name,
            content_type=content_type,
            data=data,
        )
    else:
        raise RuntimeError(f"Unsupported media storage backend: {target.backend!r}")

    if old_file_url and old_file_url != stored.file_url:
        delete_media_object(
            old_file_url,
            db=db,
            backend_override=backend_override,
            tenant_code_override=tenant_code_override,
        )
    return stored


def delete_media_object(
    file_url: str | None,
    *,
    db: Session | None = None,
    backend_override: str | None = None,
    tenant_code_override: str | None = None,
) -> None:
    if not file_url:
        return
    normalized = str(file_url).strip()
    if not normalized:
        return

    if normalized.startswith("/static/uploads/"):
        _delete_local_media_object(normalized)
        return

    target = resolve_media_storage_target(
        db,
        backend_override=backend_override,
        tenant_code_override=tenant_code_override,
    )
    if target.backend != MASTER_TENANT_MEDIA_STORAGE_BACKEND_SUPABASE_STORAGE:
        return

    object_key = extract_supabase_object_key(file_url=normalized, public_base_url=target.public_base_url)
    if not object_key:
        return

    payload = json.dumps({"prefixes": [object_key]}).encode("utf-8")
    request = Request(
        url=f"{target.project_url}/storage/v1/object/{quote(str(target.bucket), safe='')}",
        data=payload,
        headers=_supabase_storage_headers(content_type="application/json", content_length=len(payload)),
        method="DELETE",
    )
    with urlopen(request):
        return


def migrate_tenant_media_references_to_remote(
    *,
    db: Session,
    target_backend: str = MASTER_TENANT_MEDIA_STORAGE_BACKEND_SUPABASE_STORAGE,
    keep_local_files: bool = True,
) -> dict[str, int]:
    product_count = 0
    attachment_count = 0

    products = db.execute(select(Product).where(Product.image_path.is_not(None))).scalars().all()
    for product in products:
        current_url = str(product.image_path or "").strip()
        if not current_url.startswith("/static/uploads/products/"):
            continue
        absolute_path = _resolve_local_media_path(current_url)
        if not absolute_path.exists():
            continue
        content_type = _guess_content_type(absolute_path)
        stored = store_media_bytes(
            db=db,
            namespace="products",
            file_name=absolute_path.name,
            content_type=content_type,
            data=absolute_path.read_bytes(),
            old_file_url=None,
            backend_override=target_backend,
        )
        product.image_path = stored.file_url
        product_count += 1
        if not keep_local_files:
            _delete_local_media_object(current_url)

    attachments = db.execute(select(ExpenseAttachment)).scalars().all()
    for attachment in attachments:
        current_url = str(attachment.file_url or "").strip()
        if not current_url.startswith("/static/uploads/expenses/"):
            continue
        absolute_path = _resolve_local_media_path(current_url)
        if not absolute_path.exists():
            continue
        content_type = attachment.mime_type or _guess_content_type(absolute_path)
        stored = store_media_bytes(
            db=db,
            namespace="expenses",
            file_name=absolute_path.name,
            content_type=content_type,
            data=absolute_path.read_bytes(),
            old_file_url=None,
            backend_override=target_backend,
        )
        attachment.file_url = stored.file_url
        attachment.size_bytes = stored.size_bytes
        attachment_count += 1
        if not keep_local_files:
            _delete_local_media_object(current_url)

    return {
        "products_migrated": product_count,
        "expense_attachments_migrated": attachment_count,
    }


def extract_supabase_object_key(*, file_url: str, public_base_url: str | None) -> str | None:
    normalized_url = str(file_url or "").strip().rstrip("/")
    normalized_base = str(public_base_url or "").strip().rstrip("/")
    if not normalized_url or not normalized_base:
        return None
    prefix = normalized_base + "/"
    if not normalized_url.startswith(prefix):
        return None
    object_key = normalized_url.removeprefix(prefix).strip("/")
    return object_key or None


def _store_media_bytes_locally(
    *,
    namespace: MediaNamespace,
    file_name: str,
    data: bytes,
) -> StoredMediaObject:
    upload_dir = _local_upload_dir(namespace)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file_name).name.strip()
    full_path = upload_dir / safe_name
    full_path.write_bytes(data)
    return StoredMediaObject(
        file_url=f"/static/uploads/{namespace}/{safe_name}",
        storage_backend=MASTER_TENANT_MEDIA_STORAGE_BACKEND_LOCAL_STATIC,
        object_key=None,
        size_bytes=len(data),
    )


def _store_media_bytes_in_supabase(
    *,
    target: MediaStorageTarget,
    namespace: MediaNamespace,
    file_name: str,
    content_type: str,
    data: bytes,
) -> StoredMediaObject:
    object_key = build_media_object_key(
        tenant_code=target.tenant_code,
        namespace=namespace,
        file_name=file_name,
    )
    request = Request(
        url=f"{target.project_url}/storage/v1/object/{quote(str(target.bucket), safe='')}/{quote(object_key, safe='/')}",
        data=data,
        headers=_supabase_storage_headers(content_type=content_type, content_length=len(data)),
        method="POST",
    )
    with urlopen(request):
        return StoredMediaObject(
            file_url=f"{target.public_base_url}/{object_key}",
            storage_backend=MASTER_TENANT_MEDIA_STORAGE_BACKEND_SUPABASE_STORAGE,
            object_key=object_key,
            size_bytes=len(data),
        )


def _supabase_storage_headers(*, content_type: str, content_length: int) -> dict[str, str]:
    settings = load_settings()
    if not settings.media_storage_service_role_key:
        raise RuntimeError("MEDIA_STORAGE_SERVICE_ROLE_KEY is required for Supabase media writes.")
    return {
        "Authorization": f"Bearer {settings.media_storage_service_role_key}",
        "apikey": settings.media_storage_service_role_key,
        "x-upsert": "true",
        "Content-Type": content_type,
        "Content-Length": str(content_length),
    }


def _local_upload_dir(namespace: MediaNamespace) -> Path:
    if namespace == "products":
        return PRODUCT_UPLOAD_DIR
    return EXPENSE_ATTACHMENT_UPLOAD_DIR


def _resolve_local_media_path(file_url: str) -> Path:
    return APP_ROOT / Path(str(file_url).lstrip("/"))


def _delete_local_media_object(file_url: str) -> None:
    full_path = _resolve_local_media_path(file_url)
    if full_path.exists() and full_path.is_file():
        full_path.unlink()


def _normalize_tenant_code(tenant_code: str | None) -> str:
    normalized = str(tenant_code or "").strip().lower()
    return normalized or "shared"


def _guess_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    if suffix == ".pdf":
        return "application/pdf"
    return "application/octet-stream"


def generate_media_file_name(*, extension: str, original_stem: str | None = None) -> str:
    normalized_extension = extension if extension.startswith(".") else f".{extension}"
    stem = Path(original_stem or "").stem.strip() if original_stem else ""
    safe_stem = "".join(ch if (ch.isalnum() or ch in {"-", "_"}) else "_" for ch in stem).strip("_")
    if safe_stem:
        return f"{uuid4().hex}_{safe_stem}{normalized_extension}"
    return f"{uuid4().hex}{normalized_extension}"

