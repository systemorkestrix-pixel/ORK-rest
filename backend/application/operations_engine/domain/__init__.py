"""Operations Engine Domain Layer."""

from .operational import (
    count_active_delivery_users,
    ensure_delivery_capacity_reduction_allowed,
    ensure_delivery_operational,
    ensure_kitchen_capacity_reduction_allowed,
    ensure_kitchen_operational,
    get_operational_capabilities,
    get_or_create_system_order_actor_id,
    resolve_order_creator_id,
)
from .orders import attach_sent_to_kitchen_at, create_order
from .table_sessions import (
    get_table_session_snapshot,
    list_active_table_sessions,
    list_tables_with_session_summary,
    settle_table_session,
)

__all__ = [
    "count_active_delivery_users",
    "attach_sent_to_kitchen_at",
    "create_order",
    "ensure_delivery_capacity_reduction_allowed",
    "ensure_delivery_operational",
    "ensure_kitchen_capacity_reduction_allowed",
    "ensure_kitchen_operational",
    "get_operational_capabilities",
    "get_or_create_system_order_actor_id",
    "get_table_session_snapshot",
    "list_active_table_sessions",
    "list_tables_with_session_summary",
    "resolve_order_creator_id",
    "settle_table_session",
]
