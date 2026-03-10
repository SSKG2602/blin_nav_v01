from __future__ import annotations

from datetime import datetime
import logging
import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session
from starlette import status

from app.agent.control_state import (
    derive_low_confidence_status,
    derive_recovery_status,
    derive_sensitive_checkpoint,
)
from app.agent.decision_support import (
    derive_final_purchase_confirmation,
    derive_post_purchase_summary,
    derive_review_assessment,
    derive_trust_assessment,
)
from app.agent.intent_resolution import (
    derive_interpreted_intent_from_event,
    resolve_product_intent_from_event,
)
from app.agent.multimodal import build_fallback_multimodal_assessment
from app.agent.observation import (
    build_page_understanding_from_browser_observation,
    capture_page_understanding_hybrid,
)
from app.agent.orchestrator import AgentOrchestrator
from app.agent.product_verification import verify_product_against_intent
from app.agent.runtime_bridge import (
    build_cart_snapshot,
    derive_clarification_request,
    derive_runtime_follow_up_event,
)
from app.agent.order_support import build_latest_order_snapshot
from app.agent.session_closure import (
    build_final_self_diagnosis,
    build_final_session_artifact,
)
from app.agent.state import (
    AgentCommand,
    AgentCommandType,
    AgentEvent,
    AgentState,
)
from app.db.session import get_db
from app.llm.client import BlindNavLLMClient
from app.llm.dependencies import get_llm_client
from app.repositories.session_context_repo import get_session_context, update_session_context
from app.repositories.session_repo import append_agent_log, list_agent_logs_for_session
from app.security import AuthenticatedUser, get_current_user_optional
from app.schemas.agent_log import AgentLogEntry, AgentStepType
from app.schemas.clarification import ClarificationRequest, ClarificationStatus
from app.schemas.control_state import (
    CheckpointStatus,
    SensitiveCheckpointKind,
    SensitiveCheckpointRequest,
)
from app.schemas.intent import InterpretedUserIntent
from app.schemas.interruption import InterruptionMarker
from app.schemas.page_understanding import PageType, PageUnderstanding, ProductCandidate
from app.schemas.product_verification import ProductIntentSpec
from app.schemas.purchase_support import FinalPurchaseConfirmation
from app.schemas.session_context import SessionContextSnapshot
from app.tools.browser_runtime import BrowserRuntimeClient
from app.tools.dependencies import get_browser_runtime_client
from app.tools.executor import AgentCommandExecutor

router = APIRouter(prefix="/api/sessions", tags=["agent"])
logger = logging.getLogger(__name__)

_MAX_RUNTIME_CLOSURE_PASSES = 10


class AgentStepResponse(BaseModel):
    new_state: AgentState
    spoken_summary: str | None = None
    commands: list[AgentCommand]
    debug_notes: str | None = None


