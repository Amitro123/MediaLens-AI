"""Calendar service for managing meeting contexts and draft sessions"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pydantic import BaseModel
import uuid
import logging

logger = logging.getLogger(__name__)


class CalendarEvent(BaseModel):
    """Model for calendar events"""
    id: str
    title: str
    start_time: datetime
    end_time: datetime
    attendees: List[str]
    context_keywords: List[str]
    description: Optional[str] = None


class DraftSession(BaseModel):
    """Model for draft documentation sessions"""
    session_id: str
    event_id: str
    title: str
    attendees: List[str]
    context_keywords: List[str]
    status: str = "waiting_for_upload"
    created_at: datetime
    suggested_mode: Optional[str] = None
    metadata: Dict = {}
    # Notification tracking
    reminder_sent: bool = False
    nudge_sent: bool = False


class CalendarWatcher:
    """
    Service for watching calendar events and creating draft sessions.
    
    MVP Implementation: Uses mock data.
    Production: Integrate with Google Calendar API, Outlook, etc.
    """
    
    def __init__(self):
        """Initialize the calendar watcher with mock data"""
        """Initialize the calendar watcher with mock data"""
        self.draft_sessions: Dict[str, DraftSession] = {}
        
        # Determine fixed mock events for consistent testing (mtg_1, mtg_2, mtg_3)
        now = datetime.now()
        
        # Mock Session 1: Completed
        self.draft_sessions["mtg_1"] = DraftSession(
            session_id="mtg_1",
            event_id="evt_mock_1",
            title="Design Review: User Profile",
            attendees=["alice@company.com", "bob@company.com"],
            context_keywords=["profile", "settings", "ui"],
            status="completed", # Already done
            created_at=now - timedelta(days=1),
            suggested_mode="feature_kickoff",
            metadata={"description": "Review new user profile designs", "event_start": (now - timedelta(days=1)).isoformat(), "event_end": (now - timedelta(days=1, hours=-1)).isoformat()}
        )

        # Mock Session 2: Ready for upload
        self.draft_sessions["mtg_2"] = DraftSession(
            session_id="mtg_2",
            event_id="evt_mock_2",
            title="Bug Bash: Login Errors",
            attendees=["qa@company.com", "dev@company.com"],
            context_keywords=["auth", "login", "500 error"],
            status="ready_for_upload",
            created_at=now,
            suggested_mode="bug_report",
            metadata={"description": "Investigate login 500 errors", "event_start": (now + timedelta(hours=2)).isoformat(), "event_end": (now + timedelta(hours=3)).isoformat()}
        )
        
        # Mock Session 3: Architecture Deep Dive (changed from processing to avoid stuck UI)
        self.draft_sessions["mtg_3"] = DraftSession(
            session_id="mtg_3",
            event_id="evt_mock_3",
            title="Architecture Deep Dive",
            attendees=["cto@company.com", "yann@company.com"],
            context_keywords=["scalability", "database", "sharding"],
            status="ready_for_upload",
            created_at=now,
            suggested_mode="general_doc",
            metadata={"description": "Discussing database sharding strategy", "event_start": (now + timedelta(hours=4)).isoformat(), "event_end": (now + timedelta(hours=5)).isoformat()}
        )

        logger.info("CalendarWatcher initialized with deterministic mock data (mtg_1, mtg_2, mtg_3)")
    
    def check_upcoming_meetings(self, hours_ahead: int = 24) -> List[CalendarEvent]:
        """
        Check for upcoming meetings within the specified time window.
        
        Args:
            hours_ahead: Number of hours to look ahead (default: 24)
        
        Returns:
            List of upcoming calendar events
        """
        # Mock data for MVP
        now = datetime.now()
        
        mock_events = [
            CalendarEvent(
                id="evt_1",
                title="Design Review: User Profile",
                start_time=now + timedelta(hours=2),
                end_time=now + timedelta(hours=3),
                attendees=["alice@company.com", "bob@company.com"],
                context_keywords=["profile", "settings", "ui"],
                description="Review new user profile designs"
            ),
            CalendarEvent(
                id="evt_2",
                title="Bug Bash: Login Errors",
                start_time=now + timedelta(hours=5),
                end_time=now + timedelta(hours=6),
                attendees=["qa@company.com", "dev@company.com"],
                context_keywords=["auth", "login", "500 error"],
                description="Investigate login 500 errors"
            )
        ]
        
        # Filter events within the time window
        cutoff_time = now + timedelta(hours=hours_ahead)
        upcoming = [
            event for event in mock_events
            if now <= event.start_time <= cutoff_time
        ]
        
        logger.info(f"Found {len(upcoming)} upcoming meetings in next {hours_ahead} hours")
        
        return upcoming
    
    def create_draft_session(self, event: CalendarEvent) -> DraftSession:
        """
        Create a draft session from a calendar event.
        
        Args:
            event: Calendar event to create session from
        
        Returns:
            Created draft session
        """
        # Determine suggested mode based on keywords
        suggested_mode = self._suggest_mode(event.context_keywords)
        
        # Create draft session
        session = DraftSession(
            session_id=str(uuid.uuid4()),
            event_id=event.id,
            title=event.title,
            attendees=event.attendees,
            context_keywords=event.context_keywords,
            status="waiting_for_upload",
            created_at=datetime.now(),
            suggested_mode=suggested_mode,
            metadata={
                "event_start": event.start_time.isoformat(),
                "event_end": event.end_time.isoformat(),
                "description": event.description
            }
        )
        
        # Store in memory (MVP - use database in production)
        self.draft_sessions[session.session_id] = session
        
        logger.info(f"Created draft session {session.session_id} for event {event.id}")
        
        return session
    
    def _suggest_mode(self, keywords: List[str]) -> str:
        """
        Suggest a documentation mode based on context keywords.
        
        Args:
            keywords: List of context keywords
        
        Returns:
            Suggested mode ID
        """
        keywords_lower = [k.lower() for k in keywords]
        
        # Bug-related keywords
        if any(word in keywords_lower for word in ["bug", "issue", "error", "triage", "fix"]):
            return "bug_report"
        
        # Feature-related keywords
        if any(word in keywords_lower for word in ["feature", "kickoff", "design", "spec", "prd"]):
            return "feature_kickoff"
        
        # API/Documentation keywords
        if any(word in keywords_lower for word in ["api", "documentation", "docs"]):
            return "general_doc"
        
        # Default
        return "general_doc"
    
    def get_draft_sessions(self, status: Optional[str] = None) -> List[DraftSession]:
        """
        Get all draft sessions, optionally filtered by status.
        
        Args:
            status: Optional status filter (waiting_for_upload, processing, completed)
        
        Returns:
            List of draft sessions
        """
        sessions = list(self.draft_sessions.values())
        
        if status:
            sessions = [s for s in sessions if s.status == status]
        
        # Sort by creation time (newest first)
        sessions.sort(key=lambda x: x.created_at, reverse=True)
        
        return sessions
    
    def get_session(self, session_id: str) -> Optional[DraftSession]:
        """
        Get a specific draft session by ID.
        
        Args:
            session_id: Session ID to retrieve
        
        Returns:
            Draft session or None if not found
        """
        return self.draft_sessions.get(session_id)
    
    def update_session_status(self, session_id: str, status: str, metadata: Optional[Dict] = None):
        """
        Update the status of a draft session.
        
        Args:
            session_id: Session ID to update
            status: New status
            metadata: Optional metadata to merge
        """
        session = self.draft_sessions.get(session_id)
        if session:
            session.status = status
            if metadata:
                session.metadata.update(metadata)
            logger.info(f"Updated session {session_id} status to {status}")
    
    def sync_calendar(self):
        """
        Sync with calendar and create draft sessions for upcoming meetings.
        
        This would be called periodically (e.g., every hour) to check for new meetings.
        """
        upcoming_events = self.check_upcoming_meetings()
        
        # Create draft sessions for events that don't have one yet
        existing_event_ids = {s.event_id for s in self.draft_sessions.values()}
        
        new_sessions = []
        for event in upcoming_events:
            if event.id not in existing_event_ids:
                session = self.create_draft_session(event)
                new_sessions.append(session)
        
        logger.info(f"Synced calendar: created {len(new_sessions)} new draft sessions")
        
        return new_sessions
    
    def check_notification_triggers(self):
        """
        Check all draft sessions for notification triggers.
        Called periodically by the scheduler.
        
        Pre-meeting: Trigger reminder 10 mins before start
        Post-meeting: Trigger upload nudge 5 mins after end
        """
        from app.services.notification_service import get_notification_service
        from datetime import datetime, timedelta
        
        notifier = get_notification_service()
        now = datetime.now()
        
        for session in self.draft_sessions.values():
            # Skip completed/failed sessions
            if session.status in ["completed", "failed"]:
                continue
            
            # Parse event times from metadata
            event_start_str = session.metadata.get("event_start")
            event_end_str = session.metadata.get("event_end")
            
            if not event_start_str or not event_end_str:
                continue
            
            try:
                event_start = datetime.fromisoformat(event_start_str)
                event_end = datetime.fromisoformat(event_end_str)
            except ValueError:
                continue
            
            # Get first attendee email for notification
            email = session.attendees[0] if session.attendees else "user@example.com"
            
            # Pre-Meeting Reminder: 10 minutes before start
            reminder_window_start = event_start - timedelta(minutes=15)
            reminder_window_end = event_start - timedelta(minutes=5)
            
            if reminder_window_start <= now <= reminder_window_end and not session.reminder_sent:
                notifier.send_reminder(email, session.title)
                session.reminder_sent = True
                logger.info(f"Triggered pre-meeting reminder for session {session.session_id}")
            
            # Post-Meeting Nudge: 5 minutes after end (for sessions still waiting)
            nudge_window_start = event_end + timedelta(minutes=3)
            nudge_window_end = event_end + timedelta(minutes=30)
            
            if nudge_window_start <= now <= nudge_window_end and session.status == "waiting_for_upload" and not session.nudge_sent:
                notifier.send_upload_nudge(email, session.title, session.session_id)
                session.nudge_sent = True
                logger.info(f"Triggered post-meeting nudge for session {session.session_id}")


# Singleton instance
_calendar_watcher: Optional[CalendarWatcher] = None
_scheduler_running: bool = False


def get_calendar_watcher() -> CalendarWatcher:
    """Get or create the CalendarWatcher singleton"""
    global _calendar_watcher
    if _calendar_watcher is None:
        _calendar_watcher = CalendarWatcher()
        # Auto-sync on initialization
        _calendar_watcher.sync_calendar()
    return _calendar_watcher


async def start_notification_scheduler():
    """
    Start the background notification scheduler.
    Runs every 60 seconds to check for notification triggers.
    """
    import asyncio
    global _scheduler_running
    
    if _scheduler_running:
        logger.info("Notification scheduler already running")
        return
    
    _scheduler_running = True
    logger.info("Starting notification scheduler (60s interval)")
    
    while _scheduler_running:
        try:
            calendar = get_calendar_watcher()
            calendar.check_notification_triggers()
        except Exception as e:
            logger.error(f"Scheduler error: {str(e)}")
        
        await asyncio.sleep(60)  # Check every minute


def stop_notification_scheduler():
    """Stop the background notification scheduler"""
    global _scheduler_running
    _scheduler_running = False
    logger.info("Notification scheduler stopped")

