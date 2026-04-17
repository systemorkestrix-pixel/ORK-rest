from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import TableStatus
from ..models import DeliveryAssignment, DeliveryDriver, Order, User, Expense, ExpenseAttachment, ExpenseCostCenter, ShiftClosure, Product, ProductCategory, RestaurantTable
from app.schemas import TableSessionSettlementOut


def app_get_delivery_fee_setting(db: Session) -> float:
    from application.core_engine.domain import get_delivery_fee_setting

    return get_delivery_fee_setting(db)


def app_get_delivery_location_provider_settings(db: Session) -> dict[str, object]:
    from application.core_engine.domain import get_delivery_location_provider_settings

    return get_delivery_location_provider_settings(db)


def app_get_system_context_settings(db: Session) -> dict[str, object]:
    from application.core_engine.domain import get_system_context_settings

    return get_system_context_settings(db)


def app_get_storefront_settings(db: Session) -> dict[str, object]:
    from application.core_engine.domain import get_storefront_settings

    return get_storefront_settings(db)


def app_get_telegram_bot_settings(db: Session) -> dict[str, object]:
    from application.core_engine.domain.settings import get_telegram_bot_settings

    return get_telegram_bot_settings(db)


def app_get_telegram_bot_health(db: Session) -> dict[str, object]:
    from application.core_engine.domain.settings import get_telegram_bot_health

    return get_telegram_bot_health(db)


def get_system_order_actor_prefix() -> str:
    from application.operations_engine.domain.constants import SYSTEM_ORDER_ACTOR_PREFIX

    return SYSTEM_ORDER_ACTOR_PREFIX


def app_get_delivery_policy_settings(db: Session) -> dict[str, object]:
    from application.core_engine.domain import get_delivery_policy_settings

    return get_delivery_policy_settings(db)

def app_update_delivery_fee_setting(db: Session, *, delivery_fee: float, actor_id: int) -> float:
    from application.core_engine.domain import update_delivery_fee_setting

    return update_delivery_fee_setting(db, delivery_fee=delivery_fee, actor_id=actor_id)


def app_update_delivery_policy_settings(
    db: Session,
    *,
    min_order_amount: float,
    auto_notify_team: bool,
    actor_id: int,
) -> dict[str, object]:
    from application.core_engine.domain import update_delivery_policy_settings

    return update_delivery_policy_settings(
        db,
        min_order_amount=min_order_amount,
        auto_notify_team=auto_notify_team,
        actor_id=actor_id,
    )


def app_update_delivery_location_provider_settings(
    db: Session,
    *,
    provider: str,
    enabled: bool,
    geonames_username: str | None,
    country_codes: list[str],
    cache_ttl_hours: int,
    actor_id: int,
) -> dict[str, object]:
    from application.core_engine.domain import update_delivery_location_provider_settings

    return update_delivery_location_provider_settings(
        db,
        provider=provider,
        enabled=enabled,
        geonames_username=geonames_username,
        country_codes=country_codes,
        cache_ttl_hours=cache_ttl_hours,
        actor_id=actor_id,
    )


def app_update_system_context_settings(
    db: Session,
    *,
    country_code: str,
    country_name: str,
    currency_code: str,
    currency_name: str,
    currency_symbol: str,
    currency_decimal_places: int,
    actor_id: int,
) -> dict[str, object]:
    from application.core_engine.domain import update_system_context_settings

    return update_system_context_settings(
        db,
        country_code=country_code,
        country_name=country_name,
        currency_code=currency_code,
        currency_name=currency_name,
        currency_symbol=currency_symbol,
        currency_decimal_places=currency_decimal_places,
        actor_id=actor_id,
    )


