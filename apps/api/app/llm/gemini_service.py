from __future__ import annotations

import json
import logging
import re
import unicodedata
from typing import Any

from pydantic import ValidationError

from app.agent.multimodal import build_fallback_multimodal_assessment
from app.core.config import settings
from app.llm.client import BlindNavLLMClient
from app.schemas.intent import InterpretedUserIntent, ShoppingAction
from app.schemas.multimodal_assessment import (
    ConfidenceBand,
    MultimodalAssessment,
    MultimodalDecision,
)
from app.schemas.page_understanding import PageType, PageUnderstanding, ProductCandidate
from app.schemas.product_verification import (
    ProductIntentSpec,
    ProductVerificationResult,
    VerificationDecision,
)

try:
    from google import genai  # type: ignore
except Exception:  # pragma: no cover - guarded optional import
    genai = None

logger = logging.getLogger(__name__)

_SIZE_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?)\s?(kg|g|mg|ml|l|litre|liter)\b", re.IGNORECASE)
_QUANTITY_PATTERN = re.compile(r"\b(\d+)\s?(pack|packs|pcs|piece|pieces|x)\b", re.IGNORECASE)
_KNOWN_COLORS = {"black", "white", "red", "blue", "green", "yellow", "pink", "brown", "gray"}
_KNOWN_VARIANTS = {"adult", "puppy", "junior", "small", "large", "mini", "pro", "max"}
_KNOWN_BRANDS = {
    "pedigree",
    "whiskas",
    "drools",
    "purina",
    "nestle",
    "himalaya",
    "boat",
    "samsung",
    "apple",
    "nike",
    "adidas",
}
_ACTION_STOPWORDS = {
    "find",
    "search",
    "look",
    "for",
    "show",
    "me",
    "buy",
    "get",
    "please",
    "on",
    "in",
    "from",
    "add",
    "to",
    "cart",
    "checkout",
    "proceed",
    "cancel",
    "this",
    "the",
    "a",
    "an",
}


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    lowered = unicodedata.normalize("NFKC", value.lower())
    normalized = "".join(
        ch if (ch.isspace() or unicodedata.category(ch)[0] in {"L", "N", "M"}) else " "
        for ch in lowered
    )
    return re.sub(r"\s+", " ", normalized).strip()


def _extract_first_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if not stripped:
        return None

    try:
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    snippet = stripped[start : end + 1]
    try:
        payload = json.loads(snippet)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


