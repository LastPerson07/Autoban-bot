# helpers/filters.py
from pyrogram import filters
from config import Config

def is_owner():
    async def func(flt, client, update):
        return update.from_user and update.from_user.id == Config.BOT_OWNER_ID
    return filters.create(func)

owner_filter = is_owner()