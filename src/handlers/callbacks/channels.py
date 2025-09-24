from __future__ import annotations

from typing import Any, Dict, Optional


class ChannelCallbacks:
    def __init__(self, bot: "TelegramBot") -> None:
        self.bot = bot

    async def show_channels_management(self, channels_data: Dict[str, Any], message: Optional[Dict[str, Any]] = None) -> None:
        from src.bot.channels.channel_ui import ChannelUI
        channel_ui = ChannelUI(self.bot)
        await channel_ui.show_channels_management(channels_data, message)

    async def show_region_channels(self, region_key: str, page: int = 1) -> None:
        from src.bot.channels.channel_ui import ChannelUI
        channel_ui = ChannelUI(self.bot)
        await channel_ui.show_region_channels(region_key, page)

    async def show_delete_confirmation(self, region_key: str, username: str) -> None:
        from src.bot.channels.channel_ui import ChannelUI
        channel_ui = ChannelUI(self.bot)
        await channel_ui.show_delete_confirmation(region_key, username)

    async def delete_channel_from_config(self, region_key: str, username: str) -> bool:
        return await self.bot.channel_manager.delete_channel_from_config(region_key, username)