def app_update_storefront_settings(
    db: Session,
    *,
    brand_name: str,
    brand_mark: str,
    brand_icon: str,
    brand_tagline: str | None,
    socials: list[dict[str, object]],
    actor_id: int,
) -> dict[str, object]:
    from application.core_engine.domain import update_storefront_settings

    return update_storefront_settings(
        db,
        brand_name=brand_name,
        brand_mark=brand_mark,
        brand_icon=brand_icon,
        brand_tagline=brand_tagline,
        socials=socials,
        actor_id=actor_id,
    )


def app_update_telegram_bot_settings(
    db: Session,
    *,
    enabled: bool,
    bot_token: str | None,
    bot_username: str | None,
    actor_id: int,
) -> dict[str, object]:
    from application.core_engine.domain.settings import update_telegram_bot_settings

    return update_telegram_bot_settings(
        db,
        enabled=enabled,
        bot_token=bot_token,
        bot_username=bot_username,
        actor_id=actor_id,
    )


def app_ensure_delivery_operational(db: Session) -> None:
    from application.operations_engine.domain import ensure_delivery_operational

    ensure_delivery_operational(db)


def app_ensure_kitchen_operational(db: Session) -> None:
    from application.operations_engine.domain import ensure_kitchen_operational

    ensure_kitchen_operational(db)


def app_resolve_order_creator_id(db: Session, created_by: int | None, fallback_actor: str) -> int:
    from application.operations_engine.domain import resolve_order_creator_id
    from app.security import hash_password
    from app.tx import transaction_scope

    return resolve_order_creator_id(
        db,
        created_by,
        fallback_actor=fallback_actor,
        transaction_scope=transaction_scope,
        hash_password=hash_password,
    )


def app_count_active_delivery_users(db: Session) -> int:
    from application.operations_engine.domain import count_active_delivery_users

    return count_active_delivery_users(db)


def app_refresh_table_occupancy_state(db: Session, *, table_id: int) -> None:
    from application.operations_engine.domain.table_sessions import refresh_table_occupancy_state

    refresh_table_occupancy_state(db, table_id=table_id)


def app_mark_cash_paid(db: Session, order: Order, amount_received: float | None, user_id: int) -> dict[str, float | str | datetime | int]:
    from application.financial_engine.domain.collections import mark_cash_paid

    return mark_cash_paid(db, order=order, amount_received=amount_received, user_id=user_id)


def app_record_delivery_completion(
    db: Session,
    *,
    order: Order,
    assignment: DeliveryAssignment,
    driver: DeliveryDriver,
    amount_received: float | None,
    actor_id: int,
) -> dict[str, float | str | datetime | int | None]:
    from application.financial_engine.domain.delivery_accounting import record_delivery_completion

    return record_delivery_completion(
        db,
        order=order,
        assignment=assignment,
        driver=driver,
        amount_received=amount_received,
        actor_id=actor_id,
    )

def app_save_expense_attachment(*, data_base64: str, mime_type: str, file_name: str | None) -> tuple[str, str, int]:
    from application.inventory_engine.domain.media import save_expense_attachment

    return save_expense_attachment(data_base64=data_base64, mime_type=mime_type, file_name=file_name)


def app_validate_password_policy(*, password: str, username: str | None = None) -> None:
    from application.core_engine.domain.auth import validate_password_policy

    validate_password_policy(password=password, username=username)


def app_revoke_active_refresh_tokens_for_user(db: Session, *, user_id: int) -> int:
    from application.core_engine.domain.auth import revoke_active_refresh_tokens_for_user

    return revoke_active_refresh_tokens_for_user(db, user_id=user_id)


def app_ensure_delivery_capacity_reduction_allowed(db: Session) -> None:
    from application.operations_engine.domain import ensure_delivery_capacity_reduction_allowed

    ensure_delivery_capacity_reduction_allowed(db)


def app_ensure_kitchen_capacity_reduction_allowed(db: Session) -> None:
    from application.operations_engine.domain import ensure_kitchen_capacity_reduction_allowed

    ensure_kitchen_capacity_reduction_allowed(db)


def app_remove_static_file(file_url: str | None) -> None:
    from application.inventory_engine.domain.media import remove_static_file

    remove_static_file(file_url)


