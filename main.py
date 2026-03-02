import asyncio
import os
import signal
import sys

from dotenv import load_dotenv


def load_config():
    """Load and validate environment variables."""
    load_dotenv()
    missing = []
    for key in ("ANTHROPIC_API_KEY", "ELYOS_API_KEY"):
        if not os.getenv(key):
            missing.append(key)
    if missing:
        print(f"Error: missing environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your keys.")
        sys.exit(1)
    return os.getenv("ANTHROPIC_API_KEY"), os.getenv("ELYOS_API_KEY")


async def get_user_input() -> str:
    """Read user input asynchronously."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: input("You: "))


async def _consume_stream(stream_gen):
    """Consume a stream generator, printing chunks and collecting content."""
    async for chunk in stream_gen:
        print(chunk, end="", flush=True)


async def main():
    anthropic_key, elyos_key = load_config()

    from api_client import create_api_client
    from llm import create_client, stream_chat

    llm_client = create_client(anthropic_key)
    api_client = create_api_client(elyos_key)
    messages = []
    print("elyos-chat (type 'quit' to exit)")

    loop = asyncio.get_event_loop()

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

        # Run streaming in a task so we can cancel it on Ctrl+C
        task = asyncio.create_task(
            _consume_stream(stream_chat(llm_client, api_client, messages))
        )

        # Set up SIGINT to cancel the task instead of raising KeyboardInterrupt
        cancelled = False

        def _on_sigint(sig, frame):
            nonlocal cancelled
            cancelled = True
            task.cancel()

        old_handler = signal.signal(signal.SIGINT, _on_sigint)

        try:
            await task
            print()
        except asyncio.CancelledError:
            # Roll back any partial assistant/tool messages added during this turn
            del messages[msg_count_before:]
            print("\nCancelled.")
        except Exception as e:
            del messages[msg_count_before:]
            print(f"\nError: {e}")
        finally:
            signal.signal(signal.SIGINT, old_handler)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
