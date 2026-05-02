from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings


@pytest.fixture
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    database_path = tmp_path / "auth-test.sqlite3"
    previous_database_url = os.environ.get("DATABASE_URL")
    previous_jwt_secret_key = os.environ.get("JWT_SECRET_KEY")

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{database_path.as_posix()}"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-1234567890-abcdef"
    get_settings.cache_clear()

    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client

    if previous_database_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous_database_url

    if previous_jwt_secret_key is None:
        os.environ.pop("JWT_SECRET_KEY", None)
    else:
        os.environ["JWT_SECRET_KEY"] = previous_jwt_secret_key

    get_settings.cache_clear()


def register_demo_user(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "demo@example.com",
            "username": "demo",
            "password": "secret123",
        },
    )
    assert response.status_code == 201


def test_register_user_success(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "Demo@Example.com",
            "username": "demo",
            "password": "secret123",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["email"] == "demo@example.com"
    assert payload["username"] == "demo"
    assert payload["display_name"] == "demo"
    assert payload["is_admin"] is False
    assert "password_hash" not in payload


@pytest.mark.parametrize(
    ("payload", "expected_detail"),
    [
        (
            {
                "email": "demo@example.com",
                "username": "demo-two",
                "password": "secret123",
            },
            "Email is already in use.",
        ),
        (
            {
                "email": "other@example.com",
                "username": "demo",
                "password": "secret123",
            },
            "Username is already in use.",
        ),
    ],
)
def test_register_user_rejects_duplicate_identity(
    client: TestClient,
    payload: dict[str, str],
    expected_detail: str,
) -> None:
    register_demo_user(client)

    response = client.post("/api/auth/register", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == expected_detail


def test_login_user_success(client: TestClient) -> None:
    register_demo_user(client)

    response = client.post(
        "/api/auth/login",
        json={"email": "demo@example.com", "password": "secret123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["user"]["email"] == "demo@example.com"
    assert payload["user"]["is_admin"] is False


def test_login_user_rejects_invalid_credentials(client: TestClient) -> None:
    register_demo_user(client)

    response = client.post(
        "/api/auth/login",
        json={"email": "demo@example.com", "password": "wrong-pass"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_current_user_returns_authenticated_profile(client: TestClient) -> None:
    register_demo_user(client)
    login_response = client.post(
        "/api/auth/login",
        json={"email": "demo@example.com", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "demo@example.com"
    assert payload["username"] == "demo"
    assert payload["is_admin"] is False
    assert "password_hash" not in payload


def test_current_user_rejects_invalid_token(client: TestClient) -> None:
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer bad-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"