def get_operational_capabilities(db: Session) -> dict[str, object]:
    from application.operations_engine.domain import get_operational_capabilities as _get_operational_capabilities

    return _get_operational_capabilities(db)


def kitchen_monitor_summary(db: Session, *, metrics_window: str = "day") -> dict[str, int | float | str]:
    from application.intelligence_engine.domain.reports import (
        kitchen_monitor_summary as _kitchen_monitor_summary,
    )

    return _kitchen_monitor_summary(db, metrics_window=metrics_window)


def get_order_polling_ms(db: Session) -> int:
    from application.core_engine.domain import get_order_polling_ms as _get_order_polling_ms

    return _get_order_polling_ms(db)


def get_kitchen_metrics_window(db: Session) -> str:
    from application.core_engine.domain import get_kitchen_metrics_window as _get_kitchen_metrics_window

    return _get_kitchen_metrics_window(db)


def app_attach_sent_to_kitchen_at(db: Session, orders: list[Order]) -> list[Order]:
    from application.operations_engine.domain import attach_sent_to_kitchen_at
    from ..repositories.orders_repository import fetch_sent_to_kitchen_timestamps

    return attach_sent_to_kitchen_at(
        db,
        orders,
        fetch_sent_to_kitchen_timestamps=fetch_sent_to_kitchen_timestamps,
    )


def app_create_order(
    db: Session,
    *,
    payload,
    created_by: int | None,
    source_actor: str = "system",
) -> Order:
    from application.operations_engine.domain import create_order
    from application.operations_engine.domain.delivery_location_pricing import (
        resolve_delivery_pricing_for_order,
    )
    from application.operations_engine.domain.helpers import (
        get_order_or_404,
        record_transition as _record_transition,
    )
    from application.operations_engine.domain.table_sessions import get_table_or_404
    from app.repositories.orders_repository import fetch_available_sellable_products
    from app.tx import transaction_scope

    with transaction_scope(db):
        order = create_order(
            db,
            payload=payload,
            created_by=created_by,
            source_actor=source_actor,
            ensure_delivery_operational=app_ensure_delivery_operational,
            fetch_products=fetch_available_sellable_products,
            get_table=get_table_or_404,
            resolve_order_creator_id=app_resolve_order_creator_id,
            get_delivery_policy_settings=app_get_delivery_policy_settings,
            resolve_delivery_pricing=resolve_delivery_pricing_for_order,
            record_transition=_record_transition,
        )

    return get_order_or_404(db, order.id)


def app_claim_delivery_order(
    db: Session,
    *,
    order_id: int,
    actor_id: int,
) -> DeliveryAssignment:
    from application.delivery_engine.domain.assignments import claim_delivery_order

    return claim_delivery_order(db, order_id=order_id, actor_id=actor_id)


def app_start_delivery(
    db: Session,
    *,
    order_id: int,
    actor_id: int,
) -> Order:
    from application.delivery_engine.domain.assignments import start_delivery

    return start_delivery(db, order_id=order_id, actor_id=actor_id)


def app_emergency_fail_delivery_order(
    db: Session,
    *,
    order_id: int,
    performed_by: int,
    reason_code: str,
    reason_note: str | None = None,
) -> Order:
    from application.delivery_engine.domain.emergencies import emergency_fail_delivery_order

    return emergency_fail_delivery_order(
        db,
        order_id=order_id,
        performed_by=performed_by,
        reason_code=reason_code,
        reason_note=reason_note,
    )


def app_create_user(
    db: Session,
    *,
    name: str,
    username: str,
    password: str,
    role: str,
    active: bool,
    delivery_phone: str | None,
    delivery_vehicle: str | None,
    actor_id: int,
) -> User:
    from application.core_engine.domain.users import create_user

    return create_user(
        db,
        name=name,
        username=username,
        password=password,
        role=role,
        active=active,
        delivery_phone=delivery_phone,
        delivery_vehicle=delivery_vehicle,
        actor_id=actor_id,
    )


