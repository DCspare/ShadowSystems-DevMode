# manager/handlers/cmd_leech.py (formerly leech.py)
import logging
import shlex
import sys
import uuid

from shared.registry import (
    get_active_tasks_count,
)

sys.path.append("/app/shared")
from pyrogram import Client, enums, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from shared.database import db_service
from shared.settings import settings

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

        # 1. PARSE ARGUMENTS (Outside the logic block)
        try:
            all_args = shlex.split(text)
        except ValueError:
            all_args = text.split()  # Fallback for mismatched quotes

        # 2. VALIDATE USAGE
        if len(all_args) < 2:
            return await message.reply_text(
                f"<pre>⚠️ Usage:</pre>\n"
                f"{'—' * 12}\n"
                f"<code>/leech [URL] [TMDB_ID] [type] \"[name]\"</code>\n\n"
                f"<b>Example:</b> <code>/leech https://video-link.mp4 155 movie \"The Dark Knight\"</code>"
            )
        url = all_args[1]

        # Default Params
        tmdb_id = "0"
        type_hint = "auto"
        name_hint = ""

        # 3. EXTRACT OPTIONS (ID, Type, or Name)
        for arg in all_args[2:]:
            if arg.isdigit():
                tmdb_id = arg
            elif arg.lower() in ["tv", "movie", "series", "anime"]:
                type_hint = arg.lower()
            else:
                # Anything else (especially quoted strings) is the name_hint
                name_hint = arg

        # 4. QUEUE LOGIC
        if not db_service.redis:
            return await message.reply_text("❌ Redis Not Connected")

        user_id = message.from_user.id
        origin_chat_id = message.chat.id  # <--- TRACK ORIGIN
        trigger_msg_id = message.id  # <--- Store this to delete later
        limit_key = f"active_user_tasks:{user_id}"

        # GLOBAL LIMIT CHECK (Is the whole server full?)
        active_total = await get_active_tasks_count()
        if active_total >= settings.MAX_TOTAL_TASKS:
            return await message.reply_text(
                f"<pre>⚠️ <b>Server Busy!</b></pre>\n"
                f"Total active tasks: <code>{active_total}/{settings.MAX_TOTAL_TASKS}</code>\n"
                f"Your task is in the queue and will start automatically when a slot opens."
                f"Check Status --> /status"
            )

        # USER LIMIT CHECK (Bypass if user is Owner OR Toggle is OFF)
        if settings.ENABLE_USER_LIMITS and user_id != OWNER_ID:
            active_count = await db_service.redis.scard(limit_key)
            if active_count >= settings.MAX_TASKS_PER_USER:
                # Fetch IDs to show the user
                active_ids = await db_service.redis.smembers(limit_key)
                ids_str = ", ".join([f"<code>{i}</code>" for i in active_ids])
                return await message.reply_text(
                    f"⚠️ <b>Limit Reached!</b>\n"
                    f"You have <code>{active_count}</code> active tasks: {ids_str}\n\n"
                    f"Please wait for them to finish or <code>/cancel</code> one to start a new task."
                )

        # Prepare User Tag (Username or First Name)
        user_tag = (
            f"@{message.from_user.username}"
            if message.from_user.username
            else message.from_user.first_name
        )

        # 2. Setup Task Identity
        task_id = str(uuid.uuid4())[:8]  # Short unique ID
        status_key = f"task_status:{task_id}"

        # 3. Add to User's Active Set
        await db_service.redis.sadd(limit_key, task_id)
        # Auto-expire the set in 2 hours (Safety against zombie tasks)
        await db_service.redis.expire(limit_key, 7200)

        # PREPARE THE REPLY TEXT
        # Generate Channel Link from Settings
        # Strip -100 for proper Deep Link
        clean_cid = str(settings.TG_LOG_CHANNEL_ID).replace("-100", "")
        chan_link = f"https://t.me/c/{clean_cid}/1"

        # Reply with Buttons
        response_text = (
            f"<pre>🚀 Task Queued</pre>\n"
            f"{'—' * 12}\n"
            f"🆔 ID: <code>{task_id}</code>\n"
            f"📦 Content: <code>{tmdb_id}</code> ({type_hint.upper()})\n"
            f"📡 Status: <code>Added in Queue...</code>\n"
            f"📜 Channel: <a href='{chan_link}'>Open Log</a>"
        )

        # 5. Send to DM if in group, else reply in DM
        try:
            if message.chat.type != enums.ChatType.PRIVATE:
                # Send info to Owner DM
                sent_msg = await client.send_message(
                    chat_id=OWNER_ID,
                    text=response_text
                    + f"\n\n📍 <i>Triggered in: {message.chat.title}</i>",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "📊 Status", callback_data="check_status"
                                )
                            ]
                        ]
                    ),
                )
            else:
                sent_msg = await message.reply_text(response_text, quote=True)
        except Exception:
            # Fallback if user hasn't started bot in DM
            sent_msg = await message.reply_text(response_text, quote=True)

        # 6. CREATE THE REDIS STATUS ENTRY (a "Live Status" in Redis)
        await db_service.redis.hset(
            status_key,
            mapping={
                "name": name_hint or f"TMDB {tmdb_id}",
                "status": "queued",
                "progress": 0,
                "tmdb_id": tmdb_id,
                "user_tag": user_tag,
                "chat_id": str(message.chat.id),
                "msg_id": str(sent_msg.id),
                "trigger_msg_id": str(trigger_msg_id),
            },
        )
        # Expire status after 1 hour to keep Redis clean
        await db_service.redis.expire(status_key, 3600)

        # 7. PAYLOAD & PUSH TO QUEUE
        # FORMAT: task_id|tmdb_id|url|type|name|user_id|origin_chat_id|user_tag|trigger_msg_id
        payload = f"{task_id}|{tmdb_id}|{url}|{type_hint}|{name_hint}|{user_id}|{origin_chat_id}|{user_tag}|{trigger_msg_id}"

        # 5. Push to Queue
        await db_service.redis.lpush("queue:leech", payload)
        logger.info(f"Task dispatched: {payload}")

        # 🟢 CRITICAL LOG: If you don't see this in Manager Logs, the bridge failed.
        logger.info(f"📤 Task Dispatched to Redis: {task_id}")

    except Exception as e:
        logger.error(f"Leech Error: {e}")
        await message.reply_text(f"⚠️ Internal Error: {e}")


