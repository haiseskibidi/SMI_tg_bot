from __future__ import annotations

from typing import Any, Dict, Optional
import asyncio
from datetime import datetime
import pytz


class ChannelCommands:
    def __init__(self, bot: "TelegramBot") -> None:
        self.bot = bot

    async def add_channel(self, message: Optional[Dict[str, Any]]) -> None:
        if not message:
            await self.bot.send_message("📝 Отправьте ссылку на канал в формате:\n<code>https://t.me/channel_name</code>")
            return
        text = message.get("text", "")
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            await self.bot.send_message(
                "❌ <b>Неверный формат команды</b>\n\n"
                "Используйте:\n"
                "• <code>/add_channel https://t.me/news_channel</code>\n"
                "• <code>/add_channel @news_channel</code>"
            )
            return
        channel_link = parts[1].strip()
        await self.bot.add_channel_handler(channel_link)

    async def force_subscribe(self, message: Optional[Dict[str, Any]]) -> None:
        try:
            await self.bot.send_message(
                "📡 <b>Принудительная подписка на каналы</b>\n\n"
                "🔄 Запускаю проверку и подписку на все каналы из конфигурации...\n"
                "⏳ Это может занять несколько минут..."
            )

            if not hasattr(self.bot, "main_instance") or not self.bot.main_instance:
                await self.bot.send_message("❌ Главный экземпляр системы недоступен")
                return
            if not hasattr(self.bot.main_instance, "telegram_monitor") or not self.bot.main_instance.telegram_monitor:
                await self.bot.send_message("❌ Telegram мониторинг недоступен")
                return

            self.bot.main_instance.clear_subscription_cache()
            if hasattr(self.bot.main_instance.telegram_monitor, "clear_cache"):
                await self.bot.main_instance.telegram_monitor.clear_cache()

            channels_data = await self.bot.get_channels_from_config()  # type: ignore[attr-defined]
            all_channels = channels_data.get("channels", [])
            if not all_channels:
                await self.bot.send_message("❌ Нет каналов для подписки в конфигурации")
                return

            await self.bot.send_message(f"📋 Найдено {len(all_channels)} каналов для проверки подписки")

            success_count = 0
            already_subscribed_count = 0
            failed_count = 0
            rate_limited_count = 0

            from telethon.tl.functions.channels import JoinChannelRequest

            for i, channel_config in enumerate(all_channels, 1):
                try:
                    username = channel_config.get("username", "")
                    if not username:
                        continue

                    entity = await self.bot.main_instance.telegram_monitor.get_channel_entity(username)
                    if not entity:
                        failed_count += 1
                        continue

                    already_joined = await self.bot.main_instance.telegram_monitor.is_already_joined(entity)
                    if already_joined:
                        already_subscribed_count += 1
                        self.bot.main_instance.add_channel_to_cache(username)
                    else:
                        try:
                            await self.bot.main_instance.telegram_monitor.client(JoinChannelRequest(entity))
                            success_count += 1
                            self.bot.main_instance.add_channel_to_cache(username)
                            await asyncio.sleep(3)
                        except Exception as sub_error:
                            error_msg = str(sub_error).lower()
                            if "wait" in error_msg and "seconds" in error_msg:
                                rate_limited_count += 1
                            elif "already" in error_msg or "участник" in error_msg:
                                already_subscribed_count += 1
                                self.bot.main_instance.add_channel_to_cache(username)
                            else:
                                failed_count += 1

                    if i % 10 == 0:
                        progress_text = (
                            f"🔄 <b>Прогресс: {i}/{len(all_channels)}</b>\n\n"
                            f"✅ Подписался: {success_count}\n"
                            f"💾 Уже подписан: {already_subscribed_count}\n"
                            f"⏳ Rate limit: {rate_limited_count}\n"
                            f"❌ Ошибки: {failed_count}"
                        )
                        await self.bot.send_message(progress_text)
                except Exception:
                    failed_count += 1

            final_report = (
                f"📡 <b>Принудительная подписка завершена!</b>\n\n"
                f"📊 <b>Результаты:</b>\n"
                f"✅ Успешно подписался: <b>{success_count}</b>\n"
                f"💾 Уже был подписан: <b>{already_subscribed_count}</b>\n"
                f"⏳ Rate limit: <b>{rate_limited_count}</b>\n"
                f"❌ Ошибки: <b>{failed_count}</b>\n\n"
                f"📋 Всего проверено: <b>{len(all_channels)}</b> каналов\n"
                f"🎉 Активных подписок: <b>{success_count + already_subscribed_count}</b>"
            )
            if rate_limited_count > 0:
                final_report += (
                    "\n\n💡 <b>Rate limit</b> - временное ограничение Telegram.\n"
                    "Повторите команду через несколько минут для повторной попытки."
                )
            await self.bot.send_message(final_report)
        except Exception as e:
            await self.bot.send_message(f"❌ Ошибка принудительной подписки: {e}")


