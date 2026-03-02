from openai import AsyncOpenAI


def create_client(api_key: str) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=api_key)


async def stream_chat(client: AsyncOpenAI, user_message: str):
    """Send a single message to the LLM and yield streamed content chunks."""
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": user_message}],
        stream=True,
    )
    async for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
