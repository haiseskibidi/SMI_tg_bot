"""
📱 Telegram Client Module
Модуль для работы с Telegram API через Telethon
Оптимизирован под VPS с 1GB RAM
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from telethon import TelegramClient, events
from telethon.tl.types import Message, Channel
from loguru import logger
import hashlib


class TelegramMonitor:
    """Клиент для мониторинга Telegram каналов"""
    
    def __init__(self, api_id: int, api_hash: str, database):
        self.api_id = api_id
        self.api_hash = api_hash
        self.database = database
        self.client = None
        self.is_connected = False  # Флаг успешного подключения как пользователь
        import pytz
        vladivostok_tz = pytz.timezone('Asia/Vladivostok')
        self.start_time = datetime.now(vladivostok_tz)  # Время запуска бота во Владивостоке (UTC+10)
        
        # Кэш для оптимизации (ограниченный размер)
        self.channels_cache = {}
        self.messages_cache = {}
        self.cache_max_size = 1000  # Ограничение для VPS 1GB
        
        # Кэш подписанных диалогов для быстрой проверки
        self.dialogs_cache = {}
        self.dialogs_cache_time = None
        
        logger.info("📱 TelegramMonitor инициализирован")
    
    async def is_already_joined(self, entity) -> bool:
        try:
            from telethon.tl.functions.channels import GetParticipantRequest
            from telethon.errors import UserNotParticipantError, ChatAdminRequiredError
            
            try:
                await self.client(GetParticipantRequest(
                    channel=entity,
                    participant=await self.client.get_me()
                ))
                return True
            except (UserNotParticipantError, ChatAdminRequiredError):
                return False
            except Exception:
                dialogs = await self.client.get_dialogs(limit=None)
                
                for dialog in dialogs:
                    if dialog.entity.id == entity.id:
                        return True
                
                return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки подписки: {e}")
            return False
    
    async def initialize(self):
        """Инициализация Telegram клиента"""
        try:
            # Абсолютный путь к файлу сессии (исключает повторную авторизацию)
            current_dir = Path(__file__).resolve().parent
            # Ищем корень проекта (где есть config/, src/, requirements.txt)
            repo_root = current_dir.parent if (current_dir.parent / 'config').exists() else current_dir
            sessions_dir = repo_root / 'sessions'
            sessions_dir.mkdir(exist_ok=True)
            session_path = sessions_dir / 'news_monitor_session'

            self.client = TelegramClient(
                str(session_path),
                self.api_id,
                self.api_hash,
                device_model="Windows 10",
                system_version="4.16.30-vxCUSTOM",
                app_version="11.10",
                lang_code="ru",
                system_lang_code="ru-RU",
                # Оптимизация для VPS
                connection_retries=3,
                request_retries=2,
                timeout=30
            )
            
            await self.client.start()
            
            # Проверка авторизации - нужен пользователь, не бот
            me = await self.client.get_me()
            
            if hasattr(me, 'phone') and me.phone:
                logger.info(f"✅ Telegram клиент подключен как пользователь: {me.first_name} ({me.phone})")
                self.is_connected = True
            else:
                logger.warning(f"⚠️ Подключен как бот: {me.first_name}")
                logger.warning("💡 Боты не могут читать каналы - нужна авторизация по номеру телефона")
                self.is_connected = False
                # Не выбрасываем исключение, чтобы система продолжила работу
            
            return self.is_connected
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Telegram: {e}")
            logger.info("💡 Для мониторинга каналов требуется авторизация с номером телефона")
            self.is_connected = False
            # Не выбрасываем исключение, чтобы система продолжила работу без мониторинга
            return False
    
    async def get_channel_entity(self, username: str) -> Optional[Channel]:
        """Получение объекта канала с кэшированием (поддержка с/без @)"""
        
        # Нормализуем username (убираем @ для единообразия ключа кэша)
        normalized = username[1:] if isinstance(username, str) and username.startswith('@') else username
        
        # Проверяем кэш
        if normalized in self.channels_cache:
            return self.channels_cache[normalized]
        
        try:
            # Telethon принимает оба варианта, но кэшируем по normalized
            entity = await self.client.get_entity(normalized)
            
            # Сохраняем в кэш (с ограничением размера)
            if len(self.channels_cache) < self.cache_max_size:
                self.channels_cache[normalized] = entity
            
            logger.debug(f"📡 Получен канал: {normalized}")
            return entity
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения канала {normalized}: {e}")
            return None
    
    async def get_recent_messages(self, channel_config: Dict, limit: int = 50) -> List[Dict]:
        """Получение последних сообщений из канала"""
        
        # Проверяем что подключен пользователь, а не бот
        if not self.is_connected:
            logger.warning("⚠️ Мониторинг отключен - требуется авторизация пользователя")
            return []
        
        username = channel_config.get('username')
        if not username:
            return []
        
        try:
            # Получаем канал
            entity = await self.get_channel_entity(username)
            if not entity:
                return []
            
            # Получаем последние сообщения
            messages = []
            
            # Определяем время последней проверки
            last_check = await self.database.get_last_check_time(username)
            if not last_check:
                # Если первый запуск - берем сообщения только ПОСЛЕ запуска бота
                last_check = self.start_time.replace(tzinfo=None)  # Убираем timezone для совместимости с базой
            
            async for message in self.client.iter_messages(
                entity, 
                limit=limit,
                offset_date=last_check
            ):
                if not message.text:
                    continue
                
                # Применяем фильтры канала
                if not self.apply_channel_filters(message, channel_config):
                    continue
                
                # Преобразуем в словарь
                message_data = await self.message_to_dict(message, channel_config)
                messages.append(message_data)
            
            # Обновляем время последней проверки
            await self.database.update_last_check_time(username, datetime.now())
            
            logger.info(f"📥 Получено {len(messages)} новых сообщений из {username}")
            return messages
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения сообщений из {username}: {e}")
            return []
    
    def apply_channel_filters(self, message: Message, channel_config: Dict) -> bool:
        """Применение фильтров канала (для amur_mash и др.)"""
        
        # Проверяем ключевые слова для фильтрации
        filter_keywords = channel_config.get('filter_keywords', [])
        if filter_keywords:
            text_lower = message.text.lower()
            
            # Для amur_mash проверяем наличие региональных ключевых слов
            has_keyword = any(keyword.lower() in text_lower for keyword in filter_keywords)
            if not has_keyword:
                return False
        
        # Проверяем базовые критерии (просмотры, длина текста)
        if hasattr(message, 'views') and message.views:
            if message.views < 50:  # Минимальное количество просмотров
                return False
        
        # Проверяем длину сообщения
        if len(message.text) < 50:  # Слишком короткие сообщения
            return False
        
        # Исключаем рекламные сообщения
        spam_keywords = ['реклама', 'продам', 'куплю', 'сдам', 'найму']
        text_lower = message.text.lower()
        if any(spam in text_lower for spam in spam_keywords):
            return False
        
        return True
    
    def _get_replies_count(self, message: Message) -> int:
        """Безопасное получение количества ответов"""
        try:
            if hasattr(message, 'replies') and message.replies:
                return getattr(message.replies, 'replies', 0)
            return 0
        except:
            return 0
    
    async def message_to_dict(self, message: Message, channel_config: Dict) -> Dict:
        """Преобразование сообщения в словарь для обработки"""
        
        # Создаем уникальный ID сообщения
        message_id = f"{channel_config['username']}_{message.id}"
        
        # Получаем основную информацию
        message_data = {
            'id': message_id,
            'channel_username': channel_config['username'],
            'channel_name': channel_config.get('name', channel_config['username']),
            'channel_region': channel_config.get('region', 'unknown'),
            'channel_category': channel_config.get('category', 'news'),
            'message_id': message.id,
            'text': message.text[:5000],  # Ограничиваем размер текста
            'date': message.date,
            'views': getattr(message, 'views', 0),
            'forwards': getattr(message, 'forwards', 0),
            'replies': self._get_replies_count(message),
            'reactions_count': 0,  # Будем считать отдельно
            'url': f"https://t.me/{channel_config['username'].lstrip('@')}/{message.id}",
            'processed': False,
            'ai_score': None,
            'ai_analysis': None,
            'selected_for_output': False
        }
        
        # Подсчет реакций
        if hasattr(message, 'reactions') and message.reactions:
            total_reactions = sum(
                reaction.count for reaction in message.reactions.results
            )
            message_data['reactions_count'] = total_reactions
        
        # Хэш для дедупликации
        content_hash = hashlib.sha256(
            f"{message.text[:1000]}{message.date}".encode()
        ).hexdigest()
        message_data['content_hash'] = content_hash
        
        return message_data
    
    async def apply_prefilter(self, messages: List[Dict], config: Dict) -> List[Dict]:
        """Предфильтрация сообщений перед ИИ анализом"""
        
        filtered = []
        
        # Поддержка как полной конфигурации, так и вложенной секции 'monitoring'
        cfg = config.get('monitoring', config) if isinstance(config, dict) else {}
        min_views = cfg.get('min_views', 0)
        min_reactions = cfg.get('min_reactions', 0)
        priority_keywords = cfg.get('priority_keywords', [])
        exclude_keywords = cfg.get('exclude_keywords', [])
        
        for message in messages:
            text_lower = message['text'].lower()
            
            # Исключаем только откровенный спам (очень короткие сообщения)
            if len(message['text'].strip()) < 10:
                continue
            
            # Проверяем приоритетные ключевые слова
            has_priority = any(keyword in text_lower for keyword in priority_keywords)
            
            # БЕРЕМ ВСЕ НОВОСТИ - никаких ограничений!
            message['priority'] = has_priority
            filtered.append(message)
        
        # Сортируем по приоритету и активности
        filtered.sort(
            key=lambda x: (
                x.get('priority', False),
                x['views'] + x['reactions_count'] * 10
            ),
            reverse=True
        )
        
        logger.info(f"🔍 Предфильтрация: {len(messages)} → {len(filtered)} сообщений")
        return filtered
    
    async def clear_cache(self):
        """Очистка кэша для освобождения памяти"""
        self.channels_cache.clear()
        self.messages_cache.clear()
        self.dialogs_cache.clear()
        self.dialogs_cache_time = None
        logger.info("🧹 Кэш Telegram клиента очищен")

    async def _update_dialogs_cache(self):
        """Обновление кэша диалогов (раз в 10 минут)"""
        from datetime import timedelta
        
        now = datetime.now()
        
        # Обновляем кэш если он пустой или старше 10 минут
        if (not self.dialogs_cache_time or 
            now - self.dialogs_cache_time > timedelta(minutes=10)):
            
            logger.info("🔄 Обновляем кэш диалогов...")
            self.dialogs_cache = {}
            
            try:
                # Получаем все диалоги ОДИН раз
                async for dialog in self.client.iter_dialogs():
                    self.dialogs_cache[dialog.entity.id] = True
                
                self.dialogs_cache_time = now
                logger.info(f"✅ Кэш диалогов обновлен: {len(self.dialogs_cache)} каналов")
                
            except Exception as e:
                logger.error(f"❌ Ошибка обновления кэша диалогов: {e}")

    async def is_already_joined(self, entity) -> bool:
        """Проверка, состоит ли текущий пользователь в канале/чате"""
        try:
            # Обновляем кэш если нужно
            await self._update_dialogs_cache()
            
            # Быстрая проверка по кэшу
            target_id = entity.id
            return target_id in self.dialogs_cache
            
        except Exception as e:
            logger.debug(f"Ошибка проверки подписки: {e}")
            # При любых ошибках считаем что не подписаны (безопасная сторона)
            return False
    
    async def get_new_messages_simple(self, channel_config: dict) -> List[Dict]:
        """Простое получение новых сообщений без анализа - только для пересылки"""
        try:
            username = channel_config['username']
            logger.info(f"📡 Проверка новых сообщений: {username}")
            
            # Получаем entity канала
            entity = await self.get_channel_entity(username)
            if not entity:
                return []
            
            # Определяем время последней проверки
            last_check = await self.database.get_last_check_time(username)
            if not last_check:
                # Если первый запуск - берем сообщения только ПОСЛЕ запуска бота
                last_check = self.start_time.replace(tzinfo=None)  # Убираем timezone для совместимости с базой
            
            # Получаем новые сообщения
            new_messages = []
            async for message in self.client.iter_messages(
                entity, 
                limit=50,  # Максимум 50 новых сообщений за раз
                offset_date=last_check
            ):
                if message.date <= last_check:
                    break
                    
                # Простая проверка - только текстовые сообщения
                if not message.text:
                    continue
                
                message_data = {
                    'id': f"{username}_{message.id}",
                    'text': message.text,
                    'date': message.date,
                    'channel_username': username,
                    'url': f"https://t.me/{username.lstrip('@')}/{message.id}",
                }
                
                new_messages.append(message_data)
            
            # Обновляем время последней проверки
            if new_messages:
                await self.database.update_last_check_time(username)
                logger.info(f"📥 Получено {len(new_messages)} новых сообщений из {username}")
            
            return new_messages[::-1]  # Возвращаем в хронологическом порядке
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения сообщений из {username}: {e}")
            return []

    async def disconnect(self):
        """Отключение от Telegram"""
        if self.client:
            await self.client.disconnect()
            logger.info("👋 Telegram клиент отключен")
    
    async def get_channel_stats(self, username: str) -> Dict:
        """Получение статистики канала"""
        try:
            entity = await self.get_channel_entity(username)
            if not entity:
                return {}
            
            # Базовая информация
            stats = {
                'username': username,
                'title': entity.title,
                'participants_count': getattr(entity, 'participants_count', 0),
                'date_created': getattr(entity, 'date', None),
                'verified': getattr(entity, 'verified', False),
                'restricted': getattr(entity, 'restricted', False)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики {username}: {e}")
            return {}
