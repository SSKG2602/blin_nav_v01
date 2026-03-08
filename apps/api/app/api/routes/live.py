from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.api.routes.agent import run_agent_step_endpoint
from app.api.routes.session import (
    resolve_final_purchase_confirmation_state,
    resolve_sensitive_checkpoint_state,
)
from app.agent.state import HumanCheckpointResolved, SessionCloseRequested, UserIntentParsed
from app.db.session import get_db
from app.live.dependencies import get_live_speech_provider
from app.live.localization import (
    localize_message,
    localize_prompt_text,
    localize_spoken_text,
    normalize_locale,
)
from app.live.speech import LiveSpeechProvider
from app.llm.client import BlindNavLLMClient
from app.llm.dependencies import get_llm_client
from app.repositories.session_context_repo import get_session_context
from app.repositories.session_repo import create_session, get_session
from app.schemas.control_state import CheckpointStatus
from app.schemas.intent import InterpretedUserIntent, ShoppingAction
from app.schemas.live_session import LiveSessionCreateRequest, LiveSessionCreateResponse
from app.schemas.session import Merchant, SessionCreate
from app.tools.browser_runtime import BrowserRuntimeClient
from app.tools.dependencies import get_browser_runtime_client

router = APIRouter(prefix="/api/live", tags=["live"])


def _merchant_from_text(value: str | None, fallback: Merchant) -> Merchant:
    if not value:
        return fallback
    try:
        return Merchant(value)
    except ValueError:
        return fallback


def _map_action_to_intent(action: ShoppingAction) -> str:
    if action == ShoppingAction.SEARCH_PRODUCT:
        return "search_products"
    if action == ShoppingAction.REFINE_RESULTS:
        return "refine_results"
    if action == ShoppingAction.SELECT_PRODUCT:
        return "select_product"
    if action == ShoppingAction.ADD_TO_CART:
        return "add_to_cart"
    if action == ShoppingAction.PROCEED_CHECKOUT:
        return "proceed_checkout"
    if action == ShoppingAction.CANCEL:
        return "cancel"
    return "unknown"


def _build_user_intent_event(
    *,
    text: str,
    default_merchant: Merchant,
    llm_client: BlindNavLLMClient,
) -> tuple[InterpretedUserIntent, UserIntentParsed]:
    interpreted = llm_client.interpret_user_intent(text)
    merchant = _merchant_from_text(interpreted.merchant, default_merchant)
    query = text.strip()
    if interpreted.product_intent is not None:
        query = interpreted.product_intent.raw_query
    event = UserIntentParsed(
        intent=_map_action_to_intent(interpreted.action),
        query=query,
        merchant=merchant,
    )
    return interpreted, event


async def _send_event(websocket: WebSocket, event: str, data: dict[str, Any]) -> None:
    await websocket.send_json({"event": event, "data": data})


async def _send_spoken_output(
    websocket: WebSocket,
    *,
    speech_provider: LiveSpeechProvider,
    text: str,
    locale: str,
) -> None:
    localized_spoken = localize_spoken_text(text, locale)
    try:
        speech_payload = speech_provider.synthesize_text(
            text=localized_spoken,
            locale=locale,
        )
    except Exception:
        speech_payload = {
            "text": localized_spoken,
            "audio_base64": None,
            "provider": "fallback-error",
            "locale": locale,
            "playback_mode": "text_only",
        }
    await _send_event(
        websocket,
        "spoken_output",
        speech_payload if isinstance(speech_payload, dict) else {"text": localized_spoken, "locale": locale},
    )


async def _emit_control_state_events(
    websocket: WebSocket,
    *,
    db: Session,
    session_id: UUID,
    locale: str,
) -> None:
    context = get_session_context(db, session_id)
    if context is None:
        return

    if (
        context.latest_sensitive_checkpoint is not None
        and context.latest_sensitive_checkpoint.status == CheckpointStatus.PENDING
    ):
        localized_prompt = localize_prompt_text(
            context.latest_sensitive_checkpoint.prompt_to_user,
            locale,
            fallback_key="checkpoint_required",
        )
        await _send_event(
            websocket,
            "checkpoint_required",
            {
                **context.latest_sensitive_checkpoint.model_dump(mode="json"),
                "locale": locale,
                "message": localized_prompt or localize_message("checkpoint_required", locale),
            },
        )

    if (
        context.latest_final_purchase_confirmation is not None
        and context.latest_final_purchase_confirmation.required
        and not context.latest_final_purchase_confirmation.confirmed
    ):
        localized_prompt = localize_prompt_text(
            context.latest_final_purchase_confirmation.prompt_to_user,
            locale,
            fallback_key="final_confirmation_required",
        )
        await _send_event(
            websocket,
            "final_confirmation_required",
            {
                **context.latest_final_purchase_confirmation.model_dump(mode="json"),
                "locale": locale,
                "message": localized_prompt or localize_message("final_confirmation_required", locale),
            },
        )


