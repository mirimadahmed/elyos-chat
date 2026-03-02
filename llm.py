import json

import httpx
from anthropic import AsyncAnthropic, APIError

from tools import TOOLS, get_weather, research_topic


def create_client(api_key: str) -> AsyncAnthropic:
    return AsyncAnthropic(api_key=api_key)


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
    llm_client: AsyncAnthropic,
    api_client: httpx.AsyncClient,
    messages: list[dict],
):
    """Send messages to the LLM, handle tool calls, yield content chunks.

    Modifies messages in place by appending assistant and tool messages.
    """
    while True:
        try:
            stream = llm_client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=messages,
                tools=TOOLS,
            )
        except APIError as e:
            yield f"\n[LLM error: {e.message}]\n"
            return

        content_text = ""
        tool_uses = []  # list of {id, name, input}

        async with stream as response:
            async for event in response:
                if event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        tool_uses.append({
                            "id": event.content_block.id,
                            "name": event.content_block.name,
                            "input_json": "",
                        })
                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        content_text += event.delta.text
                        yield event.delta.text
                    elif event.delta.type == "input_json_delta":
                        if tool_uses:
                            tool_uses[-1]["input_json"] += event.delta.partial_json

        # If no tool calls, we're done
        if not tool_uses:
            messages.append({"role": "assistant", "content": content_text})
            return

        # Build assistant message with tool use blocks
        assistant_content = []
        if content_text:
            assistant_content.append({"type": "text", "text": content_text})
        for tu in tool_uses:
            try:
                input_data = json.loads(tu["input_json"]) if tu["input_json"] else {}
            except json.JSONDecodeError:
                input_data = {}
            assistant_content.append({
                "type": "tool_use",
                "id": tu["id"],
                "name": tu["name"],
                "input": input_data,
            })
        messages.append({"role": "assistant", "content": assistant_content})

        # Execute each tool call and collect results
        tool_results = []
        for tu in tool_uses:
            try:
                args = json.loads(tu["input_json"]) if tu["input_json"] else {}
            except json.JSONDecodeError:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu["id"],
                    "content": json.dumps({"error": "Invalid tool arguments"}),
                })
                continue

            # Show pending indicator
            if tu["name"] == "get_weather":
                yield f"\n[Fetching weather for {args.get('location', '...')}...]\n"
            elif tu["name"] == "research_topic":
                yield f"\n[Researching {args.get('topic', '...')}... (Ctrl+C to cancel)]\n"

            result = await _execute_tool(api_client, tu["name"], args)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu["id"],
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

        # Loop back to get the LLM's response incorporating tool results
