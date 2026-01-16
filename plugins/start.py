# plugins/start.py
import asyncio
from pyrogram import Client, filters, types
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config

INTRO_CAPTION = (
    "🛡️ <b>Guardian Bot</b>\n\n"
    "Premium protection for your Telegram channels & groups.\n"
    "• Rejoin-ban protection\n"
    "• Maintenance mode\n"
    "• Supervisor system\n\n"
    "Designed for channel owners & admins."
)

INTRO_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("ℹ About", callback_data="about")],
    [InlineKeyboardButton("📖 Help", callback_data="help")],
    [InlineKeyboardButton("⚙ Settings", callback_data="settings_noaccess")]
])

@Client.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, message: types.Message):
    if message.command and len(message.command) > 1:
        payload = message.command[1]
        if payload.startswith("panel_"):
            try:
                chat_id = int(payload[6:])
            except:
                await message.reply("Invalid link.")
                return
            from plugins.settings import show_settings_menu
            await show_settings_menu(client, message, chat_id)
            return
        
        # plugins/start.py (add these callbacks for About/Help)
@Client.on_callback_query(filters.regex(r"^(about|help)$"))
async def info_callbacks(client: Client, query: types.CallbackQuery):
    if query.data == "about":
        text = (
            "ℹ <b>About Guardian Bot</b>\n\n"
            "Premium channel/group protection bot.\n"
            "Built by Dhanpal\n"
            "Version 1.0"
        )
    else:
        text = (
            "📖 <b>Help</b>\n\n"
            "1. Add bot as admin with ban rights\n"
            "2. Use /panel in group to open settings\n"
            "3. Toggle features as needed"
        )
    buttons = [[InlineKeyboardButton("⬅ Back", callback_data="back_main")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    # Normal /start
    sticker = await message.reply_sticker(Config.WELCOME_STICKER)
    await asyncio.sleep(3)
    await sticker.delete()
    await message.reply_photo(
        Config.INTRO_PHOTO,
        caption=INTRO_CAPTION,
        reply_markup=INTRO_MARKUP
    )

@Client.on_message(filters.command("panel") & (filters.group | filters.channel))
async def panel_cmd(client: Client, message: types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status not in ("administrator", "creator"):
            return
    except:
        return

    me = await client.get_me()
    url = f"https://t.me/{me.username}?start=panel_{chat_id}"
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("⚙ Open Settings Panel", url=url)
    ]])
    await message.reply("Click to manage this channel/group settings:", reply_markup=markup)