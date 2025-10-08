import asyncio
import httpx
from typing import Dict, List, Optional, Any
from loguru import logger
from datetime import datetime


class UpdateProcessor:
    
    def __init__(self, bot: "TelegramBot"):
        self.bot = bot
        self.is_listening = False
        self.start_time = datetime.now()
    
    async def start_listening(self):
        self.is_listening = True
        self.bot.is_listening = True
        logger.info("👂 Бот начал прослушивание команд")
        
        while self.is_listening:
            try:
                updates = await self.get_updates()
                
                if updates:
                    for update in updates:
                        await self.process_update(update)
                        
                await asyncio.sleep(1)
                        
            except Exception as e:
                logger.error(f"❌ Ошибка в цикле прослушивания: {e}")
                await asyncio.sleep(5)
    
    def stop_listening(self):
        self.is_listening = False
        self.bot.is_listening = False
        logger.info("🛑 Прослушивание команд остановлено")
    
    async def get_updates(self, max_retries: int = 3) -> List[Dict]:
        for attempt in range(max_retries):
            try:
                data = {
                    "offset": self.bot.update_offset,
                    "limit": 10,
                    "timeout": 10
                }
                
                async with httpx.AsyncClient(timeout=15) as client:
                    response = await client.post(f"{self.bot.base_url}/getUpdates", json=data)
                    
                    if response.status_code == 200:
                        result = response.json()
                        updates = result.get("result", [])
                        
                        if updates:
                            self.bot.update_offset = updates[-1]["update_id"] + 1
                        
                        return updates
                    else:
                        logger.warning(f"⚠️ Ошибка получения обновлений: {response.text}")
                        return []
                        
            except Exception as e:
                logger.error(f"❌ Попытка {attempt + 1}/{max_retries} получения обновлений: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    
        return []
    
    async def process_update(self, update: Dict):
        try:
            if "message" in update:
                await self._handle_message(update["message"])
            elif "callback_query" in update:
                await self._handle_callback_query(update["callback_query"])
            elif "my_chat_member" in update:
                await self._handle_chat_member_update(update["my_chat_member"])
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки обновления: {e}")
    
    async def _handle_message(self, message: Dict):
        try:
            text = message.get("text", "")
            user_id = message.get("from", {}).get("id")
            chat_id = message.get("chat", {}).get("id")
            message_id = message.get("message_id")
            message_date = message.get("date", 0)
            thread_id = message.get("message_thread_id")
            
            if thread_id and self.bot.monitor_bot:
                config = self.bot.monitor_bot.config_loader.get_config()
                excluded_topics = config.get('output', {}).get('excluded_topics', [])
                if excluded_topics and thread_id in excluded_topics:
                    logger.debug(f"⏭️ Пропускаем сообщение из исключенной темы {thread_id}")
                    return
            
            if not (self.bot.is_admin_user(user_id) or self.bot.is_message_from_group(chat_id)):
                logger.warning(f"🚫 Неавторизованный доступ от пользователя {user_id}")
                return
            
            if message_date < self.start_time.timestamp():
                logger.debug(f"⏭️ Пропускаем старое сообщение от {user_id} (до запуска бота)")
                return
            
            if text.startswith("/"):
                await self._handle_command(text, message)
            elif await self._handle_ai_message(text, message):
                
                if self.bot.delete_commands and message_id:
                    await self._delete_user_message(message_id, chat_id)
            elif "forward_from_chat" in message:
                await self._handle_forwarded_message(message)
                if self.bot.delete_commands and message_id:
                    await self._delete_user_message(message_id, chat_id)
            elif self.bot.waiting_for_region_name:
                logger.info(f"📝 Обработка названия региона: '{text}'")
                await self.bot.region_commands.handle_region_creation(text)
                if self.bot.delete_commands and message_id:
                    await self._delete_user_message(message_id, chat_id)
            elif self.bot.waiting_for_emoji:
                await self.bot.region_commands.handle_custom_emoji_input(text)
                if self.bot.delete_commands and message_id:
                    await self._delete_user_message(message_id, chat_id)
            elif self.bot.waiting_for_digest_channel and ("t.me/" in text or text.startswith("@")):
                await self._handle_digest_channel_link(text, message)
                if self.bot.delete_commands and message_id:
                    await self._delete_user_message(message_id, chat_id)
            elif "t.me/" in text or text.startswith("@"):
                found_channels = self.bot.channel_manager.parser.parse_multiple_channels(text)
                
                if not found_channels:
                    await self.bot.send_message("❌ Не найдено валидных каналов в сообщении")
                elif len(found_channels) == 1:
                    await self.bot.channel_manager.add_channel_handler(found_channels[0])
                else:
                    self.bot.pending_channels_list = found_channels
                    from ..channels.channel_ui import ChannelUI
                    channel_ui = ChannelUI(self.bot)
                    await channel_ui.show_multiple_channels_selection()
                    
                if self.bot.delete_commands and message_id:
                    await self._delete_user_message(message_id, chat_id)
            else:
                logger.info(f"❓ Неизвестное сообщение: '{text}'")
                await self.bot.send_message(
                    "ℹ️ Используйте кнопки снизу или отправьте ссылку на канал.\n"
                    "Для дайджеста: /digest\nДля справки: /help"
                )
                
                if self.bot.delete_commands and message_id:
                    await self._delete_user_message(message_id, chat_id)
                    
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")
    
    async def _handle_command(self, text: str, message: Dict):
        try:
            command_part = text.split()[0][1:].lower()
            
            if '@' in command_part:
                command = command_part.split('@')[0]
            else:
                command = command_part
            
            if command in self.bot.command_handlers:
                logger.info(f"💬 Команда: /{command}")
                await self.bot.command_handlers[command](message)
            else:
                logger.warning(f"❓ Неизвестная команда: /{command}")
                await self.bot.send_command_response(
                    f"❓ Неизвестная команда: /{command}\n\n"
                    "Доступные команды: /help", 
                    message
                )
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки команды '{text}': {e}")
    
    async def _handle_callback_query(self, callback: Dict):
        try:
            callback_user_id = callback.get("from", {}).get("id")
            callback_chat_id = callback.get("message", {}).get("chat", {}).get("id")
            callback_date = callback.get("message", {}).get("date", 0)
            
            if not (self.bot.is_admin_user(callback_user_id) or self.bot.is_message_from_group(callback_chat_id)):
                return
            
            if callback_date < self.start_time.timestamp():
                logger.debug(f"⏭️ Пропускаем старый callback от {callback_user_id} (до запуска бота)")
                return
                
            callback_data = callback.get("data", "")
            logger.info(f"🎯 Получен callback: '{callback_data}' от пользователя {callback_user_id}")
            
            await self.bot.handle_callback(callback_data, callback)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки callback: {e}")
    
    async def _handle_chat_member_update(self, member_update: Dict):
        try:
            chat = member_update.get("chat", {})
            new_member = member_update.get("new_chat_member", {})
            
            if chat.get("type") == "supergroup" and new_member.get("status") == "member":
                chat_title = chat.get("title", "Неизвестная группа")
                logger.info(f"➕ Бот добавлен в группу: {chat_title}")
                
                await self.bot.send_message(
                    f"👋 Привет! Бот добавлен в группу <b>{chat_title}</b>\n\n"
                    "Используйте /start для начала работы"
                )
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки обновления членства: {e}")
    
    async def _delete_user_message(self, message_id: int, chat_id: int = None):
        try:
            target_chat_id = chat_id or self.bot.admin_chat_id
            
            data = {
                "chat_id": target_chat_id,
                "message_id": message_id
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.bot.base_url}/deleteMessage", json=data)
                
                if response.status_code != 200:
                    logger.debug(f"⚠️ Не удалось удалить сообщение {message_id}")
                    
        except Exception as e:
            logger.debug(f"⚠️ Ошибка удаления сообщения {message_id}: {e}")
    
    async def delete_user_message(self, message_id: int, chat_id: int = None):
        return await self._delete_user_message(message_id, chat_id)
    
    async def _handle_forwarded_message(self, message: Dict):
        try:
            forward_from_chat = message.get("forward_from_chat", {})
            if not forward_from_chat:
                await self.bot.send_message("❌ Не удалось получить информацию о канале")
                return
            
            channel_username = forward_from_chat.get("username")
            channel_title = forward_from_chat.get("title", "")
            channel_type = forward_from_chat.get("type", "")
            
            forward_key = f"{channel_username}_{int(message.get('date', 0))}"
            if forward_key in self.bot.processed_forwards:
                logger.info(f"⏭️ Пропускаем дублированное forward сообщение от @{channel_username}")
                return
            
            self.bot.processed_forwards.add(forward_key)
            
            current_time = int(message.get('date', 0))
            self.bot.processed_forwards = {
                key for key in self.bot.processed_forwards 
                if current_time - int(key.split('_')[-1]) < 300
            }
            
            if not channel_username:
                await self.bot.send_message("❌ Канал не имеет публичного username")
                return
            
            if channel_type != "channel":
                await self.bot.send_message("❌ Это не канал, а чат или группа")
                return
            
            logger.info(f"📩 Получен репост из канала @{channel_username}: {channel_title}")
            
            self.bot.pending_channel_url = channel_username
            
            from ..channels.channel_ui import ChannelUI
            channel_ui = ChannelUI(self.bot)
            await channel_ui.show_channel_preview_and_region_selection(channel_username, channel_title)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки репоста: {e}")
            await self.bot.send_message(f"❌ Ошибка обработки репоста: {e}")
    
    async def _handle_digest_channel_link(self, text: str, message: Dict):
        try:
            from ..channels.channel_parser import ChannelParser
            parser = ChannelParser()
            
            channel_username = parser.parse_channel_username(text)
            if not channel_username:
                await self.bot.send_message("❌ Некорректная ссылка на канал")
                return
            
            logger.info(f"📰 Получена ссылка на канал для дайджеста: @{channel_username}")
            
            await self.bot.send_message(f"📰 Читаем новости из @{channel_username}, подождите...")
            
            if hasattr(self.bot.basic_commands, 'generate_digest_for_channel'):
                days = getattr(self.bot, 'digest_days', 7)
                digest_result = await self.bot.basic_commands.generate_digest_for_channel(channel_username, days)
                
                if isinstance(digest_result, dict):
                    await self.bot.keyboard_builder.send_message_with_keyboard(
                        digest_result['text'], digest_result['keyboard'], use_reply_keyboard=False
                    )
                else:
                    keyboard = [
                        [{"text": "📰 Новый дайджест", "callback_data": "digest"}],
                        [{"text": "🏠 Главное меню", "callback_data": "start"}]
                    ]
                    await self.bot.keyboard_builder.send_message_with_keyboard(
                        digest_result, keyboard, use_reply_keyboard=False
                    )
            else:
                await self.bot.send_message("❌ Генератор дайджестов недоступен")
            
            self.bot.waiting_for_digest_channel = False
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки ссылки для дайджеста: {e}")
            await self.bot.send_message(f"❌ Ошибка: {e}")
            self.bot.waiting_for_digest_channel = False

    async def _handle_ai_message(self, text: str, message: Dict) -> bool:
        """Обработка AI сообщений (начинающихся с AI:, ИИ:, АИ:)"""
        try:
            
            if (text.lower().startswith('ai:') or 
                text.lower().startswith('ии:') or 
                text.lower().startswith('аи:')):
                
                logger.info(f"💬 Обрабатываем AI сообщение: {text[:50]}...")
                
                
                return await self.bot.basic_commands.handle_ai_message(message)
                
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки AI сообщения: {e}")
            return False