from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime
import pytz


class ManagementCommands:
    def __init__(self, bot: "TelegramBot") -> None:
        self.bot = bot

    async def manage_channels(self, message: Optional[Dict[str, Any]]) -> None:
        try:
            channels_data = await self.bot.get_all_channels_grouped()
            
            if not channels_data:
                keyboard = [
                    [{"text": "➕ Добавить первый канал", "callback_data": "add_channel"}],
                    [{"text": "🏠 Главное меню", "callback_data": "start"}]
                ]
                
                chat_id = message.get("chat", {}).get("id") if message else self.bot.admin_chat_id
                to_group = self.bot.is_message_from_group(chat_id) if chat_id else None
                
                await self.bot.send_message_with_keyboard(
                    "📂 <b>Управление каналами</b>\n\n"
                    "❌ Каналы не найдены\n\n"
                    "Добавьте первый канал для мониторинга!",
                    keyboard,
                    use_reply_keyboard=False,
                    to_group=to_group
                )
                return
            
            await self.bot.channel_callbacks.show_channels_management(channels_data, message)
            
        except Exception as e:
            await self.bot.send_message(f"❌ Ошибка получения списка каналов: {e}")

    async def stats(self, message: Optional[Dict[str, Any]]) -> None:
        try:
            if not self.bot.monitor_bot or not self.bot.monitor_bot.database:
                await self.bot.send_message("❌ База данных недоступна")
                return
            
            stats = await self.bot.monitor_bot.database.get_today_stats()
            
            stats_text = (
                "📈 <b>Статистика за сегодня</b>\n\n"
                f"📰 Всего сообщений: <b>{stats['total_messages']}</b>\n"
                f"📤 Отобрано: <b>{stats['selected_messages']}</b>\n"
                f"📊 Процент отбора: <b>{(stats['selected_messages'] / max(stats['total_messages'], 1) * 100):.1f}%</b>\n\n"
                f"🕐 Последнее обновление: {datetime.now(pytz.timezone('Asia/Vladivostok')).strftime('%d.%m.%Y %H:%M:%S')}"
            )
            
            keyboard = [
                [
                    {"text": "📊 Статус", "callback_data": "status"},
                    {"text": "🗂️ Управление каналами", "callback_data": "manage_channels"}
                ],
                [{"text": "🏠 Главное меню", "callback_data": "start"}]
            ]
            
            chat_id = message.get("chat", {}).get("id") if message else self.bot.admin_chat_id
            to_group = self.bot.is_message_from_group(chat_id) if chat_id else None
            await self.bot.send_message_with_keyboard(stats_text, keyboard, use_reply_keyboard=False, to_group=to_group)
            
        except Exception as e:
            await self.bot.send_message(f"❌ Ошибка получения статистики: {e}")

    async def settings(self, message: Optional[Dict[str, Any]]) -> None:
        delete_status = "🟢 Включено" if self.bot.delete_commands else "🔴 Выключено"
        edit_status = "🟢 Включено" if self.bot.edit_messages else "🔴 Выключено"
        
        settings_text = (
            "⚙️ <b>Настройки интерфейса</b>\n\n"
            f"🗑️ <b>Удаление команд:</b> {delete_status}\n"
            f"📝 <b>Редактирование сообщений:</b> {edit_status}\n\n"
            "🔧 <b>Описание:</b>\n"
            "• <b>Удаление команд</b> - автоматически удалять ваши команды и нажатия кнопок\n"
            "• <b>Редактирование сообщений</b> - обновлять существующие сообщения вместо создания новых\n\n"
            "💡 <b>Рекомендация:</b> Включите удаление команд для чистоты чата"
        )
        
        keyboard = [
            [
                {"text": f"🗑️ Удаление: {delete_status}", "callback_data": "toggle_delete"},
                {"text": f"📝 Редактирование: {edit_status}", "callback_data": "toggle_edit"}
            ],
            [{"text": "🏠 Главное меню", "callback_data": "start"}]
        ]
        
        chat_id = message.get("chat", {}).get("id") if message else self.bot.admin_chat_id
        to_group = self.bot.is_message_from_group(chat_id) if chat_id else None
        await self.bot.send_message_with_keyboard(settings_text, keyboard, use_reply_keyboard=False, to_group=to_group)

