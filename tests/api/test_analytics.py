"""
Integration tests for Analytics API endpoints.

NOTE: These tests require httpx >= 0.27.2 due to compatibility with Starlette 0.35.1.
If tests fail with "TypeError: Client.__init__() got an unexpected keyword argument 'app'",
run: pip install "httpx>=0.27.2" --upgrade
"""

import pytest

from app.api.main import app
from app.services.retrieval_logger import RetrievalLog, RetrievalLogger

ADMIN_HEADERS = {"X-Test-User": "admin", "X-Test-Role": "admin", "X-Test-User-Id": "admin-123"}


@pytest.fixture
def client():
    """Create a test client for the app."""
    try:
        from fastapi.testclient import TestClient

        with TestClient(app) as c:
            c.headers.update(ADMIN_HEADERS)
            yield c
    except TypeError as e:
        if "unexpected keyword argument 'app'" in str(e):
            pytest.skip(
                "TestClient incompatibility detected. Please upgrade httpx: pip install 'httpx>=0.27.2' --upgrade"
            )
        raise


@pytest.fixture(autouse=True)
def reset_logger():
    """Reset the logger before each test."""
    logger = RetrievalLogger.get_instance()
    # Clear logs by creating a new deque
    logger._logs.clear()
    yield
    logger._logs.clear()


@pytest.fixture
def sample_logs():
    """Create sample logs for testing."""
    logger = RetrievalLogger.get_instance()

    # Add some sample logs
    logs = [
        RetrievalLog(
            question="What is cybersecurity?",
            agent_class="cybersecurity",
            route="vector",
            filtered_docs_count=100,
            retrieved_count=5,
            effective_hit_count=3,
            top_scores=[0.95, 0.85, 0.75],
            retrieval_time_ms=50.0,
            total_time_ms=150.0,
            retrieved_sources=["doc1.md", "doc2.md", "doc3.md"],
            has_result=True,
        ),
        RetrievalLog(
            question="What is AI?",
            agent_class="artificial_intelligence",
            route="graph",
            filtered_docs_count=80,
            retrieved_count=4,
            effective_hit_count=2,
            top_scores=[0.90, 0.80],
            retrieval_time_ms=60.0,
            total_time_ms=180.0,
            retrieved_sources=["doc1.md", "doc4.md"],
            has_result=True,
        ),
        RetrievalLog(
            question="General question",
            agent_class="general",
            route="hybrid",
            filtered_docs_count=50,
            retrieved_count=3,
            effective_hit_count=1,
            top_scores=[0.70],
            retrieval_time_ms=40.0,
            total_time_ms=120.0,
            retrieved_sources=["doc5.md"],
            has_result=False,
            error="No relevant results",
        ),
    ]

    for log in logs:
        logger.log_retrieval(log)

    return logs


