import httpx
import pytest

from tools import get_weather, research_topic


def _mock_client(response_json, status_code=200):
    """Create a mock httpx client returning a fixed response."""
    return httpx.AsyncClient(
        base_url="https://example.com",
        transport=httpx.MockTransport(
            lambda req: httpx.Response(status_code, json=response_json)
        ),
    )


@pytest.mark.asyncio
async def test_weather_flat_response():
    client = _mock_client({"location": "London", "temperature_c": 8.1, "condition": "Clear", "humidity": 81})
    result = await get_weather(client, "London")
    assert result["temperature_c"] == 8.1
    assert result["condition"] == "Clear"


@pytest.mark.asyncio
async def test_weather_array_response():
    """API quirk: some cities return an array of conditions."""
    client = _mock_client({
        "location": "Berlin",
        "conditions": [
            {"temperature_c": 7.2, "condition": "Clear", "humidity": 61},
            {"temperature_c": 6.2, "condition": "light rain", "humidity": 74},
        ],
        "note": "Multiple conditions reported",
    })
    result = await get_weather(client, "Berlin")
    assert result["temperature_c"] == 7.2
    assert result["all_conditions"] is not None
    assert len(result["all_conditions"]) == 2


@pytest.mark.asyncio
async def test_weather_throttled_then_success():
    """API quirk: rate limiting returns 200 with status=throttled."""
    call_count = 0

    def handler(req):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(200, json={"status": "throttled", "retry_after_seconds": 0, "data": None})
        return httpx.Response(200, json={"location": "London", "temperature_c": 8.1, "condition": "Clear", "humidity": 81})

    client = httpx.AsyncClient(base_url="https://example.com", transport=httpx.MockTransport(handler))
    result = await get_weather(client, "London")
    assert result["temperature_c"] == 8.1
    assert call_count == 2


@pytest.mark.asyncio
async def test_weather_http_error():
    client = _mock_client({"error": "not found"}, status_code=404)
    result = await get_weather(client, "nonexistent")
    assert "error" in result


@pytest.mark.asyncio
async def test_research_success():
    client = _mock_client({"topic": "solar", "summary": "Research summary", "sources": ["nature.com"]})
    result = await research_topic(client, "solar")
    assert result["summary"] == "Research summary"


@pytest.mark.asyncio
async def test_research_empty_then_retry():
    """API quirk: intermittent empty {} response."""
    call_count = 0

    def handler(req):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(200, json={})
        return httpx.Response(200, json={"topic": "test", "summary": "OK"})

    client = httpx.AsyncClient(base_url="https://example.com", transport=httpx.MockTransport(handler))
    result = await research_topic(client, "test")
    assert result["summary"] == "OK"
    assert call_count == 2


@pytest.mark.asyncio
async def test_research_stale_cache_warning():
    """API quirk: stale cached response gets a warning."""
    client = _mock_client({
        "topic": "climate", "summary": "Old data", "cached": True, "cache_age_seconds": 2_000_000
    })
    result = await research_topic(client, "climate")
    assert "staleness_warning" in result
