from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import AgentLogORM, SessionContextORM, SessionORM, UserAuthTokenORM, UserORM


def _client() -> TestClient:
    assert SessionORM is not None
    assert AgentLogORM is not None
    assert SessionContextORM is not None
    assert UserORM is not None
    assert UserAuthTokenORM is not None

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_signup_login_and_me_flow() -> None:
    with _client() as client:
        signup = client.post(
            "/api/auth/signup",
            json={
                "email": "demo@example.com",
                "display_name": "Demo User",
                "password": "secret123",
                "preferred_locale": "hi-IN",
            },
        )
        assert signup.status_code == 201
        payload = signup.json()
        assert payload["token"]
        assert payload["profile"]["display_name"] == "Demo User"
        assert payload["profile"]["preferred_locale"] == "hi-IN"

        me = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {payload['token']}"},
        )
        assert me.status_code == 200
        assert me.json()["profile"]["email"] == "demo@example.com"

        login = client.post(
            "/api/auth/login",
            json={
                "email": "demo@example.com",
                "password": "secret123",
            },
        )
        assert login.status_code == 200
        assert login.json()["profile"]["display_name"] == "Demo User"


def test_authenticated_session_history_is_scoped_to_user() -> None:
    with _client() as client:
        first_user = client.post(
            "/api/auth/signup",
            json={
                "email": "first@example.com",
                "display_name": "First User",
                "password": "secret123",
            },
        ).json()
        second_user = client.post(
            "/api/auth/signup",
            json={
                "email": "second@example.com",
                "display_name": "Second User",
                "password": "secret123",
            },
        ).json()

        client.post(
            "/api/sessions",
            json={"merchant": "amazon.in"},
            headers={"Authorization": f"Bearer {first_user['token']}"},
        )
        client.post(
            "/api/sessions",
            json={"merchant": "flipkart.com"},
            headers={"Authorization": f"Bearer {second_user['token']}"},
        )

        first_history = client.get(
            "/api/sessions",
            headers={"Authorization": f"Bearer {first_user['token']}"},
        )
        assert first_history.status_code == 200
        items = first_history.json()
        assert len(items) == 1
        assert items[0]["owner_display_name"] == "First User"
