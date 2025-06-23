# =============================================================================
# agents/host_agent/orchestrator.py
# =============================================================================
# 🎯 Purpose:
# Defines the OrchestratorAgent that uses a Gemini-based LLM to interpret user
# queries and delegate them to any child A2A agent discovered at startup.
# Also defines OrchestratorTaskManager to expose this logic via JSON-RPC.
# =============================================================================

import os                           # Standard library for interacting with the operating system
import uuid                         # For generating unique identifiers (e.g., session IDs)
import logging                      # Standard library for configurable logging
from dotenv import load_dotenv      # Utility to load environment variables from a .env file

# Load the .env file so that environment variables like GOOGLE_API_KEY
# are available to the ADK client when creating LLMs
load_dotenv()

# -----------------------------------------------------------------------------
# Google ADK / Gemini imports
# -----------------------------------------------------------------------------
from google.adk.agents.llm_agent import LlmAgent
# LlmAgent: core class to define a Gemini-powered AI agent

from google.adk.sessions import InMemorySessionService
# InMemorySessionService: stores session state in memory (for simple demos)

from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
# InMemoryMemoryService: optional conversation memory stored in RAM

from google.adk.artifacts import InMemoryArtifactService
# InMemoryArtifactService: handles file/blob artifacts (unused here)

from google.adk.runners import Runner
# Runner: orchestrates agent, sessions, memory, and tool invocation

from google.adk.agents.readonly_context import ReadonlyContext
# ReadonlyContext: passed to system prompt function to read context

from google.adk.tools.tool_context import ToolContext
# ToolContext: passed to tool functions for state and actions

from google.genai import types  
from google.adk.tools.function_tool import FunctionTool
# types.Content & types.Part: used to wrap user messages for the LLM

# -----------------------------------------------------------------------------
# A2A server-side infrastructure
# -----------------------------------------------------------------------------
from server.task_manager import InMemoryTaskManager
# InMemoryTaskManager: base class providing in-memory task storage and locking

from models.request import SendTaskRequest, SendTaskResponse
# Data models for incoming task requests and outgoing responses

from models.task import Message, TaskStatus, TaskState, TextPart
# Message: encapsulates role+parts; TaskStatus/State: status enums; TextPart: text payload

# -----------------------------------------------------------------------------
# Connector to child A2A agents
# -----------------------------------------------------------------------------
from agents.host_agent.agent_connect import AgentConnector
# AgentConnector: lightweight wrapper around A2AClient to call other agents

from models.agent import AgentCard
# AgentCard: metadata structure for agent discovery results

