import logging                        
import click                          

from server.server import A2AServer    
from models.agent import (
    AgentCard,                        
    AgentCapabilities,                
    AgentSkill                       
)
from agents.sync_agent.agent import SyncAgent
from agents.sync_agent.task_manager import AgentTaskManager
from utilities.email_session import Session
from utilities.email_service import EmailService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()                     
@click.option(
    "--host",                        
    default="localhost",             
    help="Host to bind sync_agent server to"  
)
@click.option(
    "--port",
    default=10001,
    help="Port for sync_agent server"
)
@click.option(
    "--user",
    default="Alex Farner",
    help="User's full name"
)
@click.option(
    "--registry",
    default="",
    help=(
        "array of child-agent URLs"
    )
)
def main(host: str, port: int, user: str, registry: str):
    """
    Launches the sync_agent A2A server.

    Args:
        host (str): Hostname or IP to bind to (default: localhost)
        port (int): TCP port to listen on (default: 10001)
        user (str): User's full name (default: Alex Farner)
    """
    logger.info(f"\n🚀 Starting sync_agent on http://{host}:{port}/\n")

    capabilities = AgentCapabilities(streaming=False)

    skill = AgentSkill(
        id="sync_schedule",                                        
        name="meeting_sync_agent",                              
        description="Finds common times for user and another target agent to schedule a meeting - should be used as first step to schedule a meeting",
        tags=["sync", "schedule", "time"],                
        examples=[f"{user} want to schedule a meeting with another person, will you help me?", "Schedule a meeting with John Doe tomorrow"]   
    )

    agent_card = AgentCard(
        name=f"{user.lower().replace(' ', '_')}_meeting_coordination_agent",
        description=f"Coordinates meeting times between {user} and others by negotiating availability using their calendars. Use this agent first if you want to schedule a meeting *with another person*.",
        url=f"https://a2a-sync-agent-695627813996.us-central1.run.app/",
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=capabilities,
        skills=[skill]
    )

    registry = registry.split("+")
    session_db = Session()
    email_service = EmailService(user, session_db)

    initiator_agent = SyncAgent(user=user, registry=registry, role="initiator", session_db=session_db, email_service=email_service)
    responder_agent = SyncAgent(user=user, registry=registry, role="responder", session_db=session_db, email_service=email_service)

    task_manager = AgentTaskManager(initiator_agent=initiator_agent, responder_agent=responder_agent, email_service=email_service, session_db=session_db)

    server = A2AServer(
        host=host,
        port=port,
        agent_card=agent_card,
        task_manager=task_manager
    )
    server.start()  

if __name__ == "__main__":
    main()