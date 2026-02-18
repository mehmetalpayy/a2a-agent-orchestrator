.PHONY: weather-sync weather-run weather-test host-run
.PHONY: host-cli

weather-sync:
	cd agents/weather_agent && uv sync

weather-run:
	uv run --project agents/weather_agent python -m agents.weather_agent.app

weather-test:
	uv run --project agents/weather_agent python -m agents.weather_agent.app.test_client

host-run:
	@echo "Host agent run target is not wired yet."

host-cli:
	uv run python main.py
