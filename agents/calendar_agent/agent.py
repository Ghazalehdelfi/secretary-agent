# =============================================================================
# agents/calendar_agent/agent.py
# =============================================================================
# 🗓️ Purpose:
# This file defines the CalendarAgent, a specialized A2A agent that integrates
# with Google Calendar to manage scheduling, availability checking, and event
# creation. The agent uses Google's Agent Development Kit (ADK) with Gemini LLM
# to provide natural language interface for calendar operations.
#
# ✅ Features:
# - Check calendar availability for specific dates
# - Create calendar events with contact integration
# - Mock mode for testing without real calendar access
# - Timezone-aware scheduling (America/New_York)
# - Contact lookup via phonebook integration
# - Email session management for follow-ups
#
# 🔧 Dependencies:
# - Google Calendar API (googleapiclient)
# - Google ADK for LLM integration
# - Service account credentials for calendar access
# =============================================================================

import logging                             
from dotenv import load_dotenv             

# Load environment variables from .env file
load_dotenv()  

# -----------------------------------------------------------------------------
# 🧠 Google ADK / Gemini imports
# -----------------------------------------------------------------------------
from google.adk.agents.llm_agent import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.genai import types
from google.adk.tools.function_tool import FunctionTool

# -----------------------------------------------------------------------------
# 📅 Date and time handling
# -----------------------------------------------------------------------------
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# -----------------------------------------------------------------------------
# 🔐 Google Calendar API imports
# -----------------------------------------------------------------------------
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

# -----------------------------------------------------------------------------
# 🛠️ Project-specific imports
# -----------------------------------------------------------------------------
from utilities.discovery import DiscoveryClient
from agents.host_agent.agent_connect import AgentConnector
from utilities.email_session import Session

# Set up logging for this module
logger = logging.getLogger(__name__)


