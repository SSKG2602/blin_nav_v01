from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import AgentLogORM, SessionContextORM, SessionORM
from app.repositories.session_context_repo import update_session_context
from app.schemas.control_state import (
    CheckpointStatus,
    SensitiveCheckpointKind,
    SensitiveCheckpointRequest,
)
from app.schemas.purchase_support import FinalPurchaseConfirmation


@pytest.fixture
def testing_session_local():
    assert SessionORM is not None
    assert AgentLogORM is not None
    assert SessionContextORM is not None

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    yield session_local
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(testing_session_local) -> TestClient:
    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_session_and_seed_checkpoint(client: TestClient, testing_session_local) -> str:
    created = client.post("/api/sessions", json={"merchant": "amazon.in"}).json()
    session_id = created["session_id"]
    with testing_session_local() as db:
        update_session_context(
            db,
            UUID(session_id),
            latest_sensitive_checkpoint=SensitiveCheckpointRequest(
                kind=SensitiveCheckpointKind.FINAL_PURCHASE_CONFIRMATION,
                status=CheckpointStatus.PENDING,
                reason="Final confirmation required.",
                prompt_to_user="Please confirm before final purchase.",
            ),
        )
    return session_id


def test_get_checkpoint_success(client: TestClient, testing_session_local) -> None:
    session_id = _create_session_and_seed_checkpoint(client, testing_session_local)
    response = client.get(f"/api/sessions/{session_id}/checkpoint")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == CheckpointStatus.PENDING.value
    assert payload["kind"] == SensitiveCheckpointKind.FINAL_PURCHASE_CONFIRMATION.value


def test_resolve_checkpoint_approve(client: TestClient, testing_session_local) -> None:
    session_id = _create_session_and_seed_checkpoint(client, testing_session_local)
    response = client.post(
        f"/api/sessions/{session_id}/checkpoint/resolve",
        json={"approved": True, "resolution_notes": "User approved."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == CheckpointStatus.APPROVED.value
    assert payload["resolved_at"] is not None
    assert payload["resolution_notes"] == "User approved."

    context = client.get(f"/api/sessions/{session_id}/context")
    context_payload = context.json()
    assert context_payload["latest_sensitive_checkpoint"] is not None
    assert context_payload["latest_sensitive_checkpoint"]["status"] == CheckpointStatus.APPROVED.value
    assert context_payload["latest_final_purchase_confirmation"] is None


def test_resolve_checkpoint_reject(client: TestClient, testing_session_local) -> None:
    session_id = _create_session_and_seed_checkpoint(client, testing_session_local)
    response = client.post(
        f"/api/sessions/{session_id}/checkpoint/resolve",
        json={"approved": False, "resolution_notes": "User rejected."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == CheckpointStatus.REJECTED.value
    assert payload["resolution_notes"] == "User rejected."

    context = client.get(f"/api/sessions/{session_id}/context")
    context_payload = context.json()
    assert context_payload["latest_sensitive_checkpoint"] is not None
    assert context_payload["latest_sensitive_checkpoint"]["status"] == CheckpointStatus.REJECTED.value
    assert context_payload["latest_final_purchase_confirmation"] is None


def test_checkpoint_routes_missing_session_return_404(client: TestClient) -> None:
    missing = uuid4()
    get_response = client.get(f"/api/sessions/{missing}/checkpoint")
    post_response = client.post(
        f"/api/sessions/{missing}/checkpoint/resolve",
        json={"approved": True},
    )

    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Session not found"
    assert post_response.status_code == 404
    assert post_response.json()["detail"] == "Session not found"


def test_checkpoint_routes_return_404_when_no_checkpoint(client: TestClient) -> None:
    created = client.post("/api/sessions", json={"merchant": "amazon.in"}).json()
    session_id = created["session_id"]

    get_response = client.get(f"/api/sessions/{session_id}/checkpoint")
    post_response = client.post(
        f"/api/sessions/{session_id}/checkpoint/resolve",
        json={"approved": True},
    )

    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Checkpoint not found"
    assert post_response.status_code == 404
    assert post_response.json()["detail"] == "Checkpoint not found"


def test_final_confirmation_routes_round_trip(client: TestClient, testing_session_local) -> None:
    created = client.post("/api/sessions", json={"merchant": "amazon.in"}).json()
    session_id = created["session_id"]
    with testing_session_local() as db:
        update_session_context(
            db,
            UUID(session_id),
            latest_final_purchase_confirmation=FinalPurchaseConfirmation(
                required=True,
                confirmed=False,
                prompt_to_user="Please confirm final purchase.",
                confirmation_phrase_expected="confirm purchase",
                notes="seeded final confirmation",
            ),
        )

    get_response = client.get(f"/api/sessions/{session_id}/final-confirmation")
    assert get_response.status_code == 200
    assert get_response.json()["required"] is True
    assert get_response.json()["confirmed"] is False

    resolve_response = client.post(
        f"/api/sessions/{session_id}/final-confirmation/resolve",
        json={"approved": True, "resolution_notes": "Confirmed in test."},
    )
    assert resolve_response.status_code == 200
    payload = resolve_response.json()
    assert payload["required"] is True
    assert payload["confirmed"] is True
    assert payload["notes"] == "Confirmed in test."
