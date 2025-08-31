#!/usr/bin/env python3
"""
🤖 Telegram News Monitor Bot (Рефакторированная версия)
Автоматический мониторинг новостных каналов с отправкой через бота

Для запуска: python main.py
"""

import asyncio
from src.core import NewsMonitorWithBot


if __name__ == "__main__":
    asyncio.run(NewsMonitorWithBot().run())
