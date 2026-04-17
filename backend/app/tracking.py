from __future__ import annotations

import base64
import hashlib
import hmac
import re

from .config import load_settings

TRACKING_PREFIX = "ORD"
TRACKING_PATTERN = re.compile(r"^\s*(?:ORD[-\s]?)?(\d{1,10})[-\s]?([A-Z2-7]{6})\s*$", re.IGNORECASE)


def _tracking_secret() -> bytes:
    return load_settings().secret_key.encode("utf-8")


def _tracking_checksum(order_id: int) -> str:
    digest = hmac.new(
        _tracking_secret(),
        f"public-order:{int(order_id)}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b32encode(digest).decode("ascii").rstrip("=").upper()[:6]


def encode_public_order_tracking_code(order_id: int) -> str:
    normalized = max(0, int(order_id))
    return f"{TRACKING_PREFIX}-{normalized:06d}-{_tracking_checksum(normalized)}"


def decode_public_order_tracking_code(raw_code: str) -> int | None:
    match = TRACKING_PATTERN.fullmatch((raw_code or "").strip().upper())
    if not match:
        return None
    order_id = int(match.group(1))
    expected = _tracking_checksum(order_id)
    provided = match.group(2).upper()
    if not hmac.compare_digest(expected, provided):
        return None
    return order_id
