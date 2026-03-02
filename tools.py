import httpx


async def get_weather(client: httpx.AsyncClient, location: str) -> dict:
    """Fetch weather for a location from the Elyos API."""
    try:
        resp = await client.get("/weather", params={"location": location})
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except httpx.RequestError as e:
        return {"error": f"Request failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


async def research_topic(client: httpx.AsyncClient, topic: str) -> dict:
    """Research a topic via the Elyos API (slow: 3-8 seconds)."""
    try:
        resp = await client.get("/research", params={"topic": topic})
        resp.raise_for_status()
        return resp.json()
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