class CalendarAgent:
    """
    🗓️ CalendarAgent: A specialized A2A agent for Google Calendar management.
    
    This agent provides natural language interface to Google Calendar operations
    including availability checking, event creation, and scheduling management.
    It integrates with the phonebook for contact lookup and email sessions for
    follow-up communications.
    
    Attributes:
        is_mock (bool): If True, uses mock data instead of real calendar API
        agent_name (str): Identifier for this agent
        user (str): User name for the calendar owner
        user_id (str): Email address of the calendar owner
        phone_book: Contact lookup service
        session_db (Session): Email session management
        calendar_service: Google Calendar API service instance
        connectors (dict): Dictionary of agent connectors for A2A communication
    """

    # Supported content types for this agent
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self, is_mock: bool = False, user: str = None, user_email: str = None, phone_book = None):
        """
        Initialize the CalendarAgent with configuration and services.
        
        Args:
            is_mock (bool): Enable mock mode for testing (default: False)
            user (str): User name for calendar operations
            user_email (str): Email address for calendar access
            phone_book: Contact lookup service instance
            
        Raises:
            FileNotFoundError: If service account credentials are not found
            ValueError: If required environment variables are missing
        """
        self.is_mock = is_mock
        self.agent_name = "calendar_agent"
        self.user = user
        self.user_id = user_email
        self.phone_book = phone_book
        
        # Initialize email session management
        self.session_db = Session()
        
        # Build the LLM agent with calendar tools
        self.orchestrator = self._build_orchestrator()
        
        # Set up the ADK runner for agent execution
        self.runner = Runner(
            app_name=self.orchestrator.name,
            agent=self.orchestrator,
            artifact_service=InMemoryArtifactService(),       
            session_service=InMemorySessionService(),         
            memory_service=InMemoryMemoryService(),          
        )

        # Initialize agent discovery for A2A communication
        self.discovery = DiscoveryClient()
        self.connectors: dict[str, AgentConnector] = {}

        # Google Calendar API scopes
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        
        # Initialize Google Calendar service with credentials
        self.calendar_service = self._initialize_calendar_service(SCOPES)

    def _initialize_calendar_service(self, scopes: list) -> object:
        """
        Initialize Google Calendar API service with appropriate credentials.
        
        This method tries to load credentials from environment variables first,
        then falls back to a service account file. It supports both deployment
        scenarios (environment variables) and local development (file-based).
        
        Args:
            scopes (list): List of Google API scopes required
            
        Returns:
            object: Google Calendar API service instance
            
        Raises:
            FileNotFoundError: If no credentials are found
            ValueError: If credentials are invalid
        """
        # Try to get credentials from environment variable first (for deployment)
        service_creds_env = os.getenv('service-creds')
        
        if service_creds_env:
            # Parse JSON from environment variable
            import json
            try:
                service_account_info = json.loads(service_creds_env)
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info, scopes=scopes)
                logger.info("Loaded service account credentials from environment variable")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse service account JSON from environment: {e}")
                raise ValueError(f"Invalid service account JSON in environment: {e}")
        else:
            # Fall back to file-based credentials (for local development)
            SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), 'service-creds.json')
            if os.path.exists(SERVICE_ACCOUNT_FILE):
                credentials = service_account.Credentials.from_service_account_file(
                    SERVICE_ACCOUNT_FILE, scopes=scopes)
                logger.info("Loaded service account credentials from file")
            else:
                raise FileNotFoundError(
                    f"Service account file not found: {SERVICE_ACCOUNT_FILE}. "
                    "Please provide service-creds environment variable or service-creds.json file."
                )

        return build('calendar', 'v3', credentials=credentials)

    def _build_orchestrator(self) -> LlmAgent:
        """
        Build the LLM agent with calendar-specific tools and instructions.
        
        This method creates a Gemini-based agent with tools for:
        - Checking calendar availability
        - Creating calendar events
        - Mock operations for testing
        
        Returns:
            LlmAgent: Configured LLM agent with calendar tools
        """

        async def available_time(date: str = "") -> dict:
            """
            Check available time slots for a specific date.
            
            This function analyzes the calendar for a given date and returns
            available 30-minute slots during business hours (9 AM - 5 PM).
            It checks for conflicts with existing events and provides a
            structured response with availability information.
            
            Args:
                date (str): Date in YYYY-MM-DD format. If empty, defaults to tomorrow.
                
            Returns:
                dict: Availability information with status, date, and available slots
                    {
                        "status": "success" | "no_availability" | "error",
                        "date": "YYYY-MM-DD",
                        "availability": [{"time": "HH:MM", "duration": 30}, ...],
                        "message": "error message" (if status is "error")
                    }
            """
            if self.is_mock:
                return await available_time_mock(date)
            
            try:
                # Default to tomorrow if no date provided
                if not date:
                    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
                    date = tomorrow.strftime('%Y-%m-%d')

                # Parse the target date
                target_date = datetime.strptime(date, '%Y-%m-%d')

                # Define business hours (9 AM to 5 PM)
                start_time = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
                end_time = target_date.replace(hour=17, minute=0, second=0, microsecond=0)

                # Convert to timezone-aware datetime (America/New_York)
                start_time = start_time.astimezone(ZoneInfo("America/New_York"))
                end_time = end_time.astimezone(ZoneInfo("America/New_York"))

                # Fetch actual events for the day from Google Calendar
                events_result = self.calendar_service.events().list(
                    calendarId=self.user_id,
                    timeMin=start_time.isoformat(),
                    timeMax=end_time.isoformat(),
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()

                events = events_result.get('items', [])
                
                # Generate 30-minute slots during business hours
                available_slots = []
                current_time = start_time

                while current_time < end_time:
                    slot_end = current_time + timedelta(minutes=30)
                    
                    # Check if this slot conflicts with any existing events
                    is_available = True
                    for event in events:
                        # Parse event start and end times
                        event_start = datetime.fromisoformat(
                            event['start'].get('dateTime', event['start'].get('date')).replace('Z', '+00:00')
                        )
                        event_end = datetime.fromisoformat(
                            event['end'].get('dateTime', event['end'].get('date')).replace('Z', '+00:00')
                        )
                        
                        # Convert to same timezone for comparison
                        event_start = event_start.astimezone(ZoneInfo("America/New_York"))
                        event_end = event_end.astimezone(ZoneInfo("America/New_York"))
                        
                        # Check for time slot conflicts
                        if (current_time < event_end and slot_end > event_start):
                            is_available = False
                            break
                    
                    # Add slot if available
                    if is_available:
                        available_slots.append({
                            "time": current_time.strftime('%H:%M'),
                            "duration": 30
                        })
                    
                    current_time = slot_end

                return {
                    "status": "success" if available_slots else "no_availability",
                    "date": date,
                    "availability": available_slots
                }

            except Exception as e:
                logger.error(f"Error fetching calendar availability: {str(e)}")
                return {
                    "status": "error",
                    "message": str(e),
                    "availability": []
                }

        async def create_event(contact_name: str, date: str, time: str, duration: int, title: str, description: str = "", agenda: str = "") -> str:
            """
            Create a calendar event with contact integration and conflict checking.
            
            This function creates a new calendar event with the specified details.
            It includes contact lookup, conflict detection, and comprehensive
            event creation with optional description and agenda.
            
            Args:
                contact_name (str): Name of the contact to invite (looked up in phonebook)
                date (str): Date in YYYY-MM-DD format
                time (str): Time in HH:MM format
                duration (int): Duration in minutes
                title (str): Event title/summary
                description (str): Optional event description
                agenda (str): Meeting agenda or additional details
                
            Returns:
                str: Success message with event details or error message
            """
            # Look up contact in phonebook
            contact = self.phone_book.lookup(contact_name)
            if not contact:
                return f"Contact '{contact_name}' not found in phonebook"
            
            # Use mock mode if enabled
            if self.is_mock:
                return await create_event_mock(contact_name, date, time, duration, title, description, agenda)
            
            try:
                # Parse date and time
                event_date = datetime.strptime(date, '%Y-%m-%d')
                event_time = datetime.strptime(time, '%H:%M').time()
                
                # Create timezone-aware datetime
                start_datetime = datetime.combine(event_date, event_time)
                start_datetime = start_datetime.astimezone(ZoneInfo("America/New_York"))
                
                end_datetime = start_datetime + timedelta(minutes=duration)
                
                # Check for existing events at the same time
                events = self.calendar_service.events().list(
                    calendarId=self.user_id,
                    timeMin=start_datetime.isoformat(),
                    timeMax=end_datetime.isoformat(),
                    q=title,  # filter by summary/title
                    singleEvents=True
                ).execute().get('items', [])

                if events:
                    return f"Conflict detected: Event '{title}' already exists at {time} on {date}"

                # Build event description with agenda
                full_description = description
                if agenda:
                    if full_description:
                        full_description += "\n\n"
                    full_description += f"Agenda:\n{agenda}"
                
                event = {
                    'summary': title,
                    'description': full_description,
                    'start': {
                        'dateTime': start_datetime.isoformat(),
                        'timeZone': 'America/New_York',
                    },
                    'end': {
                        'dateTime': end_datetime.isoformat(),
                        'timeZone': 'America/New_York',
                    },
                }
                
                created_event = self.calendar_service.events().insert(
                    calendarId=self.user_id,
                    body=event
                ).execute()
                
                # Build success message
                success_msg = f"Event created successfully: {title} on {date} at {time} for {duration} minutes"
                if agenda:
                    success_msg += f"\nAgenda: {agenda}"
                session_id = self.session_db.get_session_by_email(contact.email)
                if session_id:
                    self.session_db.delete_session(session_id)
                logger.info(f"Successfully created event: {title} on {date} at {time}")

                return success_msg
                
            except Exception as e:
                logger.error(f"Error creating calendar event: {str(e)}")
                return f"Failed to create event: {str(e)}"

        async def available_time_mock(date: str = "") -> list[dict]:
            return {
                "status": "success",
                "date": date,
                "availability": [
                    {
                        "time": "10:00",
                        "duration": 30
                    },
                    {
                        "time": "10:30",
                        "duration": 30
                    },
                    {
                        "time": "11:00",
                        "duration": 30
                    },
                ]
            }

        async def create_event_mock(attendees: str, date: str, time: str, duration: int, title: str, description: str = "", agenda: str = "") -> str:
            success_msg = f"Event created: {title} on {date} at {time} for {duration} minutes"
            return success_msg


        system_instr = f"""
                You are a google calendar agent. You will be asked to either to check availability, fetch available times in a day or create an event in the calendar. 
                You are acting on behalf of {self.user}. So you dont need to look up the contact info on {self.user}.

                ### Responsibilities:
                - use available_time(date) tool to get the list of available times for a certain date, you can check if proposed time is in the available times
                 if the proposed time is not available, respond with no and propose a different time from the available times
                - if the user asks to create an event, use create_event(contact_name, date, time, duration, title, description, agenda) tool to create an event in the calendar
                
                ### Event Creation Guidelines:
                - Always ask for duration if not provided (default to 30 minutes if unspecified)
                - For meetings with multiple people, collect attendee email addresses
                - Ask for agenda/meeting purpose to create meaningful event descriptions
                - Duration should be in minutes (e.g., 30, 60, 90)
                
                ### tools:
                1) available_time(date) → returns a list of available times in {self.user}'s calendar on the specified date.
                2) create_event(contact_name, date, time, duration, title, description, agenda) → creates an event in {self.user}'s calendar with attendees and agenda.
                   - contact_name: name of the contact to create the event for
                   - date: YYYY-MM-DD format
                   - time: HH:MM format  
                   - duration: minutes (integer)
                   - title: event title
                   - description: optional description
                   - agenda: meeting agenda or details (optional)
            """

        tools = [
            FunctionTool(available_time),
            FunctionTool(create_event),
        ]

        return LlmAgent(
            model="gemini-2.5-flash",               # which Gemini model
            name=self.agent_name,                  # internal name
            description="Orchestrates calendar.",
            instruction=system_instr,                      # system prompt
            tools=tools,                                   # available tools
        )


    async def invoke(self, query: str, session_id: str) -> str:
        session = await self.runner.session_service.get_session(
            app_name=self.orchestrator.name,
            user_id=self.user_id,
            session_id=session_id,
        )

        if session is None:
            session = await self.runner.session_service.create_session(
                app_name=self.orchestrator.name,
                user_id=self.user_id,
                session_id=session_id,
                state={}
            )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)]
        )

        last_event = None
        async for event in self.runner.run_async(
            user_id=self.user_id,
            session_id=session.id,
            new_message=content
        ):
            last_event = event

        if not last_event or not last_event.content or not last_event.content.parts:
            return ""

        return "\n".join([p.text for p in last_event.content.parts if p.text])