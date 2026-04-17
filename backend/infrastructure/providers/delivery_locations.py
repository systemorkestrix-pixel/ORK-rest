from __future__ import annotations

from dataclasses import dataclass
import json
from urllib.parse import urlencode
from urllib.request import urlopen


GEONAMES_BASE_URL = "https://secure.geonames.org"


@dataclass
class DeliveryLocationNode:
    key: str
    parent_key: str | None
    level: str
    external_id: str | None
    country_code: str | None
    name: str
    display_name: str
    sort_order: int
    payload: dict[str, object]

    @property
    def can_expand(self) -> bool:
        return self.level in {
            "country",
            "admin_area_level_1",
            "admin_area_level_2",
            "locality",
        }


def _load_json(url: str) -> dict[str, object]:
    with urlopen(url, timeout=12) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def _build_url(path: str, params: dict[str, object]) -> str:
    return f"{GEONAMES_BASE_URL}{path}?{urlencode(params)}"


class GeoNamesDeliveryLocationProvider:
    name = "geonames"

    def list_countries(self, *, username: str, country_codes: list[str] | None = None) -> list[DeliveryLocationNode]:
        payload = _load_json(_build_url("/countryInfoJSON", {"username": username}))
        rows = payload.get("geonames", [])
        if not isinstance(rows, list):
            return []
        whitelist = {code.upper() for code in country_codes or []}
        output: list[DeliveryLocationNode] = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            country_code = str(row.get("countryCode") or "").strip().upper()
            if not country_code:
                continue
            if whitelist and country_code not in whitelist:
                continue
            geoname_id = str(row.get("geonameId") or "").strip()
            name = str(row.get("countryName") or country_code).strip()
            output.append(
                DeliveryLocationNode(
                    key=f"geonames:country:{country_code}",
                    parent_key=None,
                    level="country",
                    external_id=geoname_id or None,
                    country_code=country_code,
                    name=name,
                    display_name=name,
                    sort_order=index,
                    payload=row,
                )
            )
        return sorted(output, key=lambda item: item.name.lower())

    def list_children(
        self,
        *,
        username: str,
        parent_external_id: str,
        parent_key: str,
        parent_level: str,
        country_code: str | None,
    ) -> list[DeliveryLocationNode]:
        payload = _load_json(
            _build_url(
                "/childrenJSON",
                {
                    "geonameId": parent_external_id,
                    "username": username,
                    "maxRows": 500,
                },
            )
        )
        rows = payload.get("geonames", [])
        if not isinstance(rows, list):
            return []
        child_level = _resolve_child_level(parent_level)
        output: list[DeliveryLocationNode] = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            geoname_id = str(row.get("geonameId") or "").strip()
            if not geoname_id:
                continue
            name = str(row.get("name") or row.get("toponymName") or geoname_id).strip()
            row_country_code = str(row.get("countryCode") or country_code or "").strip().upper() or None
            output.append(
                DeliveryLocationNode(
                    key=f"geonames:{geoname_id}",
                    parent_key=parent_key,
                    level=child_level,
                    external_id=geoname_id,
                    country_code=row_country_code,
                    name=name,
                    display_name=name,
                    sort_order=index,
                    payload=row,
                )
            )
        return sorted(output, key=lambda item: item.name.lower())


def _resolve_child_level(parent_level: str) -> str:
    if parent_level == "country":
        return "admin_area_level_1"
    if parent_level == "admin_area_level_1":
        return "admin_area_level_2"
    if parent_level == "admin_area_level_2":
        return "locality"
    if parent_level == "locality":
        return "sublocality"
    return "sublocality"


def get_delivery_location_provider(provider_name: str) -> GeoNamesDeliveryLocationProvider:
    normalized = (provider_name or "").strip().lower()
    if normalized in {"", "geonames"}:
        return GeoNamesDeliveryLocationProvider()
    raise ValueError(f"Unsupported delivery location provider: {provider_name}")
