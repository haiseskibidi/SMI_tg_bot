import asyncio
import httpx
import json
from typing import Dict, Optional, Any
from loguru import logger
from datetime import datetime

from src.handlers.commands.basic import BasicCommands
from src.handlers.commands import ChannelCommands, RegionCommands, ManagementCommands
from src.handlers.callbacks import ChannelCallbacks, RegionCallbacks


class TelegramBot:
    
    def __init__(self, bot_token: str, admin_chat_id: int, group_chat_id: int = None, monitor_bot=None):
        self.bot_token = bot_token
        self.admin_chat_id = admin_chat_id
        self.group_chat_id = group_chat_id
        self.chat_id = admin_chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.monitor_bot = monitor_bot
        self.main_instance = monitor_bot
        
        logger.info(f"🤖 TelegramBot инициализирован:")
        logger.info(f"👤 Админ: {admin_chat_id}")
        logger.info(f"👥 Группа: {group_chat_id if group_chat_id else 'не настроена'}")
        
        self.update_offset = 0
        self.is_listening = False
        self.command_handlers = {}
        
        self.edit_messages = True
        self.delete_commands = True
        self.last_message_id = None
        
        self.pending_channel_url = None
        self.pending_channels_list = []
        self.waiting_for_region_name = False
        self.waiting_for_emoji = False
        self.pending_region_data = None
        self.pending_topic_data = None
        self.current_callback_chat_id = None
        self.processed_forwards = set()
        self.active_inline_messages = []
        self.waiting_for_digest_channel = False
        self.pending_topic_id = None
        self.waiting_for_topic_id = False
        
        self._update_processor = None
        self._keyboard_builder = None
        self._channel_manager = None
        self._region_manager = None
        self._callback_processor = None
        self._digest_interface = None
        
        self.basic_commands = BasicCommands(self)
        self.channel_commands = ChannelCommands(self)
        self.region_commands = RegionCommands(self)
        self.management_commands = ManagementCommands(self)
        self.channel_callbacks = ChannelCallbacks(self)
        self.region_callbacks = RegionCallbacks(self)
        
        self._register_commands()
        asyncio.create_task(self.setup_bot_commands())
    
    def _register_commands(self):
        commands = {
            "start": self.basic_commands.start,
            "help": self.basic_commands.help,
            "status": self.basic_commands.status,
            "start_monitoring": self.basic_commands.start_monitoring,
            "stop_monitoring": self.basic_commands.stop_monitoring,
            "restart": self.basic_commands.restart,
            "kill_switch": self.basic_commands.kill_switch,
            "unlock": self.basic_commands.unlock,
            "digest": self.basic_commands.digest,
            "topic_id": self.basic_commands.topic_id,
            "add_channel": self.channel_commands.add_channel,
            "manage_channels": self.management_commands.manage_channels,
            "stats": self.management_commands.stats,
            "force_subscribe": self.channel_commands.force_subscribe,
        }
        
        for command, handler in commands.items():
            self.register_command(command, handler)
    
    @property
    def update_processor(self):
        if self._update_processor is None:
            from .update_processor import UpdateProcessor
            self._update_processor = UpdateProcessor(self)
        return self._update_processor
    
    @property  
    def keyboard_builder(self):
        if self._keyboard_builder is None:
            from ..ui.keyboard_builder import KeyboardBuilder
            self._keyboard_builder = KeyboardBuilder(self)
        return self._keyboard_builder
    
    @property
    def channel_manager(self):
        if self._channel_manager is None:
            from ..channels.channel_manager import ChannelManager
            self._channel_manager = ChannelManager(self)
        return self._channel_manager
    
    @property
    def region_manager(self):
        if self._region_manager is None:
            from ..regions.region_manager import RegionManager
            self._region_manager = RegionManager(self)
        return self._region_manager
    
    @property
    def callback_processor(self):
        if self._callback_processor is None:
            from ..handlers.callback_processor import CallbackProcessor
            self._callback_processor = CallbackProcessor(self)
        return self._callback_processor
    
    def is_admin_user(self, user_id: int) -> bool:
        return user_id == self.admin_chat_id
    
    def is_message_from_group(self, chat_id: int) -> bool:
        return self.group_chat_id and chat_id == self.group_chat_id
    
    def clear_waiting_states(self):
        """Сброс всех флагов ожидания пользовательского ввода"""
        logger.info("🧹 Сброс флагов ожидания ввода пользователя")
        self.waiting_for_region_name = False
        self.waiting_for_emoji = False
        self.waiting_for_digest_channel = False
        self.waiting_for_topic_id = False
        self.pending_channel_url = None
        self.pending_region_data = None
        self.pending_topic_data = None
        self.pending_topic_id = None
    
    def register_command(self, command: str, handler):
        self.command_handlers[command] = handler
        logger.debug(f"🔧 Зарегистрирована команда: /{command}")
    
    async def setup_bot_commands(self):
        try:
            commands = [
                {"command": "start", "description": "🏠 Главное меню"},
                {"command": "status", "description": "📊 Статус системы"},
                {"command": "help", "description": "🆘 Справка"},
                {"command": "digest", "description": "📰 Дайджест новостей"},
            ]
            
            data = {"commands": commands}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.base_url}/setMyCommands", json=data)
                
                if response.status_code == 200:
                    logger.info("✅ Команды бота настроены в Telegram API")
                else:
                    logger.warning(f"⚠️ Ошибка настройки команд: {response.text}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка установки команд: {e}")
    
    async def send_message(self, text: str, parse_mode: str = "HTML", to_group: bool = True, to_user: int = None) -> bool:
        try:
            if to_user:
                target_chat_id = to_user
            elif self.group_chat_id:
                target_chat_id = self.group_chat_id
                logger.info(f"📤 Отправляем сообщение в группу: {self.group_chat_id}")
            else:
                target_chat_id = self.admin_chat_id
                logger.info(f"📤 Группа не настроена, отправляем админу: {self.admin_chat_id}")
            
            return await self._send_to_single_user(text, target_chat_id, parse_mode)
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения: {e}")
            return False
    
    async def _send_to_single_user(self, text: str, chat_id: int, parse_mode: str = "HTML") -> bool:
        try:
            data = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.base_url}/sendMessage", json=data)
                
                if response.status_code == 200:
                    return True
                else:
                    logger.error(f"❌ Telegram API ошибка: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка HTTP запроса: {e}")
            return False
    
    async def send_system_notification(self, text: str, parse_mode: str = "HTML") -> bool:
        return await self.send_message(text, parse_mode, to_group=True)
    
    async def test_connection(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/getMe")
                
                if response.status_code == 200:
                    bot_info = response.json()["result"]
                    logger.info(f"✅ Бот подключен: @{bot_info.get('username')}")
                    return True
                else:
                    logger.error(f"❌ Ошибка подключения: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования подключения: {e}")
            return False
    
    async def send_message_with_keyboard(self, text: str, keyboard: list = None, **kwargs):
        return await self.keyboard_builder.send_message_with_keyboard(text, keyboard, **kwargs)
    
    async def edit_message_with_keyboard(self, text: str, keyboard: list = None, **kwargs):
        return await self.keyboard_builder.edit_message_with_keyboard(text, keyboard, **kwargs)
    
    async def send_or_edit_message_with_keyboard(self, text: str, keyboard: list = None, should_edit: bool = False, **kwargs):
        return await self.keyboard_builder.send_or_edit_message_with_keyboard(text, keyboard, should_edit, **kwargs)
    
    async def start_listening(self):
        return await self.update_processor.start_listening()
    
    def stop_listening(self):
        self.is_listening = False
        if self._update_processor:
            self._update_processor.stop_listening()
    
    async def get_all_channels_grouped(self):
        return await self.channel_manager.get_all_channels_grouped()
    
    async def add_channel_handler(self, channel_link: str):
        return await self.channel_manager.add_channel_handler(channel_link)
    
    async def send_command_response(self, text: str, message: dict, parse_mode: str = "HTML") -> bool:
        chat_id = message.get("chat", {}).get("id", self.admin_chat_id)
        return await self._send_to_single_user(text, chat_id, parse_mode)
    
    async def remove_old_keyboard(self, to_group: bool = None):
        return await self.keyboard_builder.remove_old_keyboard(to_group)
    
    async def delete_user_message(self, message_id: int, chat_id: int = None):
        return await self.update_processor.delete_user_message(message_id, chat_id)
    
    async def handle_forwarded_message(self, message: dict):
        return await self.update_processor._handle_forwarded_message(message)
    
    async def deactivate_old_inline_messages(self, exclude_message_id: int = None):
        try:
            messages_to_remove = []
            
            for message_data in self.active_inline_messages[:]:
                chat_id = message_data['chat_id']
                message_id = message_data['message_id']
                
                if exclude_message_id and message_id == exclude_message_id:
                    continue
                
                try:
                    data = {
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "reply_markup": ""
                    }
                    
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.post(f"{self.base_url}/editMessageReplyMarkup", json=data)
                        
                        if response.status_code == 200:
                            logger.debug(f"✅ Кнопки убраны с сообщения {message_id}")
                        else:
                            logger.debug(f"⚠️ Не удалось убрать кнопки: {response.text}")
                        
                        messages_to_remove.append(message_data)
                        
                except Exception as e:
                    logger.debug(f"❌ Ошибка деактивации сообщения {message_id}: {e}")
                    messages_to_remove.append(message_data)
            
            for message_data in messages_to_remove:
                if message_data in self.active_inline_messages:
                    self.active_inline_messages.remove(message_data)
            
            if len(self.active_inline_messages) > 10:
                self.active_inline_messages = self.active_inline_messages[-5:]
                
        except Exception as e:
            logger.error(f"❌ Ошибка деактивации старых сообщений: {e}")
    
    async def handle_callback(self, data: str, callback_query: dict):
        return await self.callback_processor.handle_callback(data, callback_query)
    
    async def send_message_to_channel(self, text: str, channel_target: str, parse_mode: str = "HTML", thread_id: int = None) -> bool:
        try:
            chat_id = self._get_chat_id_from_target(channel_target)
            
            data = {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True
            }
            
            if thread_id:
                data["message_thread_id"] = thread_id
            
            if parse_mode:
                data["parse_mode"] = parse_mode
            
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.base_url}/sendMessage", json=data)
                
                if response.status_code == 200:
                    logger.info(f"📤 Сообщение отправлено в {chat_id}")
                    return True
                else:
                    logger.error(f"❌ Ошибка отправки в канал: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка send_message_to_channel: {e}")
            return False
    
    async def send_media_with_caption(self, media_path: str, caption: str = "", channel_target: str = None, media_type: str = "photo", thread_id: int = None) -> bool:
        try:
            if channel_target:
                chat_id = self._get_chat_id_from_target(channel_target)
            else:
                chat_id = self.chat_id
            
            if media_type == "photo":
                url = f"{self.base_url}/sendPhoto"
                files_key = "photo"
            elif media_type == "video":
                url = f"{self.base_url}/sendVideo"
                files_key = "video"
            else:
                url = f"{self.base_url}/sendDocument"
                files_key = "document"
            
            data = {"chat_id": chat_id}
            
            if thread_id:
                data["message_thread_id"] = thread_id
                
            if caption:
                data["caption"] = caption
                data["parse_mode"] = "HTML"
            
            with open(media_path, 'rb') as media_file:
                files = {files_key: media_file}
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, data=data, files=files)
                    
                    if response.status_code == 200:
                        logger.info(f"📤 Медиа отправлено в {chat_id}")
                        return True
                    else:
                        logger.error(f"❌ Ошибка отправки медиа: {response.text}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Ошибка send_media_with_caption: {e}")
            return False
    
    def _get_chat_id_from_target(self, channel_target: str) -> str:
        if isinstance(channel_target, str) and channel_target.startswith("https://t.me/+"):
            logger.warning(f"⚠️ Нужен chat_id для приватной группы {channel_target}")
            return str(self.chat_id)
        elif isinstance(channel_target, str) and channel_target.startswith("https://t.me/"):
            username = channel_target.split("https://t.me/")[1]
            return f"@{username}"
        elif isinstance(channel_target, str) and channel_target.startswith("@"):
            return channel_target
        elif isinstance(channel_target, str) and not channel_target.startswith("@"):
            return f"@{channel_target}"
        else:
            return str(channel_target)
    
    async def send_media_group(self, media_files: list, caption: str = "", channel_target: str = None, thread_id: int = None) -> bool:
        try:
            if channel_target:
                chat_id = self._get_chat_id_from_target(channel_target)
            else:
                chat_id = self.chat_id

            url = f"{self.base_url}/sendMediaGroup"
            
            media_group = []
            files_data = {}
            
            for i, (file_path, media_type) in enumerate(media_files):
                file_key = f"file_{i}"
                
                media_item = {
                    "type": media_type,
                    "media": f"attach://{file_key}"
                }
                
                if i == 0 and caption:
                    media_item["caption"] = caption
                    media_item["parse_mode"] = "HTML"
                
                media_group.append(media_item)
                files_data[file_key] = open(file_path, 'rb')
            
            data = {
                "chat_id": chat_id,
                "media": json.dumps(media_group)
            }
            if thread_id:
                data["message_thread_id"] = thread_id
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=data, files=files_data)
                
                for file_obj in files_data.values():
                    file_obj.close()
                
                if response.status_code == 200:
                    logger.info(f"📤 Медиа группа отправлена в {chat_id}")
                    return True
                else:
                    logger.error(f"❌ Ошибка отправки медиа группы: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка send_media_group: {e}")
            return False
    
    async def send_error_alert(self, error_message: str) -> bool:
        try:
            message = f"""
🚨 <b>Ошибка системы</b>

❌ <code>{error_message}</code>

🕐 Время: <code>{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</code>
"""
            
            return await self.send_message(message)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки алерта: {e}")
            return False
    
    async def send_status_update(self, stats: dict) -> bool:
        try:
            message = f"""
🖥️ <b>Статус системы</b>

📊 <b>Статистика за сегодня:</b>
• Всего сообщений: <b>{stats.get('total_messages', 0)}</b>
• Отобрано: <b>{stats.get('selected_messages', 0)}</b>
• Последнее обновление: <code>{datetime.now().strftime('%H:%M:%S')}</code>

💾 <b>Ресурсы системы:</b>
• Память: <b>{stats.get('memory_percent', 0):.1f}%</b>
• CPU: <b>{stats.get('cpu_percent', 0):.1f}%</b>
"""
            
            return await self.send_message(message)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки статуса: {e}")
            return False
    
    async def send_startup_notification(self) -> bool:
        try:
            import pytz
            vladivostok_tz = pytz.timezone('Asia/Vladivostok')
            current_time = datetime.now(vladivostok_tz)
            
            message = f"""
🚀 <b>Система мониторинга запущена!</b>

✅ Все компоненты инициализированы
📡 Подписки на каналы настроены  
⚡ Real-time мониторинг активен
👂 Прослушивание команд включено

🕐 {current_time.strftime('%d.%m.%Y %H:%M:%S')} (Владивосток)

💬 Используйте /start для управления системой
"""
            
            return await self.send_message(message)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о запуске: {e}")
            return False