def app_update_user(
    db: Session,
    *,
    user_id: int,
    name: str,
    role: str,
    active: bool,
    password: str | None,
    delivery_phone: str | None,
    delivery_vehicle: str | None,
    actor_id: int,
    allow_manager_self_update: bool = False,
) -> User:
    from application.core_engine.domain.users import update_user

    return update_user(
        db,
        user_id=user_id,
        name=name,
        role=role,
        active=active,
        password=password,
        delivery_phone=delivery_phone,
        delivery_vehicle=delivery_vehicle,
        actor_id=actor_id,
        allow_manager_self_update=allow_manager_self_update,
    )


def app_delete_user_permanently(db: Session, *, user_id: int, actor_id: int) -> None:
    from application.core_engine.domain.users import delete_user_permanently

    delete_user_permanently(db, user_id=user_id, actor_id=actor_id)


def app_update_user_permissions_profile(
    db: Session,
    *,
    user_id: int,
    allow: list[str] | None,
    deny: list[str] | None,
    actor_id: int,
) -> dict[str, object]:
    from application.core_engine.domain.users import update_user_permissions_profile

    return update_user_permissions_profile(
        db,
        user_id=user_id,
        allow=allow,
        deny=deny,
        actor_id=actor_id,
    )


def app_login_user(db: Session, *, username: str, password: str, role: str):
    from application.core_engine.domain.auth import login_user

    return login_user(db, username=username, password=password, role=role)


def app_refresh_user_tokens(db: Session, *, refresh_token: str):
    from application.core_engine.domain.auth import refresh_user_tokens

    return refresh_user_tokens(db, refresh_token)


def app_revoke_refresh_token(db: Session, *, refresh_token: str):
    from application.core_engine.domain.auth import revoke_refresh_token

    return revoke_refresh_token(db, refresh_token)


def app_revoke_user_refresh_sessions(db: Session, *, user_id: int, actor_id: int) -> int:
    from application.core_engine.domain.auth import revoke_user_refresh_sessions

    return revoke_user_refresh_sessions(db, user_id=user_id, actor_id=actor_id)


def app_update_operational_setting(db: Session, *, key: str, value: str, actor_id: int) -> dict[str, object]:
    from application.core_engine.domain import update_operational_setting

    return update_operational_setting(db, key=key, value=value, actor_id=actor_id)


def app_create_system_backup(db: Session, *, actor_id: int) -> dict[str, object]:
    from application.core_engine.domain import create_system_backup

    return create_system_backup(db, actor_id=actor_id)


def app_restore_system_backup(
    db: Session,
    *,
    filename: str,
    confirm_phrase: str,
    actor_id: int,
) -> dict[str, object]:
    from application.core_engine.domain import restore_system_backup

    return restore_system_backup(db, filename=filename, confirm_phrase=confirm_phrase, actor_id=actor_id)


def app_list_permissions_catalog(*, role: str | None) -> list[dict[str, object]]:
    from application.core_engine.domain.users import list_permissions_catalog

    return list_permissions_catalog(role=role)


def app_get_user_permissions_profile(db: Session, *, user_id: int) -> dict[str, object]:
    from application.core_engine.domain.users import get_user_permissions_profile

    return get_user_permissions_profile(db, user_id=user_id)


def app_list_user_refresh_sessions(
    db: Session,
    *,
    user_id: int,
    offset: int,
    limit: int,
) -> list[dict[str, object]]:
    from application.core_engine.domain.auth import list_user_refresh_sessions

    return list_user_refresh_sessions(db, user_id=user_id, offset=offset, limit=limit)


def app_list_operational_settings(db: Session, *, offset: int, limit: int) -> list[dict[str, object]]:
    from application.core_engine.domain import list_operational_settings

    return list_operational_settings(db, offset=offset, limit=limit)


