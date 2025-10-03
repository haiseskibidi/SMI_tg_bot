import asyncio
import hashlib
import pytz
from datetime import datetime
from typing import Dict, Any, Set, TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from ..database import DatabaseManager

try:
    from ..ai.urgency_detector import analyze_news_urgency
    AI_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ AI модуль недоступен - будет использована базовая логика")
    AI_AVAILABLE = False


class MessageProcessor:
    def __init__(self, database: "DatabaseManager", app_instance):
        self.database = database
        self.app_instance = app_instance
        self.processed_media_groups: Set[int] = set()

    async def handle_new_message(self, event):
        try:
            if not self.app_instance.monitoring_active:
                logger.debug("⏸️ Мониторинг приостановлен, пропускаем сообщение")
                return
            
            logger.info("🔥 СРАБОТАЛ ОБРАБОТЧИК НОВОГО СООБЩЕНИЯ!")
            message = event.message
            
            chat = await event.get_chat()
            channel_username = getattr(chat, 'username', None)
            if not channel_username:
                logger.warning(f"⚠️ Сообщение без username канала, пропускаем")
                return
            
            logger.info(f"📥 Получено сообщение от @{channel_username}: {message.text[:100] if message.text else 'без текста'}")
            
            has_text = bool(getattr(message, "text", None))
            has_media = bool(getattr(message, "media", None))
            
            if has_text and self._is_spam_message(message.text):
                logger.info(f"🚫 Отфильтровано рекламное сообщение от @{channel_username}")
                return
            
            if not await self._process_media_group(message, has_media):
                return
            
            if not await self._validate_message_time(message):
                return
                
            message_data = self._create_message_data(message, channel_username)
            
            analysis_text = await self._get_text_for_analysis(message, channel_username)
            
            # Если нашли текст в медиа-группе, обновляем message_data
            if analysis_text and not message_data.get('text'):
                message_data['text'] = analysis_text
                logger.info(f"📝 Обновлен текст в message_data для медиа-группы: {analysis_text[:100]}...")
            
            final_text = analysis_text or message.text
            
            message_data = await self._check_alerts(message_data, final_text)
            
            # 🤖 Анализ срочности с помощью AI
            message_data = await self._analyze_urgency(message_data, final_text)
            
            logger.info(f"⚡ Новое сообщение из @{channel_username} - мгновенная отправка!")
            
            await self._save_to_database(message_data)
            
            await self._send_message(message_data, has_text, has_media)
            
            await self._update_last_check_time(channel_username)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки нового сообщения: {e}")
            logger.exception("Детали ошибки:")

    async def _process_media_group(self, message, has_media: bool) -> bool:
        if has_media and hasattr(message, 'grouped_id') and message.grouped_id:
            grouped_id = message.grouped_id
            logger.info(f"📸 Сообщение является частью медиа группы: {grouped_id}")
            
            if grouped_id in self.processed_media_groups:
                logger.info(f"✅ Медиа группа {grouped_id} уже обработана, пропускаем")
                return False
            
            self.processed_media_groups.add(grouped_id)
            logger.info(f"🔄 Помечаем медиа группу {grouped_id} как обрабатываемую")
            
            if len(self.processed_media_groups) > 1000:
                self.processed_media_groups = set(list(self.processed_media_groups)[-500:])
                logger.info("🧹 Очищен кэш медиа групп (превышен лимит)")
        
        return True

    async def _get_text_for_analysis(self, message, channel_username: str) -> str:
        """Получает текст для AI анализа, включая текст из медиа-групп"""
        try:
            # Если у сообщения есть текст, используем его
            if message.text and message.text.strip():
                return message.text.strip()
            
            # Если текста нет, но есть медиа-группа, ищем текст в группе
            if hasattr(message, 'grouped_id') and message.grouped_id:
                logger.info(f"🔍 Ищем текст в медиа-группе {message.grouped_id} для AI анализа")
                
                entity = await self.app_instance.telegram_monitor.get_channel_entity(channel_username)
                if not entity:
                    logger.warning(f"❌ Не удалось получить entity для {channel_username}")
                    return ""
                
                # Получаем последние сообщения для поиска медиа-группы
                all_messages = await self.app_instance.telegram_monitor.client.get_messages(entity, limit=20)
                group_messages = [msg for msg in all_messages if hasattr(msg, 'grouped_id') and msg.grouped_id == message.grouped_id]
                
                # Ищем сообщение с текстом в группе
                for msg in group_messages:
                    if msg.text and msg.text.strip():
                        logger.info(f"📝 Найден текст в медиа-группе (длина {len(msg.text)}): {msg.text[:100]}...")
                        return msg.text.strip()
                
                logger.debug("📝 Текст в медиа-группе не найден")
            
            return ""
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении текста для анализа: {e}")
            return ""

    async def _validate_message_time(self, message) -> bool:
        msg_time = message.date
        start_time = self.app_instance.telegram_monitor.start_time
        
        vladivostok_tz = pytz.timezone('Asia/Vladivostok')
        
        if msg_time.tzinfo is None:
            msg_time = pytz.utc.localize(msg_time).astimezone(vladivostok_tz)
        else:
            msg_time = msg_time.astimezone(vladivostok_tz)
        
        logger.info(f"⏰ Время сообщения: {msg_time.strftime('%d.%m.%Y %H:%M:%S %Z')}, время запуска бота: {start_time.strftime('%d.%m.%Y %H:%M:%S %Z')}")
        
        if msg_time < start_time:
            logger.info(f"⏭️ Сообщение старое (до запуска бота), пропускаем")
            return False
        
        return True

    def _create_message_data(self, message, channel_username: str) -> Dict[str, Any]:
        vladivostok_tz = pytz.timezone('Asia/Vladivostok')
        msg_time = message.date
        
        if msg_time.tzinfo is None:
            msg_time = pytz.utc.localize(msg_time).astimezone(vladivostok_tz)
        else:
            msg_time = msg_time.astimezone(vladivostok_tz)
        
        text_for_hash = message.text or ''
        content_hash = hashlib.md5(
            f"{text_for_hash[:1000]}{message.date}".encode()
        ).hexdigest()
        
        return {
            'id': f"{channel_username}_{message.id}",
            'text': message.text or '',
            'date': msg_time,
            'channel_username': channel_username,
            'message_id': message.id,
            'url': f"https://t.me/{channel_username}/{message.id}",
            'content_hash': content_hash,
            'views': getattr(message, 'views', 0),
            'forwards': getattr(message, 'forwards', 0),
            'reactions_count': 0
        }

    async def _check_alerts(self, message_data: Dict[str, Any], text: str) -> Dict[str, Any]:
        is_alert, alert_category, alert_emoji, is_priority, matched_words = self.app_instance.check_alert_keywords(text)
        
        if is_alert:
            logger.warning(f"🚨 АЛЕРТ обнаружен в @{message_data['channel_username']}! Категория: {alert_category}, слова: {matched_words}")
            
            alert_text = self.app_instance.format_alert_message(
                text, 
                message_data['channel_username'], 
                alert_emoji, 
                alert_category, 
                matched_words
            )
            
            message_data['text'] = alert_text
            message_data['is_alert'] = True
            message_data['alert_category'] = alert_category
            message_data['alert_priority'] = is_priority
        else:
            message_data['is_alert'] = False
        
        return message_data

    async def _analyze_urgency(self, message_data: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Анализирует срочность новости с помощью AI"""
        try:
            if not text or not text.strip():
                logger.info(f"🤖 Пропускаем анализ срочности - нет текста от @{message_data.get('channel_username', 'unknown')}")
                # Для медиа-групп без текста просто добавляем белый круг
                if not message_data.get('text'):
                    message_data['text'] = f"⚪ {message_data.get('text', '')}"
                return message_data
            
            if not AI_AVAILABLE:
                logger.debug("🤖 AI модуль недоступен, пропускаем анализ срочности")
                return message_data
            
            logger.info(f"🤖 Анализируем срочность новости от @{message_data['channel_username']} (длина текста: {len(text)})")
            
            # Вызываем AI анализ
            urgency_result = await analyze_news_urgency(
                text=text,
                source=message_data['channel_username']
            )
            
            logger.info(f"🎯 AI результат: уровень={urgency_result['urgency_level']}, скор={urgency_result['urgency_score']:.2f}, эмодзи={urgency_result['emoji']}")
            
            # Проверяем, не определил ли AI это как спам/рекламу
            if urgency_result['urgency_level'] == 'ignore':
                logger.info(f"🚫 AI определил как спам/рекламу сообщение от @{message_data['channel_username']} - помечаем эмодзи")
                # Просто добавляем эмодзи 🚫 и продолжаем обработку
                message_data['text'] = f"🚫 {text}"
                message_data['urgency_level'] = 'ignore'
                message_data['urgency_score'] = 0.0
                message_data['urgency_emoji'] = '🚫'
                message_data['ai_analyzed'] = True
                
                logger.info(f"📝 Текст после AI анализа: 🚫 {text[:50]}...")
                return message_data
            
            # Сохраняем результаты анализа в message_data
            message_data['urgency_level'] = urgency_result['urgency_level']
            message_data['urgency_score'] = urgency_result['urgency_score'] 
            message_data['urgency_emoji'] = urgency_result['emoji']
            message_data['urgency_keywords'] = urgency_result['keywords']
            message_data['urgency_reasoning'] = urgency_result['reasoning']
            message_data['ai_analyzed'] = urgency_result['ai_classification']['ai_available']
            
            # Модифицируем текст сообщения в зависимости от срочности
            urgency_level = urgency_result['urgency_level']
            emoji = urgency_result['emoji']
            
            if urgency_level == 'urgent':
                # Добавляем яркий префикс для срочных новостей
                message_data['text'] = f"{emoji} **🚨 СРОЧНО 🚨**\n\n{text}"
                logger.warning(f"🔴 СРОЧНАЯ новость от @{message_data['channel_username']}: {urgency_result['urgency_score']:.2f}")
                
            elif urgency_level == 'important':
                # Добавляем префикс для важных новостей
                message_data['text'] = f"{emoji} **ВАЖНО**\n\n{text}"
                logger.info(f"🟡 ВАЖНАЯ новость от @{message_data['channel_username']}: {urgency_result['urgency_score']:.2f}")
                
            else:
                # Обычные новости - просто добавляем эмодзи
                message_data['text'] = f"{emoji} {text}"
                logger.debug(f"⚪ Обычная новость от @{message_data['channel_username']}: {urgency_result['urgency_score']:.2f}")
            
            logger.info(f"📝 Текст после AI анализа: {message_data['text'][:100]}...")
            
            # Логируем детали анализа
            if urgency_result['keywords']:
                logger.info(f"🎯 Найдены ключевые слова: {urgency_result['keywords'][:3]}...")
            
            if urgency_result['time_markers']:
                logger.info("⏰ Обнаружены временные маркеры срочности")
            
            return message_data
            
        except Exception as e:
            import traceback
            logger.error(f"❌ Ошибка анализа срочности: {e}")
            logger.error(f"📋 Трейс ошибки: {traceback.format_exc()}")
            # В случае ошибки возвращаем исходные данные с белым кружком
            message_data['text'] = f"⚪ {text}"
            return message_data

    async def _save_to_database(self, message_data: Dict[str, Any]):
        try:
            await self.database.save_message(message_data)
            logger.info(f"💾 Сообщение сохранено в базу данных")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в БД: {e}")

    async def _send_message(self, message_data: Dict[str, Any], has_text: bool, has_media: bool):
        if has_media:
            logger.info(f"📎 Сообщение содержит файлы от @{message_data['channel_username']}")
            media_sent = await self.app_instance.download_and_send_media(message_data)
            if not media_sent:
                logger.warning("⚠️ Не удалось отправить файлы, отправляем текстовое уведомление")
                await self.app_instance.send_message_to_target(message_data, is_media=True)
        elif not has_text:
            logger.info(f"📄 Сообщение без текста от @{message_data['channel_username']}")
            forwarded = await self.app_instance.forward_original_message(message_data)
            if not forwarded:
                await self.app_instance.send_message_to_target(message_data, is_media=True)
        else:
            await self.app_instance.send_message_to_target(message_data, is_media=False)

    async def _update_last_check_time(self, channel_username: str):
        vladivostok_tz = pytz.timezone('Asia/Vladivostok')
        current_time_vlk = datetime.now(vladivostok_tz)
        await self.database.update_last_check_time(channel_username, current_time_vlk)

    def clear_media_groups_cache(self):
        self.processed_media_groups.clear()
        logger.info("🧹 Кэш медиа групп очищен")

    def _is_spam_message(self, text: str) -> bool:        
        text_lower = text.lower()
        
        spam_keywords = [
            'реклама', 'Реклама'
        ]
        
        # Проверяем наличие спам-слов
        spam_words_found = [word for word in spam_keywords if word in text_lower]
        
        if spam_words_found:
            logger.debug(f"🚫 Найдены рекламные слова: {spam_words_found}")
            return True
            
        return False
