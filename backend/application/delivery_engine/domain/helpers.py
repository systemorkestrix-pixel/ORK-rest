from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import DriverStatus
from app.models import DeliveryDriver


def get_delivery_driver_for_user(db: Session, *, user_id: int, require_active: bool = True) -> DeliveryDriver:
    driver = db.execute(select(DeliveryDriver).where(DeliveryDriver.user_id == user_id)).scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يوجد ملف سائق توصيل مرتبط بهذا المستخدم.")
    if require_active and (not driver.active or driver.status == DriverStatus.INACTIVE.value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="سائق التوصيل غير نشط.")
    return driver
