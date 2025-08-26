#!/usr/bin/env python3
"""
🤖 Telegram News Monitor Bot (Версия с ботом)
Автоматический мониторинг новостных каналов с отправкой через бота

Для запуска: python main_bot.py
"""

import asyncio
import json
import logging
import yaml
import sys
import os
import pytz
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv

# Локальные модули
from src.telegram_client import TelegramMonitor
from src.telegram_bot import TelegramBot, create_bot_from_config

from src.database import DatabaseManager
from src.news_processor import NewsProcessor
from src.system_monitor import SystemMonitor
from src.web_interface import WebInterface

# Настройка логирования
from loguru import logger


class NewsMonitorWithBot:
    """Главный класс системы мониторинга с Telegram ботом"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = {}
        self.running = False
        self.monitoring_active = True  # Флаг для паузы/возобновления мониторинга
        
        # Компоненты системы
        self.database = None
        self.telegram_monitor = None
        self.telegram_bot = None

        self.news_processor = None
        self.system_monitor = None
        self.web_interface = None
        
        logger.info("🤖 News Monitor Bot инициализирован")
        
        # Кэш подписанных каналов
        self.subscription_cache_file = "config/subscriptions_cache.json"
        self.subscribed_channels = set()
        
        # Кэш для отслеживания обработанных медиа групп
        self.processed_media_groups = set()
        
        # Алерты по ключевым словам
        self.alert_keywords = {}
        
        # Динамические регионы
        self.regions_config = {}
    
    async def pause_monitoring(self):
        """Приостановить мониторинг новостей"""
        logger.info("⏸️ Приостанавливаем мониторинг новостей...")
        self.monitoring_active = False
        logger.info("✅ Мониторинг приостановлен")
    
    async def resume_monitoring(self):
        """Возобновить мониторинг новостей"""
        logger.info("▶️ Возобновляем мониторинг новостей...")
        self.monitoring_active = True
        logger.info("✅ Мониторинг возобновлен")
    
    def convert_markdown_to_html(self, text: str) -> str:
        """Конвертирует markdown форматирование в HTML для Telegram"""
        if not text:
            return text
        
        import re
        
        # Сначала обрабатываем парные **текст**
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        
        # Затем обрабатываем **текст в начале строки (заголовки без закрывающих **)
        text = re.sub(r'^(\*\*)(.*?)$', r'<b>\2</b>', text, flags=re.MULTILINE)
        
        # Конвертируем *текст* в <i>текст</i> (но только одиночные *)
        text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', text)
        
        # Экранируем опасные HTML символы (но не наши теги)
        text = text.replace('<', '&lt;').replace('>', '&gt;')
        text = text.replace('&lt;b&gt;', '<b>').replace('&lt;/b&gt;', '</b>')
        text = text.replace('&lt;i&gt;', '<i>').replace('&lt;/i&gt;', '</i>')
        text = text.replace('&lt;u&gt;', '<u>').replace('&lt;/u&gt;', '</u>')
        text = text.replace('&lt;code&gt;', '<code>').replace('&lt;/code&gt;', '</code>')
        
        return text
    
    def load_config(self) -> bool:
        """Загрузка конфигурации"""
        try:
            # Загружаем переменные окружения из .env файла
            load_dotenv()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            logger.info(f"✅ Конфигурация загружена из {self.config_path}")
            
            # Переопределяем секретные данные из переменных окружения
            bot_token = os.getenv('BOT_TOKEN')
            bot_chat_id = os.getenv('BOT_CHAT_ID')
            api_id = os.getenv('TELEGRAM_API_ID')
            api_hash = os.getenv('TELEGRAM_API_HASH')
            target_group = os.getenv('TARGET_GROUP_ID')
            
            # Обновляем конфигурацию из переменных окружения (приоритет над файлом)
            if bot_token:
                self.config.setdefault('bot', {})['token'] = bot_token
            if bot_chat_id:
                self.config.setdefault('bot', {})['chat_id'] = int(bot_chat_id)
            if api_id:
                self.config.setdefault('telegram', {})['api_id'] = int(api_id)
            if api_hash:
                self.config.setdefault('telegram', {})['api_hash'] = api_hash
            if target_group:
                self.config.setdefault('output', {})['target_group'] = int(target_group)
            
            # Проверяем наличие конфигурации бота
            if 'bot' not in self.config:
                logger.error("❌ Не найдена конфигурация бота")
                logger.info("💡 Создайте .env файл с токенами или добавьте секцию 'bot' в config.yaml")
                return False
            
            bot_config = self.config['bot']
            if not bot_config.get('token') or not bot_config.get('chat_id'):
                logger.error("❌ Не указан токен бота или chat_id")
                logger.info("💡 Проверьте .env файл или config.yaml")
                return False
            
            if str(bot_config['token']).startswith("ЗАМЕНИТЕ_НА_"):
                logger.error("❌ Токен бота не настроен")
                logger.info("💡 Укажите реальный токен в .env файле (BOT_TOKEN=...)")
                return False
            
            return True
            
        except FileNotFoundError:
            logger.error(f"❌ Файл конфигурации {self.config_path} не найден")
            return False
        except yaml.YAMLError as e:
            logger.error(f"❌ Ошибка в файле конфигурации: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки конфигурации: {e}")
            return False
    
    def load_subscription_cache(self):
        """Загружает кэш подписанных каналов из файла"""
        try:
            if os.path.exists(self.subscription_cache_file):
                with open(self.subscription_cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    self.subscribed_channels = set(cache_data.get('subscribed_channels', []))
                    logger.info(f"📋 Загружен кэш подписок: {len(self.subscribed_channels)} каналов")
            else:
                self.subscribed_channels = set()
                logger.info("📋 Файл кэша подписок не найден, создаем новый")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки кэша подписок: {e}")
            self.subscribed_channels = set()
    
    def save_subscription_cache(self):
        """Сохраняет кэш подписанных каналов в файл"""
        try:
            # Создаем директорию config если её нет
            os.makedirs(os.path.dirname(self.subscription_cache_file), exist_ok=True)
            
            cache_data = {
                'subscribed_channels': list(self.subscribed_channels),
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.subscription_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"💾 Сохранен кэш подписок: {len(self.subscribed_channels)} каналов")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения кэша подписок: {e}")
    
    def is_channel_cached_as_subscribed(self, channel_username):
        """Проверяет, есть ли канал в кэше подписанных"""
        return channel_username in self.subscribed_channels
    
    def add_channel_to_cache(self, channel_username):
        """Добавляет канал в кэш подписанных"""
        self.subscribed_channels.add(channel_username)
        self.save_subscription_cache()
    
    def clear_subscription_cache(self):
        """Очищает кэш подписок (для принудительной перепроверки)"""
        self.subscribed_channels.clear()
        self.save_subscription_cache()
        logger.info("🗑️ Кэш подписок очищен")
    
    def load_alert_keywords(self):
        """Загружает ключевые слова для алертов из конфигурации"""
        try:
            alerts_config = self.config.get('alerts', {})
            if not alerts_config.get('enabled', False):
                logger.info("📢 Алерты по ключевым словам отключены")
                return
            
            keywords_config = alerts_config.get('keywords', {})
            for category, data in keywords_config.items():
                words = data.get('words', [])
                emoji = data.get('emoji', '🚨')
                priority = data.get('priority', False)
                
                self.alert_keywords[category] = {
                    'words': [word.lower() for word in words],
                    'emoji': emoji,
                    'priority': priority
                }
            
            total_words = sum(len(cat['words']) for cat in self.alert_keywords.values())
            logger.info(f"📢 Загружено {len(self.alert_keywords)} категорий алертов, {total_words} ключевых слов")
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки алертов: {e}")
            self.alert_keywords = {}
    
    def load_regions_config(self):
        """Загружает конфигурацию регионов из config.yaml"""
        try:
            regions_config = self.config.get('regions', {})
            if not regions_config:
                logger.warning("📍 Секция regions не найдена в конфигурации, используем стандартные регионы")
                # Создаем стандартную конфигурацию
                self.regions_config = {
                    'general': {
                        'name': '📰 Общие',
                        'emoji': '📰',
                        'description': 'Общие новости',
                        'keywords': [],
                        'topic_id': None
                    }
                }
                return
            
            self.regions_config = {}
            for region_key, region_data in regions_config.items():
                self.regions_config[region_key] = {
                    'name': region_data.get('name', region_key),
                    'emoji': region_data.get('emoji', '📍'),
                    'description': region_data.get('description', ''),
                    'keywords': region_data.get('keywords', []),
                    'topic_id': region_data.get('topic_id'),
                    'created_at': region_data.get('created_at', '2025-08-26')
                }
            
            logger.info(f"📍 Загружено {len(self.regions_config)} регионов: {list(self.regions_config.keys())}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки регионов: {e}")
            self.regions_config = {}
    
    def get_regions_list(self) -> list:
        """Возвращает список всех регионов с их данными"""
        regions = []
        for region_key, region_data in self.regions_config.items():
            regions.append({
                'key': region_key,
                'name': region_data['name'],
                'emoji': region_data['emoji'],
                'description': region_data['description'],
                'channels_count': self.get_region_channels_count(region_key),
                'topic_id': region_data['topic_id']
            })
        return regions
    
    def get_region_channels_count(self, region_key: str) -> int:
        """Подсчитывает количество каналов в регионе"""
        try:
            with open('config/channels_config.yaml', 'r', encoding='utf-8') as f:
                import yaml
                channels_data = yaml.safe_load(f) or {}
            
            if 'regions' in channels_data and region_key in channels_data['regions']:
                channels = channels_data['regions'][region_key].get('channels', [])
                return len(channels)
            
            return 0
        except Exception as e:
            logger.error(f"❌ Ошибка подсчета каналов для региона {region_key}: {e}")
            return 0
    
    def add_new_region(self, region_key: str, region_name: str, region_emoji: str = '📍', 
                      region_description: str = '', region_keywords: list = None, 
                      topic_id: int = None) -> bool:
        """Добавляет новый регион в конфигурацию"""
        try:
            from datetime import datetime
            import yaml
            
            # Проверяем что региона еще нет
            if region_key in self.regions_config:
                logger.warning(f"⚠️ Регион {region_key} уже существует")
                return False
            
            # Добавляем в память
            self.regions_config[region_key] = {
                'name': region_name,
                'emoji': region_emoji,
                'description': region_description,
                'keywords': region_keywords or [],
                'topic_id': topic_id,
                'created_at': datetime.now().strftime('%Y-%m-%d')
            }
            
            # Сохраняем в config.yaml
            self.config.setdefault('regions', {})[region_key] = self.regions_config[region_key]
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            # Добавляем в channels_config.yaml
            try:
                with open('config/channels_config.yaml', 'r', encoding='utf-8') as f:
                    channels_config = yaml.safe_load(f) or {}
                
                if 'regions' not in channels_config:
                    channels_config['regions'] = {}
                
                channels_config['regions'][region_key] = {
                    'name': region_name,
                    'channels': []
                }
                
                with open('config/channels_config.yaml', 'w', encoding='utf-8') as f:
                    yaml.dump(channels_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                    
            except Exception as e:
                logger.error(f"❌ Ошибка обновления channels_config.yaml: {e}")
            
            logger.success(f"✅ Создан новый регион: {region_name} ({region_key})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания региона: {e}")
            return False
    
    def check_alert_keywords(self, text: str) -> tuple:
        """
        Проверяет текст на наличие ключевых слов алертов
        
        Возвращает: (is_alert, category, emoji, priority, matched_words)
        """
        if not self.alert_keywords or not text:
            return False, None, None, False, []
        
        text_lower = text.lower()
        
        for category, data in self.alert_keywords.items():
            matched_words = []
            for word in data['words']:
                if word in text_lower:
                    matched_words.append(word)
            
            if matched_words:
                return True, category, data['emoji'], data['priority'], matched_words
        
        return False, None, None, False, []
    
    def format_alert_message(self, original_text: str, channel_username: str, emoji: str, category: str, matched_words: list) -> str:
        """Форматирует сообщение с алертом"""
        try:
            # Создаем красивый заголовок алерта
            alert_header = f"\n{emoji} <b>ВАЖНАЯ НОВОСТЬ!</b> {emoji}\n"
            
            # Добавляем категорию
            category_names = {
                'emergency': '🔥 ПОЖАР/ЧС',
                'accident': '🚗 ДТП/АВАРИЯ', 
                'disaster': '🌊 СТИХИЯ',
                'crime': '🚔 КРИМИНАЛ',
                'weather': '🌨️ ПОГОДА'
            }
            
            category_name = category_names.get(category, category.upper())
            alert_header += f"<b>{category_name}</b>\n"
            alert_header += "─" * 30 + "\n\n"
            
            # Оригинальный текст с выделением ключевых слов
            formatted_text = original_text
            for word in matched_words:
                # Выделяем ключевые слова жирным
                formatted_text = formatted_text.replace(word, f"<b>{word.upper()}</b>")
                formatted_text = formatted_text.replace(word.capitalize(), f"<b>{word.upper()}</b>")
            
            return alert_header + formatted_text
            
        except Exception as e:
            logger.error(f"❌ Ошибка форматирования алерта: {e}")
            return f"{emoji} АЛЕРТ {emoji}\n\n{original_text}"
    
    def setup_logging(self):
        """Настройка системы логирования"""
        try:
            log_config = self.config.get('logging', {})
            
            # Создаем директорию для логов
            log_file = Path(log_config.get('file', 'logs/news_monitor.log'))
            log_file.parent.mkdir(exist_ok=True)
            
            # Настраиваем loguru
            logger.remove()  # Удаляем стандартный обработчик
            
            # Консольный вывод (только важные сообщения)
            logger.add(
                sys.stdout, 
                level="INFO",
                format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
                colorize=True
            )
            
            # Файловый вывод (все сообщения)
            logger.add(
                log_file,
                level=log_config.get('level', 'INFO'),
                rotation=f"{log_config.get('max_size_mb', 10)} MB",
                retention=log_config.get('backup_count', 5),
                encoding='utf-8',
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
            )
            
            logger.info("📝 Система логирования настроена")
            
        except Exception as e:
            print(f"❌ Ошибка настройки логирования: {e}")
    
    async def initialize_components(self) -> bool:
        """Инициализация всех компонентов"""
        try:
            # 1. База данных
            db_config = self.config.get('database', {})
            self.database = DatabaseManager(db_config.get('path', 'news_monitor.db'))
            await self.database.initialize()
            
            # 2. Системный монитор
            system_config = self.config.get('system', {})
            self.system_monitor = SystemMonitor(
                memory_limit_mb=system_config.get('memory_limit_mb', 800)
            )
            
            # 3. Telegram бот (ОСНОВНОЙ КАНАЛ СВЯЗИ)
            self.telegram_bot = await create_bot_from_config(self.config, self)
            if not self.telegram_bot:
                logger.error("❌ Не удалось создать Telegram бота")
                return False
            

            
            # 5. Telegram монитор (ОПЦИОНАЛЬНО - может вызывать проблемы с сессией)
            try:
                telegram_config = self.config['telegram']
                self.telegram_monitor = TelegramMonitor(
                    api_id=telegram_config['api_id'],
                    api_hash=telegram_config['api_hash'],
                    database=self.database
                )
                
                # Пытаемся инициализировать (без ввода кода)
                if await self.telegram_monitor.initialize():
                    logger.success("✅ Telegram мониторинг активен")
                else:
                    logger.warning("⚠️ Telegram мониторинг отключен (требуется авторизация)")
                    self.telegram_monitor = None
                    
            except Exception as e:
                logger.warning(f"⚠️ Telegram мониторинг недоступен: {e}")
                self.telegram_monitor = None
            
            # 6. Процессор новостей
            monitoring_config = self.config.get('monitoring', {})
            self.news_processor = NewsProcessor(
                database=self.database,

                telegram_bot=self.telegram_bot,  # Используем бота для уведомлений
                telegram_monitor=self.telegram_monitor,  # ИСПРАВЛЕНО: передаем telegram_monitor!
                config=monitoring_config
            )
            
            # 7. Веб-интерфейс
            try:
                web_port = self.config.get('web', {}).get('port', 8080)
                self.web_interface = WebInterface(
                    database=self.database,
                    system_monitor=self.system_monitor,
                    port=web_port
                )
                self.web_interface.start_server()
            except Exception as e:
                logger.warning(f"⚠️ Веб-интерфейс недоступен: {e}")
                logger.info("💡 Установите Flask: pip install flask")
            
            # Отправляем уведомление о запуске
            await self.telegram_bot.send_message(
                "🚀 <b>Система мониторинга запущена!</b>\n\n"
                f"📱 Telegram бот: ✅ Активен\n"
                f"🗄️ База данных: ✅ Подключена\n" 
                f"🧠 ИИ анализатор: ✅ Готов\n"
                f"📺 Мониторинг каналов: {'✅ Активен' if self.telegram_monitor else '⚠️ Отключен'}\n"
                f"🌐 Веб-интерфейс: {'✅ http://localhost:8080' if self.web_interface else '❌ Недоступен'}\n\n"
                f"🕐 {datetime.now(pytz.timezone('Asia/Vladivostok')).strftime('%d.%m.%Y %H:%M:%S')} (Владивосток)"
            )
            
            logger.success("✅ Все компоненты инициализированы")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации компонентов: {e}")
            if self.telegram_bot:
                await self.telegram_bot.send_error_alert(f"Ошибка инициализации: {e}")
            return False
    
    async def monitoring_cycle(self):
        """Мониторинг в реальном времени через Telegram события"""
        logger.info("🔄 Запуск мониторинга в реальном времени")
        
        try:
            # Загружаем кэш подписанных каналов
            self.load_subscription_cache()
            
            # Настраиваем обработчики событий для мгновенной пересылки
            await self.setup_realtime_handlers()
            
            # Запуск прослушивания команд бота в фоне
            if self.telegram_bot:
                bot_listener_task = asyncio.create_task(self.telegram_bot.start_listening())
                logger.info("👂 Запущен прослушиватель команд бота")
            
            # Основной цикл для служебных задач
            status_interval = 3600  # 1 час для статуса
            last_status_update = 0
            
            while self.running:
                try:
                    current_time = asyncio.get_event_loop().time()
                    
                    # Обновление статуса
                    if current_time - last_status_update >= status_interval:
                        await self.send_status_update()
                        last_status_update = current_time
                    
                    # Автоматическая очистка старых данных (раз в день)
                    if hasattr(self, 'last_cleanup_time'):
                        if current_time - self.last_cleanup_time >= 86400:  # 24 часа
                            await self.auto_cleanup_old_data()
                            self.last_cleanup_time = current_time
                    else:
                        self.last_cleanup_time = current_time
                    
                    # Проверка системных ресурсов
                    if self.system_monitor.check_memory_limit():
                        await self.telegram_bot.send_error_alert("Превышен лимит памяти!")
                    
                    await asyncio.sleep(300)  # Служебные задачи каждые 5 минут
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка в цикле мониторинга: {e}")
                    if self.telegram_bot:
                        await self.telegram_bot.send_error_alert(f"Ошибка мониторинга: {e}")
                    await asyncio.sleep(300)  # При ошибке ждем 5 минут
                    
        except Exception as e:
            logger.error(f"❌ Критическая ошибка настройки мониторинга: {e}")
            if self.telegram_bot:
                await self.telegram_bot.send_error_alert(f"Критическая ошибка: {e}")
    
    def get_channel_regions(self, channel_username: str) -> list:
        """Определить ВСЕ регионы канала по его username (может быть в нескольких)"""
        found_regions = []
        
        try:
            channels_config_path = "config/channels_config.yaml"
            with open(channels_config_path, 'r', encoding='utf-8') as f:
                channels_data = yaml.safe_load(f) or {}
            
            # Проверяем новую структуру с регионами
            if 'regions' in channels_data:
                for region_key, region_data in channels_data['regions'].items():
                    channels = region_data.get('channels', [])
                    for channel in channels:
                        if channel.get('username') == channel_username:
                            found_regions.append(region_key)
                            logger.info(f"🗂️ Канал @{channel_username} найден в регионе '{region_key}'")
            else:
                # Старая структура для обратной совместимости
                all_channels = channels_data.get('channels', [])
                for channel in all_channels:
                    if channel.get('username') == channel_username:
                        region = channel.get('region', 'general')
                        found_regions.append(region)
                        logger.info(f"🗂️ Канал @{channel_username} найден в конфигурации: регион '{region}'")
            
            # Если канал найден хотя бы в одном регионе, возвращаем найденные
            if found_regions:
                return found_regions
            
            # Если канал не найден, определяем по ключевым словам из динамической конфигурации
            channel_lower = channel_username.lower()
            best_match_region = 'general'
            best_match_score = 0
            
            for region_key, region_data in self.regions_config.items():
                if region_key == 'general':  # Пропускаем общий регион
                    continue
                    
                keywords = region_data.get('keywords', [])
                score = 0
                
                for keyword in keywords:
                    if keyword.lower() in channel_lower:
                        score += 1
                
                if score > best_match_score:
                    best_match_score = score
                    best_match_region = region_key
            
            if best_match_score > 0:
                region_name = self.regions_config.get(best_match_region, {}).get('name', best_match_region)
                logger.info(f"🗂️ Канал @{channel_username} определен как {region_name} ({best_match_score} совпадений)")
                return [best_match_region]
            else:
                logger.info(f"🗂️ Канал @{channel_username} определен как общий (нет ключевых слов)")
                return ['general']
                
        except Exception as e:
            logger.warning(f"⚠️ Ошибка определения региона для {channel_username}: {e}")
            return ['general']
    
    def get_channel_region(self, channel_username: str) -> str:
        """Получить ПЕРВЫЙ регион канала (для обратной совместимости)"""
        regions = self.get_channel_regions(channel_username)
        return regions[0] if regions else 'general'
    
    async def setup_realtime_handlers(self):
        """Настройка обработчиков для мгновенной пересылки сообщений"""
        from telethon import events
        from telethon.tl.functions.channels import JoinChannelRequest
        
        logger.info("⚡ Настройка обработчиков реального времени...")
        
        if not self.telegram_monitor or not self.telegram_monitor.client:
            logger.error("❌ Telegram клиент недоступен")
            return
        
        # Загружаем список каналов для мониторинга
        channels_config_path = "config/channels_config.yaml"
        try:
            with open(channels_config_path, 'r', encoding='utf-8') as f:
                channels_data = yaml.safe_load(f) or {}
        except (FileNotFoundError, yaml.YAMLError) as e:
            logger.warning(f"⚠️ Проблема с файлом каналов {channels_config_path}: {e}")
            channels_data = {}
        
        # Поддерживаем новую структуру с регионами и старые форматы
        all_channels = []
        
        if 'regions' in channels_data:
            # Новая структура с регионами
            for region_key, region_data in channels_data['regions'].items():
                region_channels = region_data.get('channels', [])
                for channel in region_channels:
                    # Добавляем регион к каналу для совместимости
                    channel_with_region = channel.copy()
                    channel_with_region['region'] = region_key
                    all_channels.append(channel_with_region)
        elif channels_data and 'channels' in channels_data and channels_data['channels']:
            # Старая единая структура
            all_channels = channels_data['channels']
        elif channels_data:
            # Совсем старый формат с vip_channels и regular_channels
            if 'vip_channels' in channels_data and channels_data['vip_channels']:
                all_channels.extend(channels_data['vip_channels'])
            if 'regular_channels' in channels_data and channels_data['regular_channels']:
                all_channels.extend(channels_data['regular_channels'])
        
        # Если каналов нет - используем пустой список
        if not all_channels:
            logger.warning("⚠️ Список каналов для мониторинга пуст. Создайте правильный config/channels_config.yaml или добавьте каналы через бота.")
            all_channels = []
        
        # Получаем entity всех каналов и подписываемся на них
        monitored_channels = []
        subscribed_count = 0
        failed_count = 0
        rate_limited_count = 0
        rate_limited_channels = []  # Для повторной попытки
        
        logger.info("🔄 Начинаем автоподписку на каналы...")
        
        for channel_config in all_channels:
            try:
                entity = await self.telegram_monitor.get_channel_entity(channel_config['username'])
                if entity:
                    # Проверяем кэш подписок
                    channel_username = channel_config['username']
                    if self.is_channel_cached_as_subscribed(channel_username):
                        logger.info(f"💾 Канал {channel_username} найден в кэше подписок")
                        monitored_channels.append(entity)
                        logger.info(f"📡 Добавлен в мониторинг: {channel_username}")
                        continue
                    
                    # Для новых каналов - проверяем реальную подписку
                    try:
                        already = await self.telegram_monitor.is_already_joined(entity)
                        logger.info(f"🔍 Проверка подписки на {channel_username}: {'ДА' if already else 'НЕТ'}")
                        if already:
                            # Добавляем в кэш, если уже подписаны
                            self.add_channel_to_cache(channel_username)
                            monitored_channels.append(entity)
                            logger.info(f"📡 Добавлен в мониторинг: {channel_username}")
                            continue
                    except Exception as check_error:
                        logger.warning(f"⚠️ Ошибка проверки подписки на {channel_username}: {check_error}")
                        already = False

                    # 🚀 АВТОПОДПИСКА НА КАНАЛ (только если не подписан)
                    try:
                        await self.telegram_monitor.client(JoinChannelRequest(entity))
                        logger.info(f"✅ Подписался на {channel_username}")
                        # Добавляем в кэш после успешной подписки
                        self.add_channel_to_cache(channel_username)
                        subscribed_count += 1
                        await asyncio.sleep(3)  # Увеличенная пауза между подписками
                    except Exception as sub_error:
                        error_msg = str(sub_error).lower()
                        
                        # Обработка rate limiting
                        if "wait" in error_msg and "seconds" in error_msg:
                            # Извлекаем количество секунд из сообщения
                            import re
                            wait_match = re.search(r'(\d+)\s+seconds', error_msg)
                            if wait_match:
                                wait_seconds = int(wait_match.group(1))
                                logger.warning(f"⏳ Rate limit на {channel_config['username']} - нужно ждать {wait_seconds}с")
                                logger.info(f"🔄 Пропускаем {channel_config['username']} из-за rate limit, добавляем в мониторинг без подписки")
                                rate_limited_channels.append((entity, channel_config['username'], wait_seconds))
                                rate_limited_count += 1
                            else:
                                logger.warning(f"⏳ Rate limit на {channel_config['username']}: {sub_error}")
                                rate_limited_channels.append((entity, channel_config['username'], 90))  # 90 сек по умолчанию
                                rate_limited_count += 1
                        elif "already" in error_msg or "участник" in error_msg:
                            logger.info(f"🔄 Уже подписан на {channel_username}")
                            # Добавляем в кэш если уже подписан
                            self.add_channel_to_cache(channel_username)
                            subscribed_count += 1  # Считаем как успех
                        elif "private" in error_msg or "приватный" in error_msg:
                            logger.warning(f"🔒 Канал {channel_config['username']} приватный - нужно приглашение")
                            failed_count += 1
                        elif "invite" in error_msg or "приглашение" in error_msg:
                            logger.warning(f"📩 Канал {channel_config['username']} требует приглашение")
                            failed_count += 1
                        else:
                            logger.warning(f"⚠️ Не удалось подписаться на {channel_config['username']}: {sub_error}")
                            failed_count += 1
                    
                    monitored_channels.append(entity)
                    logger.info(f"📡 Добавлен в мониторинг: {channel_config['username']}")
            except Exception as e:
                logger.error(f"❌ Ошибка добавления канала {channel_config['username']}: {e}")
        
        logger.info(f"📊 Результат автоподписки:")
        logger.info(f"  ✅ Успешно подписался: {subscribed_count} каналов")
        logger.info(f"  ⏳ Rate limit: {rate_limited_count} каналов")
        logger.info(f"  ⚠️ Не удалось подписаться: {failed_count} каналов")
        logger.info(f"  📡 Всего в мониторинге: {len(monitored_channels)} каналов")
        
        # Отправляем отчет об автоподписке в Telegram
        if subscribed_count > 0 or failed_count > 0 or rate_limited_count > 0:
            subscription_report = (
                f"🚀 <b>Автоподписка на каналы</b>\n\n"
                f"✅ Успешно подписался: <b>{subscribed_count}</b> каналов\n"
                f"⏳ Rate limit: <b>{rate_limited_count}</b> каналов\n"
                f"⚠️ Не удалось подписаться: <b>{failed_count}</b> каналов\n"
                f"📡 Всего в мониторинге: <b>{len(monitored_channels)}</b> каналов\n\n"
            )
            
            if rate_limited_count > 0:
                subscription_report += (
                    f"💡 <b>Rate limit</b> - это временное ограничение Telegram\n"
                    f"Каналы добавлены в мониторинг, но нужно подписаться вручную\n\n"
                )
            
            subscription_report += f"🔥 Новые посты будут приходить мгновенно!"
            
            try:
                await self.telegram_bot.send_message(subscription_report)
            except Exception as e:
                logger.error(f"❌ Ошибка отправки отчета о подписках: {e}")
        
        # Настраиваем обработчик новых сообщений
        @self.telegram_monitor.client.on(events.NewMessage(chats=monitored_channels))
        async def handle_new_message(event):
            try:
                # Проверяем, активен ли мониторинг
                if not self.monitoring_active:
                    logger.debug("⏸️ Мониторинг приостановлен, пропускаем сообщение")
                    return
                
                logger.info("🔥 СРАБОТАЛ ОБРАБОТЧИК НОВОГО СООБЩЕНИЯ!")
                message = event.message
                
                # Получаем информацию о канале
                chat = await event.get_chat()
                channel_username = getattr(chat, 'username', None)
                if not channel_username:
                    logger.warning(f"⚠️ Сообщение без username канала, пропускаем")
                    return
                
                logger.info(f"📥 Получено сообщение от @{channel_username}: {message.text[:100] if message.text else 'без текста'}")
                
                has_text = bool(getattr(message, "text", None))
                has_media = bool(getattr(message, "media", None))
                
                # Проверяем, является ли это частью медиа группы (альбома)
                if has_media and hasattr(message, 'grouped_id') and message.grouped_id:
                    grouped_id = message.grouped_id
                    logger.info(f"📸 Сообщение является частью медиа группы: {grouped_id}")
                    
                    # Проверяем, не обрабатывали ли мы уже эту группу
                    if grouped_id in self.processed_media_groups:
                        logger.info(f"✅ Медиа группа {grouped_id} уже обработана, пропускаем")
                        return
                    
                    # Помечаем группу как обрабатываемую
                    self.processed_media_groups.add(grouped_id)
                    logger.info(f"🔄 Помечаем медиа группу {grouped_id} как обрабатываемую")
                    
                    # Периодически очищаем кэш медиа групп (если стал слишком большой)
                    if len(self.processed_media_groups) > 1000:
                        # Оставляем только последние 500 записей
                        self.processed_media_groups = set(list(self.processed_media_groups)[-500:])
                        logger.info("🧹 Очищен кэш медиа групп (превышен лимит)")
                
                # Проверяем время сообщения
                msg_time = message.date
                start_time = self.telegram_monitor.start_time
                
                # Приводим время к владивостокскому часовому поясу
                vladivostok_tz = pytz.timezone('Asia/Vladivostok')
                
                # Конвертируем время сообщения во владивостокское время
                if msg_time.tzinfo is None:
                    # Если нет timezone, считаем что это UTC и конвертируем
                    msg_time = pytz.utc.localize(msg_time).astimezone(vladivostok_tz)
                else:
                    # Если есть timezone, просто конвертируем во владивостокское
                    msg_time = msg_time.astimezone(vladivostok_tz)
                
                logger.info(f"⏰ Время сообщения: {msg_time.strftime('%d.%m.%Y %H:%M:%S %Z')}, время запуска бота: {start_time.strftime('%d.%m.%Y %H:%M:%S %Z')}")
                
                # Проверяем, что сообщение действительно новое (после запуска бота)
                if msg_time < start_time:
                    logger.info(f"⏭️ Сообщение старое (до запуска бота), пропускаем")
                    return
                
                # Формируем данные сообщения
                import hashlib
                text_for_hash = message.text or ''
                content_hash = hashlib.md5(
                    f"{text_for_hash[:1000]}{message.date}".encode()
                ).hexdigest()
                
                message_data = {
                    'id': f"{channel_username}_{message.id}",
                    'text': message.text or '',
                    'date': msg_time,  # Используем конвертированное владивостокское время
                    'channel_username': channel_username,
                    'message_id': message.id,
                    'url': f"https://t.me/{channel_username}/{message.id}",
                    'content_hash': content_hash,
                    'views': getattr(message, 'views', 0),
                    'forwards': getattr(message, 'forwards', 0),
                    'reactions_count': 0  # Будем считать отдельно если нужно
                }
                
                # Проверяем сообщение на алерты по ключевым словам
                is_alert, alert_category, alert_emoji, is_priority, matched_words = self.check_alert_keywords(message.text)
                
                if is_alert:
                    logger.warning(f"🚨 АЛЕРТ обнаружен в @{channel_username}! Категория: {alert_category}, слова: {matched_words}")
                    # Форматируем текст с алертом
                    alert_text = self.format_alert_message(
                        message.text, 
                        channel_username, 
                        alert_emoji, 
                        alert_category, 
                        matched_words
                    )
                    # Обновляем данные сообщения для отправки с алертом
                    message_data['text'] = alert_text
                    message_data['is_alert'] = True
                    message_data['alert_category'] = alert_category
                    message_data['alert_priority'] = is_priority
                else:
                    message_data['is_alert'] = False
                
                logger.info(f"⚡ Новое сообщение из @{channel_username} - мгновенная отправка!")
                
                # Сохраняем в базу данных для статистики
                try:
                    await self.database.save_message(message_data)
                    logger.info(f"💾 Сообщение сохранено в базу данных")
                except Exception as e:
                    logger.error(f"❌ Ошибка сохранения в БД: {e}")
                
                # Если есть файлы — скачиваем и отправляем через Bot API, иначе отправляем текст+ссылку
                if has_media:
                    logger.info(f"📎 Сообщение содержит файлы от @{channel_username}")
                    media_sent = await self.download_and_send_media(message_data)
                    if not media_sent:
                        logger.warning("⚠️ Не удалось отправить файлы, отправляем текстовое уведомление")
                        await self.send_message_to_target(message_data, is_media=True)
                elif not has_text:
                    # Если нет текста и нет медиа - пытаемся переслать оригинал
                    logger.info(f"📄 Сообщение без текста от @{channel_username}")
                    forwarded = await self.forward_original_message(message_data)
                    if not forwarded:
                        await self.send_message_to_target(message_data, is_media=True)
                else:
                    # Обычное текстовое сообщение
                    await self.send_message_to_target(message_data, is_media=False)
                
                # Обновляем время последней проверки во владивостокском времени
                vladivostok_tz = pytz.timezone('Asia/Vladivostok')
                current_time_vlk = datetime.now(vladivostok_tz)
                await self.database.update_last_check_time(channel_username, current_time_vlk)
                
            except Exception as e:
                logger.error(f"❌ Ошибка обработки нового сообщения: {e}")
                logger.exception("Детали ошибки:")
        
        logger.info(f"⚡ Настроен мониторинг {len(monitored_channels)} каналов в реальном времени!")
        
        # Добавляем тестовое логирование для проверки работы Telethon
        logger.info("🧪 Проверяем работу Telethon client...")
        try:
            me = await self.telegram_monitor.client.get_me()
            logger.info(f"✅ Telethon client активен: {me.first_name} (ID: {me.id})")
        except Exception as e:
            logger.error(f"❌ Ошибка Telethon client: {e}")
            
        # Логируем детали мониторинга
        logger.info(f"📋 Список отслеживаемых каналов:")
        for i, entity in enumerate(monitored_channels[:5]):  # Показываем первые 5
            logger.info(f"  {i+1}. {getattr(entity, 'username', 'No username')} (ID: {entity.id})")
        if len(monitored_channels) > 5:
            logger.info(f"  ... и еще {len(monitored_channels) - 5} каналов")
        
        # 🔄 Запускаем повторную подписку для каналов с rate limit
        if rate_limited_channels:
            logger.info(f"⏰ Запускаем повторную подписку для {len(rate_limited_channels)} каналов с rate limit")
            asyncio.create_task(self.retry_rate_limited_subscriptions(rate_limited_channels))
    
    async def retry_rate_limited_subscriptions(self, rate_limited_channels):
        """Повторная попытка подписки на каналы с rate limit"""
        from telethon.tl.functions.channels import JoinChannelRequest
        
        logger.info(f"⏰ Начинаем повторную подписку на {len(rate_limited_channels)} каналов")
        
        # Ждем максимальное время из всех rate limit + небольшой запас
        max_wait = max(wait_time for _, _, wait_time in rate_limited_channels) + 10
        logger.info(f"⏳ Ждем {max_wait} секунд перед повторными попытками...")
        await asyncio.sleep(max_wait)
        
        successful_retries = 0
        failed_retries = 0
        
        for entity, username, original_wait_time in rate_limited_channels:
            try:
                logger.info(f"🔄 Повторная попытка подписки на {username}")
                await self.telegram_monitor.client(JoinChannelRequest(entity))
                logger.info(f"✅ Успешно подписался на {username} (повторная попытка)")
                successful_retries += 1
                await asyncio.sleep(5)  # Пауза между повторными попытками
            except Exception as retry_error:
                error_msg = str(retry_error).lower()
                if "already" in error_msg or "участник" in error_msg:
                    logger.info(f"🔄 Уже подписан на {username} (повторная попытка)")
                    successful_retries += 1
                else:
                    logger.warning(f"⚠️ Повторная попытка подписки на {username} неудачна: {retry_error}")
                    failed_retries += 1
        
        # Отправляем отчет о повторных попытках
        if successful_retries > 0 or failed_retries > 0:
            retry_report = (
                f"🔄 <b>Повторная подписка завершена</b>\n\n"
                f"✅ Успешно: <b>{successful_retries}</b> каналов\n"
                f"⚠️ Не удалось: <b>{failed_retries}</b> каналов\n\n"
                f"🎉 Теперь все доступные каналы подключены!"
            )
            try:
                await self.telegram_bot.send_message(retry_report)
                logger.info(f"📊 Повторная подписка: {successful_retries} успешно, {failed_retries} неудачно")
            except Exception as e:
                logger.error(f"❌ Ошибка отправки отчета о повторной подписке: {e}")
    
    async def check_all_channels_for_new_messages(self):
        """Простая проверка всех каналов на новые сообщения и их пересылка"""
        try:
            # Загружаем конфигурацию каналов
            channels_config_path = "config/channels_config.yaml"
            with open(channels_config_path, 'r', encoding='utf-8') as f:
                channels_data = yaml.safe_load(f)
            
            all_channels = []
            # Собираем все каналы (VIP и обычные)
            if 'vip_channels' in channels_data:
                all_channels.extend(channels_data['vip_channels'])
            if 'regular_channels' in channels_data:
                all_channels.extend(channels_data['regular_channels'])
            
            logger.info(f"📡 Проверка {len(all_channels)} каналов на новые сообщения...")
            
            total_new_messages = 0
            for channel_config in all_channels:
                try:
                    # Получаем новые сообщения простым способом
                    new_messages = await self.telegram_monitor.get_new_messages_simple(channel_config)
                    
                    # Отправляем каждое новое сообщение
                    for message in new_messages:
                        await self.send_text_with_link(message)
                        total_new_messages += 1
                        # Небольшая пауза между сообщениями
                        await asyncio.sleep(2)
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка проверки канала {channel_config.get('username', 'unknown')}: {e}")
            
            if total_new_messages > 0:
                logger.info(f"✅ Отправлено {total_new_messages} новых сообщений")
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки каналов: {e}")
    
    async def process_vip_channels(self):
        """Обработка VIP каналов"""
        if not self.telegram_monitor:
            return
        
        try:
            channels = self.config.get('channels', [])
            vip_channels = [ch for ch in channels if ch.get('vip', False)]
            
            if not vip_channels:
                return
            
            result = await self.news_processor.process_vip_channels_batch(vip_channels)
            
            # Отправляем только новые новости, которые еще не отправлялись
            if result.get('selected_news'):
                selected_news = result['selected_news']
                if selected_news:
                    # Фильтруем только новые неотправленные новости
                    new_news = await self.filter_unsent_news(selected_news)
                    if new_news:
                        # Отправляем каждую новость отдельно
                        for i, news in enumerate(new_news):
                            await self.send_single_news(news)
                            # Отмечаем как отправленную
                            await self.database.mark_digest_sent([news['id']])
                            # Небольшая задержка между отправками
                            if i < len(new_news) - 1:
                                await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки VIP каналов: {e}")
    
    async def process_regular_channels(self):
        """Обработка обычных каналов"""
        if not self.telegram_monitor:
            return
        
        try:
            channels = self.config.get('channels', [])
            regular_channels = [ch for ch in channels if not ch.get('vip', False)]
            
            if not regular_channels:
                return
            
            result = await self.news_processor.process_regular_channels_batch(regular_channels)
            
            # Отправляем только новые новости, которые еще не отправлялись
            if result.get('selected_news'):
                selected_news = result['selected_news']
                if selected_news:
                    # Фильтруем только новые неотправленные новости
                    new_news = await self.filter_unsent_news(selected_news)
                    if new_news:
                        # Отправляем каждую новость отдельно
                        for i, news in enumerate(new_news):
                            await self.send_single_news(news)
                            # Отмечаем как отправленную
                            await self.database.mark_digest_sent([news['id']])
                            # Небольшая задержка между отправками
                            if i < len(new_news) - 1:
                                await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки обычных каналов: {e}")
    
    async def send_single_news(self, news: Dict):
        """Отправка одной новости в Telegram"""
        try:
            # Всегда отправляем текст + ссылку (как вы просили)
            await self.send_text_with_link(news)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки новости: {e}")
    
    async def forward_original_message(self, news: Dict) -> bool:
        """Пересылка оригинального сообщения"""
        try:
            channel_username = news.get('channel_username')
            message_id = news.get('message_id')
            
            logger.info(f"🔄 Попытка пересылки медиа из @{channel_username}, message_id: {message_id}")
            
            if not channel_username or not message_id:
                logger.warning("❌ Нет channel_username или message_id для пересылки")
                return False
            
            # Целевой канал для отправки (предпочтительно output.target_channel)
            target = self.config.get('output', {}).get('target_channel')
            
            # Если target_channel не настроен или является заглушкой - используем chat_id бота
            if not target or target in ["@your_news_channel", "your_news_channel"]:
                target = self.config.get('bot', {}).get('chat_id')
                logger.info(f"📱 Используем chat_id бота для пересылки: {target}")
            else:
                logger.info(f"📺 Используем target_channel для пересылки: {target}")
            
            if not target:
                logger.error("❌ Нет target для пересылки медиа")
                return False
            
            # Получаем исходный канал
            entity = await self.telegram_monitor.get_channel_entity(channel_username)
            if not entity:
                logger.error(f"❌ Не удалось получить entity для {channel_username}")
                return False
            
            # Разрешаем цель
            target_entity = None
            try:
                if isinstance(target, int) or (isinstance(target, str) and target.lstrip('-').isdigit()):
                    target_entity = await self.telegram_monitor.client.get_entity(int(target))
                    logger.info(f"✅ Получен target_entity для chat_id: {target}")
                elif isinstance(target, str) and target.startswith("https://t.me/+"):
                    # Обработка приватной ссылки канала
                    logger.info(f"🔗 Обрабатываем приватную ссылку канала: {target}")
                    # Извлекаем hash из ссылки
                    invite_hash = target.split("https://t.me/+")[1]
                    
                    # Пытаемся присоединиться к каналу по ссылке-приглашению
                    from telethon.tl.functions.messages import ImportChatInviteRequest
                    try:
                        updates = await self.telegram_monitor.client(ImportChatInviteRequest(invite_hash))
                        # Получаем канал из обновлений
                        if hasattr(updates, 'chats') and updates.chats:
                            target_entity = updates.chats[0]
                            logger.info(f"✅ Присоединились к приватному каналу и получили entity")
                        else:
                            logger.error("❌ Не удалось получить entity после присоединения")
                    except Exception as join_error:
                        # Возможно уже состоим в канале
                        logger.warning(f"⚠️ Ошибка присоединения (возможно уже в канале): {join_error}")
                        # Пытаемся получить entity по hash
                        try:
                            target_entity = await self.telegram_monitor.client.get_entity(f"https://t.me/+{invite_hash}")
                            logger.info(f"✅ Получен entity для приватного канала")
                        except Exception as entity_error:
                            logger.error(f"❌ Не удалось получить entity для приватного канала: {entity_error}")
                else:
                    # Удаляем @ если есть для обычных каналов
                    target_name = target[1:] if isinstance(target, str) and target.startswith('@') else target
                    target_entity = await self.telegram_monitor.get_channel_entity(target_name)
                    logger.info(f"✅ Получен target_entity для канала: {target_name}")
            except Exception as e:
                logger.error(f"❌ Ошибка получения target_entity: {e}")
                target_entity = None
                
            if not target_entity:
                logger.error("❌ Не удалось получить target_entity")
                return False

            # Пересылаем сообщение
            logger.info(f"📤 Отправляем пересылку...")
            forwarded = await self.telegram_monitor.client.forward_messages(
                entity=target_entity,
                messages=message_id,
                from_peer=entity
            )
            
            if forwarded:
                logger.info(f"✅ Сообщение переслано из {channel_username}")
                return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка пересылки: {e}")
        
        return False
    
    async def download_and_send_media(self, news: Dict) -> bool:
        """Скачать медиа файлы через Telethon и отправить через Bot API"""
        try:
            import os
            import tempfile
            from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
            
            channel_username = news.get('channel_username')
            message_id = news.get('message_id')
            text = news.get('text', '')
            
            logger.info(f"📥 Скачиваем медиа из @{channel_username}, message_id: {message_id}")
            logger.info(f"📝 Текст сообщения (длина {len(text)}): {text[:100]}{'...' if len(text) > 100 else ''}")
            
            # Получаем исходное сообщение
            entity = await self.telegram_monitor.get_channel_entity(channel_username)
            if not entity:
                logger.error(f"❌ Не удалось получить entity для {channel_username}")
                return False
            
            # Получаем сообщение
            message = await self.telegram_monitor.client.get_messages(entity, ids=message_id)
            if not message or not message.media:
                logger.warning("❌ Сообщение не найдено или не содержит медиа")
                return False
            
            # Проверяем есть ли grouped_id (медиа группа)
            messages_to_process = [message]
            if hasattr(message, 'grouped_id') and message.grouped_id:
                logger.info(f"🖼️ Обнаружена медиа группа (grouped_id: {message.grouped_id})")
                # Получаем все сообщения из группы
                all_messages = await self.telegram_monitor.client.get_messages(entity, limit=50)
                group_messages = [msg for msg in all_messages if hasattr(msg, 'grouped_id') and msg.grouped_id == message.grouped_id]
                # Сортируем по ID для правильного порядка
                messages_to_process = sorted(group_messages, key=lambda x: x.id)
                logger.info(f"📦 Найдено {len(messages_to_process)} медиа в группе")
                
                # Ищем текст среди всех сообщений в группе
                for msg in messages_to_process:
                    if msg.text and msg.text.strip():
                        text = msg.text.strip()
                        news['text'] = text  # Обновляем текст в news
                        logger.info(f"📝 Найден текст в медиа-группе (длина {len(text)}): {text[:100]}{'...' if len(text) > 100 else ''}")
                        break
            
            # Анализируем медиа файлы и скачиваем только фото
            media_files = []
            temp_files = []
            video_count = 0
            photo_count = 0
            
            # Сначала подсчитываем типы медиа
            for msg in messages_to_process:
                if not msg.media:
                    continue
                    
                if isinstance(msg.media, MessageMediaPhoto):
                    photo_count += 1
                elif isinstance(msg.media, MessageMediaDocument):
                    document = msg.media.document
                    if document.mime_type:
                        if document.mime_type.startswith('image/'):
                            photo_count += 1
                        elif document.mime_type.startswith('video/'):
                            video_count += 1
            
            logger.info(f"📊 В группе: {photo_count} фото, {video_count} видео")
            
            # Скачиваем только фото/изображения
            for i, msg in enumerate(messages_to_process):
                if not msg.media:
                    continue
                    
                # Определяем тип медиа и расширение
                media_type = "document"
                file_extension = ".bin"
                should_download = False
                
                if isinstance(msg.media, MessageMediaPhoto):
                    media_type = "photo"
                    file_extension = ".jpg"
                    should_download = True
                elif isinstance(msg.media, MessageMediaDocument):
                    document = msg.media.document
                    if document.mime_type:
                        if document.mime_type.startswith('image/'):
                            media_type = "photo"
                            file_extension = ".jpg"
                            should_download = True
                        elif document.mime_type.startswith('video/'):
                            logger.info(f"🎬 Пропускаем видео {i+1} (слишком долго скачивается)")
                            continue
                        elif document.mime_type.startswith('audio/'):
                            media_type = "document"
                            file_extension = ".mp3"
                            should_download = True
                    
                    # Проверяем атрибуты для дополнительной информации
                    for attr in document.attributes:
                        if hasattr(attr, 'file_name') and attr.file_name:
                            file_extension = os.path.splitext(attr.file_name)[1] or file_extension
                            break
                
                if should_download:
                    # Создаем временный файл
                    with tempfile.NamedTemporaryFile(suffix=f"_{i}{file_extension}", delete=False) as temp_file:
                        temp_path = temp_file.name
                        temp_files.append(temp_path)
                    
                    # Скачиваем медиа
                    logger.info(f"💾 Скачиваем {media_type} {len(media_files)+1}")
                    await self.telegram_monitor.client.download_media(msg, temp_path)
                    media_files.append((temp_path, media_type))
            
            # Если нет скачанных файлов (только видео), отправляем текстовое уведомление
            if not media_files:
                if video_count > 0:
                    logger.info(f"🎬 Пост содержит только видео ({video_count} шт.), отправляем текстовое уведомление")
                    # Добавляем информацию о видео в news
                    news['video_count'] = video_count
                    news['photo_count'] = photo_count
                    await self.send_message_to_target(news, is_media=True)
                    return True
                else:
                    logger.warning("❌ Не удалось скачать медиа файлы")
                    return False
            
            try:
                # Формируем подпись
                vladivostok_tz = pytz.timezone('Asia/Vladivostok')
                date = news.get('date')
                if date:
                    try:
                        if isinstance(date, str):
                            date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                        if date.tzinfo is None:
                            date = date.replace(tzinfo=pytz.UTC)
                        date_vlk = date.astimezone(vladivostok_tz)
                        date_str = f"\n📅 {date_vlk.strftime('%d.%m.%Y %H:%M')} (Владивосток)"
                    except:
                        date_str = ""
                else:
                    date_str = ""
                
                caption = f"<b>@{channel_username}</b>"
                if text:
                    # Конвертируем markdown в HTML и ограничиваем длину
                    clean_text = self.convert_markdown_to_html(text.strip())
                    if len(clean_text) > 800:
                        clean_text = clean_text[:800] + "..."
                    caption += f"\n\n{clean_text}"
                    logger.info(f"📝 Добавлен текст в caption: {clean_text[:50]}...")
                else:
                    logger.warning("⚠️ Текст сообщения пустой!")
                
                if date_str:
                    caption += f"\n{date_str}"  # Добавляем пустую строку перед датой
                
                
                # Добавляем информацию о видео, если есть
                if video_count > 0:
                    video_text = f"{video_count} видео" if video_count > 1 else "видео"
                    caption += f"\n\n🎬 В посте также есть {video_text}"
                
                url = news.get('url')
                if url:
                    caption += f"\n\n🔗 {url}"
                
                logger.info(f"📋 Итоговый caption (длина {len(caption)}): {caption[:150]}{'...' if len(caption) > 150 else ''}")
                
                # Добавляем информацию о медиа в news для статистики
                news['video_count'] = video_count
                news['photo_count'] = photo_count
                
                # Обновляем news данными о медиа для отправки через send_message_to_target
                news['media_files'] = media_files
                news['caption'] = caption
                news['text'] = caption  # Для совместимости с send_message_to_target
                
                # Отправляем через send_message_to_target для правильной сортировки по темам
                await self.send_message_to_target(news, is_media=True)
                success = True
                
                if success:
                    logger.info(f"✅ Медиа успешно отправлено: {len(media_files)} файл(ов)")
                    return True
                else:
                    logger.error("❌ Не удалось отправить медиа")
                    return False
                
            finally:
                # Удаляем временные файлы
                for temp_path in temp_files:
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                logger.info(f"🗑️ Удалено {len(temp_files)} временных файлов")
            
        except Exception as e:
            logger.error(f"❌ Ошибка скачивания и отправки медиа: {e}")
            return False
    
    async def send_formatted_news(self, news: Dict):
        """Отправка отформатированной новости (запасной вариант)"""
        try:
            # Отправляем сообщение с правильным HTML форматированием
            text = news.get('text', '')
            # Конвертируем markdown в HTML
            text = self.convert_markdown_to_html(text)
            channel_name = news.get('channel_name', news.get('channel_username', 'Неизвестный источник'))
            url = news.get('url', '')
            
            # Простое сообщение без ** и лишних символов
            message_parts = [
                text,
                "",
                f"Источник: {channel_name}"
            ]
            
            if url:
                message_parts.append(f"Читать: {url}")
            
            message = "\n".join(message_parts)
            
            # Отправляем через бота
            success = await self.telegram_bot.send_message(message, parse_mode="HTML")  # С HTML форматированием
            if success:
                logger.info(f"✅ Новость отправлена: {text[:50]}...")
            else:
                logger.error(f"❌ Ошибка отправки новости")
            
        except Exception as e:
            logger.error(f"❌ Ошибка форматирования новости: {e}")
    
    async def send_media_via_bot(self, news: Dict):
        """Отправка сообщения с файлами через бота"""
        try:
            text = news.get('text', '')
            url = news.get('url', '')
            channel_username = news.get('channel_username', '')
            date = news.get('date')
            
            # Форматируем дату в владивостокском времени
            date_str = ""
            if date:
                try:
                    if hasattr(date, 'strftime'):
                        # Показываем владивостокское время с указанием часового пояса
                        date_str = f"\n📅 {date.strftime('%d.%m.%Y %H:%M')} (Владивосток)"
                    else:
                        date_str = f"\n📅 {date}"
                except:
                    pass
            
            # Формируем сообщение
            media_notification = f"<b>@{channel_username}</b>"
            
            if text:
                # Конвертируем markdown в HTML
                clean_text = self.convert_markdown_to_html(text)
                media_notification += f"\n\n{clean_text}"
            
            if date_str:
                media_notification += f"\n{date_str}"  # Добавляем пустую строку перед датой
            
            # Добавляем информацию о медиа контенте
            video_count = news.get('video_count', 0)
            photo_count = news.get('photo_count', 0)
            
            if video_count > 0 or photo_count > 0:
                media_info = []
                if photo_count > 0:
                    photo_text = f"{photo_count} фото" if photo_count > 1 else "фото"
                    media_info.append(f"📸 {photo_text}")
                if video_count > 0:
                    video_text = f"{video_count} видео" if video_count > 1 else "видео"
                    media_info.append(f"🎬 {video_text}")
                
                if media_info:
                    media_notification += f"\n\n{' + '.join(media_info)}"
            
            if url:
                media_notification += f"\n\n🔗 {url}"
            
            # Отправляем через бота
            success = await self.telegram_bot.send_message(media_notification)
            if success:
                logger.info(f"✅ Сообщение отправлено: @{channel_username}")
            else:
                logger.error("❌ Ошибка отправки сообщения")
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения: {e}")
    
    async def send_message_to_target(self, news: Dict, is_media: bool = False):
        """Универсальная отправка сообщения в канал или чат с сортировкой по темам"""
        try:
            # Проверяем, является ли сообщение алертом
            is_alert = news.get('is_alert', False)
            alert_priority = news.get('alert_priority', False)
            alert_category = news.get('alert_category', '')
            
            if is_alert:
                logger.warning(f"🚨 Отправляем АЛЕРТ: категория={alert_category}, приоритет={alert_priority}")
                
                # Для высокоприоритетных алертов можно добавить дополнительные действия:
                if alert_priority:
                    # Например, отправить уведомление администратору
                    logger.error(f"🚨 ВЫСОКИЙ ПРИОРИТЕТ! {alert_category}")
            
            # Определяем ВСЕ регионы канала и соответствующие темы
            channel_username = news.get('channel_username', '')
            regions = self.get_channel_regions(channel_username)
            
            # Получаем настройки вывода
            output_config = self.config.get('output', {})
            target = output_config.get('target_group') or output_config.get('target_channel')
            
            logger.info(f"📂 Канал @{channel_username} найден в регионах: {regions}")
            
            # Получаем все ID тем для регионов
            topics = output_config.get('topics', {})
            region_threads = []
            
            for region in regions:
                thread_id = topics.get(region) if topics else None
                region_threads.append((region, thread_id))
                
                if thread_id:
                    logger.info(f"📂 Канал @{channel_username} → регион '{region}' → тема {thread_id}")
                else:
                    logger.info(f"📂 Канал @{channel_username} → регион '{region}' → общая лента (темы отключены)")
            
            # Если target не настроен - используем chat_id бота (личный чат)  
            if not target or target in ["@your_news_channel", "your_news_channel"]:
                # Отправляем в личный чат через бота
                if is_media:
                    await self.send_media_via_bot(news)
                else:
                    await self.send_text_with_link(news)
                return
            
            # Отправляем в канал
            logger.info(f"📤 Отправляем сообщение в канал: {target}")
            
            # Формируем текст сообщения
            text = news.get('text', '')
            url = news.get('url', '')
            channel_username = news.get('channel_username', '')
            date = news.get('date')
            
            # Конвертируем markdown в HTML
            text = self.convert_markdown_to_html(text)
            
            # Форматируем дату
            date_str = ""
            if date:
                try:
                    if hasattr(date, 'strftime'):
                        date_str = f"\n📅 {date.strftime('%d.%m.%Y %H:%M')} (Владивосток)"
                    else:
                        date_str = f"\n📅 {date}"
                except:
                    pass
            
            # Формируем сообщение
            if is_media:
                message = f"<b>@{channel_username}</b>"
                if text:
                    message += f"\n\n{text}"
                if date_str:
                    message += f"\n{date_str}"  # Добавляем пустую строку перед датой
                
                # Добавляем информацию о медиа контенте
                video_count = news.get('video_count', 0)
                photo_count = news.get('photo_count', 0)
                
                if video_count > 0 or photo_count > 0:
                    media_info = []
                    if photo_count > 0:
                        photo_text = f"{photo_count} фото" if photo_count > 1 else "фото"
                        media_info.append(f"📸 {photo_text}")
                    if video_count > 0:
                        video_text = f"{video_count} видео" if video_count > 1 else "видео"
                        media_info.append(f"🎬 {video_text}")
                    
                    if media_info:
                        message += f"\n\n{' + '.join(media_info)}"
                
                if url:
                    message += f"\n\n🔗 {url}"
            else:
                message = f"<b>@{channel_username}</b>"
                if text:
                    message += f"\n\n{text}"
                if date_str:
                    message += f"\n{date_str}"  # Добавляем пустую строку перед датой
                if url:
                    message += f"\n\n{url}"
            
            # Отправляем через бота в канал (во все регионы/темы)
            all_success = True
            sent_count = 0
            
            for region, thread_id in region_threads:
                try:
                    logger.info(f"📤 Отправляем в регион '{region}' (тема: {thread_id or 'общая'})")
                    
                    if is_media and news.get('media_files'):
                        # Отправляем медиа файлы с caption
                        media_files = news.get('media_files', [])
                        caption = news.get('caption', message)  # Используем message как caption если caption не задан
                        
                        # Если один файл - отправляем как обычное медиа, если несколько - как группу
                        if len(media_files) == 1:
                            success = await self.telegram_bot.send_media_with_caption(
                                media_files[0][0], caption, target, media_files[0][1], thread_id
                            )
                        else:
                            success = await self.telegram_bot.send_media_group(
                                media_files, caption, target, thread_id
                            )
                    else:
                        # Отправляем текстовое сообщение
                        success = await self.telegram_bot.send_message_to_channel(message, target, "HTML", thread_id)
                    
                    if success:
                        logger.info(f"✅ Сообщение отправлено в регион '{region}'")
                        sent_count += 1
                    else:
                        logger.error(f"❌ Ошибка отправки в регион '{region}'")
                        all_success = False
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки в регион '{region}': {e}")
                    all_success = False
            
            if sent_count > 0:
                logger.info(f"✅ Сообщение отправлено в {sent_count}/{len(region_threads)} регионов")
            else:
                logger.error("❌ Ошибка отправки во все регионы")
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки в канал: {e}")

    async def send_text_with_link(self, news: Dict):
        """Отправляем простой текст поста + дату/время + ссылку на пост"""
        try:
            text = news.get('text', '')
            url = news.get('url', '')
            date = news.get('date')
            channel_username = news.get('channel_username', '')
            
            # Конвертируем markdown в HTML
            text = self.convert_markdown_to_html(text)
            
            # Форматируем дату и время в владивостокском времени
            date_str = ""
            if date:
                try:
                    if hasattr(date, 'strftime'):
                        date_str = f"\n📅 {date.strftime('%d.%m.%Y %H:%M')} (Владивосток)"
                    else:
                        date_str = f"\n📅 {date}"
                except:
                    pass
            
            # Формируем сообщение: @канал + текст + дата + ссылка
            message = f"<b>@{channel_username}</b>"
            if text:
                message += f"\n\n{text}"
            if date_str:
                message += f"\n{date_str}"  # Добавляем пустую строку перед датой
            if url:
                message += f"\n\n{url}"
            
            # Отправляем с HTML форматированием для @канала
            success = await self.telegram_bot.send_message(message, parse_mode="HTML")
            if success:
                logger.info(f"✅ Новость отправлена: {text[:50]}...")
            else:
                logger.error("❌ Ошибка отправки новости")
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки новости: {e}")
    
    async def filter_unsent_news(self, selected_news: List[Dict]) -> List[Dict]:
        """Фильтрует только неотправленные новости"""
        try:
            vladivostok_tz = pytz.timezone('Asia/Vladivostok')
            today = datetime.now(vladivostok_tz).date()
            
            # Получаем ID уже отправленных новостей через синхронное соединение
            with self.database._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT news_ids FROM sent_digests WHERE date = ?",
                    (today,)
                )
                sent_results = cursor.fetchall()
            
            sent_ids = set()
            for row in sent_results:
                if row[0]:
                    sent_ids.update(row[0].split(','))
            
            # Фильтруем только неотправленные
            new_news = []
            for news in selected_news:
                if news['id'] not in sent_ids:
                    new_news.append(news)
            
            logger.info(f"🔍 Отфильтровано {len(new_news)} новых из {len(selected_news)} отобранных")
            return new_news
            
        except Exception as e:
            logger.error(f"❌ Ошибка фильтрации новостей: {e}")
            return selected_news  # В случае ошибки возвращаем все
    
    async def send_status_update(self):
        """Отправка обновления статуса"""
        try:
            stats = await self.database.get_today_stats()
            system_stats = {
                'memory_percent': self.system_monitor.get_memory_usage()['used_percent'],
                'cpu_percent': self.system_monitor.get_cpu_usage()['cpu_percent']
            }
            
            combined_stats = {**stats, **system_stats}
            await self.telegram_bot.send_status_update(combined_stats)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки статуса: {e}")
    
    async def auto_cleanup_old_data(self):
        """Автоматическая очистка старых данных"""
        try:
            logger.info("🧹 Запуск автоматической очистки старых данных...")
            
            # Очищаем данные старше 7 дней
            await self.database.cleanup_old_data(days_to_keep=7)
            
            # Получаем статистику после очистки
            with self.database._get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM messages")
                messages_count = cursor.fetchone()[0]
            
            logger.info(f"✅ Автоочистка завершена. Осталось сообщений: {messages_count}")
            
            # Уведомляем в Telegram
            await self.telegram_bot.send_message(
                f"🧹 <b>Автоматическая очистка</b>\n\n"
                f"📊 Удалены старые данные (>7 дней)\n"
                f"📰 Сообщений в базе: {messages_count}\n"
                f"🕐 {datetime.now(pytz.timezone('Asia/Vladivostok')).strftime('%d.%m.%Y %H:%M:%S')} (Владивосток)"
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка автоочистки: {e}")
    
    async def shutdown(self):
        """Корректное завершение работы"""
        logger.info("🛑 Завершение работы системы...")
        self.running = False
        
        try:
            if self.telegram_bot:
                # Останавливаем прослушивание команд
                self.telegram_bot.stop_listening()
                
                await self.telegram_bot.send_message(
                    "🛑 <b>Система мониторинга остановлена</b>\n\n"
                    f"🕐 {datetime.now(pytz.timezone('Asia/Vladivostok')).strftime('%d.%m.%Y %H:%M:%S')} (Владивосток)"
                )
            
            if self.database:
                await self.database.close()
            
            if self.telegram_monitor:
                await self.telegram_monitor.disconnect()
            
            if self.web_interface:
                self.web_interface.stop_server()
            
            # Очищаем кэш медиа групп
            self.processed_media_groups.clear()
            logger.info("🧹 Кэш медиа групп очищен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при завершении: {e}")
        
        logger.info("👋 Система завершена")
    
    async def run(self):
        """Основной метод запуска"""
        try:
            # Загружаем конфигурацию
            if not self.load_config():
                return False
            
            # Загружаем алерты по ключевым словам
            self.load_alert_keywords()
            
            # Загружаем конфигурацию регионов
            self.load_regions_config()
            
            # Настраиваем логирование
            self.setup_logging()
            
            # Инициализируем компоненты
            if not await self.initialize_components():
                return False
            
            # Запускаем основной цикл
            self.running = True
            await self.monitoring_cycle()
            
        except KeyboardInterrupt:
            logger.info("👋 Получен сигнал завершения (Ctrl+C)")
        except Exception as e:
            logger.error(f"💥 Критическая ошибка: {e}")
            if self.telegram_bot:
                await self.telegram_bot.send_error_alert(f"Критическая ошибка: {e}")
            return False
        finally:
            await self.shutdown()
        
        return True


async def main():
    """Главная функция"""
    print("🤖 Запуск Telegram News Monitor Bot...")
    print(f"📁 Рабочая директория: {os.getcwd()}")
    print(f"🐍 Python версия: {sys.version}")
    
    bot = NewsMonitorWithBot()
    success = await bot.run()
    
    if success:
        print("✅ Бот завершил работу корректно")
    else:
        print("❌ Бот завершился с ошибками")
    
    return success


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n👋 Завершение работы по Ctrl+C")
        sys.exit(0)
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        sys.exit(1)
