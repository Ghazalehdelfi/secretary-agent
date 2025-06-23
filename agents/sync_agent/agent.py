import logging                             
from dotenv import load_dotenv             
from datetime import datetime, timezone
import uuid

load_dotenv()  

from google.adk.agents.llm_agent import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from datetime import datetime, timezone

from google.genai import types

from google.adk.tools.function_tool import FunctionTool

from utilities.discovery import DiscoveryClient
from agents.host_agent.agent_connect import AgentConnector
from utilities.phonebook import PhoneBook, Contact 

logger = logging.getLogger(__name__)

class SyncAgent:

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self, user: str, registry: list[str], role: str, session_db, email_service):
        """
        🏗️ Constructor: build the internal orchestrator LLM, runner, discovery client.
        """
        self.phone_book = PhoneBook()
        self.session_db = session_db
        self.email_service = email_service
        self.user = user
        self.agent_name = f"{user.lower().replace(' ', '_')}_sync_agent"
        self.role = role
        self.orchestrator = self._build_orchestrator(role)
        self.speed_dial = {}

        self.runner = Runner(
            app_name=self.orchestrator.name,
            agent=self.orchestrator,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

        self.discovery = DiscoveryClient(registry=registry)

        self.connectors: dict[str, AgentConnector] = {}

    def _lookup_contact(self, name: str) -> Contact | None:
        logger.info(f"lookup_contact: {name}")
        contact = self.phone_book.lookup(name)
        if contact:
            return contact
        return None

    async def send_email(self, contact: Contact, meeting_request: str, session_id: str) -> str:
        """Send an email meeting request to a contact without an agent"""
        # Send email
        success = self.email_service.send_meeting_request(
            contact=contact,
            meeting_request=meeting_request
        )
    
        if success:
            # Create agent session for tracking
            self.session_db.start_fresh_session(
                session_id=session_id,
                contact=contact,
                subject=f"Meeting Request from {self.user}",
                initial_message=meeting_request
            )
            return f"Email meeting request sent to {contact.first_name} {contact.last_name}, will continue in the background."
        else:
            return f"Failed to send email to {contact.first_name} {contact.last_name}"

    def _build_orchestrator(self, role: str) -> LlmAgent:

        async def list_agents() -> list[dict]:
            cards = await self.discovery.list_agent_cards()
            output = [card.model_dump(exclude_none=True) for card in cards]
            logger.info("found agents: " + str(output))
            return output

        async def call_contact(contact_name: str, message: str) -> str:
            if contact_name not in self.speed_dial:
                self.speed_dial[contact_name] = self._lookup_contact(contact_name)
            session_id = f"{self.user}_{uuid.uuid4()}"
            contact = self.speed_dial[contact_name]
            if contact:
                if contact.agent_url:
                    self.discovery.add_agent(contact.agent_url)
                    if contact.agent_name:
                        name = contact.agent_name
                    else:
                        name = f"{contact.first_name} {contact.last_name}"
                    return await call_agent_by_url(name, contact.agent_url, message, session_id)
                elif contact.email:
                    return await self.send_email(contact, message, session_id)
                else:
                    raise ValueError(f"Contact '{contact_name}' not found.")
            else:
                raise ValueError(f"Contact '{contact_name}' not found.")

        async def call_agent(agent_name: str, message: str) -> str:
            cards = await list_agents()
            matched = next(
                (c for c in cards
                if c["name"].lower() == agent_name.lower()
                or c.get("id", "").lower() == agent_name.lower()),
                None
            )

            if not matched:
                matched = next(
                    (c for c in cards if agent_name.lower() in c["name"].lower()),
                    None
                )

            if not matched:
                raise ValueError(f"Agent '{agent_name}' not found.")

            key = matched["name"]
            if key not in self.connectors:
                self.connectors[key] = AgentConnector(
                    name=matched["name"],
                    base_url=matched["url"]
                )
            connector = self.connectors[key]
            session_id = f"{self.user}_{uuid.uuid4()}"
            task = await connector.send_task(message, session_id=session_id, role=role)

            if task.history and task.history[-1].parts:
                return task.history[-1].parts[0].text
            return ""

        async def call_agent_by_url(agent_name: str, agent_url: str, message: str, session_id: str) -> str:
            connector = AgentConnector(
                name=agent_name,
                base_url=agent_url
            )
            task = await connector.send_task(message, session_id=session_id, role=role)
            if task.history and task.history[-1].parts:
                return task.history[-1].parts[0].text
            return ""
        
        base_system_instr = f"""
            You are a availability coordinator agent acting on behalf of {self.user}. Your job is to coordinate meetings between {self.user} and other people by negotiating availability.
            Today's date is {datetime.now(timezone.utc).strftime('%Y-%m-%d')} and the day of the week is {datetime.now(timezone.utc).strftime('%A')}.
            The name of the user you represent is {self.user}. If another agent asks who they are coordinating with, respond with "{self.user}".
        """

        initiator_system_instr = f"""
            You have access to the following tools:
            1) list_agents() → Returns metadata for all available agents.
            2) call_contact(contact_name, message) → Sends a message to a contact.
            3) call_agent(agent_name, message) → Sends a message to another agent.

            ### Responsibilities

            - ask user to provide the duration, title and agenda of the meeting
            - call the agent=`calendar_data_agent` to retrieve availability for {self.user}.
            - If no overlapping availability is found for the requested day, try the next day automatically (up to 5 days).
            - Use `call_contact(contact_name, message)` to coordinate the meeting with the other person.
            - when an agreement is reached, call the `calendar_data_agent` to create an event, provide the contact_name, duration, title and agenda and the agreed date and time in the calendar.

            ## ⛔️ Important Don'ts

            - ❌ Do not try to construct agent names like `mert_vural_calendar_agent`.
            - ❌ Do not contact a calendar agent for anyone other than {self.user}.
            """

        responder_system_instr = f"""
            You have access to the following tools:
            1) list_agents() → Returns metadata for all available agents.
            2) call_agent(agent_url, message) → Sends a message to another agent.

            ### Responsibilities
            - Call the `calendar_data_agent` with the relevant date to retrieve availability for {self.user}.
            - Respond with available times (from your user's calendar), and negotiate to reach a mutually available time.

            ## ⛔️ Important Don'ts

            - ❌ Do not try to construct agent names.
            - ❌ Do not contact a calendar agent for anyone other than {self.user}. 
            - ❌ Do not ask the `calendar_data_agent` to create an event. Only use it for retrieving availability. Ask the user to create an event.
        """

        system_instr = base_system_instr + initiator_system_instr if role == "initiator" else base_system_instr + responder_system_instr
        tools = [
            FunctionTool(call_agent),
            FunctionTool(list_agents),
        ]

        if role == "initiator":
            tools.append(FunctionTool(call_contact))

        return LlmAgent(
            model="gemini-2.5-flash",
            name=self.agent_name,
            description="Coordinates common times between user and target's schedule",
            instruction=system_instr,
            tools=tools,
        )


    async def invoke(self, query: str, session_id: str) -> str:        
        session = await self.runner.session_service.get_session(
            app_name=self.orchestrator.name,
            user_id=self.user,
            session_id=session_id,
        )

        if session is None:
            session = await self.runner.session_service.create_session(
                app_name=self.orchestrator.name,
                user_id=self.user,
                session_id=session_id,
                state={}
            )

        content = types.Content(
            role='user',
            parts=[types.Part.from_text(text=query)]
        )

        last_event = None
        async for event in self.runner.run_async(
            user_id=self.user,
            session_id=session.id,
            new_message=content
        ):
            last_event = event

        if not last_event or not last_event.content or not last_event.content.parts:
            return ""

        return "\n".join([p.text for p in last_event.content.parts if p.text])