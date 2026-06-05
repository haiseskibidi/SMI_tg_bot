import asyncio
import hashlib
import pytz
from datetime import datetime
from typing import Dict, Any, Set, TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from ..database import DatabaseManager


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
            
            # Исключаем рекламные сообщения
            if has_text and self.app_instance.telegram_monitor and self.app_instance.telegram_monitor.is_spam(message.text):
                logger.info(f"🚫 Сообщение от @{channel_username} определено как реклама/спам, пропускаем")
                return
            
            if not await self._process_media_group(message, has_media):
                return
            
            if not await self._validate_message_time(message):
                return
                
            message_data = self._create_message_data(message, channel_username)
            
            message_data = await self._check_alerts(message_data, message.text)
            
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
        content_hash = hashlib.sha256(
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