# --- 2. THE CANCEL LOGIC (Smarter Check) ---
@Client.on_message(filters.command("cancel") & filters.user(OWNER_ID))
async def cancel_task(client, message):
    if len(message.command) < 2:
        return await message.reply_text(
            "Usage: <code>/cancel task_id</code> or click link in status."
        )

    task_id = message.command[1]
    status_key = f"task_status:{task_id}"

    # Check status in Redis
    data = await db_service.redis.hgetall(status_key)
    active_statuses = ["queued", "downloading", "uploading"]

    if not data or data.get("status") not in active_statuses:
        return await message.reply_text(
            f"❌ <b>Task <code>{task_id}</code></b> is not in an active state or doesn't exist."
        )

    # Set a Kill Flag in Redis
    await db_service.redis.set(f"kill_signal:{task_id}", "1", ex=300)

    # Update status in Redis so /status reflects it immediately
    await db_service.redis.hset(status_key, "status", "cancelling")

    # Release user slot
    await db_service.redis.srem(f"active_user_tasks:{message.from_user.id}", task_id)

    await message.reply_text(
        f"🛑 Cancel requested for <code>{task_id}</code>. User slot released."
    )


# Enables clicking /cancel_ID directly from the status message
@Client.on_message(filters.regex(r"^/cancel_([a-fA-F0-9]+)") & filters.user(OWNER_ID))
async def quick_cancel(client, message):
    task_id = message.matches[0].group(1)
    # Redirect to the main cancel logic
    message.command = ["cancel", task_id]
    await cancel_task(client, message)


