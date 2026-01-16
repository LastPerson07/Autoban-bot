from dotenv import load_dotenv
import os
import logging

load_dotenv()  # This loads .env automatically


class Config:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    MONGO_URI = os.getenv("MONGO_URI", "")
    BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID"))

    INTRO_PHOTO = os.getenv("INTRO_PHOTO", "https://i.postimg.cc/26ZBtBZr/13.png ")
    WELCOME_STICKER = os.getenv("WELCOME_STICKER")


    LOG_LEVEL = logging.INFO  
