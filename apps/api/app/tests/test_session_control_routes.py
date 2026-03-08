from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import SessionContextORM, SessionORM
from app.schemas.session import Merchant
from app.tools.dependencies import get_browser_runtime_client


class FakeBrowserRuntimeClient:
    def __init__(self) -> None:
        self.observation_payload: dict[str, Any] = {
            "observed_url": "https://www.amazon.in/gp/cart/view.html",
            "page_title": "Shopping Cart",
            "detected_page_hints": ["cart"],
            "cart_item_count": 2,
            "checkout_ready": True,
            "cart_items": [
                {
                    "item_id": "item-1",
                    "title": "Pedigree dog food 3kg",
                    "price_text": "₹799",
                    "quantity_text": "1",
                },
                {
                    "item_id": "item-2",
                    "title": "Pedigree gravy pouch pack",
                    "price_text": "₹299",
                    "quantity_text": "2",
                },
            ],
        }

    def navigate_to_search_results(self, *, session_id: UUID, query: str | None, merchant: Merchant | None) -> None:
        return

    def inspect_product_page(
        self,
        *,
        session_id: UUID,
        page_type: str | None,
        candidate_url: str | None = None,
        candidate_title: str | None = None,
    ) -> None:
        return

    def verify_product_variant(
        self,
        *,
        session_id: UUID,
        variant_hint: str | None = None,
        size_hint: str | None = None,
        color_hint: str | None = None,
    ) -> None:
        return

    def select_product_variant(
        self,
        *,
        session_id: UUID,
        variant_hint: str | None = None,
        size_hint: str | None = None,
        color_hint: str | None = None,
    ) -> None:
        return

    def add_to_cart(self, *, session_id: UUID) -> None:
        return

    def review_cart(self, *, session_id: UUID) -> None:
        return

    def remove_cart_item(self, *, session_id: UUID, item_id: str | None = None, title: str | None = None) -> None:
        remaining = [
            item
            for item in self.observation_payload.get("cart_items", [])
            if item.get("item_id") != item_id
        ]
        self.observation_payload["cart_items"] = remaining
        self.observation_payload["cart_item_count"] = len(remaining)

    def update_cart_quantity(
        self,
        *,
        session_id: UUID,
        item_id: str | None = None,
        title: str | None = None,
        quantity: int,
    ) -> None:
        for item in self.observation_payload.get("cart_items", []):
            if item_id and item.get("item_id") == item_id:
                item["quantity_text"] = str(quantity)
                return

    def perform_checkout(self, *, session_id: UUID) -> None:
        return

    def finalize_purchase(self, *, session_id: UUID) -> None:
        return

    def navigate_orders_history(self, *, session_id: UUID) -> None:
        self.observation_payload = {
            "observed_url": "https://www.amazon.in/gp/css/order-history",
            "page_title": "Your Orders",
            "detected_page_hints": ["home"],
            "order_id_hint": "407-1234567-8901234",
            "order_date_text": "8 March 2026",
            "shipping_stage_text": "Shipped",
            "expected_delivery_text": "12 March 2026",
            "order_total_text": "₹799",
            "order_card_title": "Pedigree dog food 3kg",
            "orders_page_url": "https://www.amazon.in/gp/css/order-history",
            "support_entry_hint": "https://www.amazon.in/contact-us",
            "returns_entry_hint": "https://www.amazon.in/returns",
        }

    def handle_error_recovery(self, *, session_id: UUID, error_type: str | None = None) -> None:
        return

    def get_current_page_observation(self, *, session_id: UUID) -> dict[str, Any]:
        return dict(self.observation_payload)

    def get_current_page_screenshot(self, *, session_id: UUID) -> dict[str, Any]:
        return {}


@pytest.fixture
def testing_session_local():
    assert SessionORM is not None
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
def fake_browser_client() -> FakeBrowserRuntimeClient:
    return FakeBrowserRuntimeClient()


@pytest.fixture
def client(testing_session_local, fake_browser_client: FakeBrowserRuntimeClient) -> TestClient:
    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_browser_runtime_client] = lambda: fake_browser_client
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_remove_cart_item_endpoint_updates_cart_snapshot(client: TestClient) -> None:
    session_id = client.post("/api/sessions", json={"merchant": "amazon.in"}).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/cart/remove",
        json={"item_id": "item-1"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["cart_item_count"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["item_id"] == "item-2"

    context = client.get(f"/api/sessions/{session_id}/context")
    assert context.status_code == 200
    assert context.json()["latest_cart_snapshot"]["cart_item_count"] == 1


def test_load_latest_order_snapshot_endpoint_persists_context(client: TestClient) -> None:
    session_id = client.post("/api/sessions", json={"merchant": "amazon.in"}).json()["session_id"]

    response = client.post(f"/api/sessions/{session_id}/orders/latest")
    assert response.status_code == 200
    payload = response.json()
    assert payload["order_card_title"] == "Pedigree dog food 3kg"
    assert payload["shipping_stage_text"] == "Shipped"
    assert payload["returns_entry_hint"] == "https://www.amazon.in/returns"

    context = client.get(f"/api/sessions/{session_id}/context")
    assert context.status_code == 200
    assert context.json()["latest_order_snapshot"]["order_card_title"] == "Pedigree dog food 3kg"


def test_update_cart_quantity_endpoint_persists_context(client: TestClient) -> None:
    session_id = client.post("/api/sessions", json={"merchant": "amazon.in"}).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/cart/quantity",
        json={"item_id": "item-2", "quantity": 4},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][1]["quantity_text"] == "4"

    context = client.get(f"/api/sessions/{session_id}/context")
    assert context.status_code == 200
    assert context.json()["latest_cart_snapshot"]["items"][1]["quantity_text"] == "4"
