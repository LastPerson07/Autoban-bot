# plugins/owner.py
from pyrogram import Client, filters, types
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_all_channels, get_global_stats, log_action
from config import Config
from helpers.filters import owner_filter

@Client.on_message(filters.command("dhanpal") & filters.private & owner_filter)
async def owner_menu(client: Client, message: types.Message):
    stats = await get_global_stats()
    text = (
        "👑 <b>Owner Panel</b>\n"
        f"Total channels: {stats['total_channels']}\n"
        f"Total joins: {stats['total_joins']}\n"
        f"Total bans: {stats['total_bans']}"
    )
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("📋 List Channels", callback_data="owner_channels")
    ]])
    await message.reply(text, reply_markup=markup)

@Client.on_callback_query(filters.regex("^owner_") & owner_filter)
async def owner_callbacks(client: Client, query: types.CallbackQuery):
    if query.data == "owner_channels":
        channels = await get_all_channels()
        text = "📋 <b>Connected Channels</b>\n\n"
        for ch in channels[:20]:
            try:
                chat = await client.get_chat(ch["chat_id"])
                title = chat.title or "No title"
                username = f"@{chat.username}" if chat.username else ""
                text += f"• {title} {username} (ID: {ch['chat_id']})\n"
            except:
                text += f"• ID: {ch['chat_id']} (inaccessible)\n"
        buttons = [[InlineKeyboardButton("⬅ Back", callback_data="owner_back")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))