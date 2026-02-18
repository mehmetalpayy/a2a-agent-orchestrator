<h1 align="center"><strong>A2A Agent Orchestrator</strong></h1>

## Overview

This repository is a lightweight multi-agent orchestrator built around the A2A protocol. It includes:
- A **host** agent that discovers remote agents and delegates user requests.
- Example **Weather Agent** implementation exposed as an A2A server.
- Shared utilities (`env.py`, `utils/`, `prompts/`) to keep configuration and logging consistent.

The primary workflow is:
1. Run one or more remote agents (e.g., Weather Agent).
2. Run the host CLI to route user queries to the correct agent.

## What It Does

- Discovers A2A remote agents via their agent cards.
- Delegates user tasks to remote agents using `send_message`.
- Provides a simple CLI for testing the host routing logic.
- Includes a working Weather Agent that calls OpenWeather and returns live weather.

## Requirements

- Python 3.10+ (host repo uses 3.13; weather agent uses 3.10+)
- `uv` installed
- Azure OpenAI credentials for the host
- OpenWeather API key for the weather agent

## Repository Structure

- `main.py`: Host CLI entrypoint.
- `agents/host/`: Host agent implementation.
- `agents/weather_agent/`: Example A2A weather agent (own `pyproject.toml`).
- `protocol/`: Remote agent manager + ADK runner.
- `utils/`: Shared helpers and logging.
- `env.py`: Typed environment configuration.
- `prompts/`: System prompts for the host routing agent.

## Installation

Create the host environment:

```bash
uv venv
uv sync
```

Install the weather agent dependencies:

```bash
make weather-sync
```

## Configuration

Create a `.env` file in the repo root:

```bash
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT_NAME=...
AZURE_OPENAI_API_VERSION=

OPEN_WEATHER_API_KEY=...

AGENT_BIND_HOST=127.0.0.1
PORT=10001
AGENT_PUBLIC_BASE_URL=

REMOTE_AGENT_URLS=["http://127.0.0.1:10001"]
```

## Run The Agents

Start the Weather Agent:

```bash
make weather-run
```

In another terminal, start the host CLI:

```bash
make host-cli
```

Then type a message like:

```
what is the weather in İstanbul?
```

## Usage Notes

- The host uses A2A discovery to resolve agent cards from each URL in `REMOTE_AGENT_URLS`.
- Weather agent runs as a standalone A2A server and can be queried directly via its test client:

```bash
make weather-test
```

## Design Notes

- The host uses a routing prompt in `prompts/a2a_system_prompt.py`.
- Remote agents should implement:
  - Agent card endpoint
  - `send_message` JSON-RPC handler
- For now, the host runs as a CLI for quick iteration and debugging.

## Limitations

- Host streaming is disabled.
- Only one example agent (Weather) is included.
- The host currently assumes a single model provider (Azure OpenAI via LiteLLM).

## Future Improvements

- Provide a FastAPI host service for production use.
- Improve agent selection logic when multiple agents are available.
- Add structured logging and tracing hooks.

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Open a pull request.
