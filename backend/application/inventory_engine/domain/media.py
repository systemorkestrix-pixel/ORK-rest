import base64
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Product

APP_ROOT = Path(__file__).resolve().parents[3] / "app"
PRODUCT_UPLOAD_DIR = APP_ROOT / "static" / "uploads" / "products"
EXPENSE_ATTACHMENT_UPLOAD_DIR = APP_ROOT / "static" / "uploads" / "expenses"
MAX_IMAGE_SIZE_BYTES = 2 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_EXPENSE_ATTACHMENT_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_EXPENSE_ATTACHMENT_TYPES: dict[str, str] = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def upload_product_image(
    db: Session,
    *,
    product_id: int,
    data_base64: str,
    mime_type: str,
) -> Product:
    product = db.execute(select(Product).where(Product.id == product_id)).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المنتج غير موجود.")

    product.image_path = save_product_image(
        data_base64=data_base64,
        mime_type=mime_type,
        old_path=product.image_path,
    )
    return db.execute(select(Product).where(Product.id == product_id)).scalar_one()


def save_product_image(*, data_base64: str, mime_type: str, old_path: str | None = None) -> str:
    if mime_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="نوع الصورة غير مدعوم.")

    try:
        data = base64.b64decode(data_base64, validate=True)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="البيانات المرسلة للصورة غير صالحة.") from error

    if len(data) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="حجم الصورة أكبر من الحد المسموح.")

    PRODUCT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename: str
    full_path: Path

    try:
        from PIL import Image

        try:
            image = Image.open(BytesIO(data))
            image = image.convert("RGB")
        except Exception as error:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="تعذر معالجة الصورة.") from error

        image.thumbnail((1200, 1200))
        filename = f"{uuid4().hex}.webp"
        full_path = PRODUCT_UPLOAD_DIR / filename
        image.save(full_path, format="WEBP", quality=85, method=6)
    except ModuleNotFoundError:
        # Fallback mode when Pillow is unavailable: keep original bytes after signature validation.
        signatures = {
            "image/jpeg": (b"\xFF\xD8\xFF", ".jpg"),
            "image/png": (b"\x89PNG\r\n\x1A\n", ".png"),
            "image/webp": (b"RIFF", ".webp"),
        }
        expected_header, extension = signatures[mime_type]
        is_valid = data.startswith(expected_header)
        if mime_type == "image/webp":
            is_valid = data.startswith(b"RIFF") and b"WEBP" in data[:16]
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ملف الصورة غير صالح.")

        filename = f"{uuid4().hex}{extension}"
        full_path = PRODUCT_UPLOAD_DIR / filename
        full_path.write_bytes(data)

    if old_path:
        old = APP_ROOT / Path(old_path.lstrip("/"))
        if old.exists() and old.is_file():
            old.unlink()

    return f"/static/uploads/products/{filename}"


def remove_static_file(file_url: str | None) -> None:
    if not file_url:
        return
    relative = file_url.lstrip("/")
    if not relative:
        return
    full_path = APP_ROOT / Path(relative)
    if full_path.exists() and full_path.is_file():
        full_path.unlink()


def _sanitize_attachment_name(raw_name: str | None, *, fallback_stem: str) -> str:
    source = (raw_name or fallback_stem).strip()
    if not source:
        source = fallback_stem
    source = Path(source).name
    safe = "".join(ch if (ch.isalnum() or ch in {"-", "_", ".", " "}) else "_" for ch in source).strip(" .")
    return safe or fallback_stem


def _validate_attachment_signature(*, mime_type: str, data: bytes) -> None:
    if mime_type == "application/pdf":
        if not data.startswith(b"%PDF"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ملف PDF غير صالح.")
        return
    if mime_type == "image/jpeg":
        if not data.startswith(b"\xFF\xD8\xFF"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ملف الصورة غير صالح.")
        return
    if mime_type == "image/png":
        if not data.startswith(b"\x89PNG\r\n\x1A\n"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ملف الصورة غير صالح.")
        return
    if mime_type == "image/webp":
        if not (data.startswith(b"RIFF") and b"WEBP" in data[:16]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ملف الصورة غير صالح.")
        return
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="نوع الملف غير مدعوم.")


def save_expense_attachment(*, data_base64: str, mime_type: str, file_name: str | None) -> tuple[str, str, int]:
    extension = ALLOWED_EXPENSE_ATTACHMENT_TYPES.get(mime_type)
    if extension is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="نوع الملف غير مدعوم.")

    try:
        data = base64.b64decode(data_base64, validate=True)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="بيانات الملف غير صالحة.") from error

    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="الملف فارغ.")
    if len(data) > MAX_EXPENSE_ATTACHMENT_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="حجم الملف أكبر من الحد المسموح.")

    _validate_attachment_signature(mime_type=mime_type, data=data)
    EXPENSE_ATTACHMENT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = _sanitize_attachment_name(file_name, fallback_stem="expense_attachment")
    safe_stem = Path(safe_name).stem.strip() or "expense_attachment"
    final_name = f"{safe_stem}{extension}"
    stored_name = f"{uuid4().hex}_{final_name}"
    full_path = EXPENSE_ATTACHMENT_UPLOAD_DIR / stored_name
    full_path.write_bytes(data)
    return f"/static/uploads/expenses/{stored_name}", final_name, len(data)


__all__ = [
    "remove_static_file",
    "save_expense_attachment",
    "save_product_image",
    "upload_product_image",
]
