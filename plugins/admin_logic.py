# plugins/admin_logic.py (FULL UPDATED VERSION)
import asyncio
from pyrogram import Client, filters, types
from database import (
    get_channel_settings, increment_stat,
    record_join, get_and_clear_join_time,
    is_hitrun_leaver, flag_as_hitrun, log_action
)

@Client.on_chat_member_updated()
async def handle_member_updates(client: Client, update: types.ChatMemberUpdated):
    if update.chat.type not in ("supergroup", "channel"):
        return

    chat_id = update.chat.id
    settings = await get_channel_settings(chat_id)

    # Skip all protection if maintenance mode
    if settings.get("maintenance", False):
        return

    old = update.old_chat_member
    new = update.new_chat_member

    if not old or not new:
        return

    user = new.user or old.user
    if user.is_bot or user.id == (await client.get_me()).id:
        return

    anti_hitrun = settings.get("anti_hitrun", False)

    # === JOIN DETECTION ===
    was_not_member = old.status not in ("member", "administrator", "creator")
    now_member = new.status in ("member", "administrator")

    if now_member and was_not_member:
        await increment_stat(chat_id, "joins")

        if anti_hitrun:
            # If already flagged → ban immediately
            if await is_hitrun_leaver(chat_id, user.id):
                try:
                    await client.ban_chat_member(chat_id, user.id)
                    await increment_stat(chat_id, "bans")
                    await log_action(
                        chat_id,
                        "anti_hitrun_ban",
                        f"Banned flagged hit-and-run user {user.id} ({user.first_name or 'Unknown'}) on join"
                    )
                except Exception as e:
                    await log_action(chat_id, "error", f"Failed ban on join {user.id}: {e}")
            else:
                # Record fresh join time
                await record_join(chat_id, user.id)

    # === VOLUNTARY LEAVE DETECTION ===
    was_member = old.status in ("member", "administrator")
    now_left_voluntarily = new.status == "left"  # Only voluntary leaves trigger flag

    if was_member and now_left_voluntarily and anti_hitrun:
        join_time = await get_and_clear_join_time(chat_id, user.id)
        if join_time:
            time_spent = datetime.now(timezone.utc) - join_time
            if time_spent < timedelta(minutes=5):  # "few minutes" = 5 minutes
                await flag_as_hitrun(chat_id, user.id)
                await log_action(
                    chat_id,
                    "anti_hitrun_flag",
                    f"Flagged {user.id} ({user.first_name or 'Unknown'}) for hit-and-run (stayed {time_spent})"
                )

@Client.on_my_chat_member()
async def welcome_on_add(client: Client, update: types.ChatMemberUpdated):
    if update.new_chat_member.status in ("administrator", "member"):
        try:
            await client.send_message(
                update.chat.id,
                "🛡️ <b>Guardian Bot added!</b>\n\n"
                "• Anti Hit-and-Run protection\n"
                "• Maintenance mode\n"
                "• Supervisor system\n\n"
                "Use /panel in this group to open settings (admins only).",
                disable_web_page_preview=True
            )
        except:
            pass