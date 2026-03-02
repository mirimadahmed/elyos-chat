import json

import httpx
from openai import APIError, AsyncOpenAI

from tools import TOOLS, get_weather, research_topic


def create_client(api_key: str) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=api_key)


async def _execute_tool(api_client: httpx.AsyncClient, name: str, args: dict) -> str:
    """Execute a tool call and return the result as a string."""
    if name == "get_weather":
        result = await get_weather(api_client, args["location"])
    elif name == "research_topic":
        result = await research_topic(api_client, args["topic"])
    else:
        result = {"error": f"Unknown tool: {name}"}
    return json.dumps(result)


async def stream_chat(
    llm_client: AsyncOpenAI,
    api_client: httpx.AsyncClient,
    messages: list[dict],
):
    """Send messages to the LLM, handle tool calls, yield content chunks.

    Modifies messages in place by appending assistant and tool messages.
    """
    while True:
        try:
            response = await llm_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=TOOLS,
                stream=True,
            )
        except APIError as e:
            yield f"\n[LLM error: {e.message}]\n"
            return

        content = ""
        tool_calls = {}  # index -> {id, name, arguments_str}

        async for chunk in response:
            delta = chunk.choices[0].delta

            # Stream content chunks to the caller
            if delta.content:
                content += delta.content
                yield delta.content

            # Accumulate tool call chunks
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls:
                        tool_calls[idx] = {
                            "id": tc.id or "",
                            "name": tc.function.name or "",
                            "arguments": "",
                        }
                    if tc.id:
                        tool_calls[idx]["id"] = tc.id
                    if tc.function.name:
                        tool_calls[idx]["name"] = tc.function.name
                    if tc.function.arguments:
                        tool_calls[idx]["arguments"] += tc.function.arguments

        # If no tool calls, we're done
        if not tool_calls:
            messages.append({"role": "assistant", "content": content})
            return

        # Build assistant message with tool calls
        assistant_msg = {
            "role": "assistant",
            "content": content or None,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments"],
                    },
                }
                for tc in tool_calls.values()
            ],
        }
        messages.append(assistant_msg)

        # Execute each tool call and append results
        for tc in tool_calls.values():
            try:
                args = json.loads(tc["arguments"])
            except json.JSONDecodeError:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps({"error": "Invalid tool arguments"}),
                })
                continue
            # Show pending indicator
            if tc["name"] == "get_weather":
                yield f"\n[Fetching weather for {args.get('location', '...')}...]\n"
            elif tc["name"] == "research_topic":
                yield f"\n[Researching {args.get('topic', '...')}... (Ctrl+C to cancel)]\n"
            result = await _execute_tool(api_client, tc["name"], args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

        # Loop back to get the LLM's response incorporating tool results