# --- THE STATUS LOGIC (Shared by Command and Button) ---
async def build_status_text():
    """Generates a clean, professional view for /status and callback"""
    if not db_service.redis:
        return "❌ Redis Offline"

    keys = await db_service.redis.keys("task_status:*")
    active_lines = []

    for key in keys:
        data = await db_service.redis.hgetall(key)
        if not data:
            continue

        task_id = key.split(":")[-1]
        raw_status = data.get("status", "unknown") or "unknown"
        status = raw_status.upper()
        progress = data.get("progress", "0") or "0"
        name = data.get("name", "Unknown Content")

        # Only show truly active tasks
        # This hides 'CANCELLING', 'COMPLETED', and 'FAILED' from cluttering the list
        if status in ["QUEUED", "DOWNLOADING", "UPLOADING"]:
            # Better Progress Bar Logic
            try:
                prog_int = int(float(progress))
                filled = min(max(prog_int // 10, 0), 10)
                progress_bar = f"\n   └ <code>[{'■' * filled}{'□' * (10 - filled)}]</code> {prog_int}%"
            except:
                progress_bar = f" ({progress}%)"

            # Cleaner Labels (No double ID)
            # Format: ⚡ Content Name
            #           └ 🛠️ Status:
            #           └ 🆔 ID:
            #           └ 🛑 /cancel_task_id
            active_lines.append(
                f"⚡ <b>{name}</b>\n"
                f"   └ 🛠️ Status: <code>{status}</code>{progress_bar}\n"
                f"   └ 🆔 ID: <code>{task_id}</code\n"
                f"   └ 🛑 /cancel_{task_id}\n\n"
            )

    queue_items = await db_service.redis.lrange("queue:leech", 0, -1)
    pending_lines = []
    for i, item in enumerate(queue_items):
        parts = item.split("|")
        t_id = parts[0]
        # Robust name hint extraction
        n_hint = parts[4] if len(parts) > 4 and parts[4] else f"TMDB {parts[1]}"
        pending_lines.append(
            f"<code>{i+1}.</code> <b>{n_hint}</b> (ID: <code>{t_id}</code>)"
        )

    header = "🛰️ <b>Shadow Systems Status</b>\n" + ("—" * 15)
    active_section = "\n\n🔄 <b>ACTIVE TASKS</b>\n" + (
        "\n".join(active_lines) if active_lines else "_No active workers._"
    )
    queue_section = "\n\n⏳ <b>PENDING QUEUE</b>\n" + (
        "\n".join(pending_lines) if pending_lines else "_Queue is empty._"
    )
    footer = f"\n\n📊 <b>Total Pending:</b> <code>{len(queue_items)}</code>"

    return header + active_section + queue_section + footer


# --- 3. STATUS COMMAND HANDLER ---
@Client.on_message(filters.command("status") & filters.user(OWNER_ID))
async def status_cmd_handler(client, message):
    try:
        status_text = await build_status_text()
        await message.reply_text(status_text, quote=True)
    except Exception as e:
        await message.reply_text(f"❌ Status Error: {e}")


# --- 4. CALLBACK HANDLER ---
@Client.on_callback_query(filters.regex("check_status"))
async def status_callback_handler(client, callback_query):
    """Triggered when user clicks 'View Queue Status' button"""
    try:
        # Check if user is admin
        if callback_query.from_user.id != OWNER_ID:
            return await callback_query.answer("⛔ Access Denied", show_alert=True)

        status_text = await build_status_text()

        # Edit the existing message to show status
        try:
            await callback_query.message.edit_text(
                status_text,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔄 Refresh Status", callback_data="check_status"
                            )
                        ]
                    ]
                ),
            )
            # Answer the callback to remove the loading spinner
            await callback_query.answer("Status Updated")
        except Exception as edit_err:
            # Telegram throws error if you try to edit with EXACT same text
            if "MESSAGE_NOT_MODIFIED" in str(edit_err):
                await callback_query.answer("Already Up to date ✅")
            else:
                raise edit_err

    except Exception as e:
        logger.error(f"Callback Error: {e}")
        await callback_query.answer("⚠️ System Busy. Try again.")


@Client.on_callback_query(filters.regex("resume_all_tasks"))
async def resume_all_callback(client, callback_query):
    await callback_query.answer("♻️ Resuming tasks...")
    incompletes = await db_service.db.incomplete_tasks.find().to_list(length=100)

    resumed = 0
    failed_links = []

    for task in incompletes:
        payload = task["payload"]
        # Simple Link Validation (Check if it's a direct link that might have expired)
        task_id = payload.split("|")[0]
        url = payload.split("|")[2]
        logger.info(f"Resuming Task {task_id} for URL: {url}")

        # WZML-X Tip: We re-push to Redis.
        # If the link is expired, the worker will catch it during download.
        await db_service.redis.lpush("queue:leech", payload)
        await db_service.db.incomplete_tasks.delete_one({"_id": task["_id"]})
        resumed += 1

    msg = f"✅ <b>Recovery Complete</b>\nResumed <code>{resumed}</code> tasks."
    if failed_links:
        msg += f"\n\n⚠️ <b>Notice:</b> Some links might fail to download if they were temporary/expired."

    await callback_query.message.edit_text(msg)


@Client.on_callback_query(filters.regex("clear_incomplete_tasks"))
async def clear_incomplete_callback(client, callback_query):
    await db_service.db.incomplete_tasks.drop()
    await callback_query.answer("🗑️ All records cleared.", show_alert=True)
    await callback_query.message.delete()
