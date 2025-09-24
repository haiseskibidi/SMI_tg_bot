from .core.bot_client import TelegramBot
from typing import Dict, Optional
from loguru import logger


async def create_bot_from_config(config: Dict, monitor_bot=None) -> Optional[TelegramBot]:
    try:
        bot_config = config.get('bot')
        if not bot_config:
            logger.warning("⚠️ Конфигурация бота не найдена")
            return None
        
        token = bot_config.get('token')
        admin_chat_id = bot_config.get('chat_id')
        group_chat_id = bot_config.get('group_chat_id')
        
        if not token or not admin_chat_id:
            logger.error("❌ Не указан токен бота или chat_id")
            return None
        
        bot = TelegramBot(token, admin_chat_id, group_chat_id, monitor_bot)
        
        if await bot.test_connection():
            return bot
        else:
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка создания бота: {e}")
        return None


__all__ = ["TelegramBot", "create_bot_from_config"]

