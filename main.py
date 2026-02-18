import asyncio
from agents.host import A2AHost, A2AHostOptions
from env import secrets
from utils.types import ConversationMessage, ParticipantRole


def _parse_remote_agents() -> list[str]:
    return secrets.REMOTE_AGENT_URLS


async def run_cli() -> None:
    host = A2AHost(
        A2AHostOptions(
            id=None,
            name="a2a_host",
            description="Routes requests to remote agents.",
            streaming=False,
            remote_agent_addresses=_parse_remote_agents(),
        )
    )

    history: list[ConversationMessage] = []
    print("A2A Host CLI. Type 'exit' to quit.")
    while True:
        user_input = input("> ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        response = await host.process_request(user_input, history)
        history.append(
            ConversationMessage(
                role=ParticipantRole.USER,
                content=[{"text": user_input}],
            )
        )
        history.append(response)

        print(response.text or "")


def main() -> None:
    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
