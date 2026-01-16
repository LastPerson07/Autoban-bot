# plugins/settings.py
import asyncio
from pyrogram import Client, filters, types
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import (
    get_channel_settings, update_setting, add_supervisor,
    remove_supervisor, is_supervisor, log_action
)
from config import Config
from plugins.maintenance import check_maintenance

# Global pending for supervisor add (user_id -> chat_id)
pending_supervisor_add = {}

MAIN_MENU_TEXT = (
    "🛡️ <b>Guardian Bot</b>\n\n"
    "Premium protection for your Telegram channels & groups.\n"
    "• Anti Hit-and-Run protection\n"
    "• Maintenance mode\n"
    "• Supervisor system\n\n"
    "Designed for channel owners & admins."
)

MAIN_MENU_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("ℹ About", callback_data="about")],
    [InlineKeyboardButton("📖 Help", callback_data="help")],
    [InlineKeyboardButton("⚙ Settings", callback_data="settings_noaccess")]
])

async def has_access(client: Client, chat_id: int, user_id: int) -> tuple[bool, bool]:
    """Returns (has_access, is_admin)"""
    if user_id == Config.BOT_OWNER_ID:
        return True, True
    try:
        member = await client.get_chat_member(chat_id, user_id)
        is_admin = member.status in ("creator", "administrator")
        is_sup = await is_supervisor(chat_id, user_id)
        return (is_admin or is_sup), is_admin
    except:
        return False, False

async def show_settings_menu(client: Client, message_or_query, chat_id: int):
    user_id = (message_or_query.from_user.id if hasattr(message_or_query, "from_user") else message_or_query.from_user.id)
    has_acc, is_admin = await has_access(client, chat_id, user_id)
    if not has_acc:
        text = "❌ You don't have access to manage this channel."
        if isinstance(message_or_query, types.Message):
            await message_or_query.reply(text)
        else:
            await message_or_query.message.edit_text(text)
        return

    if await check_maintenance(chat_id, user_id):
        if hasattr(message_or_query, "answer"):
            await message_or_query.answer("🛠 Bot is under maintenance", show_alert=True)
        return

    settings = await get_channel_settings(chat_id)
    chat = await client.get_chat(chat_id)

    title = chat.title or "Unknown"
    status_hitrun = "ON" if settings.get("anti_hitrun", False) else "OFF"
    status_maint = "ON" if settings["maintenance"] else "OFF"
    sup_count = len(settings["supervisors"])

    buttons = [
        [InlineKeyboardButton(f"🔒 Anti Hit-and-Run: {status_hitrun}", callback_data=f"toggle_hitrun_{chat_id}")],
        [InlineKeyboardButton(f"🛠 Maintenance: {status_maint}", callback_data=f"toggle_maint_{chat_id}")],
        [InlineKeyboardButton(f"👮 Supervisors: {sup_count}", callback_data=f"sup_list_{chat_id}")],
        [InlineKeyboardButton("📊 Stats", callback_data=f"stats_{chat_id}")],
        [InlineKeyboardButton("⬅ Back", callback_data="back_main")]
    ]
    if not is_admin:
        # Supervisors can't toggle features
        buttons = buttons[2:]

    markup = InlineKeyboardMarkup(buttons)

    text = (
        f"⚙ <b>Settings for {title}</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"🔒 Anti Hit-and-Run: {status_hitrun}\n"
        f"🛠 Maintenance: {status_maint}\n"
        f"👮 Supervisors: {sup_count}\n"
    )

    if isinstance(message_or_query, types.Message):
        await message_or_query.reply(text, reply_markup=markup)
    else:
        await message_or_query.message.edit_text(text, reply_markup=markup)

