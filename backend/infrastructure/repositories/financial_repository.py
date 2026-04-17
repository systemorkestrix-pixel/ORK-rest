from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.guards.financial_invariant_guard import assert_financial_invariants
from app.models import (
    CashboxMovement,
    DeliverySettlement,
    Expense,
    ExpenseAttachment,
    ExpenseCostCenter,
    FinancialTransaction,
    Order,
    ShiftClosure,
)
from application.financial_engine.domain.helpers import get_order_or_404
from app.orchestration.service_bridge import (
    app_approve_expense,
    app_close_cash_shift,
    app_create_expense,
    app_create_expense_attachment,
    app_create_expense_cost_center,
    app_delete_expense,
    app_delete_expense_attachment,
    app_get_delivery_accounting_migration_status,
    app_list_expense_cost_centers,
    app_list_shift_closures,
    app_reject_expense,
    app_refund_order,
    app_run_delivery_accounting_backfill,
    app_update_expense,
    app_update_expense_cost_center,
)
from application.financial_engine.domain import collect_order_payment as collect_order_payment_domain
from application.financial_engine.domain import record_driver_payout as record_driver_payout_domain
from application.financial_engine.domain import record_driver_remittance as record_driver_remittance_domain
from application.financial_engine.domain import settle_delivery_order as settle_delivery_order_domain


class FinancialRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def close_shift(
        self,
        *,
        closed_by: int,
        opening_cash: float,
        actual_cash: float,
        note: str | None = None,
    ) -> ShiftClosure:
        return app_close_cash_shift(
            self._db,
            closed_by=closed_by,
            opening_cash=opening_cash,
            actual_cash=actual_cash,
            note=note,
        )

    def approve_expense(
        self,
        *,
        expense_id: int,
        approved_by: int,
        note: str | None,
    ) -> Expense:
        return app_approve_expense(
            self._db,
            expense_id=expense_id,
            approved_by=approved_by,
            note=note,
        )

    def reject_expense(
        self,
        *,
        expense_id: int,
        rejected_by: int,
        note: str | None,
    ) -> Expense:
        return app_reject_expense(
            self._db,
            expense_id=expense_id,
            rejected_by=rejected_by,
            note=note,
        )

    def create_expense(
        self,
        *,
        title: str,
        category: str,
        cost_center_id: int,
        amount: float,
        note: str | None,
        created_by: int,
    ) -> Expense:
        return app_create_expense(
            self._db,
            title=title,
            category=category,
            cost_center_id=cost_center_id,
            amount=amount,
            note=note,
            created_by=created_by,
        )

    def update_expense(
        self,
        *,
        expense_id: int,
        title: str,
        category: str,
        cost_center_id: int,
        amount: float,
        note: str | None,
        updated_by: int,
    ) -> Expense:
        return app_update_expense(
            self._db,
            expense_id=expense_id,
            title=title,
            category=category,
            cost_center_id=cost_center_id,
            amount=amount,
            note=note,
            updated_by=updated_by,
        )

    def create_expense_attachment(
        self,
        *,
        expense_id: int,
        file_name: str | None,
        mime_type: str,
        data_base64: str,
        uploaded_by: int,
    ) -> ExpenseAttachment:
        return app_create_expense_attachment(
            self._db,
            expense_id=expense_id,
            file_name=file_name,
            mime_type=mime_type,
            data_base64=data_base64,
            uploaded_by=uploaded_by,
        )

    def delete_expense_attachment(
        self,
        *,
        expense_id: int,
        attachment_id: int,
        deleted_by: int,
    ) -> None:
        app_delete_expense_attachment(
            self._db,
            expense_id=expense_id,
            attachment_id=attachment_id,
            deleted_by=deleted_by,
        )

    def create_expense_cost_center(
        self,
        *,
        code: str,
        name: str,
        active: bool,
        actor_id: int,
    ) -> ExpenseCostCenter:
        return app_create_expense_cost_center(
            self._db,
            code=code,
            name=name,
            active=active,
            actor_id=actor_id,
        )

    def update_expense_cost_center(
        self,
        *,
        center_id: int,
        code: str,
        name: str,
        active: bool,
        actor_id: int,
    ) -> ExpenseCostCenter:
        return app_update_expense_cost_center(
            self._db,
            center_id=center_id,
            code=code,
            name=name,
            active=active,
            actor_id=actor_id,
        )

    def delete_expense(self, *, expense_id: int) -> None:
        app_delete_expense(self._db, expense_id=expense_id)

    def collect_order_payment(
        self,
        *,
        order_id: int,
        collected_by: int,
        amount_received: float | None,
    ) -> Order:
        collect_order_payment_domain(
            self._db,
            order_id=order_id,
            collected_by=collected_by,
            amount_received=amount_received,
            get_order=get_order_or_404,
        )
        assert_financial_invariants(self._db)
        return get_order_or_404(self._db, order_id)

    def refund_order(
        self,
        *,
        order_id: int,
        refunded_by: int,
        note: str | None,
    ) -> Order:
        return app_refund_order(
            self._db,
            order_id=order_id,
            refunded_by=refunded_by,
            note=note,
        )

    def settle_delivery_order(
        self,
        *,
        order_id: int,
        performed_by: int,
    ) -> DeliverySettlement:
        return settle_delivery_order_domain(
            self._db,
            order_id=order_id,
            performed_by=performed_by,
        )

    def record_driver_remittance(
        self,
        *,
        settlement_id: int,
        amount: float,
        performed_by: int,
        cash_channel: str,
        note: str | None,
    ) -> DeliverySettlement:
        return record_driver_remittance_domain(
            self._db,
            settlement_id=settlement_id,
            amount=amount,
            performed_by=performed_by,
            cash_channel=cash_channel,
            note=note,
        )

    def record_driver_payout(
        self,
        *,
        settlement_id: int,
        amount: float,
        performed_by: int,
        cash_channel: str,
        note: str | None,
    ) -> DeliverySettlement:
        return record_driver_payout_domain(
            self._db,
            settlement_id=settlement_id,
            amount=amount,
            performed_by=performed_by,
            cash_channel=cash_channel,
            note=note,
        )

    def run_delivery_accounting_backfill(
        self,
        *,
        actor_id: int,
        limit: int,
        dry_run: bool,
    ) -> dict[str, object]:
        return app_run_delivery_accounting_backfill(
            self._db,
            actor_id=actor_id,
            limit=limit,
            dry_run=dry_run,
        )

    def list_financial_transactions(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[FinancialTransaction]:
        return (
            self._db.execute(
                select(FinancialTransaction)
                .order_by(FinancialTransaction.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            .scalars()
            .all()
        )

    def list_delivery_settlements(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[DeliverySettlement]:
        return (
            self._db.execute(
                select(DeliverySettlement)
                .order_by(DeliverySettlement.recognized_at.desc(), DeliverySettlement.id.desc())
                .offset(offset)
                .limit(limit)
            )
            .scalars()
            .all()
        )

    def list_cashbox_movements(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[CashboxMovement]:
        return (
            self._db.execute(
                select(CashboxMovement)
                .order_by(CashboxMovement.created_at.desc(), CashboxMovement.id.desc())
                .offset(offset)
                .limit(limit)
            )
            .scalars()
            .all()
        )

    def list_shift_closures(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[ShiftClosure]:
        return app_list_shift_closures(self._db, offset=offset, limit=limit)

    def list_expense_cost_centers(
        self,
        *,
        include_inactive: bool,
        offset: int,
        limit: int,
    ) -> list[ExpenseCostCenter]:
        return app_list_expense_cost_centers(
            self._db,
            include_inactive=include_inactive,
            offset=offset,
            limit=limit,
        )

    def list_expenses(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[Expense]:
        return (
            self._db.execute(
                select(Expense)
                .options(joinedload(Expense.attachments), joinedload(Expense.cost_center))
                .order_by(Expense.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            .unique()
            .scalars()
            .all()
        )

    def get_delivery_accounting_migration_status(self) -> dict[str, object]:
        return app_get_delivery_accounting_migration_status(self._db)
