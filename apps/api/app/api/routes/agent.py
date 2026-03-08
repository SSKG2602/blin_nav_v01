from __future__ import annotations

from datetime import datetime
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
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
from app.agent.state import (
    AgentCommand,
    AgentEvent,
    AgentState,
    HumanCheckpointResolved,
    LowConfidenceTriggered,
    PostPurchaseObserved,
    RecoveryTriggered,
    ReviewAnalysisResult,
    TrustCheckResult,
)
from app.db.session import get_db
from app.llm.client import BlindNavLLMClient
from app.llm.dependencies import get_llm_client
from app.repositories.session_context_repo import get_session_context, update_session_context
from app.schemas.control_state import (
    CheckpointStatus,
    RecoveryKind,
    SensitiveCheckpointKind,
    SensitiveCheckpointRequest,
)
from app.schemas.purchase_support import FinalPurchaseConfirmation
from app.schemas.review_analysis import ReviewAssessment, ReviewConflictLevel
from app.schemas.trust_verification import TrustAssessment
from app.tools.browser_runtime import BrowserRuntimeClient
from app.tools.dependencies import get_browser_runtime_client
from app.tools.executor import AgentCommandExecutor

router = APIRouter(prefix="/api/sessions", tags=["agent"])
logger = logging.getLogger(__name__)


class AgentStepResponse(BaseModel):
    new_state: AgentState
    spoken_summary: str | None = None
    commands: list[AgentCommand]
    debug_notes: str | None = None


def _requires_review_confirmation(review_assessment: ReviewAssessment) -> bool:
    return review_assessment.conflict_level in {
        ReviewConflictLevel.MEDIUM,
        ReviewConflictLevel.HIGH,
    }


def _post_purchase_detected(post_purchase_summary) -> bool:
    spoken = (post_purchase_summary.spoken_summary or "").lower()
    notes = (post_purchase_summary.notes or "").lower()
    return bool(
        post_purchase_summary.order_item_title
        or post_purchase_summary.order_price_text
        or "order appears placed" in spoken
        or "order confirmation appears" in spoken
        or "order-confirmation-like" in notes
    )


