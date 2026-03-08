from __future__ import annotations

import base64
import io
import re
from typing import Any

from app.core.config import settings

try:  # pragma: no cover - optional dependency path
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency path
    Image = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency path
    import pytesseract
except Exception:  # pragma: no cover - optional dependency path
    pytesseract = None  # type: ignore[assignment]


_PRICE_PATTERN = re.compile(r"(?:₹|rs\.?)\s?\d[\d,]*(?:\.\d{1,2})?", re.IGNORECASE)
_CART_COUNT_PATTERN = re.compile(r"subtotal\s*\((\d+)\s*item", re.IGNORECASE)


def extract_text_from_screenshot(
    screenshot: dict[str, object] | None,
    *,
    language: str | None = None,
) -> str | None:
    if not settings.OCR_ENABLED:
        return None
    if screenshot is None:
        return None

    image_base64 = screenshot.get("image_base64")
    if not isinstance(image_base64, str) or not image_base64.strip():
        return None
    if Image is None or pytesseract is None:
        return None

    try:  # pragma: no cover - depends on optional OCR stack
        image_bytes = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image, lang=language or settings.OCR_LANGUAGE)
    except Exception:
        return None

    normalized = re.sub(r"\s+", " ", text).strip()
    return normalized or None


def build_ocr_observation_patch(text: str | None) -> dict[str, Any]:
    if not text:
        return {}

    normalized = text.lower()
    patch: dict[str, Any] = {}
    notes: list[str] = ["ocr_extracted_text"]

    if any(token in normalized for token in ("thank you", "order placed", "order confirmation")):
        notes.append("ocr_order_confirmation_detected")

    if "proceed to buy" in normalized or "place your order" in normalized:
        patch["checkout_ready"] = True
        notes.append("ocr_checkout_ready_detected")

    if "subtotal" in normalized or "shopping cart" in normalized:
        cart_match = _CART_COUNT_PATTERN.search(normalized)
        if cart_match is not None:
            try:
                patch["cart_item_count"] = int(cart_match.group(1))
            except ValueError:
                pass
        notes.append("ocr_cart_signals_detected")

    price_match = _PRICE_PATTERN.search(text)
    if price_match is not None:
        patch["primary_product"] = {
            "price_text": price_match.group(0).strip(),
        }
        notes.append("ocr_price_detected")

    patch["notes"] = " ".join(notes)
    return patch
