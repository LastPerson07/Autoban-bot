from pyrogram import Client
import os

class GuardianBot(Client):
    def __init__(self):
        super().__init__(
            name="guardian_bot",
            api_id=int(os.environ["API_ID"]),
            api_hash=os.environ["API_HASH"],
            bot_token=os.environ["BOT_TOKEN"],
            in_memory=True
        )

    async def start(self):
        await super().start()
        print("✅ GuardianBot started successfully")

    async def stop(self, *args):
        await super().stop()
        print("🛑 GuardianBot stopped")

if __name__ == "__main__":
    GuardianBot().run()
