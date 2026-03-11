from __future__ import annotations

import re

from app.agent.state import AgentEvent, ClarificationResolved, UserIntentParsed
from app.schemas.intent import InterpretedUserIntent, ShoppingAction
from app.schemas.product_verification import ProductIntentSpec

_SIZE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s?(kg|g|mg|ml|l|pack|packs|pc|pcs)")
_MERCHANT_TOKENS = {"amazon", "amazonin", "flipkart", "meesho", "nopcommerce", "demostore"}


def _map_action(intent_text: str) -> ShoppingAction:
    normalized = intent_text.strip().lower()
    if "checkout" in normalized or "proceed" in normalized:
        return ShoppingAction.PROCEED_CHECKOUT
    if "cancel" in normalized or "stop" in normalized:
        return ShoppingAction.CANCEL
    if "add" in normalized and "cart" in normalized:
        return ShoppingAction.ADD_TO_CART
    if "select" in normalized or "choose" in normalized:
        return ShoppingAction.SELECT_PRODUCT
    if "refine" in normalized or "filter" in normalized:
        return ShoppingAction.REFINE_RESULTS
    if "search" in normalized or "find" in normalized or "buy" in normalized:
        return ShoppingAction.SEARCH_PRODUCT
    return ShoppingAction.UNKNOWN


def _extract_product_intent(raw_query: str) -> ProductIntentSpec:
    normalized = " ".join(raw_query.strip().lower().split())
    tokens = [token for token in normalized.split() if token and token not in _MERCHANT_TOKENS]

    size_match = _SIZE_PATTERN.search(normalized)
    size_text = None
    if size_match is not None:
        size_text = f"{size_match.group(1)}{size_match.group(2)}"
        normalized = normalized.replace(size_match.group(0), " ").strip()
        tokens = [token for token in normalized.split() if token and token not in _MERCHANT_TOKENS]

    brand = tokens[0] if len(tokens) > 2 else None
    product_name_tokens = tokens[1:] if brand is not None else tokens
    product_name = " ".join(product_name_tokens).strip() or None

    return ProductIntentSpec(
        raw_query=raw_query,
        brand=brand,
        product_name=product_name,
        quantity_text=None,
        size_text=size_text,
        color=None,
        variant=None,
    )


def derive_interpreted_intent_from_event(event: AgentEvent) -> InterpretedUserIntent | None:
    if isinstance(event, UserIntentParsed):
        raw_query = (event.query or event.intent or "").strip()
        if not raw_query:
            raw_query = "user_intent"
        product_intent = _extract_product_intent(raw_query)

        return InterpretedUserIntent(
            raw_utterance=raw_query,
            action=_map_action(event.intent),
            merchant=event.merchant.value if event.merchant is not None else None,
            product_intent=product_intent,
            confidence=0.62,
            requires_clarification=product_intent.product_name is None,
            spoken_confirmation="Understood. I will continue with your requested shopping step.",
            notes="Derived from current AgentEvent (no raw utterance pipeline in this route).",
        )

    if isinstance(event, ClarificationResolved):
        raw_query = (event.follow_up_query or event.follow_up_intent or event.resolution_notes or "").strip()
        if not raw_query:
            return None

        return InterpretedUserIntent(
            raw_utterance=raw_query,
            action=_map_action(event.follow_up_intent or "search_products"),
            merchant=event.merchant.value if event.merchant is not None else None,
            product_intent=_extract_product_intent(raw_query),
            confidence=0.68 if event.approved else 0.4,
            requires_clarification=False,
            spoken_confirmation="Clarification received. I will continue carefully.",
            notes="Derived from clarification response event.",
        )

    return None


def _merge_product_intents(
    current: ProductIntentSpec | None,
    previous: ProductIntentSpec | None,
) -> ProductIntentSpec | None:
    if current is None:
        return previous
    if previous is None:
        return current

    return ProductIntentSpec(
        raw_query=current.raw_query or previous.raw_query,
        brand=current.brand or previous.brand,
        product_name=current.product_name or previous.product_name,
        quantity_text=current.quantity_text or previous.quantity_text,
        size_text=current.size_text or previous.size_text,
        color=current.color or previous.color,
        variant=current.variant or previous.variant,
    )


def resolve_product_intent_from_event(
    event: AgentEvent,
    previous_product_intent: ProductIntentSpec | None,
) -> ProductIntentSpec | None:
    derived_intent = derive_interpreted_intent_from_event(event)
    if derived_intent is not None and derived_intent.product_intent is not None:
        return _merge_product_intents(derived_intent.product_intent, previous_product_intent)
    return previous_product_intent
