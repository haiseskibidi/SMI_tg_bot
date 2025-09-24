from __future__ import annotations

from typing import Any, Dict, Optional


class RegionCommands:
    def __init__(self, bot: "TelegramBot") -> None:
        self.bot = bot

    async def start_create_region_flow(self) -> None:
        await self.bot.region_manager.start_create_region_flow()

    async def handle_region_creation(self, region_input: str) -> None:
        await self.bot.region_manager.handle_region_creation(region_input)

    async def show_emoji_selection(self, region_name: str) -> None:
        from src.bot.regions.region_ui import RegionUI
        region_ui = RegionUI(self.bot)
        await region_ui.show_emoji_selection(region_name)

    async def handle_emoji_selection(self, emoji: str) -> None:
        from src.bot.regions.region_ui import RegionUI
        region_ui = RegionUI(self.bot)
        await region_ui.handle_emoji_selection(emoji)

    async def start_custom_emoji_input(self) -> None:
        from src.bot.regions.region_ui import RegionUI
        region_ui = RegionUI(self.bot)
        await region_ui.start_custom_emoji_input()

    async def handle_custom_emoji_input(self, emoji_input: str) -> None:
        from src.bot.regions.region_ui import RegionUI
        region_ui = RegionUI(self.bot)
        await region_ui.handle_custom_emoji_input(emoji_input)

    async def show_region_creation_confirmation(self, region_key: str, region_full_name: str, region_emoji: str, region_name: str) -> None:
        from src.bot.regions.region_ui import RegionUI
        region_ui = RegionUI(self.bot)
        await region_ui.show_region_creation_confirmation(region_key, region_full_name, region_emoji, region_name)

    async def create_region_confirmed(self, region_key: str) -> None:
        await self.bot.region_manager.create_region_confirmed(region_key)


