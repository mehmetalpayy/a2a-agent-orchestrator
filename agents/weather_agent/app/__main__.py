"""Entrypoint for running the Weather Agent as an A2A service."""

import sys

import httpx
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from env import secrets
from utils.logger import Logger

from .agent import WeatherAgent
from .agent_executor import WeatherAgentExecutor


def main() -> None:
    """Configure and run the Weather Agent A2A HTTP server."""
    host = secrets.AGENT_BIND_HOST
    port = secrets.PORT
    public_base_url = secrets.AGENT_PUBLIC_BASE_URL or f"http://{host}:{port}"
    public_base_url = public_base_url.rstrip("/") + "/"

    try:
        # Basic skill available to everyone
        skill = AgentSkill(
            id="get_weather",
            name="Get current weather",
            description="Returns current weather for a given location.",
            tags=["weather"],
            examples=["weather in London", "weather in Istanbul,TR"],
        )

        # Extended skill for authenticated users
        extended_skill = AgentSkill(
            id="get_detailed_weather",
            name="Get detailed weather forecast",
            description="Returns a detailed weather forecast, only for authenticated users.",
            tags=["weather", "forecast", "detailed", "extended"],
            examples=[
                "detailed forecast for Paris",
                "give me a detailed weather report",
            ],
        )

        # Public-facing agent card
        public_agent_card = AgentCard(
            name="Weather Agent",
            description="Returns current weather information for locations.",
            url=public_base_url,
            version="1.0.0",
            default_input_modes=WeatherAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=WeatherAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=AgentCapabilities(streaming=False, push_notifications=True),
            skills=[skill],  # Only the basic skill for the public card
            supports_authenticated_extended_card=True,
        )

        # Authenticated extended agent card
        specific_extended_agent_card = public_agent_card.model_copy(
            update={
                "name": "Weather Agent - Extended Edition",
                "description": "The full-featured weather agent for authenticated users.",
                "version": "1.0.1",
                "skills": [
                    skill,
                    extended_skill,
                ],  # Both skills for the extended card
            }
        )
        specific_extended_agent_card.url = public_base_url

        httpx_client = httpx.AsyncClient()
        push_config_store = InMemoryPushNotificationConfigStore()
        push_sender = BasePushNotificationSender(
            httpx_client=httpx_client, config_store=push_config_store
        )
        request_handler = DefaultRequestHandler(
            agent_executor=WeatherAgentExecutor(),
            task_store=InMemoryTaskStore(),
            push_config_store=push_config_store,
            push_sender=push_sender,
        )

        server = A2AStarletteApplication(
            agent_card=public_agent_card,
            http_handler=request_handler,
            extended_agent_card=specific_extended_agent_card,
        )

        Logger.info("Starting Weather Agent server on %s:%s", host, port)
        uvicorn.run(server.build(), host=host, port=port)

    except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        Logger.error("An error occurred during server startup: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
