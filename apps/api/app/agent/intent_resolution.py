from __future__ import annotations

from app.agent.state import AgentEvent, UserIntentParsed
from app.schemas.intent import InterpretedUserIntent, ShoppingAction
from app.schemas.product_verification import ProductIntentSpec


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


def derive_interpreted_intent_from_event(event: AgentEvent) -> InterpretedUserIntent | None:
    if not isinstance(event, UserIntentParsed):
        return None

    raw_query = (event.query or event.intent or "").strip()
    if not raw_query:
        raw_query = "user_intent"

    product_intent = ProductIntentSpec(
        raw_query=raw_query,
        product_name=event.query.strip() if isinstance(event.query, str) and event.query.strip() else None,
    )

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


def resolve_product_intent_from_event(
    event: AgentEvent,
    previous_product_intent: ProductIntentSpec | None,
) -> ProductIntentSpec | None:
    derived_intent = derive_interpreted_intent_from_event(event)
    if derived_intent is not None and derived_intent.product_intent is not None:
        return derived_intent.product_intent
    return previous_product_intent

