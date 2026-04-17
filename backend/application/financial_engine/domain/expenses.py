from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import FinancialTransactionType
from app.models import Expense, ExpenseAttachment, ExpenseCostCenter
from application.financial_engine.domain.helpers import record_system_audit


def _resolve_expense_cost_center(
    db: Session,
    *,
    center_id: int,
    require_active: bool = True,
) -> ExpenseCostCenter:
    conditions = [ExpenseCostCenter.id == center_id]
    if require_active:
        conditions.append(ExpenseCostCenter.active.is_(True))
    center = db.execute(select(ExpenseCostCenter).where(*conditions)).scalar_one_or_none()
    if center is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="مركز التكلفة غير متاح.")
    return center


def create_expense(
    db: Session,
    *,
    title: str,
    category: str,
    cost_center_id: int,
    amount: float,
    note: str | None,
    created_by: int,
) -> Expense:
    center = _resolve_expense_cost_center(db, center_id=cost_center_id, require_active=True)
    expense = Expense(
        title=title,
        category=category,
        cost_center_id=center.id,
        amount=amount,
        note=note,
        status="pending",
        reviewed_by=None,
        reviewed_at=None,
        review_note=None,
        created_by=created_by,
    )
    db.add(expense)
    db.flush()
    record_system_audit(
        db,
        module="expenses",
        action="expense_submitted",
        entity_type="expense",
        entity_id=expense.id,
        user_id=created_by,
        description=f"إنشاء مصروف #{expense.id} وربطه بمركز التكلفة {center.name}.",
    )
    db.flush()
    return expense


def update_expense(
    db: Session,
    *,
    expense: Expense,
    title: str,
    category: str,
    cost_center_id: int,
    amount: float,
    note: str | None,
    updated_by: int,
    delete_transactions,
) -> Expense:
    if expense.status == "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن تعديل مصروف تمت الموافقة عليه.",
        )
    center = _resolve_expense_cost_center(db, center_id=cost_center_id, require_active=True)
    expense.title = title
    expense.category = category
    expense.cost_center_id = center.id
    expense.amount = amount
    expense.note = note
    expense.status = "pending"
    expense.reviewed_by = None
    expense.reviewed_at = None
    expense.review_note = None
    expense.updated_at = datetime.now(UTC)
    delete_transactions(db, expense_id=int(expense.id))
    record_system_audit(
        db,
        module="expenses",
        action="expense_resubmitted",
        entity_type="expense",
        entity_id=expense.id,
        user_id=updated_by,
        description=f"إعادة إرسال مصروف #{expense.id} وربطه بمركز التكلفة {center.name}.",
    )
    db.flush()
    return expense


def approve_expense(
    db: Session,
    *,
    expense: Expense | None = None,
    expense_id: int | None = None,
    approved_by: int,
    note: str | None,
    find_latest_transaction=None,
    create_transaction=None,
) -> Expense:
    if expense is None:
        if expense_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="المصرف غير محدد.")
        from app.repositories.financial_repository import create_financial_transaction, fetch_expense_by_id, find_latest_expense_transaction

        expense = fetch_expense_by_id(db, expense_id=expense_id)
        if expense is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المصرف غير موجود.")
        find_latest_transaction = find_latest_transaction or find_latest_expense_transaction
        create_transaction = create_transaction or create_financial_transaction

    if find_latest_transaction is None or create_transaction is None:
        from app.repositories.financial_repository import create_financial_transaction, find_latest_expense_transaction

        find_latest_transaction = find_latest_transaction or find_latest_expense_transaction
        create_transaction = create_transaction or create_financial_transaction

    if expense.status == "approved":
        return expense

    expense.status = "approved"
    expense.reviewed_by = approved_by
    expense.reviewed_at = datetime.now(UTC)
    expense.review_note = note
    expense.updated_at = datetime.now(UTC)
    center_name = expense.cost_center.name if expense.cost_center is not None else "غير محدد"

    tx = find_latest_transaction(
        db,
        expense_id=int(expense.id),
        tx_type=FinancialTransactionType.EXPENSE.value,
    )
    if tx:
        tx.amount = expense.amount
        tx.created_by = approved_by
        tx.note = f"Expense approved: {expense.title} | Cost center: {center_name}"
    else:
        create_transaction(
            db,
            order_id=None,
            expense_id=int(expense.id),
            amount=float(expense.amount),
            tx_type=FinancialTransactionType.EXPENSE.value,
            created_by=approved_by,
            note=f"Expense approved: {expense.title} | Cost center: {center_name}",
        )

    record_system_audit(
        db,
        module="expenses",
        action="expense_approved",
        entity_type="expense",
        entity_id=expense.id,
        user_id=approved_by,
        description=f"اعتماد مصروف #{expense.id} لمركز التكلفة {center_name}.",
    )
    db.flush()
    return expense


