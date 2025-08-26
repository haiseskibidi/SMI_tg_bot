#!/usr/bin/env python3
"""
📝 Ручное добавление новостей
Безопасный способ добавить новости без мониторинга каналов
"""

import asyncio
from src.database import DatabaseManager
from src.telegram_bot import TelegramBot
import yaml
from datetime import datetime
from loguru import logger

async def add_manual_news():
    """Добавление новости вручную"""
    
    print("📝 Ручное добавление новости")
    print("=" * 40)
    
    # Загружаем конфигурацию
    with open('../config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    db = DatabaseManager("news_monitor.db")
    await db.initialize()
    
    bot = TelegramBot(
        token=config['bot']['token'],
        chat_id=config['bot']['chat_id']
    )
    
    # Интерактивное добавление
    print("\n💬 Введите данные новости:")
    
    title = input("📰 Заголовок: ").strip()
    if not title:
        print("❌ Заголовок обязателен!")
        return
    
    text = input("📄 Текст новости: ").strip()
    if not text:
        print("❌ Текст обязателен!")
        return
    
    source = input("📍 Источник (по умолчанию 'Ручной ввод'): ").strip() or "Ручной ввод"
    region = input("🌍 Регион (sakhalin/kamchatka/other): ").strip() or "other"
    url = input("🔗 Ссылка (необязательно): ").strip()
    
    # Создаем данные сообщения
    now = datetime.now()
    message_data = {
        "id": f"manual_{int(now.timestamp())}",
        "channel_username": "@manual",
        "channel_name": source,
        "channel_title": source,
        "text": text,
        "date": now,
        "created_at": now,
        "views": 1,
        "reactions_count": 0,
        "url": url if url else None,
        "message_id": int(now.timestamp()),
        "processed": True,
        "ai_suitable": True,
        "selected_for_output": True,  # Всегда отбираем ручные новости
        "ai_analysis": f'{{"title": "{title}", "summary": "{text[:100]}...", "region": "{region}"}}',
        "ai_score": 10,  # Максимальная оценка для ручных новостей
        "ai_priority": "high",
        "content_hash": f"manual_{now.timestamp()}"
    }
    
    try:
        # Сохраняем в базу
        await db.save_message(message_data)
        print(f"\n✅ Новость добавлена: {title}")
        
        # Отправляем уведомление
        if await bot.test_connection():
            message = f"📰 **Новая новость добавлена**\n\n**{title}**\n\n{text}"
            if url:
                message += f"\n\n🔗 [Читать полностью]({url})"
            message += f"\n\n📍 {source}"
            
            await bot.send_message(message)
            print("✅ Уведомление отправлено в Telegram")
        else:
            print("⚠️ Не удалось отправить уведомление (проверьте bot token)")
        
    except Exception as e:
        print(f"❌ Ошибка добавления: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(add_manual_news())
