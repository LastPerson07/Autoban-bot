# database/db_handler.py
import logging
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

logger = logging.getLogger(__name__)

client = AsyncIOMotorClient(Config.MONGO_URI)
db = client["guardian_bot"]
channels_col = db["channels"]
logs_col = db["action_logs"]
leavers_col = db["recent_leavers"]

DEFAULT_SETTINGS = {
    "rejoin_ban": False,
    "maintenance": False,
    "supervisors": [],
    "stats": {"joins": 0, "bans": 0, "maintenance_hits": 0},
}

async def init_db_indexes():
    try:
        await channels_col.create_index("chat_id", unique=True)
        await channels_col.create_index("supervisors")
        await logs_col.create_index("timestamp", expireAfterSeconds=90 * 24 * 3600)
        await leavers_col.create_index([("chat_id", 1), ("user_id", 1)], unique=True)
        await leavers_col.create_index("leave_time", expireAfterSeconds=86400)  # 24h
        logger.info("✅ DB indexes created")
    except Exception as e:
        logger.error(f"❌ Index creation error: {e}")

async def get_channel_settings(chat_id: int) -> dict:
    try:
        doc = await channels_col.find_one({"chat_id": chat_id})
        if not doc:
            doc = {
                "chat_id": chat_id,
                "added_on": datetime.now(timezone.utc),
                **DEFAULT_SETTINGS
            }
            await channels_col.insert_one(doc)
            logger.info(f"🆕 Registered channel: {chat_id}")
        return doc
    except Exception as e:
        logger.error(f"❌ Settings fetch error {chat_id}: {e}")
        return {"chat_id": chat_id, "added_on": datetime.now(timezone.utc), **DEFAULT_SETTINGS}
    
# database/db_handler.py (FULL UPDATED VERSION)
import logging
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

logger = logging.getLogger(__name__)

client = AsyncIOMotorClient(Config.MONGO_URI)
db = client["guardian_bot"]
channels_col = db["channels"]
logs_col = db["action_logs"]
active_members_col = db["active_members"]      # Tracks current members' join time
hitrun_leavers_col = db["hitrun_leavers"]      # Permanent flag for hit-and-run leavers

DEFAULT_SETTINGS = {
    "anti_hitrun": False,       # RENAMED from rejoin_ban to reflect new logic
    "maintenance": False,
    "supervisors": [],
    "stats": {"joins": 0, "bans": 0, "maintenance_hits": 0},
}

async def init_db_indexes():
    try:
        await channels_col.create_index("chat_id", unique=True)
        await channels_col.create_index("supervisors")
        await logs_col.create_index("timestamp", expireAfterSeconds=90 * 24 * 3600)
        
        # New collections
        await active_members_col.create_index([("chat_id", 1), ("user_id", 1)], unique=True)
        await hitrun_leavers_col.create_index([("chat_id", 1), ("user_id", 1)], unique=True)
        
        logger.info("✅ DB indexes created")
    except Exception as e:
        logger.error(f"❌ Index creation error: {e}")

async def get_channel_settings(chat_id: int) -> dict:
    try:
        doc = await channels_col.find_one({"chat_id": chat_id})
        if not doc:
            doc = {
                "chat_id": chat_id,
                "added_on": datetime.now(timezone.utc),
                **DEFAULT_SETTINGS
            }
            await channels_col.insert_one(doc)
            logger.info(f"🆕 Registered channel: {chat_id}")
        
        # Backward compatibility: migrate old "rejoin_ban" to "anti_hitrun"
        if "rejoin_ban" in doc and "anti_hitrun" not in doc:
            doc["anti_hitrun"] = doc.pop("rejoin_ban")
            await channels_col.update_one({"chat_id": chat_id}, {"$set": doc})
        
        return doc
    except Exception as e:
        logger.error(f"❌ Settings fetch error {chat_id}: {e}")
        return {"chat_id": chat_id, "added_on": datetime.now(timezone.utc), **DEFAULT_SETTINGS}

# === Existing functions unchanged (update_setting, increment_stat, supervisors, etc.) ===
# ... (keep all your existing functions like update_setting, increment_stat, add_supervisor, etc.)

# === New functions for Anti Hit-and-Run ===
async def record_join(chat_id: int, user_id: int):
    """Record when a user joins (or rejoins)"""
    try:
        await active_members_col.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$set": {"join_time": datetime.now(timezone.utc)}},
            upsert=True
        )
    except Exception as e:
        logger.error(f"❌ Record join failed {chat_id}/{user_id}: {e}")