def app_list_system_backups(*, offset: int, limit: int) -> list[dict[str, object]]:
    from application.core_engine.domain import list_system_backups

    return list_system_backups(offset=offset, limit=limit)


def app_record_security_event(
    db: Session,
    *,
    event_type: str,
    success: bool,
    severity: str,
    username: str | None,
    role: str | None,
    user_id: int | None,
    ip_address: str | None,
    user_agent: str | None,
    detail: str | None,
) -> None:
    from application.core_engine.domain.auth import record_security_event

    record_security_event(
        db,
        event_type=event_type,
        success=success,
        severity=severity,
        username=username,
        role=role,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        detail=detail,
    )


def app_create_table(db: Session, *, status_value: str) -> RestaurantTable:
    from application.operations_engine.domain.table_sessions import create_table

    return create_table(db, status_value=TableStatus(status_value))


def app_update_table(db: Session, *, table_id: int, status_value: str) -> RestaurantTable:
    from application.operations_engine.domain.table_sessions import update_table

    return update_table(db, table_id=table_id, status_value=TableStatus(status_value))


def app_delete_table(db: Session, *, table_id: int) -> None:
    from application.operations_engine.domain.table_sessions import delete_table

    delete_table(db, table_id=table_id)


def app_settle_table_session(
    db: Session,
    *,
    table_id: int,
    performed_by: int,
    amount_received: float | None = None,
) -> TableSessionSettlementOut:
    from application.operations_engine.domain.table_sessions import settle_table_session

    return settle_table_session(
        db,
        table_id=table_id,
        performed_by=performed_by,
        amount_received=amount_received,
    )


def app_list_tables_with_session_summary(
    db: Session,
    *,
    offset: int = 0,
    limit: int | None = None,
    table_ids: list[int] | None = None,
) -> list[dict[str, object]]:
    from application.operations_engine.domain.table_sessions import list_tables_with_session_summary

    return list_tables_with_session_summary(
        db,
        offset=offset,
        limit=limit,
        table_ids=table_ids,
    )


def app_list_active_table_sessions(db: Session, *, offset: int, limit: int) -> list[dict[str, object]]:
    from application.operations_engine.domain.table_sessions import list_active_table_sessions

    return list_active_table_sessions(db, offset=offset, limit=limit)


def app_get_table_session_snapshot(db: Session, *, table_id: int) -> dict[str, object]:
    from application.operations_engine.domain.table_sessions import get_table_session_snapshot

    return get_table_session_snapshot(db, table_id=table_id)


def app_list_product_categories(db: Session, *, offset: int, limit: int) -> list[dict[str, object]]:
    from application.inventory_engine.domain.catalog import list_product_categories

    return list_product_categories(db, offset=offset, limit=limit)


def app_create_product_category(
    db: Session,
    *,
    name: str,
    active: bool,
    sort_order: int,
) -> ProductCategory:
    from application.inventory_engine.domain.catalog import create_product_category

    return create_product_category(
        db,
        name=name,
        active=active,
        sort_order=sort_order,
    )


def app_update_product_category(
    db: Session,
    *,
    category_id: int,
    name: str,
    active: bool,
    sort_order: int,
) -> ProductCategory:
    from application.inventory_engine.domain.catalog import update_product_category

    return update_product_category(
        db,
        category_id=category_id,
        name=name,
        active=active,
        sort_order=sort_order,
    )


def app_delete_product_category(db: Session, *, category_id: int) -> None:
    from application.inventory_engine.domain.catalog import delete_product_category

    delete_product_category(db, category_id=category_id)


def app_create_product(
    db: Session,
    *,
    name: str,
    description: str | None,
    price: float,
    kind,
    available: bool,
    category_id: int | None,
    secondary_links,
    consumption_components,
) -> Product:
    from application.inventory_engine.domain.catalog import create_product

    return create_product(
        db,
        name=name,
        description=description,
        price=price,
        kind=kind,
        available=available,
        category_id=category_id,
        secondary_links=secondary_links,
        consumption_components=consumption_components,
    )


