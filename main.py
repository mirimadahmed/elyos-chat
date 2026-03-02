import asyncio
import os
import sys

from dotenv import load_dotenv


def load_config():
    """Load and validate environment variables."""
    load_dotenv()
    missing = []
    for key in ("OPENAI_API_KEY", "ELYOS_API_KEY"):
        if not os.getenv(key):
            missing.append(key)
    if missing:
        print(f"Error: missing environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your keys.")
        sys.exit(1)
    return os.getenv("OPENAI_API_KEY"), os.getenv("ELYOS_API_KEY")


async def get_user_input() -> str:
    """Read user input asynchronously."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: input("You: "))


async def main():
    openai_key, elyos_key = load_config()

    from api_client import create_api_client
    from llm import create_client, stream_chat

    llm_client = create_client(openai_key)
    api_client = create_api_client(elyos_key)
    messages = []
    print("elyos-chat (type 'quit' to exit)")

    while True:
        try:
            user_input = await get_user_input()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        user_input = user_input.strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        messages.append({"role": "user", "content": user_input})
        msg_count_before = len(messages)

        try:
            async for chunk in stream_chat(llm_client, api_client, messages):
                print(chunk, end="", flush=True)
            print()
        except KeyboardInterrupt:
            # Roll back any partial assistant/tool messages from this turn
            del messages[msg_count_before:]
            # Also remove the user message since the turn was cancelled
            messages.pop()
            print("\nCancelled.")
            continue


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