@Client.on_callback_query(filters.regex(r"^(back_main|settings_noaccess|toggle_hitrun_|toggle_maint_|sup_|stats_|settings_menu_)"))
async def settings_callbacks(client: Client, query: types.CallbackQuery):
    data = query.data

    # Special cases without chat_id
    if data == "settings_noaccess":
        await query.answer("Add me as admin to a group/channel and use /panel there.", show_alert=True)
        return

    if data == "back_main":
        await query.message.edit_text(MAIN_MENU_TEXT, reply_markup=MAIN_MENU_MARKUP)
        return

    # Extract chat_id (and target_id for remove)
    parts = data.split("_")
    if "sup_rem_" in data:
        try:
            chat_id = int(parts[-2])
            target_id = int(parts[-1])
        except ValueError:
            return
    else:
        try:
            chat_id = int(parts[-1])
        except ValueError:
            return

    user_id = query.from_user.id

    # Maintenance & access check (for all actions except pure view)
    if await check_maintenance(chat_id, user_id):
        await query.answer("🛠 Under maintenance", show_alert=True)
        return

    has_acc, is_admin = await has_access(client, chat_id, user_id)
    if not has_acc:
        await query.answer("❌ No access", show_alert=True)
        return

    settings = await get_channel_settings(chat_id)

    # Toggle Anti Hit-and-Run
    if data.startswith("toggle_hitrun_"):
        if not is_admin:
            await query.answer("Admins only", show_alert=True)
            return
        new_val = not settings.get("anti_hitrun", False)
        await update_setting(chat_id, "anti_hitrun", new_val)
        await log_action(chat_id, "toggle_anti_hitrun", f"Toggled to {new_val} by {user_id}")
        await show_settings_menu(client, query, chat_id)
        return

    # Toggle Maintenance
    if data.startswith("toggle_maint_"):
        if not is_admin:
            await query.answer("Admins only", show_alert=True)
            return
        new_val = not settings["maintenance"]
        await update_setting(chat_id, "maintenance", new_val)
        await log_action(chat_id, "toggle_maintenance", f"Toggled to {new_val} by {user_id}")
        await show_settings_menu(client, query, chat_id)
        return

    # Add Supervisor (just alert + pending)
    if data.startswith("sup_add_"):
        if not (is_admin or user_id == Config.BOT_OWNER_ID):
            await query.answer("Admins only", show_alert=True)
            return
        pending_supervisor_add[user_id] = chat_id
        await query.answer("Forward any message from the user you want to add as supervisor.", show_alert=True)
        return

    # Remove Supervisor
    if data.startswith("sup_rem_"):
        if not (is_admin or user_id == Config.BOT_OWNER_ID):
            await query.answer("Admins only", show_alert=True)
            return
        removed = await remove_supervisor(chat_id, target_id)
        await log_action(chat_id, "remove_supervisor", f"Removed {target_id} by {user_id}")
        await query.answer("Removed" if removed else "Failed", show_alert=True)
        await show_supervisors(client, query, chat_id)
        return

    # Show Supervisors list
    if data.startswith("sup_list_"):
        await show_supervisors(client, query, chat_id)
        return

    # Show Stats
    if data.startswith("stats_"):
        await show_stats(client, query, chat_id)
        return

    # Back to main settings menu (from sub-menus)
    if data.startswith("settings_menu_"):
        await show_settings_menu(client, query, chat_id)
        return

async def show_supervisors(client: Client, query: types.CallbackQuery, chat_id: int):
    user_id = query.from_user.id
    has_acc, is_admin = await has_access(client, chat_id, user_id)
    if not has_acc:
        await query.answer("No access", show_alert=True)
        return

    settings = await get_channel_settings(chat_id)
    supervisors = settings["supervisors"]

    buttons = []
    if is_admin or user_id == Config.BOT_OWNER_ID:
        buttons.append([InlineKeyboardButton("➕ Add Supervisor", callback_data=f"sup_add_{chat_id}")])

    for sup_id in supervisors[:20]:
        try:
            user = await client.get_users(sup_id)
            name = user.first_name or "Unknown"
        except:
            name = str(sup_id)
        buttons.append([InlineKeyboardButton(f"❌ Remove {name}", callback_data=f"sup_rem_{chat_id}_{sup_id}")])

    buttons.append([InlineKeyboardButton("⬅ Back", callback_data=f"settings_menu_{chat_id}")])
    markup = InlineKeyboardMarkup(buttons)

    text = f"👮 <b>Supervisors ({len(supervisors)})</b>\n\nSupervisors can view stats only."
    await query.message.edit_text(text, reply_markup=markup)

async def show_stats(client: Client, query: types.CallbackQuery, chat_id: int):
    settings = await get_channel_settings(chat_id)
    stats = settings["stats"]
    text = (
        f"📊 <b>Channel Stats</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"Joins: {stats['joins']}\n"
        f"Bans: {stats['bans']}\n"
        f"Maintenance hits: {stats['maintenance_hits']}"
    )
    buttons = [[InlineKeyboardButton("⬅ Back", callback_data=f"settings_menu_{chat_id}")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# Forwarded message handler for adding supervisor
@Client.on_message(filters.private & filters.forwarded)
async def handle_forwarded_for_sup(client: Client, message: types.Message):
    user_id = message.from_user.id
    if user_id not in pending_supervisor_add:
        return

    chat_id = pending_supervisor_add.pop(user_id)
    target = message.forward_from
    if not target or target.is_bot:
        await message.reply("Invalid forwarded user.")
        return

    added = await add_supervisor(chat_id, target.id)
    if added:
        await message.reply(f"✅ {target.first_name} added as supervisor!")
        await log_action(chat_id, "add_supervisor", f"Added {target.id} by {user_id}")
    else:
        await message.reply("Already a supervisor or error.")