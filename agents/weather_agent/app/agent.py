"""LangGraph-based weather agent that fetches live data from OpenWeather."""

import json
from collections.abc import AsyncIterable
from typing import Any, Literal

import requests
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel

from env import secrets

memory = MemorySaver()


@tool
def weather_api(city: str, country_code: str = "") -> str:
    """Retrieves the current weather conditions for any given location in real-time using the OpenWeather API."""
    api_key = secrets.OPEN_WEATHER_API_KEY
    if not api_key:
        return json.dumps(
            {"error": "OPEN_WEATHER_API_KEY environment variable not set in .env file"}
        )

    base_url = "http://api.openweathermap.org/data/2.5/weather"
    q_value = city if not country_code else f"{city},{country_code}"
    params = {"q": q_value, "appid": api_key, "units": "metric"}

    response = requests.get(base_url, params=params, timeout=60)

    if response.status_code != 200:
        return json.dumps(
            {
                "error": f"API request failed with status {response.status_code}",
                "details": response.text,
            }
        )
    data = response.json()

    temperature = data["main"]["temp"]
    description = data["weather"][0]["description"]

    return json.dumps(
        {
            "city": city,
            "temperature": temperature,
            "weather_description": description,
            "unit": "°C",
        },
        indent=2,
    )


class ResponseFormat(BaseModel):
    """Respond to the user in this format."""

    status: Literal["input_required", "completed", "error"] = "input_required"
    message: str


class WeatherAgent:
    """WeatherAgent - a specialized assistant for weather information."""

    SYSTEM_INSTRUCTION = (
        "You are a specialized assistant for weather information. "
        "Your sole purpose is to use the 'weather_api' tool to answer questions about current weather conditions. "
        "If the user asks about anything other than weather, "
        "politely state that you cannot help with that topic and can only assist with weather-related queries. "
        "Do not attempt to answer unrelated questions or use tools for other purposes."
    )

    def __init__(self) -> None:
        """Initialise the underlying LLM, tools, and LangGraph agent graph."""
        self.model = AzureChatOpenAI(
            azure_endpoint=secrets.AZURE_OPENAI_ENDPOINT,
            api_key=secrets.AZURE_OPENAI_API_KEY,
            azure_deployment=secrets.AZURE_OPENAI_DEPLOYMENT_NAME,
            api_version=secrets.AZURE_OPENAI_API_VERSION,
            temperature=0,
        )
        self.tools = [weather_api]

        self.graph = create_agent(
            model=self.model,
            tools=self.tools,
            checkpointer=memory,
            system_prompt=self.SYSTEM_INSTRUCTION,
            response_format=ResponseFormat,
        )

    async def invoke(self, query: str, context_id: str) -> dict[str, Any]:
        """Invokes the agent to get a single response."""
        inputs = {"messages": [("user", query)]}
        config = {"configurable": {"thread_id": context_id}}

        await self.graph.ainvoke(inputs, config)
        return self.get_agent_response(config)

    async def stream(
        self, query: str, context_id: str
    ) -> AsyncIterable[dict[str, Any]]:
        """Stream intermediate status updates and the final response to the caller."""
        inputs = {"messages": [("user", query)]}
        config = {"configurable": {"thread_id": context_id}}

        for item in self.graph.stream(inputs, config, stream_mode="values"):
            message = item["messages"][-1]
            if (
                isinstance(message, AIMessage)
                and message.tool_calls
                and len(message.tool_calls) > 0
            ):
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Fetching current weather...",
                }
            elif isinstance(message, ToolMessage):
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Processing weather data...",
                }

        yield self.get_agent_response(config)

    def get_agent_response(self, config: dict[str, Any]) -> dict[str, Any]:
        """Extract the structured response from graph state and adapt it to A2A format."""
        current_state = self.graph.get_state(config)
        structured_response = current_state.values.get("structured_response")
        if structured_response and isinstance(structured_response, ResponseFormat):
            if structured_response.status == "input_required":
                return {
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": structured_response.message,
                }
            if structured_response.status == "error":
                return {
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": structured_response.message,
                }
            if structured_response.status == "completed":
                return {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": structured_response.message,
                }

        return {
            "is_task_complete": False,
            "require_user_input": True,
            "content": (
                "We are unable to process your request at the moment. Please try again."
            ),
        }

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]
