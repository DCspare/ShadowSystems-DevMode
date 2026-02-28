import asyncio

from pyrogram import Client

# Replace these with your actual credentials from .env manually or load them
# For quick script, just edit this file or input at runtime
api_id = input("Enter API ID: ")
api_hash = input("Enter API HASH: ")


async def main():
    async with Client(":memory:", api_id=api_id, api_hash=api_hash) as app:
        print("\n✅ YOUR SESSION STRING (Copy everything below this line):")
        print(await app.export_session_string())
        print("\n-------------------------------------------------------")


if __name__ == "__main__":
    asyncio.run(main())
