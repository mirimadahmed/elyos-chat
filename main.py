import asyncio
import sys


async def get_user_input() -> str:
    """Read user input asynchronously."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: input("You: "))


async def main():
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

        # TODO: send to LLM
        print(f"[echo] {user_input}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
