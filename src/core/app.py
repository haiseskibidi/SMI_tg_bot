import asyncio
import re
import os
import sys
import pytz
from datetime import datetime
from typing import Dict, List, Any, Set, Optional
from loguru import logger

from .config_loader import ConfigLoader
from .lifecycle import LifecycleManager
from ..monitoring import SubscriptionCacheManager, ChannelMonitor, MessageProcessor


class NewsMonitorWithBot:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.running = False
        self.monitoring_active = True
        
        # Модули системы
        self.config_loader = ConfigLoader(config_path)
        self.lifecycle_manager = LifecycleManager(self.config_loader)
        self.subscription_cache = SubscriptionCacheManager()
        
        # Компоненты (будут инициализированы через lifecycle_manager)
        self.database = None
        self.telegram_monitor = None
        self.telegram_bot = None
        self.news_processor = None
        self.system_monitor = None
        self.web_interface = None
        
        # Мониторинг
        self.message_processor = None
        self.channel_monitor = None
        
        # Кэш медиа групп
        self.processed_media_groups: Set[int] = set()

    async def pause_monitoring(self):
        self.monitoring_active = False
        logger.info("⏸️ Мониторинг приостановлен")

    async def resume_monitoring(self):
        self.monitoring_active = True
        logger.info("▶️ Мониторинг возобновлен")

    def safe_html_truncate(self, html_text: str, max_length: int) -> str:
        if len(html_text) <= max_length:
            return html_text
        
        truncated = html_text[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:
            truncated = truncated[:last_space]
        
        open_tags = []
        tag_pattern = r'<(/?)([^>]+)>'
        
        for match in re.finditer(tag_pattern, truncated):
            is_closing = bool(match.group(1))
            tag_name = match.group(2).split()[0].lower()
            
            if tag_name in ['br', 'hr', 'img']:
                continue
                
            if is_closing:
                if open_tags and open_tags[-1] == tag_name:
                    open_tags.pop()
            else:
                open_tags.append(tag_name)
        
        for tag in reversed(open_tags):
            truncated += f'</{tag}>'
        
        return truncated

    def convert_markdown_to_html(self, text: str) -> str:
        if not text:
            return ""
        
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        text = re.sub(r'__(.*?)__', r'<u>\1</u>', text)
        text = re.sub(r'~~(.*?)~~', r'<s>\1</s>', text)
        text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
        text = re.sub(r'```(.*?)```', r'<pre>\1</pre>', text, flags=re.DOTALL)
        
        url_pattern = r'(?<!<[^>]*)(https?://[^\s<>"\']+)'
        text = re.sub(url_pattern, r'<a href="\1">\1</a>', text)
        
        return text

    def validate_and_fix_html(self, html_text: str) -> str:
        if not html_text:
            return ""
        
        html_text = re.sub(r'<(/?)(\w+)[^>]*?/?>', r'<\1\2>', html_text)
        
        allowed_tags = ['b', 'i', 'u', 's', 'code', 'pre', 'a', 'br']
        tag_pattern = r'<(/?)(\w+)([^>]*)>'
        
        def replace_tag(match):
            is_closing = match.group(1)
            tag_name = match.group(2).lower()
            attributes = match.group(3)
            
            if tag_name not in allowed_tags:
                return ''
            
            if tag_name == 'a' and not is_closing and 'href=' in attributes:
                return f'<{is_closing}a{attributes}>'
            elif tag_name == 'a' and is_closing:
                return '</a>'
            else:
                return f'<{is_closing}{tag_name}>'
        
        html_text = re.sub(tag_pattern, replace_tag, html_text)
        html_text = re.sub(r'&(?![a-zA-Z]+;)', '&amp;', html_text)
        html_text = re.sub(r'<(?![/a-zA-Z])', '&lt;', html_text)
        
        return html_text

    def check_alert_keywords(self, text: str) -> tuple:
        if not text or not self.config_loader.get_alert_keywords():
            return False, None, None, False, []
        
        text_lower = text.lower()
        
        for category, alert_data in self.config_loader.get_alert_keywords().items():
            words = alert_data.get('words', [])
            emoji = alert_data.get('emoji', '🚨')
            priority = alert_data.get('priority', False)
            
            matched_words = [word for word in words if word in text_lower]
            
            if matched_words:
                return True, category, emoji, priority, matched_words
        
        return False, None, None, False, []

    def format_alert_message(self, original_text: str, channel_username: str, emoji: str, category: str, matched_words: list) -> str:
        try:
            alert_header = f"{emoji} <b>АЛЕРТ: {category.upper()}</b>\n"
            alert_header += f"📺 Канал: @{channel_username}\n"
            alert_header += f"🔍 Ключевые слова: {', '.join(matched_words)}\n"
            alert_header += "─" * 30 + "\n\n"
            
            return alert_header + original_text
        except Exception as e:
            logger.error(f"❌ Ошибка форматирования алерта: {e}")
            return original_text

    def get_channel_regions(self, channel_username: str) -> list:
        found_regions = []
        regions_config = self.config_loader.get_regions_config()
        
        for region_key, region_data in regions_config.items():
            keywords = region_data.get('keywords', [])
            for keyword in keywords:
                if keyword.lower() in channel_username.lower():
                    found_regions.append(region_key)
                    break
        
        if not found_regions:
            found_regions.append('general')
        
        return found_regions

    def get_channel_region(self, channel_username: str) -> str:
        regions = self.get_channel_regions(channel_username)
        return regions[0] if regions else 'general'

    async def monitoring_cycle(self):
        logger.info("🔄 Запуск мониторинга в реальном времени")
        
        try:
            self.subscription_cache.load_subscription_cache()
            
            await self.channel_monitor.setup_realtime_handlers()
            
            if self.telegram_bot:
                bot_listener_task = asyncio.create_task(self.telegram_bot.start_listening())
                logger.info("👂 Запущен прослушиватель команд бота")
            
            status_interval = 3600
            last_status_update = 0
            
            while self.running:
                try:
                    current_time = asyncio.get_event_loop().time()
                    
                    if current_time - last_status_update >= status_interval:
                        await self.send_status_update()
                        last_status_update = current_time
                    
                    await asyncio.sleep(30)
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка в цикле мониторинга: {e}")
                    await asyncio.sleep(60)
                    
        except Exception as e:
            logger.error(f"❌ Критическая ошибка мониторинга: {e}")
            if self.telegram_bot:
                await self.telegram_bot.send_error_alert(f"Ошибка мониторинга: {e}")

    async def send_status_update(self):
        try:
            if not self.telegram_bot:
                return
            
            vladivostok_tz = pytz.timezone('Asia/Vladivostok')
            current_time = datetime.now(vladivostok_tz)
            
            status_text = (
                f"📊 <b>Статус системы</b>\n"
                f"🕐 {current_time.strftime('%d.%m.%Y %H:%M:%S')} (Владивосток)\n"
                f"🔄 Мониторинг: {'🟢 Активен' if self.monitoring_active else '🔴 Приостановлен'}\n"
            )
            
            if self.subscription_cache:
                stats = self.subscription_cache.get_cache_stats()
                status_text += f"📡 Подписок: {stats['total_subscribed']}\n"
            
            await self.telegram_bot.send_system_notification(status_text)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки статуса: {e}")

    async def initialize_components(self) -> bool:
        success = await self.lifecycle_manager.initialize_components()
        if not success:
            return False
        
        # Копируем компоненты из lifecycle_manager
        self.database = self.lifecycle_manager.database
        self.telegram_monitor = self.lifecycle_manager.telegram_monitor
        self.telegram_bot = self.lifecycle_manager.telegram_bot
        self.news_processor = self.lifecycle_manager.news_processor
        self.system_monitor = self.lifecycle_manager.system_monitor
        self.web_interface = self.lifecycle_manager.web_interface
        
        # Инициализируем мониторинг компоненты
        if self.telegram_monitor:
            self.message_processor = MessageProcessor(self.database, self)
            self.channel_monitor = ChannelMonitor(
                self.telegram_monitor,
                self.subscription_cache,
                self.message_processor,
                self.config_loader  # Передаем config_loader для загрузки настроек таймаутов
            )
        
        return True

    def clear_subscription_cache(self):
        if self.subscription_cache:
            self.subscription_cache.clear_subscription_cache()

    def add_channel_to_cache(self, channel_username: str):
        if self.subscription_cache:
            self.subscription_cache.add_channel_to_cache(channel_username)

    def is_channel_cached_as_subscribed(self, channel_username: str) -> bool:
        if self.subscription_cache:
            return self.subscription_cache.is_channel_cached_as_subscribed(channel_username)
        return False

    async def run(self):
        try:
            if not self.config_loader.load_config():
                return False
            
            self.config_loader.load_alert_keywords()
            self.config_loader.load_regions_config()
            
            self.lifecycle_manager.setup_logging()
            
            if not await self.initialize_components():
                return False
            
            self.running = True
            await self.monitoring_cycle()
            
            return True
            
        except KeyboardInterrupt:
            logger.info("👋 Получен сигнал завершения (Ctrl+C)")
        except Exception as e:
            logger.error(f"💥 Критическая ошибка: {e}")
            if self.telegram_bot:
                await self.telegram_bot.send_error_alert(f"Критическая ошибка: {e}")
            return False
        finally:
            await self.lifecycle_manager.shutdown()
        
        return True


async def main():
    print("🤖 Запуск Telegram News Monitor Bot...")
    print(f"📁 Рабочая директория: {os.getcwd()}")
    print(f"🐍 Python версия: {sys.version}")
    print()
    print("🛡️  ЗАЩИТА ОТ БЛОКИРОВОК TELEGRAM:")
    print("⚠️  НЕ перезапускайте бота часто (максимум 1-2 раза в день)")
    print("⚠️  При ошибках 'wait of X seconds' - просто ждите")
    print("⚠️  Система автоматически предотвращает частые перезапуски")
    print()
    print("🚀 ОПТИМИЗАЦИЯ СКОРОСТИ ЗАПУСКА:")
    print("⚡ Включен режим быстрого старта (приоритет кешированным каналам)")  
    print("💾 Кешированные каналы загружаются за секунды")
    print("🐌 Новые каналы обрабатываются медленно и безопасно")
    print("📖 Настройки в файле: config_example_timeouts.yaml")
    print()
    
    bot = NewsMonitorWithBot()
    success = await bot.run()
    
    if success:
        print("✅ Бот завершил работу корректно")
    else:
        print("❌ Бот завершился с ошибками")


if __name__ == "__main__":
    asyncio.run(main())
