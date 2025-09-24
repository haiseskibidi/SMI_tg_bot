from typing import Dict, Optional, Any
from loguru import logger


class DigestInterface:
    
    def __init__(self, bot: "TelegramBot"):
        self.bot = bot
    
    async def show_digest_menu(self):
        try:
            text = (
                "📰 <b>Генерация дайджеста новостей</b>\n\n"
                "Выберите период для дайджеста:"
            )
            
            keyboard = [
                [{"text": "📅 За 3 дня", "callback_data": "digest_period_3"}],
                [{"text": "📅 За неделю", "callback_data": "digest_period_7"}], 
                [{"text": "📅 За 2 недели", "callback_data": "digest_period_14"}],
                [{"text": "🔗 Ввести ссылку на канал", "callback_data": "digest_channel_link"}],
                [{"text": "🏠 Главное меню", "callback_data": "start"}]
            ]
            
            await self.bot.keyboard_builder.send_message_with_keyboard(
                text, keyboard, use_reply_keyboard=False
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа меню дайджеста: {e}")
    
    async def handle_period_selection(self, days: int):
        try:
            await self.bot.send_message(f"📰 Генерируем дайджест за {days} дней...")
            
            if hasattr(self.bot.basic_commands, 'digest_generator') and self.bot.basic_commands.digest_generator:
                digest_result = await self.bot.basic_commands.digest_generator.generate_weekly_digest(days=days)
                await self.bot.send_message(digest_result)
            else:
                await self.bot.send_message("❌ Генератор дайджестов недоступен")
                
        except Exception as e:
            logger.error(f"❌ Ошибка генерации дайджеста: {e}")
            await self.bot.send_message(f"❌ Ошибка генерации дайджеста: {e}")
    
    async def handle_channel_link_request(self):
        await self.bot.send_message(
            "🔗 <b>Дайджест конкретного канала</b>\n\n" 
            "Отправьте ссылку на канал для live-анализа:\n"
            "• <code>https://t.me/channel_name</code>\n"
            "• <code>@channel_name</code>"
        )