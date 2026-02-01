# manager/handlers/cmd_leech.py (formerly leech.py)
import os
import sys
import uuid
import logging
sys.path.append("/app/shared")
from shared.settings import settings
from shared.database import db_service
from shared.schemas import SignRequest
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger("LeechHandler")

# Security: Only allow Owner (Loaded from Pydantic Settings)
OWNER_ID = settings.TG_OWNER_ID

# --- 1. THE LEECH COMMAND ---
@Client.on_message(filters.command(["leech", "mirror"]) & filters.user(OWNER_ID))
async def leech_command(client, message):
    try:
        # Advanced Parsing to support quotes: 
        # /leech http... 123 tv "The Night Manager S01E01"
        text = message.text
        
        # 1. URL
        parts = text.split(" ", 2)
        if len(parts) < 2: 
            return await message.reply_text("❌ Usage: `/leech [URL] [TMDB_ID] [type] [name]`")
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
            # else:
            #     # User skip ID/Type? Dangerous but assume raw name override
            #     pass

        # Queue Logic
        if db_service.redis:
            # ... extract vars ...
            task_id = str(uuid.uuid4())[:8] # Short unique ID for this job

            # Format: task_id|tmdb_id|url|type_hint|name_hint
            payload = f"{task_id}|{tmdb_id}|{url}|{type_hint}|{name_hint}"
            
            # 1. Create a "Live Status" in Redis
            status_key = f"task_status:{task_id}"
            await db_service.redis.hset(status_key, mapping={
                "name": name_hint or f"TMDB {tmdb_id}",
                "status": "queued",
                "progress": 0,
                "tmdb_id": tmdb_id
            })
            # Expire status after 1 hour to keep Redis clean
            await db_service.redis.expire(status_key, 3600)

            # 2. Push to Queue
            await db_service.redis.lpush("queue:leech", payload)
            
            # Generate Channel Link from Settings
            # Strip -100 for proper Deep Link
            clean_cid = str(settings.TG_LOG_CHANNEL_ID).replace("-100", "")
            chan_link = f"https://t.me/c/{clean_cid}/1"
            
            # Reply with Buttons
            response_text = (
                f"🚀 **Task Queued**\n"
                f"{'—' * 15}\n"
                f"🆔 ID: `{task_id}`\n"
                f"📦 Content: `{tmdb_id}` ({type_hint.upper()})\n"
                f"📡 Status: `Pending in Queue...`\n"
                f"📜 Channel: [Open Log]({chan_link})"
            )

            # --- 2. SEND THE REPLY ---
            await message.reply_text(
                response_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 View Queue Status", callback_data="check_status")]
                ]),
                disable_web_page_preview=True,
                quote=True
            )
            logger.info(f"Task dispatched: {payload}")
        else:
            await message.reply_text("❌ Redis Not Connected")

    except Exception as e:
        logger.error(f"Leech Error: {e}")
        await message.reply_text(f"⚠️ Internal Error: {e}")

# --- 2. THE CANCEL LOGIC ---
@Client.on_message(filters.command("cancel") & filters.user(OWNER_ID))
async def cancel_task(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/cancel task_id`")
    
    task_id = message.command[1]
    status_key = f"task_status:{task_id}"
    
    # Check if task exists
    if not await db_service.redis.exists(status_key):
        return await message.reply_text("❌ Task not found or already finished.")

    # Set a Kill Flag in Redis
    await db_service.redis.set(f"kill_signal:{task_id}", "1", ex=300)
    await db_service.redis.hset(status_key, "status", "cancelling")
    
    await message.reply_text(f"🛑 Kill signal sent to Task `{task_id}`. Waiting for Worker to abort...")

# --- THE STATUS LOGIC (Shared by Command and Button) ---
async def build_status_text():
    """Generates the text for /status and callback"""
    if not db_service.redis:
        return "❌ Redis Offline"

    keys = await db_service.redis.keys("task_status:*")
    active_lines = []
    
    for key in keys:
        data = await db_service.redis.hgetall(key)
        if not data: continue
        
        task_id = key.split(":")[-1]
        raw_status = data.get("status", "unknown") or "unknown"
        status = raw_status.upper()
        progress = data.get("progress", "0") or "0"
        name = data.get("name", "Unknown Content")
        
        if status not in ["COMPLETED", "CANCELLED"]:
            # Better Progress Bar Logic
            try:
                prog_int = int(float(progress))
                filled = min(max(prog_int // 10, 0), 10)
                progress_bar = f"\n   └ `[{'■' * filled}{'□' * (10 - filled)}]` {prog_int}%"
            except: 
                progress_bar = f" ({progress}%)"
            
            active_lines.append(
                f"⚡ `{task_id}`: **{name}**\n"
                f"   └ 🛠️ {status}{progress_bar}\n"
                f"   └ 🛑 Abort: `/cancel {task_id}`"
            )

    queue_items = await db_service.redis.lrange("queue:leech", 0, -1)
    pending_lines = []
    for i, item in enumerate(queue_items):
        parts = item.split("|")
        t_id = parts[0]
        # Robust name hint extraction
        n_hint = parts[4] if len(parts) > 4 and parts[4] else f"TMDB {parts[1]}"
        pending_lines.append(f"`{i+1}.` **{n_hint}** (ID: `{t_id}`)")

    header = "🛰️ **Shadow Systems Status**\n" + ("—" * 15)
    active_section = "\n\n🔄 **ACTIVE TASKS**\n" + ("\n".join(active_lines) if active_lines else "_No active workers._")
    queue_section = "\n\n⏳ **PENDING QUEUE**\n" + ("\n".join(pending_lines) if pending_lines else "_Queue is empty._")
    footer = f"\n\n📊 **Total Pending:** `{len(queue_items)}`"
    
    return header + active_section + queue_section + footer

# --- 3. STATUS COMMAND HANDLER ---
@Client.on_message(filters.command("status") & filters.user(OWNER_ID))
async def status_cmd_handler(client, message):
    try:
        status_text = await build_status_text()
        await message.reply_text(status_text, quote=True)
    except Exception as e:
        await message.reply_text(f"❌ Status Error: {e}")

# --- 4. CALLBACK HANDLER (The Button Fix) ---
@Client.on_callback_query(filters.regex("check_status"))
async def status_callback_handler(client, callback_query):
    """Triggered when user clicks 'View Queue Status' button"""
    try:
        # Check if user is admin
        if callback_query.from_user.id != OWNER_ID:
            return await callback_query.answer("⛔ Access Denied", show_alert=True)

        status_text = await build_status_text()
        
        # Edit the existing message to show status
        await callback_query.message.edit_text(
            status_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh Status", callback_data="check_status")]
            ])
        )
        # Answer the callback to remove the loading spinner
        await callback_query.answer()
    except Exception as e:
        logger.error(f"Callback Error: {e}")
        await callback_query.answer("⚠️ Could not fetch status")