def test_get_overview_empty(client):
    """Test overview endpoint with no logs."""
    response = client.get("/api/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert "total_queries" in data
    assert "success_rate" in data
    assert data["total_queries"] == 0
    assert data["success_rate"] == 0.0


def test_get_overview_empty_with_app_base_prefix(client):
    """Analytics overview should remain reachable when public deployments prefix APIs with /app."""
    response = client.get("/app/api/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["total_queries"] == 0
    assert data["success_rate"] == 0.0


def test_get_overview(client, sample_logs):
    """Test overview endpoint with sample logs."""
    response = client.get("/api/analytics/overview")
    assert response.status_code == 200
    data = response.json()

    # Check required fields
    assert "total_queries" in data
    assert "success_rate" in data
    assert "avg_retrieval_time_ms" in data
    assert "avg_total_time_ms" in data
    assert "avg_retrieved_count" in data
    assert "avg_effective_hit_count" in data
    assert "agent_distribution" in data
    assert "route_distribution" in data

    # Verify values
    assert data["total_queries"] == 3
    assert data["success_rate"] == pytest.approx(66.67, rel=0.1)  # 2/3 successful
    assert isinstance(data["agent_distribution"], dict)
    assert isinstance(data["route_distribution"], dict)


def test_get_agents_empty(client):
    """Test agents endpoint with no logs."""
    response = client.get("/api/analytics/agents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 0


def test_get_agents(client, sample_logs):
    """Test agents endpoint with sample logs."""
    response = client.get("/api/analytics/agents")
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 3  # Three different agents

    # Check structure of first agent
    if data:
        agent = data[0]
        assert "agent_class" in agent
        assert "query_count" in agent
        assert "success_rate" in agent
        assert "avg_retrieval_time_ms" in agent
        assert "avg_total_time_ms" in agent
        assert "avg_retrieved_count" in agent
        assert "avg_effective_hit_count" in agent
        assert "avg_top_score" in agent


def test_get_documents_empty(client):
    """Test documents endpoint with no logs."""
    response = client.get("/api/analytics/documents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 0


def test_get_documents_default_limit(client, sample_logs):
    """Test documents endpoint with default limit."""
    response = client.get("/api/analytics/documents")
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) <= 20  # Default limit

    # Check structure
    if data:
        doc = data[0]
        assert "source" in doc
        assert "retrieval_count" in doc
        assert "avg_score" in doc
        assert "agent_usage" in doc


def test_get_documents_custom_limit(client, sample_logs):
    """Test documents endpoint with custom limit."""
    response = client.get("/api/analytics/documents?limit=2")
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) <= 2


def test_get_documents_limit_validation(client):
    """Test documents endpoint limit validation."""
    # Test minimum limit
    response = client.get("/api/analytics/documents?limit=0")
    assert response.status_code == 422  # Validation error

    # Test maximum limit
    response = client.get("/api/analytics/documents?limit=101")
    assert response.status_code == 422  # Validation error

    # Test valid limits
    response = client.get("/api/analytics/documents?limit=1")
    assert response.status_code == 200

    response = client.get("/api/analytics/documents?limit=100")
    assert response.status_code == 200


def test_export_json_empty(client):
    """Test JSON export with no logs."""
    response = client.get("/api/analytics/export?format=json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_export_json(client, sample_logs):
    """Test JSON export with sample logs."""
    response = client.get("/api/analytics/export?format=json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3

    # Check structure of first log
    log = data[0]
    assert "log_id" in log
    assert "timestamp" in log
    assert "question" in log
    assert "agent_class" in log
    assert "route" in log


def test_export_json_default_format(client, sample_logs):
    """Test export endpoint defaults to JSON."""
    response = client.get("/api/analytics/export")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"


def test_export_csv_empty(client):
    """Test CSV export with no logs."""
    response = client.get("/api/analytics/export?format=csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "Content-Disposition" in response.headers
    assert "attachment" in response.headers["Content-Disposition"]
    assert "retrieval_logs.csv" in response.headers["Content-Disposition"]

    # Should have header row
    content = response.text
    assert "log_id" in content
    assert "timestamp" in content


def test_export_csv(client, sample_logs):
    """Test CSV export with sample logs."""
    response = client.get("/api/analytics/export?format=csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "Content-Disposition" in response.headers
    assert "attachment" in response.headers["Content-Disposition"]
    assert "retrieval_logs.csv" in response.headers["Content-Disposition"]

    # Check content
    content = response.text
    lines = content.strip().split("\n")
    assert len(lines) >= 4  # Header + 3 data rows

    # Check header
    header = lines[0]
    assert "log_id" in header
    assert "question" in header
    assert "agent_class" in header


def test_export_format_validation(client):
    """Test export format validation."""
    # Invalid format
    response = client.get("/api/analytics/export?format=xml")
    assert response.status_code == 422  # Validation error

    # Valid formats
    response = client.get("/api/analytics/export?format=json")
    assert response.status_code == 200

    response = client.get("/api/analytics/export?format=csv")
    assert response.status_code == 200

