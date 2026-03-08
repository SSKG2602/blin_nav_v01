from __future__ import annotations

from typing import Any

from app.schemas.order_support import LatestOrderSnapshot


def _safe_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def build_latest_order_snapshot(
    observation: dict[str, Any] | None,
) -> LatestOrderSnapshot | None:
    if not isinstance(observation, dict):
        return None

    order_card_title = _safe_text(observation.get("order_card_title"))
    shipping_stage_text = _safe_text(observation.get("shipping_stage_text"))
    expected_delivery_text = _safe_text(observation.get("expected_delivery_text"))
    order_date_text = _safe_text(observation.get("order_date_text"))
    order_total_text = _safe_text(observation.get("order_total_text"))
    orders_page_url = _safe_text(observation.get("orders_page_url"))
    order_id_hint = _safe_text(observation.get("order_id_hint"))
    support_entry_hint = _safe_text(observation.get("support_entry_hint"))
    returns_entry_hint = _safe_text(observation.get("returns_entry_hint"))
    notes = _safe_text(observation.get("notes"))

    if not any(
        [
            order_card_title,
            shipping_stage_text,
            expected_delivery_text,
            order_date_text,
            order_total_text,
            order_id_hint,
        ]
    ):
        return None

    spoken_parts: list[str] = []
    if order_card_title:
        spoken_parts.append(f"Latest order: {order_card_title}.")
    if shipping_stage_text:
        spoken_parts.append(f"Status: {shipping_stage_text}.")
    if expected_delivery_text:
        spoken_parts.append(f"Expected delivery: {expected_delivery_text}.")

    return LatestOrderSnapshot(
        order_id_hint=order_id_hint,
        order_date_text=order_date_text,
        shipping_stage_text=shipping_stage_text,
        expected_delivery_text=expected_delivery_text,
        order_total_text=order_total_text,
        order_card_title=order_card_title,
        orders_page_url=orders_page_url,
        support_entry_hint=support_entry_hint,
        returns_entry_hint=returns_entry_hint,
        spoken_summary=" ".join(spoken_parts) or "Latest order details captured.",
        notes=notes,
    )
