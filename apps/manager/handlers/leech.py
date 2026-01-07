import os
import logging
from pyrogram import Client, filters, enums
from services.database import db_service

logger = logging.getLogger("LeechHandler")

# Security: Only allow Owner
OWNER_ID = int(os.getenv("TG_OWNER_ID", 0))

@Client.on_message(filters.command(["leech", "mirror"]) & filters.user(OWNER_ID))
async def leech_command(client, message):
    try:
        # Format: /leech LINK TMDB_ID
        parts = message.command
        
        if len(parts) < 2:
            await message.reply_text(
                "❌ **Syntax Error**\n\nUsage: \nExample: "
            )
            return

        url = parts[1]
        tmdb_id = parts[2] if len(parts) > 2 else "999" # Default dummy ID for tests

        # Queue Logic
        if db_service.redis:
            payload = f"{tmdb_id}|{url}"
            # Push to the same list the Worker watches
            await db_service.redis.lpush("queue:leech", payload)
            
            await message.reply_text(
                f"🚀 **Dispatched to Swarm**\n"
                f"📦 Payload: \n"
                f"🔗 URL: ",
                quote=True
            )
            logger.info(f"Task dispatched: {payload}")
        else:
            await message.reply_text("❌ Redis Not Connected")

    except Exception as e:
        logger.error(f"Leech Error: {e}")
        await message.reply_text(f"⚠️ Internal Error: {e}")
