from contextlib import aclosing

from google.adk import Agent
from google.adk.apps import App
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import (
    InMemoryCredentialService,
)
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from utils.logger import Logger


class ADKRunnerHelper:
    """
    A helper class to encapsulate the boilerplate of setting up and running
    a Google ADK Agent to get a single, final response.
    """

    def __init__(self, app_name: str, agent: Agent):
        """Initializes the App, Runner, and required services."""
        self.app = App(name=f"{app_name}_app", root_agent=agent)
        self.agent = agent
        self.runner = Runner(
            app=self.app,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            credential_service=InMemoryCredentialService(),
        )
        self.user_id = "mehmet"

    async def run_and_get_final_response(
        self, user_input: str, history: list[dict]
    ) -> str:
        """
        Runs the agent, processes the event stream, and returns a single final text response.
        """
        session = await self.runner.session_service.create_session(
            app_name=self.app.name, user_id=self.user_id
        )

        # Append historical messages to the session
        if history:
            Logger.info(f"AdkRunnerHelper | Appending history | count={len(history)}")
            for message in history:
                text = (message.get("content") or "").strip()
                if not text:
                    continue
                role = message.get("role") or "user"
                content_role = "user" if role == "user" else "model"
                author = "user" if role == "user" else self.agent.name
                content = types.Content(
                    role=content_role, parts=[types.Part(text=text)]
                )
                event = Event(author=author, content=content)
                await self.runner.session_service.append_event(session, event)

        user_message = types.Content(role="user", parts=[types.Part(text=user_input)])
        final_text = "No response received from delegated agents."

        try:
            async with aclosing(
                self.runner.run_async(
                    user_id=self.user_id,
                    session_id=session.id,
                    new_message=user_message,
                )
            ) as events:
                async for event in events:
                    text_from_event = self.extract_text_from_event(event)
                    if text_from_event:
                        final_text = text_from_event
        finally:
            await self.runner.close()

        return final_text

    def extract_text_from_event(self, event: Event) -> str | None:
        """Extracts and consolidates meaningful text from an ADK event."""
        if event.author == "user" or not event.content or not event.content.parts:
            return None

        current_event_texts: list[str] = []
        for part in event.content.parts:
            if getattr(part, "text", None):
                current_event_texts.append(part.text)

            fr = getattr(part, "function_response", None)
            if fr and getattr(fr, "response", None) is not None:
                resp = fr.response
                if isinstance(resp, dict) and "response" in resp:
                    current_event_texts.append(str(resp["response"]))
                elif isinstance(resp, str):
                    current_event_texts.append(resp)

        if current_event_texts:
            text = "\n".join(tp for tp in current_event_texts if tp).strip()
            return text if text else None

        return None
