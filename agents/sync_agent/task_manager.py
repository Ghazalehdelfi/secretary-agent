import asyncio
import threading
import logging
import time

from models.request import (
    SendTaskRequest, SendTaskResponse,    # For sending tasks to the agent
)

from models.task import (
    TaskStatus, TaskState, Message, TextPart          # Task metadata and history objects
)

from server.task_manager import InMemoryTaskManager


logger = logging.getLogger(__name__)

class AgentTaskManager(InMemoryTaskManager):
    def __init__(self, initiator_agent, responder_agent, email_service, session_db):
        super().__init__()
        self.initiator_agent = initiator_agent
        self.responder_agent = responder_agent
        self.user = initiator_agent.user
        self.email_service = email_service
        self.session_db = session_db
                # Start email monitoring in background
        self.email_monitor_thread = threading.Thread(target=self._monitor_emails, daemon=True)
        self.email_monitor_thread.start()

    def _monitor_emails(self):
        """Background thread to monitor email replies"""
        while True:
            try:
                replies = self.email_service.check_for_replies()
                for reply in replies:
                    # Forward reply to the agent session
                    asyncio.run(self._forward_email_reply(reply))
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in email monitoring: {e}")
                time.sleep(60)  # Wait longer on error

    async def _forward_email_reply(self, reply: dict):
        """Forward email reply to the appropriate agent session"""
        try:
            session_id = reply['session_id']
            contact_name = reply['contact_name']
            content = reply['content']
            # Create a message to forward to the agent
            message = f"Email reply from {contact_name}:\n\n{content}"
            
            # Create or update agent session in database
            session = self.session_db.get_session_by_id(session_id)
            
            if session:
                agent_response = await self.initiator_agent.invoke(message, session_id)     
            
            logger.info(f"Forwarded email reply to session {session_id}")
            self.email_service.send_follow_up(session_id, agent_response)
        
        except Exception as e:
            logger.error(f"Error forwarding email reply: {e}")

    def _get_user_text(self, request: SendTaskRequest) -> str:
        return request.params.message.parts[0].text

    def _get_role(self, request: SendTaskRequest) -> str:
        return request.params.metadata["agent_role"] if request.params.metadata["agent_role"] else "user"

    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        logger.info(f"sync agent task manager received task {request.params.id}")

        task = await self.upsert_task(request.params)

        user_text = self._get_user_text(request)

        role = self._get_role(request)

        if role in ["responder", "user"]:
            agent_response = await self.initiator_agent.invoke(user_text, request.params.sessionId) 
        else:
            agent_response = await self.responder_agent.invoke(user_text, request.params.sessionId)

        reply_message = Message(
            role='agent',
            parts=[TextPart(text=agent_response)]
        )

        async with self.lock:
            task.status = TaskStatus(state=TaskState.COMPLETED)
            task.history.append(reply_message)

        return SendTaskResponse(id=request.id, result=task)