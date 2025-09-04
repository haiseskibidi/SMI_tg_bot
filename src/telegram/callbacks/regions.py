from __future__ import annotations

from typing import Any, Dict, Optional


class RegionCallbacks:
    def __init__(self, bot: "TelegramBot") -> None:
        self.bot = bot

    async def handle_region_selection(self, region: str) -> None:
        await self.bot.handle_region_selection(region)

    async def handle_bulk_region_selection(self, region: str) -> None:
        await self.bot.handle_bulk_region_selection(region)

    async def start_create_region_flow(self) -> None:
        await self.bot.start_create_region_flow()

    async def handle_emoji_selection(self, emoji: str) -> None:
        await self.bot.handle_emoji_selection(emoji)

    async def start_custom_emoji_input(self) -> None:
        await self.bot.start_custom_emoji_input()

    async def create_region_confirmed(self, region_key: str) -> None:
        await self.bot.create_region_confirmed(region_key)

    async def auto_add_topic_to_config(self, region_key: str) -> None:
        await self.bot.auto_add_topic_to_config(region_key)

    async def cancel_region_actions(self) -> None:
        self.bot.pending_channel_url = None
        self.bot.waiting_for_region_name = False
        self.bot.waiting_for_emoji = False
        self.bot.pending_region_data = None
        self.bot.pending_topic_data = None
        callback_message = {"message": {"chat": {"id": self.bot.current_callback_chat_id}}}
        await self.bot.basic_commands.start(callback_message)


