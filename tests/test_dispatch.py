import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from llm import _execute_tool


def _mock_api_client(response_json):
    return httpx.AsyncClient(
        base_url="https://example.com",
        transport=httpx.MockTransport(
            lambda req: httpx.Response(200, json=response_json)
        ),
    )


@pytest.mark.asyncio
async def test_execute_weather_tool():
    client = _mock_api_client({"location": "London", "temperature_c": 10, "condition": "Sunny", "humidity": 50})
    result = json.loads(await _execute_tool(client, "get_weather", {"location": "London"}))
    assert result["location"] == "London"
    assert result["temperature_c"] == 10


@pytest.mark.asyncio
async def test_execute_research_tool():
    client = _mock_api_client({"topic": "AI", "summary": "AI research", "sources": []})
    result = json.loads(await _execute_tool(client, "research_topic", {"topic": "AI"}))
    assert result["topic"] == "AI"


@pytest.mark.asyncio
async def test_execute_unknown_tool():
    client = _mock_api_client({})
    result = json.loads(await _execute_tool(client, "unknown_tool", {}))
    assert "error" in result
    assert "Unknown tool" in result["error"]
