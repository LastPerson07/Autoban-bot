# database/__init__.py
from .db_handler import (
    get_channel_settings, update_setting, increment_stat,
    add_supervisor, remove_supervisor, is_supervisor,
    record_leave, is_recent_rejoin,
    get_all_channels, get_global_stats, log_action
)