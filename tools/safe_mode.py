#!/usr/bin/env python3
"""
🛡️ Безопасный режим - система без мониторинга каналов
Только уведомления + ручное добавление новостей
"""

import asyncio
from src.telegram_bot import TelegramBot
from src.database import DatabaseManager
import yaml
from loguru import logger

async def run_safe_mode():
    """Запуск в безопасном режиме"""
    
    print("🛡️ БЕЗОПАСНЫЙ РЕЖИМ - без мониторинга каналов")
    print("=" * 50)
    
    # Загружаем конфигурацию
    with open('../config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Инициализируем компоненты
    db = DatabaseManager("news_monitor.db")
    await db.initialize()
    
    bot = TelegramBot(
        token=config['bot']['token'],
        chat_id=config['bot']['chat_id']
    )
    
    # Тестируем бота
    if await bot.test_connection():
        print("✅ Telegram бот работает")
        
        # Отправляем тестовое сообщение
        await bot.send_message("🛡️ Система запущена в БЕЗОПАСНОМ РЕЖИМЕ\n\n✅ Мониторинг каналов ОТКЛЮЧЕН\n📱 Уведомления работают\n🖥️ Веб-интерфейс доступен на http://localhost:8080")
        
        print("\n🎯 Что работает:")
        print("  ✅ Telegram уведомления")
        print("  ✅ Веб-интерфейс на http://localhost:8080")
        print("  ✅ База данных")
        print("  ❌ Мониторинг каналов ОТКЛЮЧЕН")
        
        print("\n💡 Как добавлять новости:")
        print("  1. python add_demo_news.py - добавить тестовые")
        print("  2. Создать скрипт для ручного добавления")
        print("  3. Использовать веб-интерфейс")
        
    else:
        print("❌ Ошибка подключения к боту")
        print("Проверьте bot token в config.yaml")
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(run_safe_mode())
