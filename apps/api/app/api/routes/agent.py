from __future__ import annotations

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
from app.agent.observation import build_page_understanding_from_browser_observation
from app.agent.orchestrator import AgentOrchestrator
from app.agent.product_verification import verify_product_against_intent
from app.agent.state import AgentCommand, AgentEvent, AgentState
from app.db.session import get_db
from app.llm.client import BlindNavLLMClient
from app.llm.dependencies import get_llm_client
from app.repositories.session_context_repo import get_session_context, update_session_context
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

    try:
        previous_context = get_session_context(db, session_id)
        previous_product_intent = (
            previous_context.latest_product_intent if previous_context is not None else None
        )
        derived_intent = derive_interpreted_intent_from_event(event)
        resolved_product_intent = resolve_product_intent_from_event(event, previous_product_intent)
        spoken_summary = transition.spoken_summary

        try:
            observation_payload = browser_client.get_current_page_observation(session_id=session_id)
        except Exception as exc:
            logger.warning(
                "observation_fetch_failed session_id=%s error=%s",
                session_id,
                exc,
            )
            observation_payload = {}

        try:
            page_understanding = build_page_understanding_from_browser_observation(
                observation_payload if isinstance(observation_payload, dict) else {}
            )
        except Exception as exc:
            logger.warning(
                "page_understanding_build_failed session_id=%s error=%s",
                session_id,
                exc,
            )
            page_understanding = None

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
        new_state=transition.new_state,
        spoken_summary=transition.spoken_summary,
        commands=transition.commands,
        debug_notes=transition.debug_notes,
    )
