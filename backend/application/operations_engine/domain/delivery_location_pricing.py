from __future__ import annotations

import json

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DeliveryAddressNode, DeliveryZonePricing
from application.core_engine.domain.settings import get_delivery_fee_setting


def _parse_selected_node_id(location_key: str | None) -> int | None:
    if location_key is None:
        return None
    normalized = str(location_key).strip()
    if not normalized:
        return None
    if normalized.startswith("address-node:"):
        normalized = normalized.split(":", 1)[1].strip()
    if normalized.isdigit():
        return int(normalized)
    return None


def _count_active_rules(db: Session) -> int:
    return int(
        db.execute(
            select(func.count(DeliveryZonePricing.id)).where(
                DeliveryZonePricing.active.is_(True),
                DeliveryZonePricing.provider == "manual",
            )
        ).scalar_one()
        or 0
    )


def _get_node_or_404(db: Session, *, node_id: int) -> DeliveryAddressNode:
    node = db.execute(select(DeliveryAddressNode).where(DeliveryAddressNode.id == node_id)).scalars().first()
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="تعذر العثور على عقدة العنوان المحددة.")
    return node


def _load_rule_map_for_ancestry(
    db: Session,
    *,
    selected_node: DeliveryAddressNode,
) -> tuple[list[DeliveryAddressNode], dict[str, DeliveryZonePricing]]:
    ancestors: list[DeliveryAddressNode] = []
    current: DeliveryAddressNode | None = selected_node
    seen_ids: set[int] = set()
    while current is not None and current.id not in seen_ids:
        seen_ids.add(int(current.id))
        ancestors.append(current)
        current = current.parent

    keys = [str(int(node.id)) for node in ancestors]
    rules = (
        db.execute(
            select(DeliveryZonePricing).where(
                DeliveryZonePricing.location_key.in_(keys),
                DeliveryZonePricing.active.is_(True),
                DeliveryZonePricing.provider == "manual",
            )
        )
        .scalars()
        .all()
    )
    return ancestors, {str(rule.location_key): rule for rule in rules}


def resolve_delivery_pricing_for_order(
    db: Session,
    *,
    location_key: str | None,
) -> dict[str, object]:
    active_rules_count = _count_active_rules(db)
    fallback_fee = float(get_delivery_fee_setting(db))
    selected_node_id = _parse_selected_node_id(location_key)

    if selected_node_id is None:
        if active_rules_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="اختر عنوان التوصيل من القوائم المحددة قبل إرسال الطلب.",
            )
        return {
            "delivery_fee": fallback_fee,
            "pricing_source": "fallback_fixed",
            "location_key": None,
            "location_label": None,
            "location_level": None,
            "location_snapshot_json": None,
            "active_zones_count": active_rules_count,
        }

    selected_node = _get_node_or_404(db, node_id=selected_node_id)
    ancestors, rule_map = _load_rule_map_for_ancestry(db, selected_node=selected_node)
    resolved_rule = next((rule_map.get(str(int(node.id))) for node in ancestors if str(int(node.id)) in rule_map), None)
    if resolved_rule is not None:
        resolved_node = next(node for node in ancestors if int(node.id) == int(resolved_rule.location_key))
        return {
            "delivery_fee": float(resolved_rule.delivery_fee),
            "pricing_source": "manual_tree",
            "location_key": str(int(selected_node.id)),
            "location_label": selected_node.display_name,
            "location_level": selected_node.level,
            "location_snapshot_json": json.dumps(
                {
                    "selected_node_id": int(selected_node.id),
                    "selected_node_label": selected_node.display_name,
                    "selected_node_level": selected_node.level,
                    "resolved_node_id": int(resolved_node.id),
                    "resolved_node_label": resolved_node.display_name,
                    "resolved_node_level": resolved_node.level,
                    "country_code": selected_node.country_code,
                },
                ensure_ascii=False,
            ),
            "active_zones_count": active_rules_count,
        }

    if active_rules_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="العنوان المحدد خارج نطاق التوصيل الحالي.",
        )

    return {
        "delivery_fee": fallback_fee,
        "pricing_source": "fallback_fixed",
        "location_key": str(int(selected_node.id)),
        "location_label": selected_node.display_name,
        "location_level": selected_node.level,
        "location_snapshot_json": json.dumps(
            {
                "selected_node_id": int(selected_node.id),
                "selected_node_label": selected_node.display_name,
                "selected_node_level": selected_node.level,
                "country_code": selected_node.country_code,
            },
            ensure_ascii=False,
        ),
        "active_zones_count": active_rules_count,
    }


def quote_delivery_location_pricing(
    db: Session,
    *,
    location_key: str | None,
) -> dict[str, object]:
    active_rules_count = _count_active_rules(db)
    fallback_fee = float(get_delivery_fee_setting(db))
    selected_node_id = _parse_selected_node_id(location_key)

    if selected_node_id is None:
        return {
            "selected_node_id": None,
            "location_key": None,
            "location_label": None,
            "location_level": None,
            "resolved_node_id": None,
            "resolved_node_label": None,
            "resolved_node_level": None,
            "available": active_rules_count == 0,
            "pricing_source": "fallback_fixed",
            "delivery_fee": fallback_fee if active_rules_count == 0 else None,
            "active_zones_count": active_rules_count,
            "message": None if active_rules_count == 0 else "اختر عنوانًا من القوائم المتاحة لحساب رسوم التوصيل.",
        }

    selected_node = _get_node_or_404(db, node_id=selected_node_id)
    ancestors, rule_map = _load_rule_map_for_ancestry(db, selected_node=selected_node)
    resolved_rule = next((rule_map.get(str(int(node.id))) for node in ancestors if str(int(node.id)) in rule_map), None)
    if resolved_rule is not None:
        resolved_node = next(node for node in ancestors if int(node.id) == int(resolved_rule.location_key))
        return {
            "selected_node_id": int(selected_node.id),
            "location_key": str(int(selected_node.id)),
            "location_label": selected_node.display_name,
            "location_level": selected_node.level,
            "resolved_node_id": int(resolved_node.id),
            "resolved_node_label": resolved_node.display_name,
            "resolved_node_level": resolved_node.level,
            "available": True,
            "pricing_source": "manual_tree",
            "delivery_fee": float(resolved_rule.delivery_fee),
            "active_zones_count": active_rules_count,
            "message": None,
        }

    if active_rules_count > 0:
        return {
            "selected_node_id": int(selected_node.id),
            "location_key": str(int(selected_node.id)),
            "location_label": selected_node.display_name,
            "location_level": selected_node.level,
            "resolved_node_id": None,
            "resolved_node_label": None,
            "resolved_node_level": None,
            "available": False,
            "pricing_source": "unavailable",
            "delivery_fee": None,
            "active_zones_count": active_rules_count,
            "message": "هذا العنوان غير مغطى ضمن قواعد التوصيل الحالية.",
        }

    return {
        "selected_node_id": int(selected_node.id),
        "location_key": str(int(selected_node.id)),
        "location_label": selected_node.display_name,
        "location_level": selected_node.level,
        "resolved_node_id": None,
        "resolved_node_label": None,
        "resolved_node_level": None,
        "available": True,
        "pricing_source": "fallback_fixed",
        "delivery_fee": fallback_fee,
        "active_zones_count": active_rules_count,
        "message": None if fallback_fee > 0 else "لم يتم ضبط رسوم توصيل بعد.",
    }
