import logging                        
import click                          

from server.server import A2AServer    
from models.agent import (
    AgentCard,                        
    AgentCapabilities,                
    AgentSkill                       
)
from server.task_manager import AgentTaskManager
from agents.calendar_agent.agent import CalendarAgent
from utilities.phonebook import PhoneBook

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()                     
@click.option(
    "--host",                        
    default="localhost",             
    help="Host to bind calendar_agent server to"  
)
@click.option(
    "--port",
    default=10001,
    help="Port for calendar_agent server"
)
@click.option(
    "--is_mock",
    default=False,
    help="Whether to use the mock calendar agent"
)
@click.option(
    "--user",
    default="John Doe",
    help="User name for the calendar agent"
)
@click.option(
    "--user_email",
    default="John.Doe@example.com",
    help="User email for the calendar agent"
)
def main(host: str, port: int, is_mock: bool, user: str, user_email: str):
    logger.info(f"\n🚀 Starting calendar_agent on http://{host}:{port}/\n")

    capabilities = AgentCapabilities(streaming=False)

    skill = AgentSkill(
        id="greet",                                        
        name="google_calendar_tool",                              
        description="Finds available time for a meeting between you and another agent",
        tags=["availablity", "time", "event", "calendar"],                
        examples=["What are my available times for tomorrow?", "What are my available times for the next week?", "create an event for thursday at 10am for 30 minutes"]   
    )

    agent_card = AgentCard(
        name="calendar_data_agent",
        description=f"Reads from and writes to {user}'s Google Calendar. Use only when you need to know what times {user} is available or to create an event in {user}'s calendar",
        url=f"https://a2a-calendar-agent-695627813996.us-central1.run.app/",
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=capabilities,
        skills=[skill]
    )
    phone_book = PhoneBook()
    google_calendar_agent = CalendarAgent(is_mock=is_mock, user=user, user_email=user_email, phone_book=phone_book)
    task_manager = AgentTaskManager(agent=google_calendar_agent)

    server = A2AServer(
        host=host,
        port=port,
        agent_card=agent_card,
        task_manager=task_manager
    )
    server.start()  
if __name__ == "__main__":
    main()