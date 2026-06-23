"""Tests for admin language statistics API endpoints."""

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

api_main = pytest.importorskip("app.api.main")
from app.services.language_analytics import LanguageAnalytics


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(api_main.app)


@pytest.fixture
def analytics():
    """Create fresh analytics instance."""
    LanguageAnalytics._instance = None
    instance = LanguageAnalytics.get_instance()
    instance.clear_statistics()
    yield instance
    instance.clear_statistics()


@pytest.fixture
def admin_user():
    """Mock admin user with required permissions."""
    return {
        "user_id": "admin-123",
        "username": "admin",
        "role": "admin",
        "status": "active",
    }


@pytest.fixture
def regular_user():
    """Mock regular user without admin permissions."""
    return {
        "user_id": "user-123",
        "username": "user",
        "role": "viewer",
        "status": "active",
    }


class TestLanguageStatsEndpoint:
    """Test GET /admin/language/stats endpoint."""

    def test_get_language_statistics_empty(self, client, analytics, admin_user):
        """Test getting statistics when no events logged."""
        api_main.app.dependency_overrides[api_main._require_user] = lambda: admin_user
        try:
            response = client.get("/admin/language/stats")
            assert response.status_code == 200
            data = response.json()
            assert data["total_queries"] == 0
            assert data["language_distribution"] == {}
            assert data["forced_vs_auto"]["auto_detected"] == 0
            assert data["forced_vs_auto"]["forced"] == 0
        finally:
            api_main.app.dependency_overrides.clear()

    def test_get_language_statistics_with_data(self, client, analytics, admin_user):
        """Test getting statistics with logged events."""
        api_main.app.dependency_overrides[api_main._require_user] = lambda: admin_user
        try:
            # Log some events
            analytics.log_detection("Query 1", "en", "", "session-1")
            analytics.log_detection("Query 2", "zh", "", "session-1")
            analytics.log_detection("Query 3", "en", "en", "session-2")

            response = client.get("/admin/language/stats")
            assert response.status_code == 200
            data = response.json()
            assert data["total_queries"] == 3
            assert data["language_distribution"]["en"] == 2
            assert data["language_distribution"]["zh"] == 1
            assert data["forced_vs_auto"]["auto_detected"] == 2
            assert data["forced_vs_auto"]["forced"] == 1
            assert data["session_count"] == 2
            assert len(data["recent_events"]) == 3
        finally:
            api_main.app.dependency_overrides.clear()

    def test_get_language_statistics_requires_admin(self, client, regular_user):
        """Test that endpoint requires admin role."""
        api_main.app.dependency_overrides[api_main._require_user] = lambda: regular_user
        try:
            response = client.get("/admin/language/stats")
            assert response.status_code == 403
        finally:
            api_main.app.dependency_overrides.clear()


class TestSessionLanguageStatsEndpoint:
    """Test GET /admin/language/stats/session/{session_id} endpoint."""

    def test_get_session_statistics_empty(self, client, analytics, admin_user):
        """Test getting session statistics when session has no events."""
        api_main.app.dependency_overrides[api_main._require_user] = lambda: admin_user
        try:
            response = client.get("/admin/language/stats/session/session-1")
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "session-1"
            assert data["total_queries"] == 0
            assert data["language_distribution"] == {}
            assert data["events"] == []
        finally:
            api_main.app.dependency_overrides.clear()

    def test_get_session_statistics_with_data(self, client, analytics, admin_user):
        """Test getting session statistics with logged events."""
        api_main.app.dependency_overrides[api_main._require_user] = lambda: admin_user
        try:
            # Log events for multiple sessions
            analytics.log_detection("Q1", "en", "", "session-1")
            analytics.log_detection("Q2", "zh", "", "session-1")
            analytics.log_detection("Q3", "en", "", "session-2")

            response = client.get("/admin/language/stats/session/session-1")
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "session-1"
            assert data["total_queries"] == 2
            assert data["language_distribution"]["en"] == 1
            assert data["language_distribution"]["zh"] == 1
            assert len(data["events"]) == 2
        finally:
            api_main.app.dependency_overrides.clear()

    def test_get_session_statistics_requires_admin(self, client, regular_user):
        """Test that endpoint requires admin role."""
        api_main.app.dependency_overrides[api_main._require_user] = lambda: regular_user
        try:
            response = client.get("/admin/language/stats/session/session-1")
            assert response.status_code == 403
        finally:
            api_main.app.dependency_overrides.clear()


class TestClearLanguageStatsEndpoint:
    """Test DELETE /admin/language/stats endpoint."""

    def test_clear_language_statistics(self, client, analytics, admin_user):
        """Test clearing language statistics."""
        api_main.app.dependency_overrides[api_main._require_user] = lambda: admin_user
        try:
            # Log some events
            analytics.log_detection("Q1", "en", "", "session-1")
            analytics.log_detection("Q2", "zh", "", "session-1")

            # Verify events exist
            stats_before = analytics.get_statistics()
            assert stats_before["total_queries"] == 2

            # Clear statistics
            response = client.delete("/admin/language/stats")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "cleared" in data["message"].lower()

            # Verify events are cleared
            stats_after = analytics.get_statistics()
            assert stats_after["total_queries"] == 0
        finally:
            api_main.app.dependency_overrides.clear()

    def test_clear_language_statistics_requires_admin(self, client, regular_user):
        """Test that endpoint requires admin role."""
        api_main.app.dependency_overrides[api_main._require_user] = lambda: regular_user
        try:
            response = client.delete("/admin/language/stats")
            assert response.status_code == 403
        finally:
            api_main.app.dependency_overrides.clear()


class TestLanguageStatsAuthentication:
    """Test authentication and authorization for language stats endpoints."""

    def test_endpoints_require_authentication(self, client):
        """Test that all endpoints require authentication."""
        # No dependency override = no authentication
        response = client.get("/admin/language/stats")
        assert response.status_code == 401

        response = client.get("/admin/language/stats/session/session-1")
        assert response.status_code == 401

        response = client.delete("/admin/language/stats")
        assert response.status_code == 401
