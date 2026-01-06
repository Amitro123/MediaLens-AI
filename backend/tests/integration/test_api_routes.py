"""Integration tests for API routes using TestClient"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client for FastAPI app"""
    from app.main import app
    return TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_root_endpoint(self, client):
        """Test root endpoint returns app info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        # Root returns name, description, version, docs
        assert "name" in data
        assert "DevLens" in data["name"]

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        # Status can be "ok" or "healthy" depending on implementation
        assert data.get("status") in ["ok", "healthy"]


class TestModesEndpoint:
    """Test documentation modes endpoint"""

    def test_list_modes(self, client):
        """Test listing available modes"""
        response = client.get("/api/v1/modes")
        assert response.status_code == 200
        data = response.json()
        assert "modes" in data
        assert isinstance(data["modes"], list)
        assert len(data["modes"]) > 0

    def test_mode_structure(self, client):
        """Test mode object structure"""
        response = client.get("/api/v1/modes")
        data = response.json()
        
        if data["modes"]:
            mode = data["modes"][0]
            assert "mode" in mode
            assert "name" in mode
            assert "description" in mode


class TestSessionsEndpoint:
    """Test sessions/history endpoints"""

    def test_get_history(self, client):
        """Test getting session history"""
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_nonexistent_session(self, client):
        """Test getting a session that doesn't exist"""
        response = client.get("/api/sessions/nonexistent_session_xyz")
        # Should return 404 or empty response
        assert response.status_code in [200, 404]

    def test_get_active_session(self, client):
        """Test getting active session (returns null if none)"""
        response = client.get("/api/v1/active-session")
        assert response.status_code == 200
        # Response can be null or an active session object


class TestStatusEndpoints:
    """Test status polling endpoints"""

    def test_get_status_invalid_task(self, client):
        """Test getting status for invalid task ID"""
        response = client.get("/api/v1/status/invalid_task_id")
        # Should return 404 or not_found status
        assert response.status_code in [200, 404]

    def test_get_result_invalid_task(self, client):
        """Test getting result for invalid task ID"""
        response = client.get("/api/v1/result/invalid_task_id")
        # Should return 404 or error
        assert response.status_code in [200, 404]


class TestDraftSessions:
    """Test draft/calendar session endpoints"""

    def test_get_draft_sessions(self, client):
        """Test getting draft sessions"""
        response = client.get("/api/v1/sessions/drafts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestFeedbackEndpoint:
    """Test feedback submission"""

    def test_submit_feedback_invalid_session(self, client):
        """Test submitting feedback for invalid session"""
        response = client.post(
            "/api/v1/sessions/invalid_session/feedback",
            json={"rating": 5, "comment": "Great!"}
        )
        # Should accept or return 404
        assert response.status_code in [200, 404]


class TestCancelEndpoint:
    """Test session cancellation"""

    def test_cancel_invalid_session(self, client):
        """Test cancelling an invalid session"""
        response = client.post("/api/v1/sessions/invalid_session/cancel")
        # Should return success or not found
        assert response.status_code in [200, 404]


class TestExportEndpoint:
    """Test export functionality"""

    def test_export_invalid_session(self, client):
        """Test exporting an invalid session"""
        response = client.post(
            "/api/v1/sessions/invalid_session/export",
            json={"target": "clipboard"}
        )
        assert response.status_code in [200, 404]