def app_update_product(
    db: Session,
    *,
    product_id: int,
    name: str,
    description: str | None,
    price: float,
    kind,
    available: bool,
    category_id: int | None,
    secondary_links,
    consumption_components,
    is_archived: bool | None,
) -> Product:
    from application.inventory_engine.domain.catalog import update_product

    return update_product(
        db,
        product_id=product_id,
        name=name,
        description=description,
        price=price,
        kind=kind,
        available=available,
        category_id=category_id,
        secondary_links=secondary_links,
        consumption_components=consumption_components,
        is_archived=is_archived,
    )


def app_upload_product_image(
    db: Session,
    *,
    product_id: int,
    data_base64: str,
    mime_type: str,
) -> Product:
    from application.inventory_engine.domain.media import upload_product_image

    return upload_product_image(
        db,
        product_id=product_id,
        data_base64=data_base64,
        mime_type=mime_type,
    )


def app_archive_product(db: Session, *, product_id: int) -> None:
    from application.inventory_engine.domain.catalog import archive_product

    archive_product(db, product_id=product_id)


def app_delete_product_permanently(db: Session, *, product_id: int) -> None:
    from application.inventory_engine.domain.catalog import delete_product_permanently

    delete_product_permanently(db, product_id=product_id)


def app_get_operational_capabilities(db: Session) -> dict[str, object]:
    from application.operations_engine.domain import get_operational_capabilities as _get_operational_capabilities

    return _get_operational_capabilities(db)


def app_financial_snapshot(db: Session, *, start_date, end_date):
    from application.intelligence_engine.domain.reports import financial_snapshot as _financial_snapshot

    return _financial_snapshot(db, start_date=start_date, end_date=end_date)


def app_daily_report(db: Session, *, offset: int, limit: int):
    from application.intelligence_engine.domain.reports import daily_report as _daily_report

    return _daily_report(db, offset=offset, limit=limit)


def app_monthly_report(db: Session, *, offset: int, limit: int):
    from application.intelligence_engine.domain.reports import monthly_report as _monthly_report

    return _monthly_report(db, offset=offset, limit=limit)


def app_report_by_order_type(db: Session):
    from application.intelligence_engine.domain.reports import report_by_order_type as _report_by_order_type

    return _report_by_order_type(db)


def app_prep_performance_report(db: Session):
    from application.intelligence_engine.domain.reports import prep_performance_report as _prep_performance_report

    return _prep_performance_report(db)


def app_profitability_report(db: Session, *, start_date, end_date):
    from application.intelligence_engine.domain.reports import profitability_report as _profitability_report

    return _profitability_report(db, start_date=start_date, end_date=end_date)


def app_period_comparison_report(db: Session, *, start_date, end_date):
    from application.intelligence_engine.domain.reports import period_comparison_report as _period_comparison_report

    return _period_comparison_report(db, start_date=start_date, end_date=end_date)


def app_peak_hours_performance_report(db: Session, *, start_date, end_date):
    from application.intelligence_engine.domain.reports import (
        peak_hours_performance_report as _peak_hours_performance_report,
    )

    return _peak_hours_performance_report(db, start_date=start_date, end_date=end_date)


def app_operational_heart_dashboard(db: Session):
    from application.intelligence_engine.domain.operational_heart import (
        operational_heart_dashboard as _operational_heart_dashboard,
    )

    return _operational_heart_dashboard(db)


def app_close_cash_shift(
    db: Session,
    *,
    closed_by: int,
    opening_cash: float,
    actual_cash: float,
    note: str | None = None,
) -> ShiftClosure:
    from app.guards.financial_invariant_guard import assert_financial_invariants
    from application.financial_engine.domain.shifts import close_cash_shift
    from application.intelligence_engine.domain.reports import financial_snapshot

    closure = close_cash_shift(
        db,
        closed_by=closed_by,
        opening_cash=opening_cash,
        actual_cash=actual_cash,
        note=note,
        financial_snapshot=financial_snapshot,
    )
    assert_financial_invariants(db)
    return closure


