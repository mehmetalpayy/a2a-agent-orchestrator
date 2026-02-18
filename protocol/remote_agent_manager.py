import json

import httpx
from a2a.client import A2ACardResolver
from a2a.types import AgentCard

from utils.logger import Logger

from .remote_agent_connection import RemoteAgentConnections


class RemoteAgentManager:
    """Manages the discovery and connections for all remote agents."""

    def __init__(self, agent_addresses: list[str]) -> None:
        """
        Initializes the manager with a list of remote agent URLs.
        """
        self.agent_addresses = agent_addresses
        self.connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}

    async def initialize(self) -> None:
        """
        Asynchronously connects to all remote agents, resolves their cards,
        and prepares connection objects.
        """
        Logger.info(
            f"RemoteAgentManager: Initializing connections to {self.agent_addresses}"
        )
        async with httpx.AsyncClient(timeout=30) as client:
            for address in self.agent_addresses:
                try:
                    card_resolver = A2ACardResolver(client, address)
                    card = await card_resolver.get_agent_card()
                    Logger.info(f"Successfully resolved card for agent at {address}")

                    self.cards[card.name] = card
                    self.connections[card.name] = RemoteAgentConnections(
                        agent_card=card, agent_url=address
                    )
                except Exception as e:
                    Logger.info(
                        f"Failed to initialize connection to agent at {address}: {e}"
                    )

    def get_connection(self, agent_name: str) -> RemoteAgentConnections:
        """
        Retrieves the active connection for a given agent name.
        """
        connection = self.connections.get(agent_name)
        if not connection:
            raise ValueError(f"Agent connection for '{agent_name}' not found.")
        return connection

    def get_agent_details(self) -> list[dict]:
        """
        Returns a list of dictionaries containing details for each available agent.
        """
        if not self.cards:
            return []

        return [
            {"name": card.name, "description": card.description}
            for card in self.cards.values()
        ]

    def get_formatted_remote_agent_details_str(self) -> str | None:
        """
        Returns a comma-separated string of remote agents and their descriptions.
        Example: "Agent1 (Desc1), Agent2 (Desc2)"
        """
        if not self.cards:
            return None

        return ", ".join(
            f"{card.name} ({card.description})" for card in self.cards.values()
        )

    def get_agents_prompt_string(self) -> str:
        """
        Generates a formatted string of all available agents for the system prompt.
        """
        if not self.cards:
            return "No remote agents available."

        agent_info_list = [json.dumps(detail) for detail in self.get_agent_details()]
        return "\n".join(agent_info_list)