def _safe_text(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _coerce_interpreted_intent(value: object) -> InterpretedUserIntent | None:
    if value is None:
        return None
    if isinstance(value, InterpretedUserIntent):
        return value
    if isinstance(value, dict):
        try:
            return InterpretedUserIntent.model_validate(value)
        except ValidationError:
            return None
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


def _resolve_interpreted_intent(
    *,
    event: AgentEvent,
    interpreted_intent: InterpretedUserIntent | None,
    previous_context: SessionContextSnapshot | None,
) -> InterpretedUserIntent | None:
    if interpreted_intent is not None:
        return interpreted_intent

    derived = derive_interpreted_intent_from_event(event)
    if derived is not None:
        return derived

    if previous_context is None:
        return None
    return _coerce_interpreted_intent(previous_context.latest_intent)


def _resolve_product_intent(
    *,
    event: AgentEvent,
    interpreted_intent: InterpretedUserIntent | None,
    previous_context: SessionContextSnapshot | None,
) -> ProductIntentSpec | None:
    previous_product_intent = (
        previous_context.latest_product_intent if previous_context is not None else None
    )
    if interpreted_intent is not None and interpreted_intent.product_intent is not None:
        return _merge_product_intents(
            interpreted_intent.product_intent,
            previous_product_intent,
        )
    return resolve_product_intent_from_event(event, previous_product_intent)


def _derive_expected_merchant(
    *,
    interpreted_intent: InterpretedUserIntent | None,
    previous_context: SessionContextSnapshot | None,
) -> str | None:
    merchant = _safe_text(interpreted_intent.merchant if interpreted_intent is not None else None)
    if merchant:
        return merchant

    previous_intent = _coerce_interpreted_intent(
        previous_context.latest_intent if previous_context is not None else None
    )
    return _safe_text(previous_intent.merchant if previous_intent is not None else None)


def _derive_trust_query(
    *,
    interpreted_intent: InterpretedUserIntent | None,
    product_intent: ProductIntentSpec | None,
) -> str | None:
    if product_intent is not None and _safe_text(product_intent.raw_query):
        return _safe_text(product_intent.raw_query)
    if interpreted_intent is not None:
        return _safe_text(interpreted_intent.raw_utterance)
    return None


def _decorate_commands(
    commands: list[AgentCommand],
    *,
    product_intent: ProductIntentSpec | None,
    previous_context: SessionContextSnapshot | None,
    llm_client: BlindNavLLMClient | None = None,
) -> list[AgentCommand]:
    decorated: list[AgentCommand] = []
    query = _safe_text(product_intent.raw_query if product_intent is not None else None)
    variant_hint = _safe_text(product_intent.variant if product_intent is not None else None)
    size_hint = _safe_text(product_intent.size_text if product_intent is not None else None)
    color_hint = _safe_text(product_intent.color if product_intent is not None else None)
    preferred_candidate = _choose_candidate_for_intent(
        page=previous_context.latest_page_understanding if previous_context is not None else None,
        product_intent=product_intent,
        llm_client=llm_client,
    )

    for command in commands:
        payload = dict(command.payload or {})
        if command.type == AgentCommandType.NAVIGATE_TO_SEARCH_RESULTS and query and not payload.get("query"):
            payload["query"] = query
        if command.type == AgentCommandType.INSPECT_PRODUCT_PAGE and preferred_candidate is not None:
            if preferred_candidate.url and not payload.get("candidate_url"):
                payload["candidate_url"] = preferred_candidate.url
            if preferred_candidate.title and not payload.get("candidate_title"):
                payload["candidate_title"] = preferred_candidate.title
        if command.type in {
            AgentCommandType.SELECT_PRODUCT_VARIANT,
            AgentCommandType.VERIFY_PRODUCT_VARIANT,
        }:
            if variant_hint and not payload.get("variant_hint"):
                payload["variant_hint"] = variant_hint
            if size_hint and not payload.get("size_hint"):
                payload["size_hint"] = size_hint
            if color_hint and not payload.get("color_hint"):
                payload["color_hint"] = color_hint
        decorated.append(command.model_copy(update={"payload": payload}))
    return decorated


def _normalized_tokens(value: str | None) -> list[str]:
    text = _safe_text(value)
    if not text:
        return []
    return [token for token in text.lower().replace("/", " ").replace("-", " ").split() if token]


def _score_candidate(
    candidate: ProductCandidate,
    *,
    product_intent: ProductIntentSpec,
) -> int:
    haystack = " ".join(
        part
        for part in [
            _safe_text(candidate.title),
            _safe_text(candidate.variant_text),
            _safe_text(candidate.availability_text),
        ]
        if part
    ).lower()
    score = 0

    brand = _safe_text(product_intent.brand)
    if brand:
        if brand.lower() in haystack:
            score += 5
        else:
            score -= 2

    product_name_tokens = _normalized_tokens(product_intent.product_name)
    matched_name_tokens = sum(1 for token in product_name_tokens if token in haystack)
    score += matched_name_tokens * 3
    if product_name_tokens and matched_name_tokens == 0:
        score -= 5

    for field_value in (
        product_intent.variant,
        product_intent.color,
        product_intent.size_text,
        product_intent.quantity_text,
    ):
        field_text = _safe_text(field_value)
        if not field_text:
            continue
        field_lower = field_text.lower()
        haystack_nospace = re.sub(r"\s+", "", haystack)
        field_nospace = re.sub(r"\s+", "", field_lower)
        if field_lower in haystack or (field_nospace and field_nospace in haystack_nospace):
            score += 4
        else:
            score -= 1

    if candidate.url and "/dp/" in candidate.url.lower():
        score += 4
    if candidate.price_text:
        score += 1
    if candidate.rating_text:
        score += 1

    return score


def _choose_candidate_for_intent(
    *,
    page: PageUnderstanding | None,
    product_intent: ProductIntentSpec | None,
    llm_client: BlindNavLLMClient | None = None,
) -> ProductCandidate | None:
    if page is None or product_intent is None or not page.product_candidates:
        return None

    scored: list[tuple[int, ProductCandidate]] = []
    for candidate in page.product_candidates:
        score = _score_candidate(candidate, product_intent=product_intent)
        scored.append((score, candidate))

    scored.sort(key=lambda x: x[0], reverse=True)
    best_candidate = scored[0][1] if scored else None
    best_score = scored[0][0] if scored else -10_000

    if best_candidate is None or best_score < 1:
        return None

    if (
        llm_client is not None
        and len(scored) >= 2
        and abs(scored[0][0] - scored[1][0]) <= 2
        and product_intent.raw_query
    ):
        top2_candidates = [scored[0][1], scored[1][1]]
        try:
            gemini_index = llm_client.score_product_candidates(
                query=product_intent.raw_query,
                candidates=[
                    {
                        "title": candidate.title,
                        "url": candidate.url,
                        "price_text": candidate.price_text,
                    }
                    for candidate in top2_candidates
                ],
            )
            if gemini_index is not None and 0 <= gemini_index < len(top2_candidates):
                chosen = top2_candidates[gemini_index]
                logger.info(
                    "gemini_tiebreak_applied query=%s picked=%s over=%s",
                    product_intent.raw_query,
                    chosen.title,
                    top2_candidates[1 - gemini_index].title,
                )
                return chosen
        except Exception as exc:
            logger.warning(
                "gemini_tiebreak_failed query=%s error=%s falling_back_to_regex_winner",
                product_intent.raw_query,
                exc,
            )

    return best_candidate


def _resolve_clarification_request(
    *,
    previous_request: ClarificationRequest | None,
    derived_request: ClarificationRequest | None,
    triggering_event: AgentEvent,
    new_state: AgentState,
) -> ClarificationRequest | None:
    if derived_request is not None:
        return derived_request

    if previous_request is None:
        return None

    if previous_request.status == ClarificationStatus.PENDING and new_state != AgentState.CLARIFICATION_REQUIRED:
        if hasattr(triggering_event, "event_type") and getattr(triggering_event, "event_type") == "clarification_resolved":
            status_value = ClarificationStatus.PROVIDED_INPUT
            if bool(getattr(triggering_event, "approved", True)) and not (
                getattr(triggering_event, "follow_up_query", None)
                or getattr(triggering_event, "follow_up_intent", None)
            ):
                status_value = ClarificationStatus.APPROVED
            if not bool(getattr(triggering_event, "approved", True)):
                status_value = ClarificationStatus.REJECTED
            return previous_request.model_copy(
                update={
                    "status": status_value,
                    "clarified_response": _safe_text(
                        getattr(triggering_event, "follow_up_query", None)
                    ),
                    "resolution_notes": _safe_text(
                        getattr(triggering_event, "resolution_notes", None)
                    ),
                    "resolved_at": datetime.utcnow(),
                }
            )

        return previous_request.model_copy(
            update={
                "status": ClarificationStatus.CANCELLED,
                "resolution_notes": "Clarification boundary cleared without a pending prompt.",
                "resolved_at": datetime.utcnow(),
            }
        )

    return previous_request


def _resolve_interruption_marker(
    *,
    previous_marker: InterruptionMarker | None,
    triggering_event: AgentEvent,
    prior_state: AgentState,
    latest_spoken_summary: str | None,
) -> InterruptionMarker | None:
    if hasattr(triggering_event, "event_type") and getattr(triggering_event, "event_type") == "interruption_requested":
        return InterruptionMarker(
            active=True,
            interrupted_at=datetime.utcnow(),
            prior_state=prior_state.value,
            reason=_safe_text(getattr(triggering_event, "reason", None)),
            latest_user_utterance=None,
            resume_summary=_safe_text(latest_spoken_summary),
        )

    if (
        previous_marker is not None
        and previous_marker.active
        and hasattr(triggering_event, "event_type")
        and getattr(triggering_event, "event_type") == "clarification_resolved"
    ):
        return previous_marker.model_copy(
            update={
                "active": False,
                "latest_user_utterance": _safe_text(
                    getattr(triggering_event, "follow_up_query", None)
                ),
                "resume_summary": _safe_text(latest_spoken_summary) or previous_marker.resume_summary,
            }
        )

    return previous_marker


def _bind_clarification_resolution(
    *,
    event: AgentEvent,
    previous_request: ClarificationRequest | None,
) -> AgentEvent:
    if (
        previous_request is None
        or previous_request.status != ClarificationStatus.PENDING
        or not hasattr(event, "event_type")
        or getattr(event, "event_type") != "clarification_resolved"
    ):
        return event

    if (
        previous_request.kind == "PRODUCT_SELECTION"
        and bool(getattr(event, "approved", True))
        and not getattr(event, "follow_up_query", None)
        and previous_request.candidate_options
    ):
        selected = previous_request.candidate_options[0]
        return event.model_copy(
            update={
                "candidate_url": selected.candidate_url,
                "candidate_title": selected.title,
            }
        )
    return event


def _ensure_final_confirmation_boundary(
    *,
    current_state: AgentState,
    current_confirmation: FinalPurchaseConfirmation,
) -> FinalPurchaseConfirmation:
    if current_state != AgentState.FINAL_CONFIRMATION or current_confirmation.required:
        return current_confirmation

    return FinalPurchaseConfirmation(
        required=True,
        confirmed=False,
        prompt_to_user="Checkout is ready. Please provide explicit final purchase confirmation.",
        confirmation_phrase_expected="confirm purchase",
        notes="Derived from FINAL_CONFIRMATION state boundary.",
    )


def _loop_signature(
    *,
    current_state: AgentState,
    follow_up_event: AgentEvent,
    observation_payload: dict[str, object],
    verification_result,
    checkpoint_request: SensitiveCheckpointRequest | None,
    clarification_request: ClarificationRequest | None,
    final_purchase_confirmation: FinalPurchaseConfirmation,
) -> tuple[object, ...]:
    return (
        current_state.value,
        getattr(follow_up_event, "event_type", "unknown"),
        observation_payload.get("observed_url"),
        observation_payload.get("page_title"),
        getattr(verification_result, "decision", None),
        checkpoint_request.kind.value if checkpoint_request is not None else None,
        checkpoint_request.status.value if checkpoint_request is not None else None,
        clarification_request.kind.value if clarification_request is not None else None,
        clarification_request.status.value if clarification_request is not None else None,
        final_purchase_confirmation.required,
        final_purchase_confirmation.confirmed,
    )


def _apply_efficiency_policy(
    *,
    session_id: UUID,
    prior_state: AgentState,
    new_state: AgentState,
    commands: list[AgentCommand],
    recent_logs: list[AgentLogEntry],
    pass_index: int,
) -> tuple[list[AgentCommand], AgentLogEntry | None]:
    if not commands:
        return commands, None

    recent_window = recent_logs[-10:]
    same_state_count = sum(1 for log in recent_window if log.state_after == new_state.value)
    repeated_errors = sum(1 for log in recent_window if log.error_type)
    repeated_checkout = sum(
        1
        for log in recent_window
        if log.tool_name == "agent.checkout_planner" or log.tool_name == "agent.final_confirmation"
    )
    fallback_error_type: str | None = None
    summary: str | None = None

    if pass_index >= 8:
        fallback_error_type = "runtime_budget_exceeded"
        summary = "Runtime step budget was exceeded; switching to recovery."
    elif new_state in {
        AgentState.SEARCHING_PRODUCTS,
        AgentState.VIEWING_PRODUCT_DETAIL,
        AgentState.CART_VERIFICATION,
        AgentState.CHECKOUT_FLOW,
        AgentState.UI_STABILIZING,
    } and same_state_count >= 3:
        fallback_error_type = "loop_suppressed"
        summary = f"Repeated transitions into {new_state.value} were suppressed."
    elif new_state == AgentState.CHECKOUT_FLOW and repeated_checkout >= 2:
        fallback_error_type = "checkout_retry_budget_exceeded"
        summary = "Repeated checkout attempts were suppressed and routed to recovery."
    elif repeated_errors >= 2:
        fallback_error_type = "repeated_failure_suppressed"
        summary = "Repeated tool failures were suppressed and routed to recovery."

    if fallback_error_type is None:
        return commands, None

    replacement = [
        AgentCommand(
            type=AgentCommandType.HANDLE_ERROR_RECOVERY,
            payload={"error_type": fallback_error_type},
        )
    ]
    log_entry = AgentLogEntry(
        session_id=session_id,
        step_type=AgentStepType.META,
        state_before=prior_state.value,
        state_after=new_state.value,
        tool_name="agent.efficiency",
        tool_input_excerpt=",".join(command.type.value for command in commands[:4]),
        tool_output_excerpt=summary,
        error_type=fallback_error_type,
        error_message=summary,
        user_spoken_summary=summary,
        created_at=datetime.utcnow(),
    )
    return replacement, log_entry


def run_agent_step(
    *,
    session_id: UUID,
    event: AgentEvent,
    db: Session,
    browser_client: BrowserRuntimeClient,
    llm_client: BlindNavLLMClient,
    interpreted_intent: InterpretedUserIntent | None = None,
) -> AgentStepResponse:
    orchestrator = AgentOrchestrator(db)
    executor = AgentCommandExecutor(browser_client)

    aggregated_commands: list[AgentCommand] = []
    response_transition = None
    response_spoken_summary: str | None = None
    current_event = event
    active_interpreted_intent = interpreted_intent
    seen_signatures: set[tuple[object, ...]] = set()

    for pass_index in range(_MAX_RUNTIME_CLOSURE_PASSES):
        previous_context = get_session_context(db, session_id)
        current_event = _bind_clarification_resolution(
            event=current_event,
            previous_request=(
                previous_context.latest_clarification_request if previous_context is not None else None
            ),
        )
        prior_state = orchestrator._infer_current_state(session_id)
        active_interpreted_intent = _resolve_interpreted_intent(
            event=current_event,
            interpreted_intent=active_interpreted_intent,
            previous_context=previous_context,
        )
        resolved_product_intent = _resolve_product_intent(
            event=current_event,
            interpreted_intent=active_interpreted_intent,
            previous_context=previous_context,
        )

        transition = orchestrator.run_step(session_id, current_event)
        recent_logs = list_agent_logs_for_session(db, session_id)
        efficiency_commands, efficiency_log = _apply_efficiency_policy(
            session_id=session_id,
            prior_state=prior_state,
            new_state=transition.new_state,
            commands=transition.commands,
            recent_logs=recent_logs,
            pass_index=pass_index,
        )
        if efficiency_log is not None:
            append_agent_log(db, efficiency_log)
            recent_logs.append(efficiency_log)

        decorated_commands = _decorate_commands(
            efficiency_commands,
            product_intent=resolved_product_intent,
            previous_context=previous_context,
            llm_client=llm_client,
        )
        executor.execute_many(session_id, decorated_commands)

        aggregated_commands.extend(decorated_commands)
        response_transition = transition.model_copy(update={"commands": decorated_commands})
        if transition.spoken_summary:
            response_spoken_summary = transition.spoken_summary

        try:
            page_understanding, observation_payload, screenshot_payload = capture_page_understanding_hybrid(
                browser_client=browser_client,
                llm_client=llm_client,
                session_id=session_id,
            )
        except Exception as exc:
            logger.warning(
                "page_understanding_hybrid_capture_failed session_id=%s error=%s",
                session_id,
                exc,
            )
            page_understanding = build_page_understanding_from_browser_observation({})
            observation_payload = {}
            screenshot_payload = None

        verification_result = None
        if (
            resolved_product_intent is not None
            and page_understanding is not None
            and page_understanding.primary_product is not None
        ):
            verification_result = verify_product_against_intent(
                resolved_product_intent,
                page_understanding.primary_product,
            )
        if (
            verification_result is not None
            and verification_result.decision.name == "INSUFFICIENT_EVIDENCE"
            and previous_context is not None
            and previous_context.latest_verification is not None
            and page_understanding is not None
            and page_understanding.page_type == PageType.UNKNOWN
        ):
            verification_result = previous_context.latest_verification

        spoken_summary = response_spoken_summary
        if page_understanding is not None:
            try:
                llm_summary = llm_client.summarize_page_and_verification(
                    page_understanding,
                    verification_result,
                )
                if isinstance(llm_summary, str) and llm_summary.strip():
                    spoken_summary = llm_summary.strip()
            except Exception as exc:
                logger.warning(
                    "llm_summary_generation_failed session_id=%s error=%s",
                    session_id,
                    exc,
                )

        try:
            multimodal_assessment = llm_client.analyze_multimodal_assessment(
                intent=resolved_product_intent,
                page=page_understanding,
                verification=verification_result,
                spoken_summary=spoken_summary,
            )
        except Exception as exc:
            logger.warning(
                "llm_multimodal_assessment_failed session_id=%s error=%s",
                session_id,
                exc,
            )
            multimodal_assessment = build_fallback_multimodal_assessment(
                intent=resolved_product_intent,
                page=page_understanding,
                verification=verification_result,
                spoken_summary=spoken_summary,
            )

        checkpoint_request = derive_sensitive_checkpoint(
            multimodal_assessment=multimodal_assessment,
            page=page_understanding,
            verification=verification_result,
            previous_checkpoint=(
                previous_context.latest_sensitive_checkpoint if previous_context is not None else None
            ),
        )
        if checkpoint_request is None and transition.new_state == AgentState.CHECKPOINT_SENSITIVE_ACTION:
            checkpoint_request = SensitiveCheckpointRequest(
                kind=SensitiveCheckpointKind.PAYMENT_CONFIRMATION,
                status=CheckpointStatus.PENDING,
                reason="State machine entered a protected checkpoint boundary.",
                prompt_to_user="A sensitive checkpoint needs your approval before continuing.",
                created_at=datetime.utcnow(),
            )

        low_confidence_status = derive_low_confidence_status(
            multimodal_assessment=multimodal_assessment,
        )
        recovery_status = derive_recovery_status(
            current_state=transition.new_state,
            multimodal_assessment=multimodal_assessment,
            page=page_understanding,
            low_confidence_status=low_confidence_status,
        )

        expected_merchant = _derive_expected_merchant(
            interpreted_intent=active_interpreted_intent,
            previous_context=previous_context,
        )
        trust_assessment = derive_trust_assessment(
            observation=observation_payload if isinstance(observation_payload, dict) else None,
            expected_merchant=expected_merchant,
        )
        review_assessment = derive_review_assessment(
            page=page_understanding,
            multimodal_assessment=multimodal_assessment,
        )
        final_purchase_confirmation = _ensure_final_confirmation_boundary(
            current_state=transition.new_state,
            current_confirmation=derive_final_purchase_confirmation(
                checkpoint=checkpoint_request,
                multimodal_assessment=multimodal_assessment,
                page=page_understanding,
                previous_confirmation=(
                    previous_context.latest_final_purchase_confirmation
                    if previous_context is not None
                    else None
                ),
            ),
        )
        post_purchase_summary = derive_post_purchase_summary(
            page=page_understanding,
            observation=observation_payload if isinstance(observation_payload, dict) else None,
            trust_assessment=trust_assessment,
        )
        cart_snapshot = build_cart_snapshot(
            page=page_understanding,
            observation=observation_payload if isinstance(observation_payload, dict) else None,
            previous_snapshot=(
                previous_context.latest_cart_snapshot if previous_context is not None else None
            ),
        )
        latest_order_snapshot = build_latest_order_snapshot(
            observation_payload if isinstance(observation_payload, dict) else None
        ) or (previous_context.latest_order_snapshot if previous_context is not None else None)
        interruption_marker = _resolve_interruption_marker(
            previous_marker=(
                previous_context.latest_interruption_marker if previous_context is not None else None
            ),
            triggering_event=current_event,
            prior_state=prior_state,
            latest_spoken_summary=spoken_summary,
        )
        clarification_request = _resolve_clarification_request(
            previous_request=(
                previous_context.latest_clarification_request if previous_context is not None else None
            ),
            derived_request=derive_clarification_request(
                current_state=transition.new_state,
                page=page_understanding,
                derived_intent=active_interpreted_intent,
                product_intent=resolved_product_intent,
                verification=verification_result,
                review_assessment=review_assessment,
                previous_request=(
                    previous_context.latest_clarification_request if previous_context is not None else None
                ),
                interruption_active=bool(interruption_marker and interruption_marker.active),
            ),
            triggering_event=current_event,
            new_state=transition.new_state,
        )

        latest_post_purchase_summary = post_purchase_summary
        if screenshot_payload is not None and screenshot_payload.get("notes"):
            existing_notes = post_purchase_summary.notes or ""
            screenshot_note = str(screenshot_payload.get("notes"))
            if screenshot_note and screenshot_note not in existing_notes:
                latest_post_purchase_summary = post_purchase_summary.model_copy(
                    update={"notes": (existing_notes + " " + screenshot_note).strip()}
                )

        update_payload: dict[str, object] = {
            "latest_multimodal_assessment": multimodal_assessment,
            "latest_sensitive_checkpoint": checkpoint_request,
            "latest_clarification_request": clarification_request,
            "latest_low_confidence_status": low_confidence_status,
            "latest_recovery_status": recovery_status,
            "latest_interruption_marker": interruption_marker,
            "latest_trust_assessment": trust_assessment,
            "latest_review_assessment": review_assessment,
            "latest_final_purchase_confirmation": final_purchase_confirmation,
            "latest_post_purchase_summary": latest_post_purchase_summary,
            "latest_cart_snapshot": cart_snapshot,
            "latest_order_snapshot": latest_order_snapshot,
            "latest_spoken_summary": spoken_summary,
        }
        if active_interpreted_intent is not None:
            update_payload["latest_intent"] = active_interpreted_intent
        if resolved_product_intent is not None:
            update_payload["latest_product_intent"] = resolved_product_intent
        if page_understanding is not None:
            update_payload["latest_page_understanding"] = page_understanding
        if verification_result is not None:
            update_payload["latest_verification"] = verification_result

        provisional_context = SessionContextSnapshot(
            session_id=session_id,
            latest_intent=active_interpreted_intent or (previous_context.latest_intent if previous_context is not None else None),
            latest_product_intent=resolved_product_intent,
            latest_page_understanding=page_understanding,
            latest_verification=verification_result,
            latest_multimodal_assessment=multimodal_assessment,
            latest_sensitive_checkpoint=checkpoint_request,
            latest_clarification_request=clarification_request,
            latest_low_confidence_status=low_confidence_status,
            latest_recovery_status=recovery_status,
            latest_interruption_marker=interruption_marker,
            latest_trust_assessment=trust_assessment,
            latest_review_assessment=review_assessment,
            latest_final_purchase_confirmation=final_purchase_confirmation,
            latest_post_purchase_summary=latest_post_purchase_summary,
            latest_cart_snapshot=cart_snapshot,
            latest_order_snapshot=latest_order_snapshot,
            latest_final_session_artifact=(
                previous_context.latest_final_session_artifact if previous_context is not None else None
            ),
            latest_final_self_diagnosis=(
                previous_context.latest_final_self_diagnosis if previous_context is not None else None
            ),
            latest_spoken_summary=spoken_summary,
            updated_at=datetime.utcnow(),
        )
        recent_logs = list_agent_logs_for_session(db, session_id)
        update_payload["latest_final_session_artifact"] = build_final_session_artifact(
            context=provisional_context,
            logs=recent_logs,
        )
        update_payload["latest_final_self_diagnosis"] = build_final_self_diagnosis(
            context=provisional_context,
            logs=recent_logs,
        )

        update_session_context(
            db,
            session_id,
            **update_payload,
        )
        if (
            checkpoint_request is not None
            and checkpoint_request.status == CheckpointStatus.PENDING
            and (
                previous_context is None
                or previous_context.latest_sensitive_checkpoint is None
                or previous_context.latest_sensitive_checkpoint.kind != checkpoint_request.kind
                or previous_context.latest_sensitive_checkpoint.status != checkpoint_request.status
            )
        ):
            append_agent_log(
                db,
                AgentLogEntry(
                    session_id=session_id,
                    step_type=AgentStepType.CHECKOUT,
                    state_before=prior_state.value,
                    state_after=transition.new_state.value,
                    tool_name="agent.checkpoint.classifier",
                    tool_input_excerpt=checkpoint_request.kind.value,
                    tool_output_excerpt=checkpoint_request.prompt_to_user,
                    human_checkpoint=True,
                    user_spoken_summary=checkpoint_request.prompt_to_user,
                    created_at=datetime.utcnow(),
                ),
            )

        follow_up_event = derive_runtime_follow_up_event(
            current_state=transition.new_state,
            page=page_understanding,
            trust_assessment=trust_assessment,
            review_assessment=review_assessment,
            trust_query=_derive_trust_query(
                interpreted_intent=active_interpreted_intent,
                product_intent=resolved_product_intent,
            ),
            trust_merchant=expected_merchant,
            verification=verification_result,
            clarification_request=clarification_request,
            final_purchase_confirmation=final_purchase_confirmation,
            post_purchase_summary=latest_post_purchase_summary,
            low_confidence_status=low_confidence_status,
            recovery_status=recovery_status,
            cart_snapshot=cart_snapshot,
            consumed=set(),
        )
        if follow_up_event is None:
            break

        signature = _loop_signature(
            current_state=transition.new_state,
            follow_up_event=follow_up_event,
            observation_payload=observation_payload,
            verification_result=verification_result,
            checkpoint_request=checkpoint_request,
            clarification_request=clarification_request,
            final_purchase_confirmation=final_purchase_confirmation,
        )
        if signature in seen_signatures:
            logger.warning(
                "runtime_follow_up_loop_stopped session_id=%s state=%s follow_up=%s",
                session_id,
                transition.new_state.value,
                getattr(follow_up_event, "event_type", "unknown"),
            )
            break

        seen_signatures.add(signature)
        current_event = follow_up_event

    if response_transition is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent transition did not execute.",
        )

    return AgentStepResponse(
        new_state=response_transition.new_state,
        spoken_summary=response_spoken_summary,
        commands=aggregated_commands,
        debug_notes=response_transition.debug_notes,
    )


@router.post(
    "/{session_id}/agent/step",
    response_model=AgentStepResponse,
    status_code=status.HTTP_200_OK,
)
def run_agent_step_endpoint(
    session_id: UUID,
    event: AgentEvent,
    db: Session = Depends(get_db),
    browser_client: BrowserRuntimeClient = Depends(get_browser_runtime_client),
    llm_client: BlindNavLLMClient = Depends(get_llm_client),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> AgentStepResponse:
    from app.api.routes.session import _require_existing_session

    _require_existing_session(db, session_id, current_user=current_user)
    try:
        return run_agent_step(
            session_id=session_id,
            event=event,
            db=db,
            browser_client=browser_client,
            llm_client=llm_client,
        )
    except ValueError as exc:
        if str(exc) == "Session does not exist":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        raise