class GeminiIntentSummaryService(BlindNavLLMClient):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        intent_model: str | None = None,
        summary_model: str | None = None,
        multimodal_model: str | None = None,
        vision_model: str | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self._intent_model = intent_model or settings.GEMINI_MODEL_INTENT
        self._summary_model = summary_model or settings.GEMINI_MODEL_SUMMARY
        self._multimodal_model = multimodal_model or settings.GEMINI_MODEL_MULTIMODAL
        self._vision_model = vision_model or settings.GEMINI_MODEL_VISION
        self._gemini_client: Any | None = None

        if not self._api_key:
            logger.info("Gemini API key not configured; LLM service using deterministic fallback.")
            return
        if genai is None:
            logger.warning("Gemini SDK not installed; LLM service using deterministic fallback.")
            return

        try:
            self._gemini_client = genai.Client(api_key=self._api_key)
        except Exception as exc:  # pragma: no cover - depends on SDK runtime
            logger.warning(
                "Gemini client initialization failed; using deterministic fallback: %s",
                exc,
            )
            self._gemini_client = None

    def _generate_text(self, *, model: str, prompt: str) -> str | None:
        if self._gemini_client is None:
            return None

        try:
            response = self._gemini_client.models.generate_content(model=model, contents=prompt)
        except Exception as exc:  # pragma: no cover - external dependency behavior
            logger.warning("Gemini generation failed for model %s: %s", model, exc)
            return None

        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()

        candidates = getattr(response, "candidates", None)
        if not candidates:
            return None

        try:  # pragma: no cover - depends on SDK object shapes
            first_candidate = candidates[0]
            content = getattr(first_candidate, "content", None)
            parts = getattr(content, "parts", None) if content is not None else None
            if parts:
                first_part = parts[0]
                part_text = getattr(first_part, "text", None)
                if isinstance(part_text, str) and part_text.strip():
                    return part_text.strip()
        except Exception:
            return None
        return None

    def _detect_action(self, normalized: str) -> ShoppingAction:
        if any(
            token in normalized
            for token in {
                "cancel",
                "stop",
                "abort",
                "nevermind",
                "never mind",
                "रद्द",
                "रोक",
                "कैंसल",
            }
        ):
            return ShoppingAction.CANCEL
        if any(
            token in normalized
            for token in {
                "checkout",
                "proceed",
                "pay now",
                "place order",
                "चेकआउट",
                "भुगतान",
                "पे",
            }
        ):
            return ShoppingAction.PROCEED_CHECKOUT
        if any(
            token in normalized
            for token in {
                "add to cart",
                "add cart",
                "add this",
                "कार्ट में डालो",
                "कार्ट में जोड़ो",
                "कार्ट",
            }
        ):
            return ShoppingAction.ADD_TO_CART
        if any(
            token in normalized
            for token in {"select", "choose", "open first", "pick first", "चुनो", "पहला", "चुनिए"}
        ):
            return ShoppingAction.SELECT_PRODUCT
        if any(
            token in normalized
            for token in {"refine", "filter", "sort", "cheaper", "under ", "above ", "फ़िल्टर", "सस्ता"}
        ):
            return ShoppingAction.REFINE_RESULTS
        if any(
            token in normalized
            for token in {
                "search",
                "find",
                "look for",
                "buy",
                "get me",
                "show me",
                "खोज",
                "खोजो",
                "ढूंढ",
                "ढूंढो",
                "दूँढो",
                "दिखाओ",
                "लाओ",
            }
        ):
            return ShoppingAction.SEARCH_PRODUCT
        return ShoppingAction.UNKNOWN

    def _detect_merchant(self, normalized: str) -> str | None:
        if "amazon" in normalized or "अमेज़न" in normalized:
            return "amazon.in"
        if "flipkart" in normalized or "फ्लिपकार्ट" in normalized:
            return "flipkart.com"
        if "meesho" in normalized or "मीशो" in normalized:
            return "meesho.com"
        return None

    def _extract_product_intent(self, utterance: str, normalized: str) -> ProductIntentSpec:
        tokens = normalized.split()
        brand = next((token for token in tokens if token in _KNOWN_BRANDS), None)

        size_match = _SIZE_PATTERN.search(normalized)
        quantity_match = _QUANTITY_PATTERN.search(normalized)

        color = next((token for token in tokens if token in _KNOWN_COLORS), None)
        variant = next((token for token in tokens if token in _KNOWN_VARIANTS), None)

        filtered_tokens = [
            token
            for token in tokens
            if token not in _ACTION_STOPWORDS
            and token not in {"amazon", "amazonin", "flipkart", "meesho"}
            and token not in _KNOWN_COLORS
            and token not in _KNOWN_VARIANTS
            and (brand is None or token != brand)
        ]

        product_name = " ".join(filtered_tokens).strip() or None
        if product_name and size_match:
            size_text = f"{size_match.group(1)}{size_match.group(2)}"
            product_name = product_name.replace(size_match.group(0).strip(), "").strip() or product_name
        else:
            size_text = None

        quantity_text = (
            f"{quantity_match.group(1)} {quantity_match.group(2)}"
            if quantity_match is not None
            else None
        )

        return ProductIntentSpec(
            raw_query=utterance.strip(),
            brand=brand,
            product_name=product_name,
            quantity_text=quantity_text,
            size_text=size_text,
            color=color,
            variant=variant,
        )

    def _fallback_intent(self, utterance: str, notes: str) -> InterpretedUserIntent:
        utterance_clean = utterance.strip()
        normalized = _normalize_text(utterance_clean)
        action = self._detect_action(normalized)
        merchant = self._detect_merchant(normalized)

        confidence_by_action = {
            ShoppingAction.SEARCH_PRODUCT: 0.78,
            ShoppingAction.REFINE_RESULTS: 0.68,
            ShoppingAction.SELECT_PRODUCT: 0.70,
            ShoppingAction.ADD_TO_CART: 0.82,
            ShoppingAction.PROCEED_CHECKOUT: 0.86,
            ShoppingAction.CANCEL: 0.95,
            ShoppingAction.UNKNOWN: 0.25,
        }
        confidence = confidence_by_action[action]
        requires_clarification = action in {
            ShoppingAction.UNKNOWN,
            ShoppingAction.REFINE_RESULTS,
        }

        product_intent: ProductIntentSpec | None = None
        if action in {
            ShoppingAction.SEARCH_PRODUCT,
            ShoppingAction.REFINE_RESULTS,
            ShoppingAction.SELECT_PRODUCT,
            ShoppingAction.ADD_TO_CART,
        }:
            product_intent = self._extract_product_intent(utterance_clean, normalized)

        if action == ShoppingAction.CANCEL:
            spoken_confirmation = "Okay, I will cancel and stop this flow."
        elif action == ShoppingAction.PROCEED_CHECKOUT:
            spoken_confirmation = "Understood. You want to proceed to checkout."
        elif action == ShoppingAction.ADD_TO_CART:
            spoken_confirmation = "Understood. You want to add this item to the cart."
        elif action == ShoppingAction.SEARCH_PRODUCT:
            query_text = product_intent.raw_query if product_intent is not None else utterance_clean
            spoken_confirmation = f"Understood. I will search for {query_text}."
        elif action == ShoppingAction.REFINE_RESULTS:
            spoken_confirmation = "Understood. I will refine the current results, but I may need clarification."
        elif action == ShoppingAction.SELECT_PRODUCT:
            spoken_confirmation = "Understood. I will select the requested product."
        else:
            spoken_confirmation = (
                "I am not fully sure what you want. Please restate the action and product details."
            )

        return InterpretedUserIntent(
            raw_utterance=utterance_clean,
            action=action,
            merchant=merchant,
            product_intent=product_intent,
            confidence=confidence,
            requires_clarification=requires_clarification,
            spoken_confirmation=spoken_confirmation,
            notes=notes,
        )

    def _gemini_intent(self, utterance: str) -> InterpretedUserIntent | None:
        prompt = (
            "You are BlindNav intent parser. Return ONLY JSON.\n"
            "Schema:\n"
            "{\n"
            '  "action": "SEARCH_PRODUCT|REFINE_RESULTS|SELECT_PRODUCT|ADD_TO_CART|PROCEED_CHECKOUT|CANCEL|UNKNOWN",\n'
            '  "merchant": "amazon.in|flipkart.com|meesho.com|null",\n'
            '  "confidence": 0.0,\n'
            '  "requires_clarification": false,\n'
            '  "spoken_confirmation": "short safe confirmation",\n'
            '  "notes": "optional",\n'
            '  "product_intent": {\n'
            '    "raw_query": "original query",\n'
            '    "brand": null,\n'
            '    "product_name": null,\n'
            '    "quantity_text": null,\n'
            '    "size_text": null,\n'
            '    "color": null,\n'
            '    "variant": null\n'
            "  }\n"
            "}\n"
            f"Utterance: {utterance}\n"
            "If uncertain, set action UNKNOWN and requires_clarification true."
        )
        text = self._generate_text(model=self._intent_model, prompt=prompt)
        if not text:
            return None

        payload = _extract_first_json_object(text)
        if payload is None:
            return None

        action_text = payload.get("action")
        try:
            action = ShoppingAction(str(action_text).upper())
        except Exception:
            action = ShoppingAction.UNKNOWN

        product_intent_payload = payload.get("product_intent")
        product_intent: ProductIntentSpec | None = None
        if isinstance(product_intent_payload, dict):
            if "raw_query" not in product_intent_payload:
                product_intent_payload["raw_query"] = utterance.strip()
            try:
                product_intent = ProductIntentSpec.model_validate(product_intent_payload)
            except ValidationError:
                product_intent = None

        try:
            confidence = float(payload.get("confidence", 0.35))
        except (TypeError, ValueError):
            confidence = 0.35
        confidence = max(0.0, min(1.0, confidence))

        requires_clarification = bool(payload.get("requires_clarification", action == ShoppingAction.UNKNOWN))
        spoken_confirmation = payload.get("spoken_confirmation")
        if not isinstance(spoken_confirmation, str) or not spoken_confirmation.strip():
            spoken_confirmation = "I interpreted your request and will proceed carefully."

        return InterpretedUserIntent(
            raw_utterance=utterance.strip(),
            action=action,
            merchant=payload.get("merchant") if isinstance(payload.get("merchant"), str) else None,
            product_intent=product_intent,
            confidence=confidence,
            requires_clarification=requires_clarification,
            spoken_confirmation=spoken_confirmation.strip(),
            notes=payload.get("notes") if isinstance(payload.get("notes"), str) else "Gemini intent parse.",
        )

    def interpret_user_intent(self, utterance: str) -> InterpretedUserIntent:
        utterance_clean = utterance.strip()
        if not utterance_clean:
            return self._fallback_intent("", "Fallback intent parse: empty utterance.")

        parsed = self._gemini_intent(utterance_clean)
        if parsed is not None:
            return parsed
        return self._fallback_intent(utterance_clean, "Fallback intent parse: Gemini unavailable.")

    def score_product_candidates(
        self,
        *,
        query: str,
        candidates: list[dict[str, object]],
    ) -> int | None:
        """
        Uses Gemini to pick the best candidate when regex scoring produces a tie.
        Designed to be fast: compact prompt, structured JSON output, no retries.
        Returns 0-based index or None on any failure.
        """
        try:
            if not candidates:
                return None
            if len(candidates) == 1:
                return 0
            if self._gemini_client is None:
                return None

            lines: list[str] = []
            for i, candidate in enumerate(candidates):
                title = str(candidate.get("title") or "Unknown product")
                price = str(candidate.get("price_text") or "price unknown")
                lines.append(f'{i}: "{title}" — {price}')
            candidates_text = "\n".join(lines)

            prompt = (
                "You are a product selection assistant for a blind user's voice shopping app.\n"
                f'The user asked for: "{query}"\n'
                "Choose the single best matching product from the numbered list below.\n\n"
                "Rules (apply in order):\n"
                "1. Match brand exactly if the query specifies a brand.\n"
                "2. Match size/weight exactly if specified. Treat '3kg', '3 kg', '3000g' as equivalent.\n"
                "3. Prefer adult/standard variants over puppy/junior/baby unless the query specifies otherwise.\n"
                "4. Prefer the more common pack size when ambiguous.\n"
                "5. Never pick a sponsored, unrelated, or clearly wrong product.\n\n"
                "Candidates:\n"
                f"{candidates_text}\n\n"
                "Respond with ONLY valid JSON and nothing else:\n"
                '{"best_index": <integer>, "reason": "<one short sentence>"}\n'
            )

            text = self._generate_text(model=self._intent_model, prompt=prompt)
            if not text:
                logger.warning("score_product_candidates: Gemini returned empty text")
                return None

            payload = _extract_first_json_object(text)
            if payload is None:
                logger.warning(
                    "score_product_candidates: could not parse JSON from response: %s",
                    text[:300],
                )
                return None

            try:
                index = int(payload["best_index"])
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning(
                    "score_product_candidates: bad best_index in payload=%s error=%s",
                    payload,
                    exc,
                )
                return None

            if index < 0 or index >= len(candidates):
                logger.warning(
                    "score_product_candidates: index %d out of range for %d candidates",
                    index,
                    len(candidates),
                )
                return None

            logger.info(
                "score_product_candidates gemini_pick index=%d reason=%s query=%s",
                index,
                payload.get("reason", ""),
                query,
            )
            return index
        except Exception as exc:
            logger.warning("score_product_candidates failed query=%s error=%s", query, exc)
            return None

    def _fallback_summary(
        self,
        page: PageUnderstanding,
        verification: ProductVerificationResult | None,
    ) -> str:
        title = page.primary_product.title if page.primary_product is not None else None
        price = page.primary_product.price_text if page.primary_product is not None else None

        if verification is not None:
            if verification.decision == VerificationDecision.MATCH:
                return (
                    f"I found a strong match{f': {title}' if title else ''}"
                    f"{f' at {price}' if price else ''}. "
                    "Please confirm if I should continue."
                )
            if verification.decision in {
                VerificationDecision.PARTIAL_MATCH,
                VerificationDecision.AMBIGUOUS,
            }:
                return (
                    "I found a possible match, but some details need confirmation before proceeding."
                )
            if verification.decision == VerificationDecision.INSUFFICIENT_EVIDENCE:
                return "I do not have enough evidence to verify this product safely yet."
            return "The current product appears not to match your request."

        if page.page_type == PageType.SEARCH_RESULTS:
            count = len(page.product_candidates)
            if count > 0:
                return f"I found {count} product results. I can open the top candidate for verification."
            return "I am on search results, but I could not read product cards clearly."

        if page.page_type == PageType.PRODUCT_DETAIL:
            return (
                f"I am on a product detail page{f' for {title}' if title else ''}. "
                "I can now verify the key details."
            )

        if page.page_type == PageType.CART:
            if page.cart_item_count is not None:
                return f"Your cart appears to have {page.cart_item_count} item(s)."
            return "I am on the cart page."

        if page.page_type == PageType.CHECKOUT:
            return "I am at checkout. I will proceed carefully and request confirmation at sensitive steps."

        return "I am not fully certain about the current page yet."

    def summarize_page_and_verification(
        self,
        page: PageUnderstanding,
        verification: ProductVerificationResult | None,
    ) -> str:
        prompt = (
            "You are BlindNav. Provide one short, safe spoken summary for a blind user.\n"
            "Keep it factual and cautious. Do not claim certainty when evidence is weak.\n"
            f"Page understanding JSON: {json.dumps(page.model_dump(), ensure_ascii=True)}\n"
            f"Verification JSON: {json.dumps(verification.model_dump() if verification else None, ensure_ascii=True)}\n"
            "Return plain text only."
        )
        text = self._generate_text(model=self._summary_model, prompt=prompt)
        if text:
            cleaned = " ".join(text.split())
            if cleaned:
                return cleaned[:320]
        return self._fallback_summary(page, verification)

    def _fallback_visual_page(
        self,
        *,
        raw_observation: dict[str, object],
        screenshot: dict[str, object] | None,
    ) -> dict[str, object]:
        hints = raw_observation.get("detected_page_hints")
        page_type = "UNKNOWN"
        if isinstance(hints, list) and hints:
            first = hints[0]
            if isinstance(first, str) and first.strip():
                page_type = first.strip().upper()

        notes = "Fallback visual reasoning: relying on browser observation hints."
        image_available = bool(
            screenshot
            and isinstance(screenshot.get("image_base64"), str)
            and screenshot.get("image_base64")
        )
        if image_available:
            notes = "Fallback visual reasoning used screenshot metadata only."

        return {
            "page_type": page_type,
            "confidence": 0.42,
            "notes": notes,
        }

    def _gemini_visual_page(
        self,
        *,
        raw_observation: dict[str, object],
        screenshot: dict[str, object] | None,
    ) -> dict[str, object] | None:
        if self._gemini_client is None:
            return None

        prompt = (
            "You are BlindNav visual page reasoner. Return ONLY JSON.\n"
            "Schema:\n"
            "{\n"
            '  "page_type": "HOME|SEARCH_RESULTS|PRODUCT_DETAIL|CART|CHECKOUT|UNKNOWN",\n'
            '  "confidence": 0.0,\n'
            '  "notes": "short conservative note"\n'
            "}\n"
            f"Browser observation JSON: {json.dumps(raw_observation, ensure_ascii=True)}\n"
            "Use UNKNOWN when uncertain. Be conservative."
        )

        image_base64: str | None = None
        if screenshot is not None:
            raw_image = screenshot.get("image_base64")
            if isinstance(raw_image, str) and raw_image.strip():
                image_base64 = raw_image.strip()

        if image_base64 is None:
            text = self._generate_text(model=self._vision_model, prompt=prompt)
            if not text:
                return None
            payload = _extract_first_json_object(text)
            return payload if isinstance(payload, dict) else None

        try:  # pragma: no cover - depends on SDK availability/runtime
            image_bytes = None
            import base64

            image_bytes = base64.b64decode(image_base64, validate=False)
            response = self._gemini_client.models.generate_content(
                model=self._vision_model,
                contents=[
                    prompt,
                    {"mime_type": "image/png", "data": image_bytes},
                ],
            )
            text = getattr(response, "text", None)
            if not isinstance(text, str) or not text.strip():
                return None
            payload = _extract_first_json_object(text)
            return payload if isinstance(payload, dict) else None
        except Exception as exc:  # pragma: no cover - external dependency behavior
            logger.warning("Gemini visual generation failed; using fallback: %s", exc)
            return None

    def _clean_string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        items: list[str] = []
        for raw in value:
            if isinstance(raw, str):
                cleaned = " ".join(raw.split())
                if cleaned:
                    items.append(cleaned)
        return items

    def _parse_multimodal_decision(self, value: Any, fallback: MultimodalDecision) -> MultimodalDecision:
        if isinstance(value, str):
            try:
                return MultimodalDecision(value.upper())
            except ValueError:
                return fallback
        return fallback

    def _parse_confidence_band(self, value: Any, *, confidence: float) -> ConfidenceBand:
        if isinstance(value, str):
            try:
                return ConfidenceBand(value.upper())
            except ValueError:
                pass
        if confidence >= 0.75:
            return ConfidenceBand.HIGH
        if confidence >= 0.45:
            return ConfidenceBand.MEDIUM
        return ConfidenceBand.LOW

    def _gemini_multimodal_assessment(
        self,
        *,
        intent: ProductIntentSpec | None,
        page: PageUnderstanding | None,
        verification: ProductVerificationResult | None,
        spoken_summary: str | None,
    ) -> MultimodalAssessment | None:
        prompt = (
            "You are BlindNav multimodal reasoning module. Return ONLY JSON.\n"
            "Use conservative safety-first reasoning from provided evidence only.\n"
            "Schema:\n"
            "{\n"
            '  "decision": "PROCEED|REQUIRE_USER_CONFIRMATION|REQUIRE_SENSITIVE_CHECKPOINT|HALT_LOW_CONFIDENCE",\n'
            '  "confidence": 0.0,\n'
            '  "confidence_band": "HIGH|MEDIUM|LOW",\n'
            '  "needs_user_confirmation": false,\n'
            '  "needs_sensitive_checkpoint": false,\n'
            '  "should_halt_low_confidence": false,\n'
            '  "ambiguity_notes": ["..."],\n'
            '  "trust_notes": ["..."],\n'
            '  "review_notes": ["..."],\n'
            '  "reasoning_summary": "short summary",\n'
            '  "recommended_next_step": "optional",\n'
            '  "notes": "optional"\n'
            "}\n"
            f"ProductIntentSpec JSON: {json.dumps(intent.model_dump() if intent else None, ensure_ascii=True)}\n"
            f"PageUnderstanding JSON: {json.dumps(page.model_dump() if page else None, ensure_ascii=True)}\n"
            f"ProductVerificationResult JSON: {json.dumps(verification.model_dump() if verification else None, ensure_ascii=True)}\n"
            f"Spoken summary: {json.dumps(spoken_summary, ensure_ascii=True)}\n"
            "If uncertain, favor REQUIRE_USER_CONFIRMATION or HALT_LOW_CONFIDENCE."
        )
        text = self._generate_text(model=self._multimodal_model, prompt=prompt)
        if not text:
            return None
        payload = _extract_first_json_object(text)
        if payload is None:
            return None

        fallback = build_fallback_multimodal_assessment(
            intent=intent,
            page=page,
            verification=verification,
            spoken_summary=spoken_summary,
        )
        decision = self._parse_multimodal_decision(payload.get("decision"), fallback.decision)

        try:
            confidence = float(payload.get("confidence", fallback.confidence))
        except (TypeError, ValueError):
            confidence = fallback.confidence
        confidence = max(0.0, min(1.0, confidence))

        assessment = MultimodalAssessment(
            decision=decision,
            confidence=confidence,
            confidence_band=self._parse_confidence_band(payload.get("confidence_band"), confidence=confidence),
            needs_user_confirmation=bool(
                payload.get(
                    "needs_user_confirmation",
                    decision == MultimodalDecision.REQUIRE_USER_CONFIRMATION,
                )
            ),
            needs_sensitive_checkpoint=bool(
                payload.get(
                    "needs_sensitive_checkpoint",
                    decision == MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT,
                )
            ),
            should_halt_low_confidence=bool(
                payload.get(
                    "should_halt_low_confidence",
                    decision == MultimodalDecision.HALT_LOW_CONFIDENCE,
                )
            ),
            ambiguity_notes=self._clean_string_list(payload.get("ambiguity_notes")) or fallback.ambiguity_notes,
            trust_notes=self._clean_string_list(payload.get("trust_notes")) or fallback.trust_notes,
            review_notes=self._clean_string_list(payload.get("review_notes")) or fallback.review_notes,
            reasoning_summary=(
                payload.get("reasoning_summary")
                if isinstance(payload.get("reasoning_summary"), str) and payload.get("reasoning_summary").strip()
                else fallback.reasoning_summary
            ),
            recommended_next_step=(
                payload.get("recommended_next_step")
                if isinstance(payload.get("recommended_next_step"), str) and payload.get("recommended_next_step").strip()
                else fallback.recommended_next_step
            ),
            notes=payload.get("notes") if isinstance(payload.get("notes"), str) else "Gemini multimodal assessment.",
        )
        return assessment

    def analyze_multimodal_assessment(
        self,
        *,
        intent: ProductIntentSpec | None,
        page: PageUnderstanding | None,
        verification: ProductVerificationResult | None,
        spoken_summary: str | None = None,
    ) -> MultimodalAssessment:
        parsed = self._gemini_multimodal_assessment(
            intent=intent,
            page=page,
            verification=verification,
            spoken_summary=spoken_summary,
        )
        if parsed is not None:
            return parsed
        return build_fallback_multimodal_assessment(
            intent=intent,
            page=page,
            verification=verification,
            spoken_summary=spoken_summary,
        )

    def analyze_visual_page(
        self,
        *,
        raw_observation: dict[str, object],
        screenshot: dict[str, object] | None,
    ) -> dict[str, object]:
        parsed = self._gemini_visual_page(
            raw_observation=raw_observation,
            screenshot=screenshot,
        )
        if isinstance(parsed, dict):
            return parsed
        return self._fallback_visual_page(
            raw_observation=raw_observation,
            screenshot=screenshot,
        )