def _next_follow_up_event(
    *,
    current_state: AgentState,
    trust_assessment: TrustAssessment,
    review_assessment: ReviewAssessment,
    trust_query: str | None,
    trust_merchant: str | None,
    final_purchase_confirmation,
    post_purchase_summary,
    low_confidence_status,
    recovery_status,
    consumed: set[str],
):
    if (
        low_confidence_status.active
        and current_state not in {AgentState.LOW_CONFIDENCE_HALT, AgentState.SESSION_CLOSING, AgentState.DONE}
        and "low_confidence" not in consumed
    ):
        consumed.add("low_confidence")
        return LowConfidenceTriggered(
            reason=low_confidence_status.reason or "Low confidence was activated from evidence pipeline."
        )

    if current_state == AgentState.TRUST_CHECK and "trust_check" not in consumed:
        consumed.add("trust_check")
        return TrustCheckResult(
            status=trust_assessment.status,
            reason=trust_assessment.reasoning_summary,
            query=trust_query,
            merchant=trust_merchant,
        )

    if current_state == AgentState.REVIEW_ANALYSIS and "review_analysis" not in consumed:
        consumed.add("review_analysis")
        return ReviewAnalysisResult(
            conflict_level=review_assessment.conflict_level,
            requires_user_confirmation=_requires_review_confirmation(review_assessment),
            notes=review_assessment.review_summary_spoken,
        )

    if current_state == AgentState.FINAL_CONFIRMATION and "final_confirmation" not in consumed:
        if final_purchase_confirmation.required and not final_purchase_confirmation.confirmed:
            return None
        consumed.add("final_confirmation")
        return HumanCheckpointResolved(
            approved=bool(final_purchase_confirmation.confirmed or not final_purchase_confirmation.required)
        )

    if current_state == AgentState.ORDER_PLACED and "post_purchase" not in consumed:
        if not _post_purchase_detected(post_purchase_summary):
            return None
        consumed.add("post_purchase")
        return PostPurchaseObserved(
            detected=True,
            notes=post_purchase_summary.notes,
        )

    if (
        recovery_status.active
        and recovery_status.recovery_kind
        in {
            RecoveryKind.MODAL_INTERRUPTION,
            RecoveryKind.CHECKOUT_BLOCKED,
            RecoveryKind.NAVIGATION_RECOVERY,
        }
        and current_state
        in {
            AgentState.SEARCHING_PRODUCTS,
            AgentState.VIEWING_PRODUCT_DETAIL,
            AgentState.CART_VERIFICATION,
            AgentState.CHECKOUT_FLOW,
            AgentState.ASSISTED_MODE,
            AgentState.UI_STABILIZING,
        }
        and "recovery" not in consumed
    ):
        consumed.add("recovery")
        return RecoveryTriggered(
            reason=recovery_status.reason or recovery_status.last_attempt_summary
        )

    return None


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
) -> AgentStepResponse:
    orchestrator = AgentOrchestrator(db)
    try:
        transition = orchestrator.run_step(session_id, event)
    except ValueError as exc:
        if str(exc) == "Session does not exist":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        raise

    executor = AgentCommandExecutor(browser_client)
    executor.execute_many(session_id, transition.commands)
    response_transition = transition
    aggregated_commands = list(transition.commands)
    response_spoken_summary = transition.spoken_summary

    try:
        previous_context = get_session_context(db, session_id)
        previous_product_intent = (
            previous_context.latest_product_intent if previous_context is not None else None
        )
        derived_intent = derive_interpreted_intent_from_event(event)
        resolved_product_intent = resolve_product_intent_from_event(event, previous_product_intent)
        spoken_summary = transition.spoken_summary

        observation_payload: dict[str, object] = {}
        screenshot_payload: dict[str, object] | None = None
        try:
            page_understanding, hybrid_observation, hybrid_screenshot = capture_page_understanding_hybrid(
                browser_client=browser_client,
                llm_client=llm_client,
                session_id=session_id,
            )
            observation_payload = (
                hybrid_observation if isinstance(hybrid_observation, dict) else {}
            )
            screenshot_payload = (
                hybrid_screenshot if isinstance(hybrid_screenshot, dict) else None
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
                previous_context.latest_sensitive_checkpoint
                if previous_context is not None
                else None
            ),
        )
        if checkpoint_request is None and response_transition.new_state == AgentState.CHECKPOINT_SENSITIVE_ACTION:
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
            multimodal_assessment=multimodal_assessment,
            page=page_understanding,
            low_confidence_status=low_confidence_status,
        )

        if checkpoint_request is not None:
            logger.info(
                "sensitive_checkpoint_activated session_id=%s kind=%s",
                session_id,
                checkpoint_request.kind.value,
            )
        if low_confidence_status.active:
            logger.info("low_confidence_active session_id=%s", session_id)
        if recovery_status.active:
            logger.info(
                "recovery_active session_id=%s kind=%s",
                session_id,
                recovery_status.recovery_kind.value if recovery_status.recovery_kind else "UNKNOWN",
            )

        expected_merchant: str | None = None
        if derived_intent is not None and derived_intent.merchant:
            expected_merchant = derived_intent.merchant
        elif previous_context is not None and previous_context.latest_intent is not None:
            previous_intent = previous_context.latest_intent
            merchant_value = None
            if isinstance(previous_intent, dict):
                merchant_value = previous_intent.get("merchant")
            else:
                merchant_value = getattr(previous_intent, "merchant", None)
            if isinstance(merchant_value, str) and merchant_value.strip():
                expected_merchant = merchant_value.strip()

        trust_assessment = derive_trust_assessment(
            observation=observation_payload if isinstance(observation_payload, dict) else None,
            expected_merchant=expected_merchant,
        )
        review_assessment = derive_review_assessment(
            page=page_understanding,
            multimodal_assessment=multimodal_assessment,
        )
        final_purchase_confirmation = derive_final_purchase_confirmation(
            checkpoint=checkpoint_request,
            multimodal_assessment=multimodal_assessment,
            page=page_understanding,
            previous_confirmation=(
                previous_context.latest_final_purchase_confirmation
                if previous_context is not None
                else None
            ),
        )
        if (
            response_transition.new_state == AgentState.FINAL_CONFIRMATION
            and not final_purchase_confirmation.required
        ):
            final_purchase_confirmation = FinalPurchaseConfirmation(
                required=True,
                confirmed=False,
                prompt_to_user="Checkout is ready. Please provide explicit final purchase confirmation.",
                confirmation_phrase_expected="confirm purchase",
                notes="Derived from FINAL_CONFIRMATION state boundary.",
            )
        post_purchase_summary = derive_post_purchase_summary(
            page=page_understanding,
            observation=observation_payload if isinstance(observation_payload, dict) else None,
            trust_assessment=trust_assessment,
        )

        update_payload: dict[str, object] = {"latest_spoken_summary": spoken_summary}
        if derived_intent is not None:
            update_payload["latest_intent"] = derived_intent
        if resolved_product_intent is not None:
            update_payload["latest_product_intent"] = resolved_product_intent
        if page_understanding is not None:
            update_payload["latest_page_understanding"] = page_understanding
        if verification_result is not None:
            update_payload["latest_verification"] = verification_result
        update_payload["latest_multimodal_assessment"] = multimodal_assessment
        update_payload["latest_sensitive_checkpoint"] = checkpoint_request
        update_payload["latest_low_confidence_status"] = low_confidence_status
        update_payload["latest_recovery_status"] = recovery_status
        update_payload["latest_trust_assessment"] = trust_assessment
        update_payload["latest_review_assessment"] = review_assessment
        update_payload["latest_final_purchase_confirmation"] = final_purchase_confirmation
        update_payload["latest_post_purchase_summary"] = post_purchase_summary
        if screenshot_payload is not None and screenshot_payload.get("notes"):
            existing_notes = post_purchase_summary.notes or ""
            screenshot_note = str(screenshot_payload.get("notes"))
            if screenshot_note and screenshot_note not in existing_notes:
                update_payload["latest_post_purchase_summary"] = post_purchase_summary.model_copy(
                    update={
                        "notes": (existing_notes + " " + screenshot_note).strip(),
                    }
                )

        trust_query: str | None = None
        if resolved_product_intent is not None:
            trust_query = resolved_product_intent.raw_query
        elif derived_intent is not None:
            trust_query = derived_intent.raw_utterance

        consumed_follow_ups: set[str] = set()
        for _ in range(6):
            follow_up_event = _next_follow_up_event(
                current_state=response_transition.new_state,
                trust_assessment=trust_assessment,
                review_assessment=review_assessment,
                trust_query=trust_query,
                trust_merchant=expected_merchant,
                final_purchase_confirmation=final_purchase_confirmation,
                post_purchase_summary=post_purchase_summary,
                low_confidence_status=low_confidence_status,
                recovery_status=recovery_status,
                consumed=consumed_follow_ups,
            )
            if follow_up_event is None:
                break

            follow_up_transition = orchestrator.run_step(session_id, follow_up_event)
            executor.execute_many(session_id, follow_up_transition.commands)
            aggregated_commands.extend(follow_up_transition.commands)
            response_transition = follow_up_transition
            if follow_up_transition.spoken_summary:
                response_spoken_summary = follow_up_transition.spoken_summary

        update_session_context(
            db,
            session_id,
            **update_payload,
        )
    except Exception as exc:
        logger.warning(
            "agent_step_evidence_pipeline_failed session_id=%s error=%s",
            session_id,
            exc,
        )

    return AgentStepResponse(
        new_state=response_transition.new_state,
        spoken_summary=response_spoken_summary,
        commands=aggregated_commands,
        debug_notes=response_transition.debug_notes,
    )
