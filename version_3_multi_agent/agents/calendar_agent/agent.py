import logging                             
from dotenv import load_dotenv             

load_dotenv()  

from google.adk.agents.llm_agent import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

from google.genai import types

from google.adk.tools.function_tool import FunctionTool

from utilities.discovery import DiscoveryClient
from agents.host_agent.agent_connect import AgentConnector
from utilities.email_session import Session

logger = logging.getLogger(__name__)

class CalendarAgent:

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self, is_mock:bool=False, user:str=None, user_email:str=None, phone_book=None):
        self.is_mock = is_mock
        self.agent_name = "calendar_agent"
        self.user = user
        self.user_id = user_email
        self.orchestrator = self._build_orchestrator()
        self.phone_book = phone_book
        self.session_db = Session()
        self.runner = Runner(
            app_name=self.orchestrator.name,
            agent=self.orchestrator,
            artifact_service=InMemoryArtifactService(),       
            session_service=InMemorySessionService(),         
            memory_service=InMemoryMemoryService(),          
        )

        self.discovery = DiscoveryClient()

        self.connectors: dict[str, AgentConnector] = {}

        SCOPES = ['https://www.googleapis.com/auth/calendar']
        
        # Try to get credentials from environment variable first, then fall back to file
        service_creds_env = os.getenv('service-creds')
        
        if service_creds_env:
            # Parse JSON from environment variable
            import json
            try:
                service_account_info = json.loads(service_creds_env)
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info, scopes=SCOPES)
                logger.info("Loaded service account credentials from environment variable")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse service account JSON from environment: {e}")
                raise
        else:
            # Fall back to file-based credentials
            SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), 'service-creds.json')
            if os.path.exists(SERVICE_ACCOUNT_FILE):
                credentials = service_account.Credentials.from_service_account_file(
                    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
                logger.info("Loaded service account credentials from file")
            else:
                raise FileNotFoundError(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")

        self.calendar_service = build('calendar', 'v3', credentials=credentials)

    def _build_orchestrator(self) -> LlmAgent:

        async def available_time(date: str = "") -> dict:
            if self.is_mock:
                return await available_time_mock(date)
            
            try:
                if not date:
                    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
                    date = tomorrow.strftime('%Y-%m-%d')

                target_date = datetime.strptime(date, '%Y-%m-%d')

                start_time = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
                end_time = target_date.replace(hour=17, minute=0, second=0, microsecond=0)

                # Convert to timezone-aware datetime
                start_time = start_time.astimezone(ZoneInfo("America/New_York"))
                end_time = end_time.astimezone(ZoneInfo("America/New_York"))

                # Fetch actual events for the day
                events_result = self.calendar_service.events().list(
                    calendarId=self.user_id,
                    timeMin=start_time.isoformat(),
                    timeMax=end_time.isoformat(),
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()

                events = events_result.get('items', [])
                
                # Define business hours (9 AM to 5 PM)
                business_start = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
                business_end = target_date.replace(hour=17, minute=0, second=0, microsecond=0)
                business_start = business_start.astimezone(ZoneInfo("America/New_York"))
                business_end = business_end.astimezone(ZoneInfo("America/New_York"))

                # Generate 30-minute slots during business hours
                available_slots = []
                current_time = business_start

                while current_time < business_end:
                    slot_end = current_time + timedelta(minutes=30)
                    
                    # Check if this slot conflicts with any existing events
                    is_available = True
                    for event in events:
                        event_start = datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date')).replace('Z', '+00:00'))
                        event_end = datetime.fromisoformat(event['end'].get('dateTime', event['end'].get('date')).replace('Z', '+00:00'))
                        
                        # Convert to same timezone for comparison
                        event_start = event_start.astimezone(ZoneInfo("America/New_York"))
                        event_end = event_end.astimezone(ZoneInfo("America/New_York"))
                        
                        if (current_time < event_end and slot_end > event_start):
                            is_available = False
                            break
                    
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
            Creates an event in the calendar with enhanced features.
            
            Args:
                date (str): Date in YYYY-MM-DD format
                time (str): Time in HH:MM format
                duration (int): Duration in minutes
                title (str): Event title
                description (str): Optional event description
                attendees (str): Comma-separated list of attendee email addresses
                agenda (str): Meeting agenda or additional details
            
            Returns:
                str: Success message with event details or error message
            """
            contact = self.phone_book.lookup(contact_name)
            if not contact:
                return f"Contact '{contact_name}' not found"
            
            if self.is_mock:
                return await create_event_mock(contact_name, date, time, duration, title, description, agenda)
            
            try:
                event_date = datetime.strptime(date, '%Y-%m-%d')
                event_time = datetime.strptime(time, '%H:%M').time()
                
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
                    return f"Event '{title}' already exists at {time} on {date}"
                
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