async def get_and_clear_join_time(chat_id: int, user_id: int) -> datetime | None:
    """Get join time and remove record (on leave)"""
    try:
        doc = await active_members_col.find_one_and_delete(
            {"chat_id": chat_id, "user_id": user_id}
        )
        return doc["join_time"] if doc else None
    except Exception as e:
        logger.error(f"❌ Clear join time failed {chat_id}/{user_id}: {e}")
        return None

async def is_hitrun_leaver(chat_id: int, user_id: int) -> bool:
    """Check if user is flagged for hit-and-run"""
    try:
        return await hitrun_leavers_col.count_documents(
            {"chat_id": chat_id, "user_id": user_id}, limit=1
        ) > 0
    except Exception:
        return False

async def flag_as_hitrun(chat_id: int, user_id: int):
    """Permanently flag user (ignore duplicates due to unique index)"""
    try:
        await hitrun_leavers_col.insert_one({
            "chat_id": chat_id,
            "user_id": user_id,
            "flagged_on": datetime.now(timezone.utc)
        })
    except Exception as e:
        if "duplicate key" not in str(e).lower():
            logger.error(f"❌ Flag hitrun failed {chat_id}/{user_id}: {e}")

# === Keep get_all_channels, get_global_stats, log_action ===

async def update_setting(chat_id: int, key: str, value):
    try:
        await channels_col.update_one(
            {"chat_id": chat_id},
            {"$set": {key: value}},
            upsert=True
        )
    except Exception as e:
        logger.error(f"❌ Update error {key} {chat_id}: {e}")
    

async def increment_stat(chat_id: int, field: str):
    if field not in {"joins", "bans", "maintenance_hits"}:
        return
    try:
        await channels_col.update_one(
            {"chat_id": chat_id},
            {"$inc": {f"stats.{field}": 1}},
            upsert=True
        )
    except Exception as e:
        logger.error(f"❌ Increment error {field} {chat_id}: {e}")

async def add_supervisor(chat_id: int, user_id: int) -> bool:
    try:
        result = await channels_col.update_one(
            {"chat_id": chat_id},
            {"$addToSet": {"supervisors": user_id}},
            upsert=True
        )
        return bool(result.modified_count or result.upserted_id)
    except Exception as e:
        logger.error(f"❌ Add supervisor error: {e}")
        return False

async def remove_supervisor(chat_id: int, user_id: int) -> bool:
    try:
        result = await channels_col.update_one(
            {"chat_id": chat_id},
            {"$pull": {"supervisors": user_id}}
        )
        return bool(result.modified_count)
    except Exception as e:
        logger.error(f"❌ Remove supervisor error: {e}")
        return False

async def is_supervisor(chat_id: int, user_id: int) -> bool:
    try:
        return await channels_col.count_documents(
            {"chat_id": chat_id, "supervisors": user_id}, limit=1
        ) > 0
    except Exception:
        return False

async def record_leave(chat_id: int, user_id: int):
    try:
        await leavers_col.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$set": {"leave_time": datetime.now(timezone.utc)}},
            upsert=True
        )
    except Exception as e:
        logger.error(f"❌ Record leave error: {e}")

async def is_recent_rejoin(chat_id: int, user_id: int) -> bool:
    try:
        doc = await leavers_col.find_one({"chat_id": chat_id, "user_id": user_id})
        if doc:
            if (datetime.now(timezone.utc) - doc["leave_time"]) < timedelta(minutes=30):
                await leavers_col.delete_one({"chat_id": chat_id, "user_id": user_id})
                return True
        return False
    except Exception as e:
        logger.error(f"❌ Rejoin check error: {e}")
        return False

async def get_all_channels():
    try:
        return await channels_col.find().to_list(None)
    except Exception as e:
        logger.error(f"❌ All channels fetch error: {e}")
        return []

async def get_global_stats() -> dict:
    try:
        pipeline = [{"$group": {
            "_id": None,
            "total_channels": {"$sum": 1},
            "total_joins": {"$sum": "$stats.joins"},
            "total_bans": {"$sum": "$stats.bans"},
            "total_maintenance_hits": {"$sum": "$stats.maintenance_hits"}
        }}]
        result = await channels_col.aggregate(pipeline).to_list(1)
        return result[0] if result else {"total_channels": 0, "total_joins": 0, "total_bans": 0, "total_maintenance_hits": 0}
    except Exception as e:
        logger.error(f"❌ Global stats error: {e}")
        return {}

async def log_action(chat_id: int, action_type: str, details: str):
    try:
        await logs_col.insert_one({
            "chat_id": chat_id,
            "action": action_type,
            "details": details,
            "timestamp": datetime.now(timezone.utc)
        })
    except Exception as e:
        logger.error(f"❌ Log error: {e}")