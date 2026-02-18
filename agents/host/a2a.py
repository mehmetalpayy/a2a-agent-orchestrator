import uuid
from typing import Any

from a2a.types import (
    MessageSendParams,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
)
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.tool_context import ToolContext
from pydantic import Field
from pydantic.dataclasses import ConfigDict, dataclass

from env import secrets
from prompts import A2A_SYSTEM_PROMPT
from protocol import ADKRunnerHelper, RemoteAgentManager, TaskUpdateCallback
from utils.logger import Logger
from utils.types import ConversationMessage, ParticipantRole

from .base import Agent as BaseAgent
from .base import AgentOptions


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class A2AHostOptions(AgentOptions):
    task_callback: TaskUpdateCallback | None = None
    client: Any | None = None
    inference_config: dict[str, Any] | None = None
    custom_system_prompt: dict[str, Any] | None = None
    remote_agent_addresses: list[str] = Field(default_factory=list)


class A2AHost(BaseAgent):
    def __init__(self, options: A2AHostOptions):
        super().__init__(options)

        default_inference_config = {
            "max_tokens": 4096,
            "temperature": 0.0,
            "top_p": None,
            "stop_sequences": None,
        }

        self.inference_config = default_inference_config.copy()
        if options.inference_config:
            self.inference_config.update(options.inference_config)

        self.client = options.client or LiteLlm(
            model=f"azure/{secrets.AZURE_OPENAI_DEPLOYMENT_NAME}",
            api_key=secrets.AZURE_OPENAI_API_KEY,
            api_base=secrets.AZURE_OPENAI_ENDPOINT,
            api_version=secrets.AZURE_OPENAI_API_VERSION,
            **self.inference_config,
        )

        if options.custom_system_prompt:
            self.set_system_prompt(
                options.custom_system_prompt.get("template"),
                options.custom_system_prompt.get("variables"),
            )

        self.task_callback = options.task_callback
        self.agent_manager = RemoteAgentManager(options.remote_agent_addresses or [])
        self._is_ready: bool = False

    async def create(self) -> "A2AHost":
        """Finalize asynchronous setup for this RoutingAgent instance."""
        if self._is_ready:
            return self

        Logger.info("A2AHost.create | Initializing remote agent manager...")
        await self.agent_manager.initialize()

        self._is_ready = True
        Logger.info("A2AHost.create | completed | ready=True")
        return self

    def create_agent(self) -> Agent:
        """Create an instance of the RoutingAgent."""
        Logger.info(f"A2AHost.create_agent | creating ADK Agent | name={self.name}")
        return Agent(
            model=self.client,
            name=self.name,
            instruction=self.root_instruction,
            before_model_callback=self.before_model_callback,
            description=self.description,
            tools=[
                self.send_message,
            ],
        )

    def root_instruction(self, context: ReadonlyContext) -> str:
        """Generate the root instruction for the RoutingAgent."""
        current_agent = self.check_active_agent(context)
        agents_list = self.agent_manager.get_agents_prompt_string()
        return A2A_SYSTEM_PROMPT.format(
            instruction=self.system_prompt,
            agents=agents_list,
            current_agent=current_agent["active_agent"],
        )

    def check_active_agent(self, context: ReadonlyContext):
        state = context.state
        if (
            "session_id" in state
            and "session_active" in state
            and state["session_active"]
            and "active_agent" in state
        ):
            return {"active_agent": f"{state['active_agent']}"}
        return {"active_agent": "None"}

    def before_model_callback(self, callback_context: CallbackContext, llm_request):
        state = callback_context.state
        if "session_active" not in state or not state["session_active"]:
            if "session_id" not in state:
                state["session_id"] = str(uuid.uuid4())
            state["session_active"] = True

    def get_remote_agents_str(self) -> str:
        remote_details_str = self.agent_manager.get_formatted_remote_agent_details_str()

        if remote_details_str:
            return f"{self.description} can access the following remote agents: [{remote_details_str}]"

        return self.description

    async def send_message(self, agent_name: str, task: str, tool_context: ToolContext):
        """Sends a task to remote agent."""
        client = self.agent_manager.get_connection(agent_name)
        state = tool_context.state
        state["active_agent"] = agent_name

        if "context_id" not in state:
            state["context_id"] = str(uuid.uuid4())

        message_id = state.get("input_message_metadata", {}).get(
            "message_id", str(uuid.uuid4())
        )

        payload = {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": task}],
                "messageId": message_id,
                "contextId": state["context_id"],
            },
        }

        message_request = SendMessageRequest(
            id=message_id, params=MessageSendParams.model_validate(payload)
        )

        send_response = await client.send_message(message_request=message_request)

        Logger.info(
            f"A2AHost.send_message | raw_response={send_response.model_dump_json(exclude_none=True)}"
        )

        return self.parse_send_message_response(send_response)

    def parse_send_message_response(
        self, response: SendMessageResponse
    ) -> dict | Task | None:
        """Parses the complex response from a remote agent."""
        if not isinstance(response.root, SendMessageSuccessResponse):
            Logger.warn("A2AHost response parser | Non-success response")
            return None

        if isinstance(response.root.result, Task):
            return response.root.result

        try:
            payload = response.model_dump(exclude_none=True)
            result = payload.get("result", {})
            if result.get("kind") == "message":
                parts = result.get("parts", [])
                texts = [p.get("text", "") for p in parts if p.get("kind") == "text"]
                text = "\n".join(t for t in texts if t)
                if text:
                    return {"response": text}
        except Exception as e:
            Logger.error(f"A2AHost response parser | Fallback parse error: {e}")

        Logger.warn("A2AHost response parser | Could not parse a valid result.")
        return None

    async def process_request(
        self, user_input: str, chat_history: list[ConversationMessage]
    ) -> ConversationMessage:
        """Handle an incoming payload using the agent's configuration."""
        if not self._is_ready:
            await self.create()

        Logger.info(
            f"A2AHost.process_request | start | user_input_len={len(user_input)} | history_len={len(chat_history)}"
        )
        history_messages = await self.prepare_chat_history(chat_history)

        if self.streaming:
            raise NotImplementedError(
                "Streaming mode is not supported for A2AHost agents."
            )

        response = await self.single_response(user_input, history_messages)
        Logger.info(
            f"A2AHost.process_request | completed | response_text_len={len(response.text or '')}"
        )
        return response

    async def single_response(
        self, user_input: str, history: list[dict[str, str]] | None = None
    ) -> ConversationMessage:
        """Produce a single assistant response by delegating to the ADK runner helper."""
        if not self._is_ready:
            await self.create()

        Logger.info("A2AHost.single_response | start")
        adk_agent = self.create_agent()

        runner_helper = ADKRunnerHelper(app_name=self.name, agent=adk_agent)
        final_text = await runner_helper.run_and_get_final_response(
            user_input, history or []
        )

        Logger.info(f"A2AHost.single_response | completed | final_text={final_text}")
        return ConversationMessage(
            role=ParticipantRole.ASSISTANT.value,
            content=[{"text": final_text}],
        )
