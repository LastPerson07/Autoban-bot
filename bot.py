# bot.py (UPDATED - Fix for Render.com / Ephemeral Filesystem)
import asyncio
import logging
from pyrogram import Client
from config import Config
from database.db_handler import init_db_indexes

logging.basicConfig(
    level=Config.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class GuardianBot(Client):
    def __init__(self):
        super().__init__(
            name="guardian_bot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            plugins=dict(root="plugins"),
            in_memory=True  # ← THIS FIXES THE SQLITE ERROR ON RENDER
        )

    async def start(self):
        await super().start()
        await init_db_indexes()  # Ensure indexes on startup
        me = await self.get_me()
        logger.info(f"🛡️ Guardian Bot started: @{me.username}")

    async def stop(self, *args):
        logger.info("🛑 Guardian Bot stopping...")
        await super().stop(*args)

if __name__ == "__main__":
    GuardianBot().run()