async def _emit_agent_step_bundle(
    websocket: WebSocket,
    *,
    db: Session,
    session_id: UUID,
    locale: str,
    speech_provider: LiveSpeechProvider,
    step_response,
    fallback_text: str,
) -> None:
    await _send_event(
        websocket,
        "agent_step",
        step_response.model_dump(mode="json"),
    )
    spoken_text = step_response.spoken_summary or fallback_text
    await _send_spoken_output(
        websocket,
        speech_provider=speech_provider,
        text=spoken_text,
        locale=locale,
    )
    await _emit_control_state_events(
        websocket,
        db=db,
        session_id=session_id,
        locale=locale,
    )


@router.post(
    "/sessions",
    response_model=LiveSessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_live_session_endpoint(
    payload: LiveSessionCreateRequest,
    db: Session = Depends(get_db),
) -> LiveSessionCreateResponse:
    normalized_locale = normalize_locale(payload.locale)
    created = create_session(
        db,
        SessionCreate(
            merchant=payload.merchant,
            locale=normalized_locale,
        ),
    )
    return LiveSessionCreateResponse(
        session_id=created.session_id,
        websocket_path=f"/api/live/sessions/{created.session_id}/stream",
        locale=normalized_locale,
    )


@router.websocket("/sessions/{session_id}/stream")
async def live_session_stream(
    session_id: UUID,
    websocket: WebSocket,
    db: Session = Depends(get_db),
    browser_client: BrowserRuntimeClient = Depends(get_browser_runtime_client),
    llm_client: BlindNavLLMClient = Depends(get_llm_client),
    speech_provider: LiveSpeechProvider = Depends(get_live_speech_provider),
) -> None:
    session = get_session(db, session_id)
    if session is None:
        await websocket.close(code=4404)
        return

    default_locale = normalize_locale(session.locale)
    await websocket.accept()
    await _send_event(
        websocket,
        "session_connected",
        {
            "session_id": str(session_id),
            "merchant": session.merchant.value,
            "locale": default_locale,
            "message": localize_message("session_connected", default_locale),
        },
    )
    await _emit_control_state_events(
        websocket,
        db=db,
        session_id=session_id,
        locale=default_locale,
    )

    while True:
        try:
            incoming = await websocket.receive_json()
        except WebSocketDisconnect:
            break

        if not isinstance(incoming, dict):
            await _send_event(websocket, "error", {"detail": "Invalid event payload."})
            continue

        event_type_raw = incoming.get("type")
        event_type = event_type_raw.lower().strip() if isinstance(event_type_raw, str) else ""
        requested_locale = incoming.get("locale") if isinstance(incoming.get("locale"), str) else None
        locale = normalize_locale(requested_locale or default_locale)

        if event_type == "ping":
            await _send_event(websocket, "pong", {})
            continue

        if event_type == "start":
            await _send_event(
                websocket,
                "session_started",
                {
                    "session_id": str(session_id),
                    "locale": locale,
                    "message": localize_message("session_started", locale),
                },
            )
            continue

        if event_type == "interrupt":
            await _send_event(
                websocket,
                "interrupted",
                {"message": localize_message("interrupted", locale), "locale": locale},
            )
            continue

        if event_type == "checkpoint_response":
            approved = bool(incoming.get("approved"))
            resolution_notes = (
                incoming.get("resolution_notes")
                if isinstance(incoming.get("resolution_notes"), str)
                else None
            )
            try:
                checkpoint = resolve_sensitive_checkpoint_state(
                    db=db,
                    session_id=session_id,
                    approved=approved,
                    resolution_notes=resolution_notes,
                )
            except HTTPException as exc:
                await _send_event(
                    websocket,
                    "error",
                    {"detail": str(exc.detail), "locale": locale},
                )
                continue

            await _send_event(
                websocket,
                "checkpoint_resolved",
                {
                    **checkpoint.model_dump(mode="json"),
                    "locale": locale,
                    "message": localize_message(
                        "checkpoint_approved" if approved else "checkpoint_rejected",
                        locale,
                    ),
                },
            )
            try:
                step_response = run_agent_step_endpoint(
                    session_id=session_id,
                    event=HumanCheckpointResolved(approved=approved),
                    db=db,
                    browser_client=browser_client,
                    llm_client=llm_client,
                )
            except HTTPException as exc:
                await _send_event(
                    websocket,
                    "error",
                    {"detail": str(exc.detail), "locale": locale},
                )
                continue

            await _emit_agent_step_bundle(
                websocket,
                db=db,
                session_id=session_id,
                locale=locale,
                speech_provider=speech_provider,
                step_response=step_response,
                fallback_text=localize_message(
                    "checkpoint_approved" if approved else "checkpoint_rejected",
                    locale,
                ),
            )
            continue

        if event_type == "final_confirmation_response":
            approved = bool(incoming.get("approved"))
            resolution_notes = (
                incoming.get("resolution_notes")
                if isinstance(incoming.get("resolution_notes"), str)
                else None
            )
            try:
                final_confirmation = resolve_final_purchase_confirmation_state(
                    db=db,
                    session_id=session_id,
                    approved=approved,
                    resolution_notes=resolution_notes,
                )
            except HTTPException as exc:
                await _send_event(
                    websocket,
                    "error",
                    {"detail": str(exc.detail), "locale": locale},
                )
                continue

            await _send_event(
                websocket,
                "final_confirmation_resolved",
                {
                    **final_confirmation.model_dump(mode="json"),
                    "locale": locale,
                    "message": localize_message(
                        "final_confirmation_approved"
                        if approved
                        else "final_confirmation_rejected",
                        locale,
                    ),
                },
            )
            try:
                step_response = run_agent_step_endpoint(
                    session_id=session_id,
                    event=HumanCheckpointResolved(approved=approved),
                    db=db,
                    browser_client=browser_client,
                    llm_client=llm_client,
                )
            except HTTPException as exc:
                await _send_event(
                    websocket,
                    "error",
                    {"detail": str(exc.detail), "locale": locale},
                )
                continue

            await _emit_agent_step_bundle(
                websocket,
                db=db,
                session_id=session_id,
                locale=locale,
                speech_provider=speech_provider,
                step_response=step_response,
                fallback_text=localize_message(
                    "final_confirmation_approved"
                    if approved
                    else "final_confirmation_rejected",
                    locale,
                ),
            )
            continue

        user_text: str | None = None
        if event_type == "audio_chunk":
            audio_base64 = incoming.get("audio_base64")
            transcript_hint = (
                incoming.get("transcript_hint")
                if isinstance(incoming.get("transcript_hint"), str)
                else None
            )
            if not isinstance(audio_base64, str) or not audio_base64.strip():
                await _send_event(
                    websocket,
                    "error",
                    {"detail": "audio_base64 is required.", "locale": locale},
                )
                continue
            try:
                user_text = speech_provider.transcribe_audio_chunk(
                    audio_base64=audio_base64,
                    locale=locale,
                    transcript_hint=transcript_hint,
                )
            except Exception:
                user_text = None
            await _send_event(
                websocket,
                "transcription",
                {"text": user_text, "locale": locale},
            )
            if not user_text:
                continue
        elif event_type == "user_text":
            raw_text = incoming.get("text")
            if not isinstance(raw_text, str) or not raw_text.strip():
                await _send_event(
                    websocket,
                    "error",
                    {"detail": "text is required.", "locale": locale},
                )
                continue
            user_text = raw_text.strip()
        elif event_type == "cancel":
            try:
                step_response = run_agent_step_endpoint(
                    session_id=session_id,
                    event=SessionCloseRequested(),
                    db=db,
                    browser_client=browser_client,
                    llm_client=llm_client,
                )
            except HTTPException as exc:
                await _send_event(
                    websocket,
                    "error",
                    {"detail": str(exc.detail), "locale": locale},
                )
                continue

            await _send_event(
                websocket,
                "agent_step",
                step_response.model_dump(mode="json"),
            )
            await _send_spoken_output(
                websocket,
                speech_provider=speech_provider,
                text=localize_message("cancelled", locale),
                locale=locale,
            )
            continue
        else:
            await _send_event(
                websocket,
                "error",
                {"detail": "Unsupported event type.", "locale": locale},
            )
            continue

        interpreted_intent, agent_event = _build_user_intent_event(
            text=user_text,
            default_merchant=session.merchant,
            llm_client=llm_client,
        )
        await _send_event(
            websocket,
            "interpreted_intent",
            interpreted_intent.model_dump(mode="json"),
        )

        try:
            step_response = run_agent_step_endpoint(
                session_id=session_id,
                event=agent_event,
                db=db,
                browser_client=browser_client,
                llm_client=llm_client,
            )
        except HTTPException as exc:
            await _send_event(
                websocket,
                "error",
                {"detail": str(exc.detail), "locale": locale},
            )
            continue

        await _emit_agent_step_bundle(
            websocket,
            db=db,
            session_id=session_id,
            locale=locale,
            speech_provider=speech_provider,
            step_response=step_response,
            fallback_text=interpreted_intent.spoken_confirmation,
        )