def reject_expense(
    db: Session,
    *,
    expense: Expense | None = None,
    expense_id: int | None = None,
    rejected_by: int,
    note: str | None,
    delete_transactions=None,
) -> Expense:
    if expense is None:
        if expense_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="المصرف غير محدد.")
        from app.repositories.financial_repository import delete_expense_transactions, fetch_expense_by_id

        expense = fetch_expense_by_id(db, expense_id=expense_id)
        if expense is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المصرف غير موجود.")
        delete_transactions = delete_transactions or delete_expense_transactions

    if delete_transactions is None:
        from app.repositories.financial_repository import delete_expense_transactions

        delete_transactions = delete_transactions or delete_expense_transactions

    if expense.status == "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن رفض مصروف تمت الموافقة عليه.",
        )

    expense.status = "rejected"
    expense.reviewed_by = rejected_by
    expense.reviewed_at = datetime.now(UTC)
    expense.review_note = note
    expense.updated_at = datetime.now(UTC)
    delete_transactions(db, expense_id=int(expense.id))
    record_system_audit(
        db,
        module="expenses",
        action="expense_rejected",
        entity_type="expense",
        entity_id=expense.id,
        user_id=rejected_by,
        description=f"رفض مصروف #{expense.id}.",
    )
    db.flush()
    return expense


def create_expense_attachment(
    db: Session,
    *,
    expense: Expense,
    file_name: str | None,
    mime_type: str,
    data_base64: str,
    uploaded_by: int,
    save_attachment,
) -> ExpenseAttachment:
    if expense.status == "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن تعديل المرفقات بعد اعتماد المصروف.",
        )

    file_url, final_name, size_bytes = save_attachment(
        data_base64=data_base64,
        mime_type=mime_type,
        file_name=file_name,
    )

    attachment = ExpenseAttachment(
        expense_id=expense.id,
        file_name=final_name,
        file_url=file_url,
        mime_type=mime_type,
        size_bytes=size_bytes,
        uploaded_by=uploaded_by,
    )
    db.add(attachment)
    db.flush()
    record_system_audit(
        db,
        module="expenses",
        action="expense_attachment_added",
        entity_type="expense",
        entity_id=expense.id,
        user_id=uploaded_by,
        description=f"إضافة مرفق للمصروف #{expense.id}.",
    )
    return attachment


def delete_expense_attachment(
    db: Session,
    *,
    expense: Expense,
    attachment: ExpenseAttachment,
    deleted_by: int,
) -> str | None:
    if expense.status == "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن تعديل المرفقات بعد اعتماد المصروف.",
        )

    file_url = attachment.file_url
    db.delete(attachment)
    record_system_audit(
        db,
        module="expenses",
        action="expense_attachment_deleted",
        entity_type="expense",
        entity_id=expense.id,
        user_id=deleted_by,
        description=f"حذف مرفق من المصروف #{expense.id}.",
    )
    return file_url


def delete_expense(
    db: Session,
    *,
    expense: Expense,
    delete_transactions,
) -> list[str]:
    if expense.status == "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن حذف مصروف تمت الموافقة عليه.",
        )
    attachments = db.execute(
        select(ExpenseAttachment).where(ExpenseAttachment.expense_id == int(expense.id))
    ).scalars().all()
    file_urls = [attachment.file_url for attachment in attachments]
    delete_transactions(db, expense_id=int(expense.id))
    for attachment in attachments:
        db.delete(attachment)
    db.delete(expense)
    return file_urls
