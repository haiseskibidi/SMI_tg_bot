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


try:
    from ..ai.urgency_detector import initialize_urgency_detector
    AI_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ AI модуль недоступен")
    AI_AVAILABLE = False


class NewsMonitorWithBot:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.running = False
        self.monitoring_active = True
        
        
        self.config_loader = ConfigLoader(config_path)
        self.lifecycle_manager = LifecycleManager(self.config_loader)
        self.subscription_cache = SubscriptionCacheManager()
        
        
        self.database = None
        self.telegram_monitor = None
        self.telegram_bot = None
        self.news_processor = None
        self.system_monitor = None
        
        
        self.message_processor = None
        self.channel_monitor = None
        
        
        self.processed_media_groups: Set[int] = set()

    async def pause_monitoring(self):
        """Остановка мониторинга с сохранением системы"""
        try:
            self.monitoring_active = False
            
            
            if self.channel_monitor and hasattr(self.channel_monitor, 'stop_monitoring'):
                await self.channel_monitor.stop_monitoring()
            
            
            if self.telegram_monitor and hasattr(self.telegram_monitor, 'pause_handlers'):
                await self.telegram_monitor.pause_handlers()
            
            logger.info("⏸️ Мониторинг полностью приостановлен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке мониторинга: {e}")

    async def resume_monitoring(self):
        """Возобновление мониторинга"""
        try:
            self.monitoring_active = True
            
            
            if self.channel_monitor and hasattr(self.channel_monitor, 'start_monitoring'):
                await self.channel_monitor.start_monitoring()
            
            
            if self.telegram_monitor and hasattr(self.telegram_monitor, 'resume_handlers'):
                await self.telegram_monitor.resume_handlers()
            elif self.channel_monitor:
                
                await self.channel_monitor.setup_realtime_handlers()
            
            logger.info("▶️ Мониторинг полностью возобновлен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске мониторинга: {e}")



    def clean_text_formatting(self, text: str) -> str:
        """Простая очистка текста от markdown символов"""
        if not text:
            return ""
        
        
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  
        text = re.sub(r'\*(.*?)\*', r'\1', text)      
        text = re.sub(r'__(.*?)__', r'\1', text)      
        text = re.sub(r'~~(.*?)~~', r'\1', text)      
        text = re.sub(r'`(.*?)`', r'\1', text)        
        text = re.sub(r'```(.*?)```', r'\1', text, flags=re.DOTALL)  
        
        return text



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
            alert_header = f"{emoji} АЛЕРТ: {category.upper()}\n"
            alert_header += f"📺 Канал: @{channel_username}\n"
            alert_header += f"🔍 Ключевые слова: {', '.join(matched_words)}\n"
            alert_header += "─" * 30 + "\n\n"
            
            return alert_header + original_text
        except Exception as e:
            logger.error(f"❌ Ошибка форматирования алерта: {e}")
            return original_text

    def get_channel_regions(self, channel_username: str) -> list:
        found_regions = []
        
        
        try:
            import yaml
            with open('config/channels_config.yaml', 'r', encoding='utf-8') as f:
                channels_config = yaml.safe_load(f)
                
            if channels_config and 'regions' in channels_config:
                for region_key, region_data in channels_config['regions'].items():
                    channels = region_data.get('channels', [])
                    for channel in channels:
                        if channel.get('username') == channel_username:
                            found_regions.append(region_key)
                            logger.debug(f"📍 Канал @{channel_username} найден в channels_config.yaml → {region_key}")
                            return found_regions  
        except Exception as e:
            logger.warning(f"⚠️ Ошибка чтения channels_config.yaml: {e}")
        
        
        regions_config = self.config_loader.get_regions_config()
        for region_key, region_data in regions_config.items():
            keywords = region_data.get('keywords', [])
            for keyword in keywords:
                if keyword.lower() in channel_username.lower():
                    found_regions.append(region_key)
                    logger.debug(f"📍 Канал @{channel_username} найден по ключевому слову '{keyword}' → {region_key}")
                    break
        
        
        if not found_regions:
            found_regions.append('general')
            logger.debug(f"📍 Канал @{channel_username} не найден → general")
        
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
                
                await self.telegram_bot.send_startup_notification()
                logger.info("📢 Отправлено уведомление о запуске системы")
            
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
        
        
        self.database = self.lifecycle_manager.database
        self.telegram_monitor = self.lifecycle_manager.telegram_monitor
        self.telegram_bot = self.lifecycle_manager.telegram_bot
        self.news_processor = self.lifecycle_manager.news_processor
        self.system_monitor = self.lifecycle_manager.system_monitor
        
        
        if self.telegram_bot:
            self.telegram_bot.monitor_bot = self
            logger.info("✅ Monitor bot установлен в Telegram бота")
        
        
        if self.telegram_monitor:
            self.message_processor = MessageProcessor(self.database, self)
            self.channel_monitor = ChannelMonitor(
                self.telegram_monitor,
                self.subscription_cache,
                self.message_processor,
                self.config_loader  
            )
        
        
        if AI_AVAILABLE:
            try:
                logger.info("🤖 Инициализация AI модулей...")
                await initialize_urgency_detector()
                logger.success("✅ AI модули успешно инициализированы")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации AI: {e}")
                logger.warning("⚠️ Продолжаем работу без AI анализа")
        else:
            logger.info("ℹ️ AI модули недоступны - используется базовая логика")
        
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

    async def send_message_to_target(self, news: Dict, is_media: bool = False):
        """Универсальная отправка сообщения в канал или чат с сортировкой по темам"""
        try:
            is_alert = news.get('is_alert', False)
            alert_priority = news.get('alert_priority', False)
            alert_category = news.get('alert_category', '')
            
            if is_alert:
                logger.warning(f"🚨 Отправляем АЛЕРТ: категория={alert_category}, приоритет={alert_priority}")
                
                if alert_priority:
                    logger.error(f"🚨 ВЫСОКИЙ ПРИОРИТЕТ! {alert_category}")
            
            channel_username = news.get('channel_username', '')
            regions = self.get_channel_regions(channel_username)
            
            config = self.config_loader.get_config() or {}
            output_config = config.get('output', {})
            target = output_config.get('target_group') or output_config.get('target_channel')
            
            logger.info(f"📂 Канал @{channel_username} найден в регионах: {regions}")
            
            topics = output_config.get('topics', {})
            region_threads = []
            
            for region in regions:
                thread_id = topics.get(region) if topics else None
                region_threads.append((region, thread_id))
                
                if thread_id:
                    logger.info(f"📂 Канал @{channel_username} → регион '{region}' → тема {thread_id}")
                else:
                    logger.info(f"📂 Канал @{channel_username} → регион '{region}' → общая лента (темы отключены)")
            
            if not target or target in ["@your_news_channel", "your_news_channel"]:
                if is_media:
                    await self.send_media_via_bot(news)
                else:
                    await self.send_text_with_link(news)
                return
            
            logger.info(f"📤 Отправляем сообщение в канал: {target}")
            
            text = news.get('text', '')
            url = news.get('url', '')
            channel_username = news.get('channel_username', '')
            date = news.get('date')
            
            text = self.clean_text_formatting(text)
            
            date_str = ""
            if date:
                try:
                    if hasattr(date, 'strftime'):
                        date_str = f"\n📅 {date.strftime('%d.%m.%Y %H:%M')} (Владивосток)"
                    else:
                        date_str = f"\n📅 {date}"
                except:
                    pass
            
            if is_media:
                message = f"@{channel_username}"
                if text:
                    message += f"\n\n{text}"
                if date_str:
                    message += f"\n{date_str}"
                
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
                message = f"@{channel_username}"
                if text:
                    message += f"\n\n{text}"
                if date_str:
                    message += f"\n{date_str}"
                if url:
                    message += f"\n\n{url}"
            
            all_success = True
            sent_count = 0
            
            for region, thread_id in region_threads:
                try:
                    logger.info(f"📤 Отправляем в регион '{region}' (тема: {thread_id or 'общая'})")
                    
                    if is_media and news.get('media_files'):
                        media_files = news.get('media_files', [])
                        caption = news.get('caption', message)
                        
                        if len(media_files) == 1:
                            success = await self.telegram_bot.send_media_with_caption(
                                media_files[0][0], caption, target, media_files[0][1], thread_id
                            )
                        else:
                            success = await self.telegram_bot.send_media_group(
                                media_files, caption, target, thread_id
                            )
                    else:
                        success = await self.telegram_bot.send_message_to_channel(message, target, None, thread_id)
                    
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

    async def forward_original_message(self, news: Dict) -> bool:
        """Пересылка оригинального сообщения"""
        try:
            channel_username = news.get('channel_username')
            message_id = news.get('message_id')
            
            logger.info(f"🔄 Попытка пересылки медиа из @{channel_username}, message_id: {message_id}")
            
            if not channel_username or not message_id:
                logger.warning("❌ Нет channel_username или message_id для пересылки")
                return False
            
            config = self.config_loader.get_config() or {}
            target = config.get('output', {}).get('target_channel')
            
            if not target or target in ["@your_news_channel", "your_news_channel"]:
                target = config.get('bot', {}).get('chat_id')
                logger.info(f"📱 Используем chat_id бота для пересылки: {target}")
            else:
                logger.info(f"📺 Используем target_channel для пересылки: {target}")
            
            if not target:
                logger.error("❌ Нет target для пересылки медиа")
                return False
            
            entity = await self.telegram_monitor.get_channel_entity(channel_username)
            if not entity:
                logger.error(f"❌ Не удалось получить entity для {channel_username}")
                return False
            
            target_entity = None
            try:
                if isinstance(target, int) or (isinstance(target, str) and target.lstrip('-').isdigit()):
                    target_entity = await self.telegram_monitor.client.get_entity(int(target))
                    logger.info(f"✅ Получен target_entity для chat_id: {target}")
                elif isinstance(target, str) and target.startswith("https://t.me/+"):
                    logger.info(f"🔗 Обрабатываем приватную ссылку канала: {target}")
                    invite_hash = target.split("https://t.me/+")[1]
                    
                    from telethon.tl.functions.messages import ImportChatInviteRequest
                    try:
                        updates = await self.telegram_monitor.client(ImportChatInviteRequest(invite_hash))
                        if hasattr(updates, 'chats') and updates.chats:
                            target_entity = updates.chats[0]
                            logger.info(f"✅ Присоединились к приватному каналу и получили entity")
                        else:
                            logger.error("❌ Не удалось получить entity после присоединения")
                    except Exception as join_error:
                        logger.warning(f"⚠️ Ошибка присоединения (возможно уже в канале): {join_error}")
                        try:
                            target_entity = await self.telegram_monitor.client.get_entity(f"https://t.me/+{invite_hash}")
                            logger.info(f"✅ Получен entity для приватного канала")
                        except Exception as entity_error:
                            logger.error(f"❌ Не удалось получить entity для приватного канала: {entity_error}")
                else:
                    target_name = target[1:] if isinstance(target, str) and target.startswith('@') else target
                    target_entity = await self.telegram_monitor.get_channel_entity(target_name)
                    logger.info(f"✅ Получен target_entity для канала: {target_name}")
            except Exception as e:
                logger.error(f"❌ Ошибка получения target_entity: {e}")
                target_entity = None
                
            if not target_entity:
                logger.error("❌ Не удалось получить target_entity")
                return False

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
            
            entity = await self.telegram_monitor.get_channel_entity(channel_username)
            if not entity:
                logger.error(f"❌ Не удалось получить entity для {channel_username}")
                return False
            
            message = await self.telegram_monitor.client.get_messages(entity, ids=message_id)
            if not message or not message.media:
                logger.warning("❌ Сообщение не найдено или не содержит медиа")
                return False
            
            messages_to_process = [message]
            if hasattr(message, 'grouped_id') and message.grouped_id:
                logger.info(f"🖼️ Обнаружена медиа группа (grouped_id: {message.grouped_id})")
                all_messages = await self.telegram_monitor.client.get_messages(entity, limit=50)
                group_messages = [msg for msg in all_messages if hasattr(msg, 'grouped_id') and msg.grouped_id == message.grouped_id]
                messages_to_process = sorted(group_messages, key=lambda x: x.id)
                logger.info(f"📦 Найдено {len(messages_to_process)} медиа в группе")
                
                
                ai_processed_text = news.get('text')
                
                for msg in messages_to_process:
                    if msg.text and msg.text.strip():
                        original_text = msg.text.strip()
                        if not ai_processed_text or ai_processed_text.strip() == "":
                            news['text'] = original_text
                            text = original_text  
                            logger.info(f"📝 Найден оригинальный текст в медиа-группе (длина {len(original_text)}): {original_text[:100]}{'...' if len(original_text) > 100 else ''}")
                        else:
                            text = ai_processed_text  
                            logger.info(f"📝 Используем AI обработанный текст (длина {len(ai_processed_text)}): {ai_processed_text[:100]}{'...' if len(ai_processed_text) > 100 else ''}")
                        break
            
            media_files = []
            temp_files = []
            video_count = 0
            photo_count = 0
            
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
            
            for i, msg in enumerate(messages_to_process):
                if not msg.media:
                    continue
                    
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
                    
                    for attr in document.attributes:
                        if hasattr(attr, 'file_name') and attr.file_name:
                            file_extension = os.path.splitext(attr.file_name)[1] or file_extension
                            break
                
                if should_download:
                    with tempfile.NamedTemporaryFile(suffix=f"_{i}{file_extension}", delete=False) as temp_file:
                        temp_path = temp_file.name
                        temp_files.append(temp_path)
                    
                    logger.info(f"💾 Скачиваем {media_type} {len(media_files)+1}")
                    await self.telegram_monitor.client.download_media(msg, temp_path)
                    media_files.append((temp_path, media_type))
            
            if not media_files:
                if video_count > 0:
                    logger.info(f"🎬 Пост содержит только видео ({video_count} шт.), отправляем текстовое уведомление")
                    news['video_count'] = video_count
                    news['photo_count'] = photo_count
                    await self.send_message_to_target(news, is_media=True)
                    return True
                else:
                    logger.warning("❌ Не удалось скачать медиа файлы")
                    return False
            
            try:
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
                
                caption = f"@{channel_username}"
                if text:
                    clean_text = self.clean_text_formatting(text.strip())
                    if len(clean_text) > 800:
                        clean_text = clean_text[:800] + "..."
                    caption += f"\n\n{clean_text}"
                    logger.info(f"📝 Добавлен текст в caption: {clean_text[:50]}...")
                else:
                    logger.warning("⚠️ Текст сообщения пустой!")
                
                if date_str:
                    caption += f"\n{date_str}"
                
                if video_count > 0:
                    video_text = f"{video_count} видео" if video_count > 1 else "видео"
                    caption += f"\n\n🎬 В посте также есть {video_text}"
                
                url = news.get('url')
                if url:
                    caption += f"\n\n🔗 {url}"
                
                logger.info(f"📋 Итоговый caption (длина {len(caption)}): {caption[:150]}{'...' if len(caption) > 150 else ''}")
                
                news['video_count'] = video_count
                news['photo_count'] = photo_count
                news['media_files'] = media_files
                news['caption'] = caption
                news['text'] = caption
                
                await self.send_message_to_target(news, is_media=True)
                success = True
                
                if success:
                    logger.info(f"✅ Медиа успешно отправлено: {len(media_files)} файл(ов)")
                    return True
                else:
                    logger.error("❌ Не удалось отправить медиа")
                    return False
                
            finally:
                for temp_path in temp_files:
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                logger.info(f"🗑️ Удалено {len(temp_files)} временных файлов")
            
        except Exception as e:
            logger.error(f"❌ Ошибка скачивания и отправки медиа: {e}")
            return False

    async def send_media_via_bot(self, news: Dict):
        """Отправка сообщения с файлами через бота"""
        try:
            text = news.get('text', '')
            url = news.get('url', '')
            channel_username = news.get('channel_username', '')
            date = news.get('date')
            
            date_str = ""
            if date:
                try:
                    if hasattr(date, 'strftime'):
                        date_str = f"\n📅 {date.strftime('%d.%m.%Y %H:%M')} (Владивосток)"
                    else:
                        date_str = f"\n📅 {date}"
                except:
                    pass
            
            media_notification = f"@{channel_username}"
            
            if text:
                clean_text = self.clean_text_formatting(text)
                media_notification += f"\n\n{clean_text}"
            
            if date_str:
                media_notification += f"\n{date_str}"
            
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
            
            success = await self.telegram_bot.send_message(media_notification)
            if success:
                logger.info(f"✅ Сообщение отправлено: @{channel_username}")
            else:
                logger.error("❌ Ошибка отправки сообщения")
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения: {e}")

    async def send_text_with_link(self, news: Dict):
        """Отправка текстового сообщения с ссылкой через бота"""
        try:
            text = news.get('text', '')
            url = news.get('url', '')
            channel_username = news.get('channel_username', '')
            date = news.get('date')
            
            clean_text = self.clean_text_formatting(text)
            
            date_str = ""
            if date:
                try:
                    if hasattr(date, 'strftime'):
                        date_str = f"\n📅 {date.strftime('%d.%m.%Y %H:%M')} (Владивосток)"
                    else:
                        date_str = f"\n📅 {date}"
                except:
                    pass
            
            message = f"@{channel_username}"
            if clean_text:
                message += f"\n\n{clean_text}"
            if date_str:
                message += f"\n{date_str}"
            if url:
                message += f"\n\n{url}"
            
            success = await self.telegram_bot.send_message(message)
            if success:
                logger.info(f"✅ Сообщение отправлено: @{channel_username}")
            else:
                logger.error("❌ Ошибка отправки сообщения")
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения: {e}")


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