def app_approve_expense(
    db: Session,
    *,
    expense_id: int,
    approved_by: int,
    note: str | None,
) -> Expense:
    from app.guards.financial_invariant_guard import assert_financial_invariants
    from app.repositories.financial_repository import (
        create_financial_transaction,
        fetch_expense_by_id,
        find_latest_expense_transaction,
    )
    from application.financial_engine.domain.expenses import approve_expense

    expense = fetch_expense_by_id(db, expense_id=expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المصروف غير موجود.")
    expense = approve_expense(
        db,
        expense=expense,
        approved_by=approved_by,
        note=note,
        find_latest_transaction=find_latest_expense_transaction,
        create_transaction=create_financial_transaction,
    )
    assert_financial_invariants(db)
    return expense


def app_reject_expense(
    db: Session,
    *,
    expense_id: int,
    rejected_by: int,
    note: str | None,
) -> Expense:
    from app.guards.financial_invariant_guard import assert_financial_invariants
    from app.repositories.financial_repository import delete_expense_transactions, fetch_expense_by_id
    from application.financial_engine.domain.expenses import reject_expense

    expense = fetch_expense_by_id(db, expense_id=expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المصروف غير موجود.")
    expense = reject_expense(
        db,
        expense=expense,
        rejected_by=rejected_by,
        note=note,
        delete_transactions=delete_expense_transactions,
    )
    assert_financial_invariants(db)
    return expense


def app_create_expense(
    db: Session,
    *,
    title: str,
    category: str,
    cost_center_id: int,
    amount: float,
    note: str | None,
    created_by: int,
) -> Expense:
    from application.financial_engine.domain.expenses import create_expense

    return create_expense(
        db,
        title=title,
        category=category,
        cost_center_id=cost_center_id,
        amount=amount,
        note=note,
        created_by=created_by,
    )


def app_update_expense(
    db: Session,
    *,
    expense_id: int,
    title: str,
    category: str,
    cost_center_id: int,
    amount: float,
    note: str | None,
    updated_by: int,
) -> Expense:
    from app.guards.financial_invariant_guard import assert_financial_invariants
    from app.repositories.financial_repository import delete_expense_transactions, fetch_expense_by_id
    from application.financial_engine.domain.expenses import update_expense

    expense = fetch_expense_by_id(db, expense_id=expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المصروف غير موجود.")
    expense = update_expense(
        db,
        expense=expense,
        title=title,
        category=category,
        cost_center_id=cost_center_id,
        amount=amount,
        note=note,
        updated_by=updated_by,
        delete_transactions=delete_expense_transactions,
    )
    assert_financial_invariants(db)
    return expense


def app_delete_expense(db: Session, *, expense_id: int, deleted_by: int) -> None:
    from app.guards.financial_invariant_guard import assert_financial_invariants
    from app.repositories.financial_repository import delete_expense_transactions, fetch_expense_by_id
    from application.financial_engine.domain.expenses import delete_expense

    expense = fetch_expense_by_id(db, expense_id=expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المصروف غير موجود.")
    file_urls = delete_expense(db, expense=expense, delete_transactions=delete_expense_transactions)
    for file_url in file_urls:
        app_remove_static_file(file_url)
    assert_financial_invariants(db)


def app_create_expense_attachment(
    db: Session,
    *,
    expense_id: int,
    data_base64: str,
    mime_type: str,
    file_name: str | None,
    created_by: int,
) -> ExpenseAttachment:
    from app.repositories.financial_repository import fetch_expense_by_id
    from application.financial_engine.domain.expenses import create_expense_attachment

    expense = fetch_expense_by_id(db, expense_id=expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المصروف غير موجود.")

    file_url = None
    attachment: ExpenseAttachment | None = None
    try:
        attachment = create_expense_attachment(
            db,
            expense=expense,
            file_name=file_name,
            mime_type=mime_type,
            data_base64=data_base64,
            uploaded_by=created_by,
            save_attachment=app_save_expense_attachment,
        )
        file_url = attachment.file_url if attachment is not None else None
    except Exception:
        if file_url:
            app_remove_static_file(file_url)
        raise
    return attachment


def app_delete_expense_attachment(db: Session, *, expense_id: int, attachment_id: int, deleted_by: int) -> None:
    from app.repositories.financial_repository import fetch_expense_by_id
    from application.financial_engine.domain.expenses import delete_expense_attachment

    expense = fetch_expense_by_id(db, expense_id=expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المصروف غير موجود.")

    attachment = db.execute(
        select(ExpenseAttachment).where(
            ExpenseAttachment.id == attachment_id,
            ExpenseAttachment.expense_id == expense_id,
        )
    ).scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المرفق غير موجود.")

    file_url = delete_expense_attachment(
        db,
        expense=expense,
        attachment=attachment,
        deleted_by=deleted_by,
    )
    if file_url:
        app_remove_static_file(file_url)


def app_create_expense_cost_center(
    db: Session,
    *,
    code: str,
    name: str,
    active: bool,
    created_by: int,
) -> ExpenseCostCenter:
    from application.financial_engine.domain.expense_cost_centers import create_expense_cost_center

    return create_expense_cost_center(db, code=code, name=name, active=active, actor_id=created_by)


def app_update_expense_cost_center(
    db: Session,
    *,
    cost_center_id: int,
    code: str,
    name: str,
    active: bool,
    updated_by: int,
) -> ExpenseCostCenter:
    from application.financial_engine.domain.expense_cost_centers import update_expense_cost_center

    return update_expense_cost_center(
        db,
        cost_center_id=cost_center_id,
        code=code,
        name=name,
        active=active,
        actor_id=updated_by,
    )


def app_list_expense_cost_centers(
    db: Session,
    *,
    include_inactive: bool,
    offset: int,
    limit: int,
) -> list[ExpenseCostCenter]:
    from application.financial_engine.domain.expense_cost_centers import list_expense_cost_centers

    return list_expense_cost_centers(db, include_inactive=include_inactive, offset=offset, limit=limit)


def app_list_shift_closures(db: Session, *, offset: int, limit: int) -> list[ShiftClosure]:
    from application.financial_engine.domain.shifts import list_shift_closures

    return list_shift_closures(db, offset=offset, limit=limit)


def app_refund_order(
    db: Session,
    *,
    order_id: int,
    refunded_by: int,
    note: str | None,
) -> dict[str, object]:
    from app.guards.financial_invariant_guard import assert_financial_invariants
    from app.repositories.financial_repository import find_latest_order_transaction_by_type
    from application.financial_engine.domain.delivery_accounting import (
        build_reference_group,
        record_financial_entry,
        reverse_delivery_detailed_entries,
    )
    from application.financial_engine.domain.helpers import get_order_or_404
    from application.financial_engine.domain.refunds import refund_order

    order = refund_order(
        db,
        order_id=order_id,
        refunded_by=refunded_by,
        note=note,
        get_order=get_order_or_404,
        find_latest_order_transaction_by_type=find_latest_order_transaction_by_type,
        reverse_delivery_entries=reverse_delivery_detailed_entries,
        record_financial_entry=record_financial_entry,
        build_reference_group=build_reference_group,
    )
    assert_financial_invariants(db)
    return order


def app_run_delivery_accounting_backfill(db: Session) -> dict[str, object]:
    from application.financial_engine.domain.delivery_accounting_migration import run_delivery_accounting_backfill

    return run_delivery_accounting_backfill(db)


def app_get_delivery_accounting_migration_status() -> dict[str, object]:
    from application.financial_engine.domain.delivery_accounting_migration import get_delivery_accounting_migration_status

    return get_delivery_accounting_migration_status()
