from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.api.routes.agent import _apply_efficiency_policy
from app.agent.state import AgentCommand, AgentCommandType, AgentState
from app.schemas.agent_log import AgentLogEntry, AgentStepType


def _log(*, state_after: AgentState, tool_name: str = "agent.runtime", error_type: str | None = None) -> AgentLogEntry:
    return AgentLogEntry(
        session_id=uuid4(),
        step_type=AgentStepType.NAVIGATION,
        state_before=AgentState.SEARCHING_PRODUCTS.value,
        state_after=state_after.value,
        tool_name=tool_name,
        error_type=error_type,
        created_at=datetime.utcnow(),
    )


def test_efficiency_policy_suppresses_repeated_state_loops() -> None:
    commands = [AgentCommand(type=AgentCommandType.INSPECT_PRODUCT_PAGE)]
    recent_logs = [
        _log(state_after=AgentState.VIEWING_PRODUCT_DETAIL),
        _log(state_after=AgentState.VIEWING_PRODUCT_DETAIL),
        _log(state_after=AgentState.VIEWING_PRODUCT_DETAIL),
    ]

    replacement, log_entry = _apply_efficiency_policy(
        session_id=uuid4(),
        prior_state=AgentState.SEARCHING_PRODUCTS,
        new_state=AgentState.VIEWING_PRODUCT_DETAIL,
        commands=commands,
        recent_logs=recent_logs,
        pass_index=1,
    )

    assert [command.type for command in replacement] == [AgentCommandType.HANDLE_ERROR_RECOVERY]
    assert replacement[0].payload["error_type"] == "loop_suppressed"
    assert log_entry is not None
    assert log_entry.tool_name == "agent.efficiency"
    assert log_entry.error_type == "loop_suppressed"


def test_efficiency_policy_enforces_runtime_budget() -> None:
    commands = [AgentCommand(type=AgentCommandType.REVIEW_CART)]

    replacement, log_entry = _apply_efficiency_policy(
        session_id=uuid4(),
        prior_state=AgentState.CART_VERIFICATION,
        new_state=AgentState.CART_VERIFICATION,
        commands=commands,
        recent_logs=[],
        pass_index=8,
    )

    assert [command.type for command in replacement] == [AgentCommandType.HANDLE_ERROR_RECOVERY]
    assert replacement[0].payload["error_type"] == "runtime_budget_exceeded"
    assert log_entry is not None
    assert "budget" in (log_entry.error_message or "").lower()
