import asyncio

import httpx


def _normalize_weather(data: dict) -> dict:
    """Normalize variable weather response shapes (flat vs array)."""
    if "conditions" in data:
        primary = data["conditions"][0] if data["conditions"] else {}
        return {
            "location": data.get("location", "Unknown"),
            "temperature_c": primary.get("temperature_c"),
            "condition": primary.get("condition"),
            "humidity": primary.get("humidity"),
            "note": data.get("note", ""),
            "all_conditions": data["conditions"],
        }
    return data


async def _api_call(client, path, params):
    """Make an API call with standard error handling."""
    try:
        resp = await client.get(path, params=params)
        resp.raise_for_status()
        return resp.json(), None
    except httpx.HTTPStatusError as e:
        return None, f"HTTP {e.response.status_code}: {e.response.text}"
    except httpx.RequestError as e:
        return None, f"Request failed: {e}"


async def get_weather(client: httpx.AsyncClient, location: str) -> dict:
    """Fetch weather. Handles rate limiting (200 + throttled) and variable shapes."""
    data, err = await _api_call(client, "/weather", {"location": location})
    if err:
        return {"error": err}

    # Quirk: rate limiting returns 200 with status="throttled"
    if data.get("status") == "throttled":
        await asyncio.sleep(data.get("retry_after_seconds", 1))
        data, err = await _api_call(client, "/weather", {"location": location})
        if err or data.get("status") == "throttled":
            return {"error": err or "Rate limited. Try again shortly."}

    return _normalize_weather(data)


async def research_topic(client: httpx.AsyncClient, topic: str) -> dict:
    """Research a topic (3-8s). Handles empty {} responses and stale caches."""
    data, err = await _api_call(client, "/research", {"topic": topic})
    if err:
        return {"error": err}

    # Quirk: intermittent empty response — retry once
    if not data:
        await asyncio.sleep(1)
        data, err = await _api_call(client, "/research", {"topic": topic})
        if err or not data:
            return {"error": err or "Empty response after retry."}

    # Quirk: stale cached response
    if data.get("cached") and data.get("cache_age_seconds", 0) > 86400:
        data["staleness_warning"] = f"Cached ~{data['cache_age_seconds'] // 86400} days ago."

    return data


TOOLS = [
    {
        "name": "get_weather",
        "description": "Get current weather for a city. Fast response (~200ms).",
        "input_schema": {"type": "object", "properties": {
            "location": {"type": "string", "description": "City name, e.g. London, Tokyo"}
        }, "required": ["location"]},
    },
    {
        "name": "research_topic",
        "description": "Research a topic in depth. Takes 3-8 seconds.",
        "input_schema": {"type": "object", "properties": {
            "topic": {"type": "string", "description": "Topic to research, e.g. 'solar energy'"}
        }, "required": ["topic"]},
    },
]
