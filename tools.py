import asyncio

import httpx


def _normalize_weather(data: dict) -> dict:
    """Normalize variable weather response shapes into a consistent format.

    The API sometimes returns a flat object, sometimes an array of conditions.
    """
    if "conditions" in data:
        # Array format — pick the first condition as primary
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


async def get_weather(client: httpx.AsyncClient, location: str) -> dict:
    """Fetch weather for a location from the Elyos API.

    Handles quirks: rate limiting (HTTP 200 with throttled status),
    variable response shapes, and standard HTTP errors.
    """
    try:
        resp = await client.get("/weather", params={"location": location})
        resp.raise_for_status()
        data = resp.json()

        # Quirk: rate limiting returns 200 with status="throttled"
        if data.get("status") == "throttled":
            wait = data.get("retry_after_seconds", 1)
            await asyncio.sleep(wait)
            resp = await client.get("/weather", params={"location": location})
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "throttled":
                return {"error": "Rate limited. Please try again shortly."}

        return _normalize_weather(data)
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except httpx.RequestError as e:
        return {"error": f"Request failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


async def research_topic(client: httpx.AsyncClient, topic: str) -> dict:
    """Research a topic via the Elyos API (slow: 3-8 seconds).

    Handles quirks: intermittent empty {} responses (retries once),
    stale cached responses (adds warning), and standard HTTP errors.
    """
    try:
        resp = await client.get("/research", params={"topic": topic})
        resp.raise_for_status()
        data = resp.json()

        # Quirk: intermittent empty JSON response — retry once
        if not data:
            await asyncio.sleep(1)
            resp = await client.get("/research", params={"topic": topic})
            resp.raise_for_status()
            data = resp.json()
            if not data:
                return {"error": "Research returned empty response after retry."}

        # Quirk: stale cached response — add warning
        if data.get("cached") and data.get("cache_age_seconds", 0) > 86400:
            days = data["cache_age_seconds"] // 86400
            data["staleness_warning"] = f"Cached data from ~{days} days ago."

        return data
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except httpx.RequestError as e:
        return {"error": f"Request failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city. Fast response (~200ms).",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name, e.g. London, Tokyo",
                    }
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "research_topic",
            "description": "Research a topic in depth. Takes 3-8 seconds. Use for questions requiring detailed research.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic to research, e.g. 'solar energy', 'climate change'",
                    }
                },
                "required": ["topic"],
            },
        },
    },
]
