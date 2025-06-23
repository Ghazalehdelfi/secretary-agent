import logging                       # logging is used to record warning/error/info messages
from typing import List             # List is a type hint for functions that return lists

import httpx                         # httpx is an async HTTP client library for sending requests
from models.agent import AgentCard   # AgentCard is a Pydantic model representing an agent's metadata

# Create a named logger for this module; __name__ is the module's name
logger = logging.getLogger(__name__)


class DiscoveryClient:
    """
    🔍 Discovers A2A agents by reading a registry file of URLs and querying
    each one's /.well-known/agent.json endpoint to retrieve an AgentCard.

    Attributes:
        registry_file (str): Path to the JSON file listing base URLs (strings).
        base_urls (List[str]): Loaded list of agent base URLs.
    """

    def __init__(self, registry: list[str] = []):
        """
        Initialize the DiscoveryClient.

        Args:
            registry_file (str, optional): Path to the registry JSON. If None,
                defaults to 'agent_registry.json' in this utilities folder.
        """
        self.base_urls = registry

    async def list_agent_cards(self) -> List[AgentCard]:
        """
        Asynchronously fetch the discovery endpoint from each registered URL
        and parse the returned JSON into AgentCard objects.

        Returns:
            List[AgentCard]: Successfully retrieved agent cards.
        """
        cards: List[AgentCard] = []  # Prepare an empty list to collect AgentCard instances

        # Create a new AsyncClient and ensure it's closed when done
        async with httpx.AsyncClient() as client:
            # Iterate through each base URL in the registry
            for base in self.base_urls:
                # Normalize URL (remove trailing slash) and append the discovery path
                url = base.rstrip("/") + "/.well-known/agent.json"
                try:
                    # Send a GET request to the discovery endpoint with a timeout
                    response = await client.get(url, timeout=5.0)
                    # Raise an exception if the response status is 4xx or 5xx
                    response.raise_for_status()
                    # Convert the JSON response into an AgentCard Pydantic model
                    card = AgentCard.model_validate(response.json())
                    # Add the valid AgentCard to our list
                    cards.append(card)
                except Exception as e:
                    # If anything goes wrong, log which URL failed and why
                    logger.warning(f"Failed to discover agent at {url}: {e}")
        # Return the list of successfully fetched AgentCards
        return cards
    def add_agent(self, agent_url: str):
        self.base_urls.append(agent_url)