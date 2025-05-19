import threading
from typing import Dict, Any, Optional

import utilities as utils


class SyncChannelsCache:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SyncChannelsCache, cls).__new__(cls)
                    cls._instance.cache: Dict[int, Dict[str, Any]] = {}
                    # Maps LINE group IDs & Discord channel IDs to sub_nums
                    cls._instance.line_group_ids: Dict[str, int] = {}
                    cls._instance.discord_channel_ids: Dict[int, int] = {}
        return cls._instance

    def load_all_sync_channels(self):
        """Load all sync channels into cache."""
        sync_channels = utils.read_sync_channels()
        for entry in sync_channels:
            sub_num = entry['sub_num']
            self.cache[sub_num] = entry
            self.line_group_ids[entry['line_group_id']] = sub_num
            self.discord_channel_ids[entry['discord_channel_id']] = sub_num
        print(f"Successfully loaded {len(self.cache)} sync channels into cache.")

    def get_dc_webhook_by_line_group_id(self, line_group_id: str) -> Optional[str]:
        """Get Discord webhook by LINE group ID.

        :param str line_group_id: The LINE group ID to look up.
        :return: Discord webhook or None if not found.
        """
        sub_num = self.line_group_ids.get(line_group_id)
        if sub_num is None:
            return None
        return self.cache[sub_num]['discord_channel_webhook']

    def get_info_by_dc_channel_id(self, dc_channel_id: int) -> Optional[Dict[str, Any]]:
        """Get sync channel information by Discord channel ID.

        :param int dc_channel_id: The Discord channel ID to look up.
        :return: Dict with sync channel information or None if not found.
        """
        sub_num = self.discord_channel_ids.get(dc_channel_id)
        if sub_num is None:
            return None
        return self.cache[sub_num]

    def get_info_by_line_group_id(self, line_group_id: str) -> Optional[Dict[str, Any]]:
        """Get sync channel information by LINE group ID.

        :param str line_group_id: The LINE group ID to look up.
        :return: Dict with sync channel information or None if not found.
        """
        sub_num = self.line_group_ids.get(line_group_id)
        if sub_num is None:
            return None
        return self.cache[sub_num]

    def add_sync_channel(self, sub_num: int, folder_name: str, line_group_id: str,
                         line_group_name: str, discord_channel_id: int, discord_channel_name: str,
                         discord_channel_webhook: str):
        """Add a new sync channel to the cache."""
        self.cache[sub_num] = {
            'sub_num': sub_num,
            'folder_name': folder_name,
            'line_group_id': line_group_id,
            'line_group_name': line_group_name,
            'discord_channel_id': discord_channel_id,
            'discord_channel_name': discord_channel_name,
            'discord_channel_webhook': discord_channel_webhook
        }
        self.line_group_ids[line_group_id] = sub_num
        self.discord_channel_ids[discord_channel_id] = sub_num

    def remove_sync_channel(self, line_group_id: str = None, discord_channel_id: int = None):
        """Remove a sync channel from the cache."""
        if line_group_id:
            sub_num = self.line_group_ids.pop(line_group_id, None)
        elif discord_channel_id:
            sub_num = self.discord_channel_ids.pop(discord_channel_id, None)
        else:
            return

        if sub_num is not None:
            cache_entry = self.cache.get(sub_num)
            if cache_entry:
                self.line_group_ids.pop(cache_entry['line_group_id'], None)
                self.discord_channel_ids.pop(cache_entry['discord_channel_id'], None)
                self.cache.pop(sub_num, None)


# Create a global instance for easy importing
sync_channels_cache = SyncChannelsCache()
