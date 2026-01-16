# plugins/maintenance.py
from database import get_channel_settings
from config import Config

async def check_maintenance(chat_id: int, user_id: int) -> bool:
    """Return True if maintenance blocks the action (except for owner)"""
    settings = await get_channel_settings(chat_id)
    return settings["maintenance"] and user_id != Config.BOT_OWNER_ID