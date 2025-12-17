
import pytest
from app.api.routes import session_feedback

# TestClient is provided by conftest.py's client fixture

def test_submit_feedback_success(client):
    session_id = "test_feedback_session"
    feedback_data = {
        "rating": 5,
        "comment": "Great documentation!",
        "section_id": "overview"
    }
    
    response = client.post(f"/api/v1/sessions/{session_id}/feedback", json=feedback_data)
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Verify storage
    assert session_id in session_feedback
    assert len(session_feedback[session_id]) == 1
    stored = session_feedback[session_id][0]
    assert stored["rating"] == 5
    assert stored["comment"] == "Great documentation!"

def test_submit_feedback_invalid_rating(client):
    session_id = "test_invalid_rating"
    feedback_data = {
        "rating": 6,  # Invalid
        "comment": "Too good"
    }
    
    response = client.post(f"/api/v1/sessions/{session_id}/feedback", json=feedback_data)
    
    assert response.status_code == 400
    assert "Rating must be between 1 and 5" in response.json()["detail"]

def test_submit_feedback_multiple(client):
    session_id = "test_multiple_feedback"
    
    # First feedback
    res1 = client.post(f"/api/v1/sessions/{session_id}/feedback", json={"rating": 4})
    assert res1.status_code == 200, f"First request failed: {res1.text}"
    
    # Second feedback
    res2 = client.post(f"/api/v1/sessions/{session_id}/feedback", json={"rating": 3})
    assert res2.status_code == 200, f"Second request failed: {res2.text}"
    
    assert len(session_feedback[session_id]) == 2
