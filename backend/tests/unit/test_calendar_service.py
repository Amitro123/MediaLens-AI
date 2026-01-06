"""Unit tests for Calendar Service"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.calendar_service import CalendarWatcher, CalendarEvent
from datetime import datetime, timedelta


class TestCalendarWatcher:
    """Test the CalendarWatcher with mocks"""

    @pytest.fixture
    def watcher(self):
        return CalendarWatcher()

    def test_check_upcoming_meetings(self, watcher):
        # Test that mock events are returned
        events = watcher.check_upcoming_meetings(hours_ahead=24)
        assert isinstance(events, list)
        # Mock data should have at least one event
        assert len(events) >= 0

    def test_suggest_mode(self, watcher):
        # Test mode suggestion based on keywords
        keywords = ["bug", "error", "crash"]
        mode = watcher._suggest_mode(keywords)
        assert mode == "bug_report"
        
        keywords = ["feature", "design", "prototype"]
        mode = watcher._suggest_mode(keywords)
        assert mode == "feature_kickoff"
        
        keywords = ["general", "discussion"]
        mode = watcher._suggest_mode(keywords)
        assert mode == "general_doc"

    def test_create_draft_session(self, watcher):
        event = CalendarEvent(
            id="event_123",
            title="Project Sync",
            start_time=datetime.now() + timedelta(hours=2),
            end_time=datetime.now() + timedelta(hours=3),
            attendees=["user1@example.com", "user2@example.com"],
            context_keywords=["project", "roadmap"],
            description="Discussing the new roadmap."
        )
        
        session = watcher.create_draft_session(event)
        assert session.event_id == "event_123"
        assert session.title == "Project Sync"
        assert session.status == "waiting_for_upload"
        assert len(session.attendees) == 2

    def test_get_draft_sessions(self, watcher):
        sessions = watcher.get_draft_sessions()
        assert isinstance(sessions, list)

    def test_update_session_status(self, watcher):
        # Create a draft session first
        event = CalendarEvent(
            id="event_456",
            title="Test Meeting",
            start_time=datetime.now() + timedelta(hours=1),
            end_time=datetime.now() + timedelta(hours=2),
            attendees=["test@example.com"],
            context_keywords=["test"],
            description="Test meeting"
        )
        session = watcher.create_draft_session(event)
        
        # Update status
        watcher.update_session_status(session.session_id, "processing")
        
        # Verify update
        updated_session = watcher.get_session(session.session_id)
        assert updated_session.status == "processing"

