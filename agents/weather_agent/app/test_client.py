"""Manual test client for interacting with the Weather Agent over HTTP."""

from typing import Any
from uuid import uuid4

import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
    EXTENDED_AGENT_CARD_PATH,
)
from utils.logger import Logger


async def main() -> None:
    """Fetch the agent card and send example synchronous and streaming requests."""
    base_url = "http://localhost:10001"

    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
        )

        final_agent_card_to_use: AgentCard | None = None

        try:
            Logger.info(
                "Attempting to fetch public agent card from: %s%s",
                base_url,
                AGENT_CARD_WELL_KNOWN_PATH,
            )
            public_card = await resolver.get_agent_card()
            Logger.info("Successfully fetched public agent card:")
            Logger.info(
                "%s",
                public_card.model_dump_json(indent=2, exclude_none=True),
            )
            final_agent_card_to_use = public_card
            Logger.info(
                "\nUsing PUBLIC agent card for client initialization (default)."
            )

            if public_card.supports_authenticated_extended_card:
                try:
                    Logger.info(
                        "\nPublic card supports authenticated extended card. Attempting to fetch from: %s%s",
                        base_url,
                        EXTENDED_AGENT_CARD_PATH,
                    )
                    auth_headers_dict = {
                        "Authorization": "Bearer dummy-token-for-extended-card"
                    }
                    extended_card = await resolver.get_agent_card(
                        relative_card_path=EXTENDED_AGENT_CARD_PATH,
                        http_kwargs={"headers": auth_headers_dict},
                    )
                    Logger.info(
                        "Successfully fetched authenticated extended agent card:"
                    )
                    Logger.info(
                        "%s",
                        extended_card.model_dump_json(indent=2, exclude_none=True),
                    )
                    final_agent_card_to_use = extended_card
                    Logger.info(
                        "\nUsing AUTHENTICATED EXTENDED agent card for client initialization."
                    )
                except (
                    Exception
                ) as exc_extended:  # noqa: BLE001  # pylint: disable=broad-exception-caught
                    Logger.warn(
                        "Failed to fetch extended agent card: %s. Will proceed with public card.",
                        exc_extended,
                        exc_info=True,
                    )
            elif public_card:
                Logger.info(
                    "\nPublic card does not indicate support for an extended card. Using public card."
                )

        except (
            Exception
        ) as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            Logger.error(
                "Critical error fetching public agent card: %s", exc, exc_info=True
            )
            raise RuntimeError(
                "Failed to fetch the public agent card. Cannot continue."
            ) from exc

        client = A2AClient(
            httpx_client=httpx_client, agent_card=final_agent_card_to_use
        )
        Logger.info("A2AClient initialized.")

        send_message_payload: dict[str, Any] = {
            "message": {
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": "weather in Istanbul,TR",
                    }
                ],
                "messageId": uuid4().hex,
            },
        }
        request = SendMessageRequest(
            id=str(uuid4()), params=MessageSendParams(**send_message_payload)
        )

        response = await client.send_message(request)
        print(response.model_dump(mode="json", exclude_none=True))

        enable_streaming = False
        if enable_streaming:
            streaming_request = SendStreamingMessageRequest(
                id=str(uuid4()), params=MessageSendParams(**send_message_payload)
            )
            stream_response = client.send_message_streaming(streaming_request)
            async for chunk in stream_response:
                print(chunk.model_dump(mode="json", exclude_none=True))


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
