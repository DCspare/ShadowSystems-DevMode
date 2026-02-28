# apps/worker-video/handlers/recovery_handler.py
import logging

from pyrogram import Client, filters

from shared.database import db_service
from shared.ext_utils.button_build import ButtonMaker

logger = logging.getLogger("RecoveryHandler")


@Client.on_callback_query(
    filters.regex(
        r"^(resume_all_tasks|clear_incomplete_tasks|select_incomplete_tasks)$"
    )
)
async def recovery_callbacks(client, callback_query):
    query = callback_query.data

    if query == "clear_incomplete_tasks":
        # 1. Get all task IDs from MongoDB before dropping it
        incompletes = await db_service.db.incomplete_tasks.find().to_list(length=100)

        # 2. Loop and delete corresponding Redis keys
        for task in incompletes:
            task_id = task["_id"]
            payload = task.get("payload", "")
            user_id = payload.split("|")[5] if "|" in payload else "0"

            await db_service.redis.delete(f"task_status:{task_id}")
            if user_id != "0":
                await db_service.redis.srem(f"active_user_tasks:{user_id}", task_id)

        # 3. Clear MongoDB
        await db_service.db.incomplete_tasks.drop()
        await callback_query.answer("🗑️ All records and live statuses cleared.", show_alert=True)
        return await callback_query.message.delete()

    if query == "resume_all_tasks":
        await callback_query.answer("♻️ Resuming all...")
        incompletes = await db_service.db.incomplete_tasks.find().to_list(length=100)
        resumed = 0
        for task in incompletes:
            await db_service.redis.lpush("queue:leech", task["payload"])
            await db_service.db.incomplete_tasks.delete_one({"_id": task["_id"]})
            resumed += 1
        await callback_query.message.edit_text(
            f"✅ <b>Successfully resumed {resumed} tasks.</b>\n<i>Note: If links were temporary/expired, the worker will log a 'Download Failed' error shortly.</i>"
        )

    if query == "select_incomplete_tasks":
        incompletes = await db_service.db.incomplete_tasks.find().to_list(length=100)
        if not incompletes:
            return await callback_query.answer("No tasks found!", show_alert=True)

        buttons = ButtonMaker()
        for task in incompletes:
            # Payload part 4 is the name_hint
            name = task["payload"].split("|")[4] or f"ID: {task['_id']}"
            buttons.data_button(f"📥 {name[:20]}", f"resume_single_{task['_id']}")

        buttons.data_button("🔙 Back", "back_to_recovery")
        await callback_query.message.edit_text(
            "<b>Select specific tasks to resume:</b>",
            reply_markup=buttons.build_menu(1),
        )


@Client.on_callback_query(filters.regex(r"^resume_single_(.+)$"))
async def resume_single_callback(client, callback_query):
    task_id = callback_query.matches[0].group(1)
    task = await db_service.db.incomplete_tasks.find_one({"_id": task_id})

    if task:
        await db_service.redis.lpush("queue:leech", task["payload"])
        await db_service.db.incomplete_tasks.delete_one({"_id": task_id})
        await callback_query.answer(f"✅ Resumed {task_id}")
        # Refresh the selection menu
        return await recovery_callbacks(client, callback_query)

    await callback_query.answer("Task no longer exists!", show_alert=True)


@Client.on_callback_query(filters.regex("back_to_recovery"))
async def back_to_recovery(client, callback_query):
    # This logic rebuilds the main menu from your worker.py reconciliation
    buttons = ButtonMaker()
    buttons.data_button("♻️ Resume All", "resume_all_tasks")
    buttons.data_button("🗑️ Clear All", "clear_incomplete_tasks")
    buttons.data_button("🔍 Select Tasks", "select_incomplete_tasks")
    await callback_query.message.edit_text(
        "🚩 <b>Recovery Menu</b>\n<i>What would you like to do?</i>",
        reply_markup=buttons.build_menu(2),
    )
