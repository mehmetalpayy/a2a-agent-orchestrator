"""A2A AgentExecutor implementation wrapping the WeatherAgent logic."""

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    InvalidParamsError,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import (
    new_agent_text_message,
    new_task,
)
from a2a.utils.errors import ServerError

from utils.logger import Logger

from .agent import WeatherAgent


# --8<-- [start:WeatherAgentExecutor_init]
class WeatherAgentExecutor(AgentExecutor):
    """Weather Agent Executor that adapts WeatherAgent to the A2A protocol."""

    def __init__(self) -> None:
        """Initialise the executor with a WeatherAgent instance."""
        self.agent = WeatherAgent()

    # --8<-- [end:WeatherAgentExecutor_init]
    # --8<-- [start:WeatherAgentExecutor_execute]
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute a single agent request and update the associated task."""
        error = self._validate_request(context)
        if error:
            raise ServerError(error=InvalidParamsError())

        query = context.get_user_input()
        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        try:
            response = await self.agent.invoke(query, task.context_id)

            content = response["content"]
            require_user_input = response["require_user_input"]
            is_task_complete = response["is_task_complete"]

            if require_user_input:
                await updater.update_status(
                    TaskState.input_required,
                    new_agent_text_message(
                        content,
                        task.context_id,
                        task.id,
                    ),
                    final=True,
                )
            elif is_task_complete:
                await updater.add_artifact(
                    [Part(root=TextPart(text=content))],
                    name="conversion_result",
                )
                await updater.complete()
            else:
                Logger.error("Unexpected state from agent: %s", response)
                raise ServerError(
                    error=InternalError(message="Agent returned an unexpected state.")
                )

        except (
            Exception
        ) as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            Logger.error(
                "An error occurred while executing the agent: %s", exc, exc_info=True
            )
            raise ServerError(error=InternalError()) from exc

    def _validate_request(self, context: RequestContext) -> bool:  # noqa: ARG002
        """Validate incoming request; currently always returns False (no error)."""
        Logger.debug("WeatherAgentExecutor | request_context=%s", context)
        return False

    async def cancel(  # noqa: ARG002
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Cancel is not supported for this agent; always raises an error."""
        raise ServerError(error=UnsupportedOperationError())
