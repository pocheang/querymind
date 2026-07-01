"""Tests for unified admin model APIs."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.services.auth_db import AuthDBService

auth_service = AuthDBService()


@pytest.fixture
def client():
    """Create test client."""
    from app.api.main import app
    return TestClient(app)


@pytest.fixture
def admin_token():
    """Create an admin user and return their token."""
    username = f"test_admin_{uuid.uuid4().hex[:8]}"
    user = auth_service.create_user_with_role(username=username, password="AdminPass123!", role="admin")
    result = auth_service.login(username, "AdminPass123!")
    token = result["token"]

    yield token

    # Cleanup
    try:
        auth_service.user_manager.delete_user(user["user_id"])
    except Exception:
        pass


@pytest.fixture
def user_token():
    """Create a regular user and return their token."""
    username = f"test_user_{uuid.uuid4().hex[:8]}"
    user = auth_service.register(username, "UserPass123!")
    result = auth_service.login(username, "UserPass123!")
    token = result["token"]

    yield token

    # Cleanup
    try:
        auth_service.user_manager.delete_user(user["user_id"])
    except Exception:
        pass


def test_list_model_providers_returns_catalog(client, admin_token):
    """Test that /api/admin/model-providers/list returns the provider catalog."""
    response = client.get(
        "/admin/model-providers/list",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "providers" in data

    providers = data["providers"]
    assert len(providers) > 0

    # Verify structure of each provider
    for provider in providers:
        assert "name" in provider
        assert "supports_chat" in provider
        assert "supports_embeddings" in provider
        assert "default_chat_model" in provider
        assert "default_embedding_model" in provider
        assert "display_name" in provider
        assert "requires_api_key" in provider

    # Verify specific providers exist
    provider_names = {p["name"] for p in providers}
    assert "local" in provider_names
    assert "openai" in provider_names
    assert "anthropic" in provider_names
    assert "deepseek" in provider_names


def test_list_model_providers_requires_admin(client, user_token):
    """Test that non-admin users cannot access the endpoint."""
    response = client.get(
        "/admin/model-providers/list",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 403


def test_model_monitor_stats_returns_usage_data(client, admin_token):
    """Test that /api/admin/model-monitor/stats returns model usage statistics."""
    response = client.get(
        "/admin/model-monitor/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "stats" in data

    stats = data["stats"]
    assert "total_requests" in stats
    assert "by_provider" in stats
    assert "by_model" in stats
    assert "recent_errors" in stats
    assert isinstance(stats["total_requests"], int)
    assert isinstance(stats["by_provider"], dict)
    assert isinstance(stats["by_model"], dict)
    assert isinstance(stats["recent_errors"], list)


def test_model_monitor_stats_with_time_window(client, admin_token):
    """Test that the stats endpoint accepts time window parameters."""
    response = client.get(
        "/admin/model-monitor/stats?hours=24",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "stats" in data


def test_model_monitor_stats_requires_admin(client, user_token):
    """Test that non-admin users cannot access the endpoint."""
    response = client.get(
        "/admin/model-monitor/stats",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 403
