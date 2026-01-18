# manager/handlers/cmd_leech.py (formerly leech.py)
import os
import sys
import logging
sys.path.append("/app/shared")
from shared.settings import settings
from shared.database import db_service
from shared.schemas import SignRequest
from pyrogram import Client, filters, enums

logger = logging.getLogger("LeechHandler")

# Security: Only allow Owner (Loaded from Pydantic Settings)
OWNER_ID = settings.TG_OWNER_ID

@Client.on_message(filters.command(["leech", "mirror"]) & filters.user(OWNER_ID))
async def leech_command(client, message):
    try:
        # Advanced Parsing to support quotes: 
        # /leech http... 123 tv "The Night Manager S01E01"
        text = message.text
        
        # 1. URL
        parts = text.split(" ", 2)
        if len(parts) < 2: return # usage error
        url = parts[1]
        
        # Default Params
        tmdb_id = "0"
        type_hint = "auto"
        name_hint = ""

        # 2. Extract Options if present
        if len(parts) > 2:
            remaining = parts[2]
            
            # Logic: If starts with quotes, it's a name hint, otherwise ID
            # Simple splitter by spaces
            sub_args = remaining.split(" ")
            
            # Helper to check if string looks like an ID
            if sub_args[0].isdigit():
                tmdb_id = sub_args[0]
                if len(sub_args) > 1: type_hint = sub_args[1]
                
                # Check for Name Hint (everything after type)
                # Join remaining args and strip quotes
                if len(sub_args) > 2:
                    name_hint = " ".join(sub_args[2:]).strip('"')
            else:
                # User skip ID/Type? Dangerous but assume raw name override
                pass

        # Queue Logic
        if db_service.redis:
            
            # Format: tmdb_id|url|type_hint|name_hint
            payload = f"{tmdb_id}|{url}|{type_hint}|{name_hint}"
            
            await db_service.redis.lpush("queue:leech", payload)
            
            # Generate Channel Link from Settings
            # Strip -100 for proper Deep Link
            clean_cid = str(settings.TG_LOG_CHANNEL_ID).replace("-100", "")
            chan_link = f"https://t.me/c/{clean_cid}/1"
            
            await message.reply_text(
                f"🚀 **Dispatched to Swarm**\n"
                f"📦 Payload: `{tmdb_id}` ({type_hint.upper()})\n"
                f"📝 Hint: `{name_hint}`\n"
                f"📡 Channel: [Open Log]({chan_link})",
                quote=True
            )
            logger.info(f"Task dispatched: {payload}")
        else:
            await message.reply_text("❌ Redis Not Connected")

    except Exception as e:
        logger.error(f"Leech Error: {e}")
        await message.reply_text(f"⚠️ Internal Error: {e}")
