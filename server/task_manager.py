# =============================================================================
# server/task_manager.py
# =============================================================================
# 🎯 Purpose:
# This file defines how tasks are managed in an Agent-to-Agent (A2A) protocol.
#
# ✅ Includes:
# - A base abstract class `TaskManager` that outlines required methods
# - A simple `InMemoryTaskManager` that keeps tasks temporarily in memory
#
# ❌ Does not include:
# - Cancel task functionality
# - Push notifications or real-time updates
# - Persistent storage (like a database)
# =============================================================================


# -----------------------------------------------------------------------------
# 📚 Standard Python Imports
# -----------------------------------------------------------------------------

from abc import ABC, abstractmethod        # Lets us define abstract base classes (like an interface)
from typing import Dict                    # Dict is a dictionary type for storing key-value pairs
import asyncio                             # Used here for locks to safely handle concurrency (async operations)
import logging                             # Used for logging

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 📦 Project Imports: Request and Task Models
# -----------------------------------------------------------------------------

from models.request import (
    SendTaskRequest, SendTaskResponse,    # For sending tasks to the agent
    GetTaskRequest, GetTaskResponse       # For querying task info from the agent
)

from models.task import (
    Task, TaskSendParams, TaskQueryParams,  # Task and input models
    TaskStatus, TaskState, Message, TextPart          # Task metadata and history objects
)

# -----------------------------------------------------------------------------
# 🧩 TaskManager (Abstract Base Class)
# -----------------------------------------------------------------------------

class TaskManager(ABC):
    """
    🔧 This is a base interface class.

    All Task Managers must implement these two async methods:
    - on_send_task(): to receive and process new tasks
    - on_get_task(): to fetch the current status or conversation history of a task

    This makes sure all implementations follow a consistent structure.
    """

    @abstractmethod
    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        """📥 This method will handle new incoming tasks."""
        pass

    @abstractmethod
    async def on_get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        """📤 This method will return task details by task ID."""
        pass


# -----------------------------------------------------------------------------
# 🧠 InMemoryTaskManager
# -----------------------------------------------------------------------------

class InMemoryTaskManager(TaskManager):
    """
    🧠 A simple, temporary task manager that stores everything in memory (RAM).

    Great for:
    - Demos
    - Local development
    - Single-session interactions

    ❗ Not for production: Data is lost when the app stops or restarts.
    """

    def __init__(self):
        self.tasks: Dict[str, Task] = {}   # 🗃️ Dictionary where key = task ID, value = Task object
        self.lock = asyncio.Lock()         # 🔐 Async lock to ensure two requests don't modify data at the same time

    # -------------------------------------------------------------------------
    # 💾 upsert_task: Create or update a task in memory
    # -------------------------------------------------------------------------
    async def upsert_task(self, params: TaskSendParams) -> Task:
        """
        Create a new task if it doesn't exist, or update the history if it does.

        Args:
            params: TaskSendParams – includes task ID, session ID, and message

        Returns:
            Task – the newly created or updated task
        """
        async with self.lock:
            task = self.tasks.get(params.id)  # Try to find an existing task with this ID

            if task is None:
                # If task doesn't exist, create it with a "submitted" status
                task = Task(
                    id=params.id,
                    status=TaskStatus(state=TaskState.SUBMITTED),
                    history=[params.message]
                )
                self.tasks[params.id] = task
            else:
                # If task exists, add the new message to its history
                task.history.append(params.message)

            return task

    # -------------------------------------------------------------------------
    # 🚫 on_send_task: Must be implemented by any subclass
    # -------------------------------------------------------------------------
    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        """
        This method is intentionally not implemented here.
        Subclasses like `AgentTaskManager` should override it.

        Raises:
            NotImplementedError: if someone tries to use it directly
        """
        raise NotImplementedError("on_send_task() must be implemented in subclass")

    # -------------------------------------------------------------------------
    # 📥 on_get_task: Fetch a task by its ID
    # -------------------------------------------------------------------------
    async def on_get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        """
        Look up a task using its ID, and optionally return only recent messages.

        Args:
            request: A GetTaskRequest with an ID and optional history length

        Returns:
            GetTaskResponse – contains the task if found, or an error message
        """
        async with self.lock:
            query: TaskQueryParams = request.params
            task = self.tasks.get(query.id)

            if not task:
                # If task not found, return a structured error
                return GetTaskResponse(id=request.id, error={"message": "Task not found"})

            # Optional: Trim the history to only show the last N messages
            task_copy = task.model_copy()  # Make a copy so we don't affect the original
            if query.historyLength is not None:
                task_copy.history = task_copy.history[-query.historyLength:]  # Get last N messages
            else:
                task_copy.history = task_copy.history

            return GetTaskResponse(id=request.id, result=task_copy)



class AgentTaskManager(InMemoryTaskManager):
    def __init__(self, agent):
        super().__init__()
        self.agent = agent

    def _get_user_text(self, request: SendTaskRequest) -> str:
        return request.params.message.parts[0].text

    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        logger.info(f"{self.agent.agent_name} task manager received task {request.params.id}")

        task = await self.upsert_task(request.params)

        user_text = self._get_user_text(request)

        agent_response = await self.agent.invoke(
            user_text,
            request.params.sessionId
        )

        reply_message = Message(
            role="agent",
            parts=[TextPart(text=agent_response)]
        )

        async with self.lock:
            task.status = TaskStatus(state=TaskState.COMPLETED)
            task.history.append(reply_message)

        return SendTaskResponse(id=request.id, result=task)