# Set up module-level logger for debug/info messages
logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    🤖 Uses a Gemini LLM to route incoming user queries,
    calling out to any discovered child A2A agents via tools.
    """

    # Define supported MIME types for input/output
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self, agent_cards: list[AgentCard]):
        # Build one AgentConnector per discovered AgentCard
        # agent_cards is a list of AgentCard objects returned by discovery
        self.connectors = {
            card.name: AgentConnector(card.name, card.url)
            for card in agent_cards
        }

        # Build the internal LLM agent with our custom tools and instructions
        self._agent = self._build_agent()

        # Static user ID for session tracking across calls
        self._user_id = "orchestrator_user"

        # Runner wires up sessions, memory, artifacts, and handles agent.run()
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    def _build_agent(self) -> LlmAgent:
        """
        Construct the Gemini-based LlmAgent with:
        - Model name
        - Agent name/description
        - System instruction callback
        - Available tool functions
        """
        def list_agents() -> list[str]:
            return list(self.connectors.keys())
        
        async def delegate_task(agent_name: str, message: str, tool_context: ToolContext) -> str:
            if agent_name not in self.connectors:
                raise ValueError(f"Unknown agent: {agent_name}")
            connector = self.connectors[agent_name]

            # Ensure session_id persists across tool calls via tool_context.state
            state = tool_context.state
            if "session_id" not in state:
                state["session_id"] = str(uuid.uuid4())
            session_id = state["session_id"]

            # Delegate task asynchronously and await Task result
            child_task = await connector.send_task(message, session_id)

            # Extract text from the last history entry if available
            if child_task.history and len(child_task.history) > 1:
                return child_task.history[-1].parts[0].text
            return ""
        
        system_instr = f"""
            You are an orchestrator agent. You will be asked to delegate a task to a child agent.
            You have two tools:
            1) list_agents() -> list available child agents
            2) delegate_task(agent_name, message) -> call that agent
        """

        return LlmAgent(
            model="gemini-2.5-flash",    # Specify Gemini model version
            name="orchestrator_agent",          # Human identifier for this agent
            description="Delegates user queries to child A2A agents based on intent.",
            instruction=system_instr,  # Function providing system prompt text
            tools=[
                FunctionTool(list_agents),               # Tool 1: list available child agents
                FunctionTool(delegate_task)             # Tool 2: call a child agent
            ],
        )

    async def invoke(self, query: str, session_id: str) -> str:
        """
        Main entry: receives a user query + session_id,
        sets up or retrieves a session, wraps the query for the LLM,
        runs the Runner (with tools enabled), and returns the final text.
        Note - function updated 28 May 2025
        Summary of changes:
        1. Agent's invoke method is made async
        2. All async calls (get_session, create_session, run_async) 
            are awaited inside invoke method
        3. task manager's on_send_task updated to await the invoke call

        Reason - get_session and create_session are async in the 
        "Current" Google ADK version and were synchronous earlier 
        when this lecture was recorded. This is due to a recent change 
        in the Google ADK code 
        https://github.com/google/adk-python/commit/1804ca39a678433293158ec066d44c30eeb8e23b

        """
        # Attempt to reuse an existing session
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id
        )
        # Create new if not found
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                session_id=session_id,
                state={}
            )

        # Wrap the user query in a types.Content message
        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)]
        )

        # 🚀 Run the agent using the Runner and collect the last event
        last_event = None
        async for event in self._runner.run_async(
            user_id=self._user_id,
            session_id=session.id,
            new_message=content
        ):
            last_event = event

        # 🧹 Fallback: return empty string if something went wrong
        if not last_event or not last_event.content or not last_event.content.parts:
            return ""

        # 📤 Extract and join all text responses into one string
        return "\n".join([p.text for p in last_event.content.parts if p.text])


class OrchestratorTaskManager(InMemoryTaskManager):
    """
    🪄 OrchestratorTaskManager: A2A task manager for the orchestrator agent.
    
    This class extends InMemoryTaskManager to provide A2A JSON-RPC protocol
    support for the OrchestratorAgent. It handles incoming task requests,
    delegates them to the orchestrator agent for processing, and manages
    the task lifecycle including storage and response formatting.
    
    The task manager integrates the OrchestratorAgent's LLM-based routing
    logic with the A2A protocol, enabling the orchestrator to receive
    requests via JSON-RPC and delegate them to appropriate child agents.
    
    Attributes:
        agent (OrchestratorAgent): The orchestrator agent instance
    """
    
    def __init__(self, agent: OrchestratorAgent):
        """
        Initialize the OrchestratorTaskManager with an orchestrator agent.
        
        Args:
            agent (OrchestratorAgent): The orchestrator agent to delegate tasks to
        """
        super().__init__()       # Initialize base in-memory storage
        self.agent = agent       # Store our orchestrator logic

    def _get_user_text(self, request: SendTaskRequest) -> str:
        """
        Extract the user's raw input text from the A2A request object.
        
        This helper method extracts the text content from the first part
        of the user's message in the request.
        
        Args:
            request (SendTaskRequest): The incoming A2A task request
            
        Returns:
            str: The user's input text
            
        Raises:
            IndexError: If the message has no parts
        """
        return request.params.message.parts[0].text

    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        """
        Handle incoming A2A task requests by delegating to the orchestrator agent.
        
        This method is called by the A2A server when a new task arrives. It:
        1. Stores the incoming user message in the task history
        2. Invokes the OrchestratorAgent to process the request and route to child agents
        3. Appends the orchestrator's response to the task history
        4. Marks the task as completed
        5. Returns a structured SendTaskResponse with the full task information
        
        The orchestrator agent uses its LLM to determine which child agent
        should handle the request and delegates accordingly.
        
        Args:
            request (SendTaskRequest): The incoming A2A task request containing
                the user's message and session information
                
        Returns:
            SendTaskResponse: Response containing the completed task with
                both user input and agent response in the history
                
        Example:
            The orchestrator might receive a request like "What time is it?"
            and delegate it to a time agent, then return the time agent's
            response as part of the task history.
        """
        logger.info(f"OrchestratorTaskManager received task {request.params.id}")

        # Step 1: Save the initial user message to task history
        task = await self.upsert_task(request.params)

        # Step 2: Extract user text and run orchestration logic
        user_text = self._get_user_text(request)
        response_text = await self.agent.invoke(user_text, request.params.sessionId)

        # Step 3: Wrap the LLM output into a Message and add to history
        reply = Message(role="agent", parts=[TextPart(text=response_text)])
        async with self.lock:
            task.status = TaskStatus(state=TaskState.COMPLETED)
            task.history.append(reply)

        # Step 4: Return structured response with complete task information
        return SendTaskResponse(id=request.id, result=task)
