#!/usr/bin/env python3
"""
🤖 Telegram News Monitor Bot (Рефакторированная версия)
Автоматический мониторинг новостных каналов с отправкой через бота

Для запуска: python main.py
"""

import asyncio
from src.core import NewsMonitorWithBot


if __name__ == "__main__":
    # 🔒 KILL SWITCH - проверяем файл блокировки  
    import os
    if os.path.exists("STOP_BOT"):
        print("🛑 НАЙДЕН ФАЙЛ БЛОКИРОВКИ: STOP_BOT")
        print("🚫 БОТ ЗАБЛОКИРОВАН ОТ ЗАПУСКА")  
        print("💡 Удалите файл STOP_BOT для разблокировки")
        exit(0)
    
    asyncio.run(NewsMonitorWithBot().run())
