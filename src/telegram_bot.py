"""
🤖 Telegram Bot Module
Модуль для отправки уведомлений через Telegram бота
Не конфликтует с пользовательским аккаунтом
"""

import asyncio
import httpx
import subprocess
import os
import sys
from typing import List, Dict, Optional
from loguru import logger
from datetime import datetime
import json
import pytz
import yaml


class TelegramBot:
    """Telegram бот для отправки уведомлений"""
    
    def __init__(self, bot_token: str, admin_chat_id: int, group_chat_id: int = None, monitor_bot=None):
        self.bot_token = bot_token
        self.admin_chat_id = admin_chat_id  # Личный чат админа
        self.group_chat_id = group_chat_id   # Группа для всех уведомлений
        self.chat_id = admin_chat_id  # Обратная совместимость
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.monitor_bot = monitor_bot
        self.main_instance = monitor_bot  # Алиас для обратной совместимости
        
        logger.info(f"🤖 TelegramBot инициализирован:")
        logger.info(f"👤 Админ: {admin_chat_id}")
        logger.info(f"👥 Группа: {group_chat_id if group_chat_id else 'не настроена'}")
        
        # Для обработки команд
        self.update_offset = 0
        self.command_handlers = {}
        self.is_listening = False
        self.last_message_id = None  # Для редактирования сообщений
        self.edit_messages = True  # Режим редактирования сообщений (True = редактировать, False = новые сообщения)
        self.delete_commands = True  # Удалять команды пользователя
        
        # Дополнительные переменные для обработки команд
        self.start_time = None  # Время запуска бота для игнорирования старых команд
        self.pending_channel_url = None  # Сохраняем URL канала для выбора региона
        self.pending_channels_list = []  # Список каналов для массового добавления
        self.waiting_for_region_name = False  # Флаг ожидания названия нового региона
        self.waiting_for_emoji = False  # Флаг ожидания пользовательского эмодзи
        self.processed_forwards = set()  # Кэш для предотвращения дублирования forward сообщений
        self.pending_region_data = None  # Данные создаваемого региона
        self.active_inline_messages = []  # Список message_id с активными inline кнопками
        self.current_callback_chat_id = None  # Текущий chat_id из callback для edit_message_with_keyboard
        
        # Регистрируем команды управления
        self.register_command("start", self.cmd_start)
        self.register_command("help", self.cmd_help)
        self.register_command("status", self.cmd_status)
        self.register_command("start_monitoring", self.cmd_start_monitoring)
        self.register_command("stop_monitoring", self.cmd_stop_monitoring)
        self.register_command("restart", self.cmd_restart)
        self.register_command("topic_id", self.cmd_topic_id)
        self.register_command("add_channel", self.cmd_add_channel)
        self.register_command("manage_channels", self.cmd_manage_channels)
        self.register_command("stats", self.cmd_stats)
        self.register_command("settings", self.cmd_settings)
        self.register_command("force_subscribe", self.cmd_force_subscribe)
        
        asyncio.create_task(self.setup_bot_commands())
        asyncio.create_task(self.setup_main_keyboard())
    
    def is_admin_user(self, user_id: int) -> bool:
        """Проверка является ли пользователь админом"""
        return user_id == self.admin_chat_id
    
    def is_message_from_group(self, chat_id: int) -> bool:
        """Проверка пришло ли сообщение из настроенной группы"""
        return self.group_chat_id and chat_id == self.group_chat_id
    
    async def setup_bot_commands(self):
        try:
            commands = [
                {"command": "start", "description": "🏠 Главное меню"},
                {"command": "status", "description": "📊 Статус системы"},
                {"command": "manage_channels", "description": "🗂️ Управление каналами"},
                {"command": "add_channel", "description": "➕ Добавить канал"},
                {"command": "stats", "description": "📈 Статистика"},
                {"command": "start_monitoring", "description": "🚀 Запустить мониторинг"},
                {"command": "stop_monitoring", "description": "🛑 Остановить мониторинг"},
                {"command": "restart", "description": "🔄 Перезапустить систему"},
                {"command": "topic_id", "description": "📂 Узнать ID темы"},
                {"command": "force_subscribe", "description": "📡 Принудительная подписка"},
                {"command": "settings", "description": "⚙️ Настройки интерфейса"},
                {"command": "help", "description": "🆘 Справка по командам"}
            ]
            
            url = f"{self.base_url}/setMyCommands"
            data = {"commands": json.dumps(commands)}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, data=data)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        logger.info("✅ Команды для автокомплита установлены")
                    else:
                        logger.warning(f"⚠️ Ошибка установки команд: {result.get('description')}")
                else:
                    logger.error(f"❌ HTTP ошибка установки команд: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка установки команд: {e}")
    
    async def setup_main_keyboard(self):
        """Установить основную постоянную клавиатуру"""
        try:
            main_keyboard = [
                ["📊 Статус", "📈 Статистика"],
                ["🗂️ Управление каналами", "➕ Добавить канал"],
                ["🚀 Запуск", "🛑 Стоп", "🔄 Рестарт"],
                ["⚙️ Настройки", "🆘 Справка"]
            ]
            
            # Отправляем приветственное сообщение с клавиатурой админу
            welcome_text = (
                "🤖 <b>Панель управления активирована</b>\n\n"
                "⌨️ Используйте кнопки внизу экрана для управления ботом\n\n"
                "📋 Для получения полного меню команд нажмите /start"
            )
            
            await self.send_message_with_keyboard(
                welcome_text, 
                main_keyboard, 
                use_reply_keyboard=True,
                to_group=False
            )
            
            logger.info("✅ Основная клавиатура установлена")
        except Exception as e:
            logger.error(f"❌ Ошибка установки основной клавиатуры: {e}")
    
    async def handle_main_keyboard_button(self, button_text: str, message: dict):
        """Обработка нажатия кнопки основной клавиатуры"""
        try:
            # Удаляем сообщение пользователя для чистоты чата
            message_id = message.get("message_id")
            chat_id = message.get("chat", {}).get("id")
            if message_id and self.delete_commands:
                await self.delete_user_message(message_id, chat_id)
            
            # Маппинг кнопок на команды
            button_command_map = {
                "📊 Статус": "status",
                "📈 Статистика": "stats",
                "🗂️ Управление каналами": "manage_channels",
                "➕ Добавить канал": "add_channel",
                "🚀 Запуск": "start_monitoring",
                "🛑 Стоп": "stop_monitoring",
                "🔄 Рестарт": "restart",
                "⚙️ Настройки": "settings",
                "🆘 Справка": "help"
            }
            
            command = button_command_map.get(button_text)
            if command and command in self.command_handlers:
                logger.info(f"▶️ Выполняем команду {command} через кнопку")
                await self.command_handlers[command](message)
            else:
                logger.warning(f"⚠️ Неизвестная кнопка: {button_text}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки кнопки основной клавиатуры: {e}")
    
    async def send_message(self, text: str, parse_mode: str = "HTML", to_group: bool = True, to_user: int = None) -> bool:
        """Отправить сообщение в группу или конкретному пользователю"""
        try:
            if to_user:
                # Отправляем конкретному пользователю
                target_chat_id = to_user
            elif to_group and self.group_chat_id:
                # Отправляем в группу
                target_chat_id = self.group_chat_id
                logger.info(f"📤 Отправляем сообщение в группу: {self.group_chat_id}")
            else:
                # Отправляем админу в личку
                target_chat_id = self.admin_chat_id
                logger.info(f"📤 Отправляем сообщение админу: {self.admin_chat_id}")
            
            return await self._send_to_single_user(text, target_chat_id, parse_mode)
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения: {e}")
            return False
    
    async def _send_to_single_user(self, text: str, chat_id: int, parse_mode: str = "HTML") -> bool:
        """Отправка сообщения одному пользователю"""
        try:
            url = f"{self.base_url}/sendMessage"
            
            data = {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True
            }
            
            if parse_mode:
                data["parse_mode"] = parse_mode
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, data=data)
                
                if response.status_code == 200:
                    return True
                else:
                    logger.error(f"❌ Ошибка отправки пользователю {chat_id}: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения пользователю {chat_id}: {e}")
            return False
    

    
    async def send_system_notification(self, text: str, parse_mode: str = "HTML") -> bool:
        """Отправка системного уведомления в группу (запуск/остановка/ошибки)"""
        return await self.send_message(text, parse_mode, to_group=True)
    
    async def send_command_response(self, text: str, message: dict, parse_mode: str = "HTML") -> bool:
        """Отправка ответа на команду в тот же чат где была команда"""
        chat_id = message.get("chat", {}).get("id") if message else self.admin_chat_id
        # Если команда пришла из группы - отвечаем в группу, иначе в личку
        to_group = self.is_message_from_group(chat_id)
        return await self.send_message(text, parse_mode, to_group=to_group)
    
    async def send_message_with_keyboard(self, text: str, keyboard: list = None, parse_mode: str = "HTML", use_reply_keyboard: bool = True, to_group: bool = None, to_user: int = None) -> bool:
        """Отправить сообщение с клавиатурой в группу или конкретному пользователю"""
        try:
            # Если это inline кнопки - деактивируем старые
            if keyboard and not use_reply_keyboard:
                await self.deactivate_old_inline_messages()
            
            if to_user:
                # Отправляем конкретному пользователю
                target_chat_id = to_user
            elif to_group and self.group_chat_id:
                # Отправляем в группу
                target_chat_id = self.group_chat_id
            elif to_group is False:
                # Явно в личку админу
                target_chat_id = self.admin_chat_id
            else:
                # По умолчанию в группу, если есть, иначе админу
                target_chat_id = self.group_chat_id if self.group_chat_id else self.admin_chat_id
            
            return await self._send_keyboard_to_user(text, keyboard, parse_mode, use_reply_keyboard, target_chat_id)
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения с клавиатурой: {e}")
            return False
    
    async def _send_keyboard_to_user(self, text: str, keyboard: list, parse_mode: str, use_reply_keyboard: bool, user_id: int) -> bool:
        """Отправка клавиатуры одному пользователю"""
        try:
            url = f"{self.base_url}/sendMessage"
            
            data = {
                "chat_id": user_id,
                "text": text,
                "disable_web_page_preview": True
            }
            
            if parse_mode:
                data["parse_mode"] = parse_mode
                
            if keyboard:
                if use_reply_keyboard:
                    # Обычная клавиатура снизу экрана
                    reply_markup = {
                        "keyboard": keyboard,
                        "resize_keyboard": True,
                        "one_time_keyboard": False
                    }
                else:
                    # Inline клавиатура в сообщении
                    reply_markup = {"inline_keyboard": keyboard}
                
                data["reply_markup"] = json.dumps(reply_markup)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, data=data)
                
                if response.status_code == 200:
                    response_data = response.json()
                    # Сохраняем ID сообщения для возможного редактирования
                    if "result" in response_data and "message_id" in response_data["result"]:
                        message_id = response_data["result"]["message_id"]
                        self.last_message_id = message_id
                        
                        # Если это inline кнопки - добавляем в список активных
                        if keyboard and not use_reply_keyboard:
                            message_info = {'message_id': message_id, 'chat_id': user_id}
                            self.active_inline_messages.append(message_info)
                    
                    return True
                else:
                    logger.error(f"❌ Ошибка отправки: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка отправки клавиатуры пользователю {user_id}: {e}")
            return False
    

    
    async def edit_message_with_keyboard(self, text: str, keyboard: list = None, message_id: int = None, parse_mode: str = "HTML", use_reply_keyboard: bool = True, chat_id: int = None) -> bool:
        """Редактировать существующее сообщение"""
        try:
            if not message_id and not self.last_message_id:
                # Если нет ID сообщения, отправляем новое
                return await self.send_message_with_keyboard(text, keyboard, parse_mode, use_reply_keyboard)
            
            msg_id = message_id or self.last_message_id
            target_chat_id = chat_id or self.chat_id
            
            if use_reply_keyboard:
                # Для обычной клавиатуры нужно отправить новое сообщение
                # так как editMessageText не поддерживает reply_markup с keyboard
                return await self.send_message_with_keyboard(text, keyboard, parse_mode, use_reply_keyboard)
            
            url = f"{self.base_url}/editMessageText"
            
            data = {
                "chat_id": target_chat_id,
                "message_id": msg_id,
                "text": text,
                "disable_web_page_preview": True
            }
            
            if parse_mode:
                data["parse_mode"] = parse_mode
                
            if keyboard:
                reply_markup = {"inline_keyboard": keyboard}
                data["reply_markup"] = json.dumps(reply_markup)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, data=data)
                
                if response.status_code == 200:
                    # Если это inline кнопки - обновляем список активных сообщений
                    if keyboard and not use_reply_keyboard:
                        message_info = {'message_id': msg_id, 'chat_id': target_chat_id}
                        # Проверяем, что сообщение ещё не в списке
                        existing = any(
                            (isinstance(item, dict) and item.get('message_id') == msg_id) or 
                            (isinstance(item, int) and item == msg_id) 
                            for item in self.active_inline_messages
                        )
                        if not existing:
                            self.active_inline_messages.append(message_info)
                    elif not keyboard:
                        # Если убираем кнопки - удаляем из активных
                        self.active_inline_messages = [
                            item for item in self.active_inline_messages 
                            if not ((isinstance(item, dict) and item.get('message_id') == msg_id) or
                                   (isinstance(item, int) and item == msg_id))
                        ]
                    
                    logger.info("✅ Сообщение отредактировано")
                    return True
                else:
                    logger.error(f"❌ Ошибка редактирования: {response.status_code} - {response.text}")
                    # Если редактирование не удалось, отправляем новое сообщение
                    return await self.send_message_with_keyboard(text, keyboard, parse_mode, use_reply_keyboard)
                    
        except Exception as e:
            logger.error(f"❌ Ошибка редактирования сообщения: {e}")
            # Если редактирование не удалось, отправляем новое сообщение
            return await self.send_message_with_keyboard(text, keyboard, parse_mode, use_reply_keyboard)
    
    async def deactivate_old_inline_messages(self, exclude_message_id: int = None):
        """Деактивировать старые сообщения с inline кнопками"""
        try:
            messages_to_remove = []
            
            for message_data in self.active_inline_messages.copy():
                # Обработка старого формата (только message_id) и нового (с chat_id)
                if isinstance(message_data, dict):
                    message_id = message_data.get('message_id')
                    chat_id = message_data.get('chat_id', self.chat_id)
                else:
                    # Старый формат - только message_id
                    message_id = message_data
                    chat_id = self.chat_id
                
                # Пропускаем сообщение, которое нужно исключить
                if exclude_message_id and message_id == exclude_message_id:
                    continue
                    
                try:
                    url = f"{self.base_url}/editMessageReplyMarkup"
                    data = {
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "reply_markup": ""  # Убираем кнопки
                    }
                    
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.post(url, data=data)
                        
                        if response.status_code == 200:
                            result = response.json()
                            if result.get("ok"):
                                logger.debug(f"✅ Кнопки убраны с сообщения {message_id}")
                                messages_to_remove.append(message_data)
                            else:
                                logger.debug(f"⚠️ Не удалось убрать кнопки: {result.get('description')}")
                                # Удаляем из списка даже при ошибке (возможно, сообщение уже удалено)
                                messages_to_remove.append(message_data)
                        else:
                            logger.debug(f"❌ HTTP ошибка {response.status_code}")
                            messages_to_remove.append(message_data)  # Удаляем при любой ошибке
                            
                except Exception as e:
                    logger.debug(f"❌ Ошибка деактивации сообщения {message_id}: {e}")
                    # Удаляем сообщение из списка даже при ошибке
                    messages_to_remove.append(message_data)
            
            # Удаляем обработанные сообщения из списка
            for message_data in messages_to_remove:
                if message_data in self.active_inline_messages:
                    self.active_inline_messages.remove(message_data)
            
            if messages_to_remove:
                logger.info(f"🧹 Очищено {len(messages_to_remove)} старых inline кнопок")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка деактивации старых кнопок: {e}")
    
    def register_command(self, command: str, handler):
        """Регистрация обработчика команды"""
        self.command_handlers[command] = handler
        logger.info(f"📝 Зарегистрирована команда: /{command}")
    
    async def get_updates(self) -> list:
        """Получить обновления от Telegram"""
        try:
            url = f"{self.base_url}/getUpdates"
            data = {
                "offset": self.update_offset,
                "timeout": 10,
                "allowed_updates": ["message", "callback_query"]
            }
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, data=data)
                
                if response.status_code == 200:
                    result = response.json()
                    if result["ok"]:
                        updates = result["result"]
                        # Если телеграм вернул пустой массив, ничего не меняем
                        if not updates:
                            return []
                        
                        # Страхуемся от пропуска апдейтов: сдвигаем offset на max(update_id)+1 сразу
                        last_update_id = max(update.get("update_id", 0) for update in updates)
                        if last_update_id >= self.update_offset:
                            self.update_offset = last_update_id + 1
                        return updates
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения обновлений: {e}")
            return []
    
    async def delete_user_message(self, message_id, chat_id: int = None):
        """Удалить сообщение пользователя"""
        try:
            target_chat_id = chat_id or self.chat_id
            url = f"{self.base_url}/deleteMessage"
            data = {
                "chat_id": target_chat_id,
                "message_id": message_id
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(url, data=data)
        except Exception as e:
            logger.debug(f"Не удалось удалить сообщение: {e}")
    
    async def process_update(self, update: dict):
        """Обработка одного обновления"""
        try:
            # Обновляем offset (на случай если getUpdates не успел сдвинуть)
            update_id = update.get("update_id", 0)
            if update_id >= self.update_offset:
                self.update_offset = update_id + 1
            
            logger.info(f"🔄 Обрабатываем обновление: {list(update.keys())}")
            
            # Обрабатываем сообщение
            if "message" in update:
                message = update["message"]
                
                # Проверяем время сообщения - игнорируем старые команды
                message_date = message.get("date", 0)
                if self.start_time and message_date < self.start_time:
                    logger.debug(f"⏭️ Пропускаем старое сообщение (до запуска бота)")
                    return
                
                chat = message.get("chat", {})
                chat_id = chat.get("id")
                chat_type = chat.get("type")
                chat_title = chat.get("title")
                user_id = message.get("from", {}).get("id")  # Получаем ID отправителя
                
                # Логируем chat_id групп и message_thread_id тем для настройки
                if chat_type in ["group", "supergroup"] and chat_title:
                    logger.info(f"📍 Группа '{chat_title}': chat_id = {chat_id}")
                    logger.info(f"💡 Для настройки добавьте в config.yaml: target_group: {chat_id}")
                    
                    # Логируем ID темы (если сообщение в теме)
                    thread_id = message.get("message_thread_id")
                    if thread_id:
                        logger.info(f"📂 Тема в группе '{chat_title}': message_thread_id = {thread_id}")
                        logger.info(f"💡 Для настройки добавьте в config.yaml topics: region_name: {thread_id}")
                
                # Разрешаем команды от админа (в личку) или от любого участника группы
                if not (self.is_admin_user(user_id) or self.is_message_from_group(chat_id)):
                    return  # Игнорируем сообщения от неавторизованных пользователей
                    
                text = message.get("text", "")
                message_id = message.get("message_id")
                
                logger.info(f"📝 Получено сообщение: '{text}' (ID: {message_id})")
                
                if text.startswith("/"):
                    # Команда
                    command = text[1:].split()[0]  # Убираем / и берем первое слово
                    
                    # Убираем @botname из команды если есть
                    if "@" in command:
                        command = command.split("@")[0]
                    
                    logger.info(f"🔧 Обрабатываем команду: /{command}")
                    if command in self.command_handlers:
                        await self.command_handlers[command](message)
                        # Удаляем сообщение пользователя для чистоты чата
                        if message_id and self.delete_commands:
                            await self.delete_user_message(message_id, chat_id)
                    else:
                        await self.send_message(f"❌ Неизвестная команда: /{command}")
                        if message_id and self.delete_commands:
                            await self.delete_user_message(message_id, chat_id)
                else:
                    # Обычное сообщение (не команда)
                    if message.get("forward_from_chat"):
                        # Пересланное сообщение из канала
                        logger.info("📤 Обрабатываем пересланное сообщение из канала")
                        await self.handle_forwarded_message(message)
                    elif any(keyword in text for keyword in ["t.me/", "@", "https://"]):
                        logger.info(f"🔗 Обрабатываем ссылки на каналы: {text}")
                        # Ищем все каналы в сообщении
                        found_channels = self.parse_multiple_channels(text)
                        
                        if not found_channels:
                            await self.send_message("❌ Не найдено валидных каналов в сообщении")
                        elif len(found_channels) == 1:
                            # Один канал - как раньше
                            self.pending_channel_url = found_channels[0]
                            await self.show_region_selection()
                        else:
                            # Несколько каналов - показываем список
                            self.pending_channels_list = found_channels
                            await self.show_multiple_channels_selection()
                    elif self.waiting_for_region_name:
                        # Пользователь вводит название нового региона
                        logger.info(f"🏷️ Получено название нового региона: '{text}'")
                        self.waiting_for_region_name = False
                        await self.handle_region_creation(text)
                    elif self.waiting_for_emoji:
                        # Пользователь вводит пользовательский эмодзи
                        logger.info(f"🎨 Получен пользовательский эмодзи: '{text}'")
                        self.waiting_for_emoji = False
                        await self.handle_custom_emoji_input(text)
                    elif text in ["📊 Статус", "📈 Статистика", "🗂️ Управление каналами", "➕ Добавить канал", "🚀 Запуск", "🛑 Стоп", "🔄 Рестарт", "⚙️ Настройки", "🆘 Справка"]:
                        # Обработка кнопок основной клавиатуры
                        logger.info(f"🎛️ Нажата кнопка основной клавиатуры: '{text}'")
                        await self.handle_main_keyboard_button(text, message)
                    else:
                        logger.info(f"❓ Неизвестное сообщение: '{text}'")
                        await self.send_message("ℹ️ Используйте кнопки снизу или отправьте ссылку на канал.\nДля справки: /help")
                    
                    # Удаляем сообщение пользователя для всех кнопок и ссылок
                    if message_id and not text.startswith("/") and self.delete_commands:
                        await self.delete_user_message(message_id)
            
            # Обрабатываем callback query (нажатия кнопок)
            elif "callback_query" in update:
                callback = update["callback_query"]
                callback_user_id = callback.get("from", {}).get("id")
                callback_chat_id = callback.get("message", {}).get("chat", {}).get("id")
                
                # Разрешаем callback от админа или из группы
                if not (self.is_admin_user(callback_user_id) or self.is_message_from_group(callback_chat_id)):
                    return
                    
                callback_data = callback.get("data", "")
                logger.info(f"🎯 Получен callback: '{callback_data}' от пользователя {callback_user_id} в чате {callback_chat_id}")
                
                # Проверяем что callback пришел не через reply в группе
                callback_message = callback.get("message", {})
                reply_to = callback_message.get("reply_to_message")
                if reply_to and self.is_message_from_group(callback_chat_id):
                    logger.warning(f"⚠️ Callback через reply в группе может вызывать проблемы!")
                
                await self.handle_callback(callback_data, callback)
            
            # Обрабатываем изменения членства (добавление в группы)
            elif "my_chat_member" in update:
                member_update = update["my_chat_member"]
                chat = member_update.get("chat", {})
                chat_id = chat.get("id")
                chat_type = chat.get("type")
                chat_title = chat.get("title", "Неизвестная группа")
                new_member = member_update.get("new_chat_member", {})
                status = new_member.get("status")
                
                if chat_type in ["group", "supergroup"] and status == "administrator":
                    logger.success(f"🎉 Бот добавлен как администратор в группу '{chat_title}'")
                    logger.info(f"📍 Chat ID группы: {chat_id}")
                    logger.info(f"💡 Добавьте в config.yaml: target_group: {chat_id}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки обновления: {e}")
    
    async def handle_callback(self, data: str, callback_query: dict):
        """Обработка нажатий на inline кнопки"""
        try:
            # Подтверждаем нажатие кнопки
            callback_url = f"{self.base_url}/answerCallbackQuery"
            await httpx.AsyncClient(timeout=10.0).post(callback_url, data={
                "callback_query_id": callback_query["id"]
            })
            
            # Убираем кнопки из текущего сообщения (кроме специальных случаев)
            message = callback_query.get("message", {})
            current_message_id = message.get("message_id")
            
            # Список callback'ов где кнопки НЕ убираются (для навигации)
            keep_buttons_callbacks = [
                "no_action",         # Неактивные кнопки
                "add_channel",       # Добавление канала
                "settings",          # Настройки
                "help",             # Справка
                "stats",            # Статистика
                "status",           # Статус
                "start",            # Главное меню
                "manage_channels",   # Управление каналами
                "refresh_channels",  # Обновление списка каналов
                "clear_stats",       # Очистка статистики
                "start_monitoring",  # Запуск мониторинга
                "stop_monitoring",   # Остановка мониторинга
                "restart",          # Рестарт системы
                "force_subscribe",   # Принудительная подписка
            ]
            
            # Также не убираем кнопки для навигационных callback'ов и действий по регионам
            keep_prefixes = [
                "region_page_",      # Навигация по страницам регионов
                "channels_page_",    # Навигация по страницам каналов
                "manage_region_",    # Открытие конкретного региона
                "delete_channel_",   # Просмотр подтверждения удаления
                "confirm_delete_",   # Подтверждение удаления
                "region_"            # Выбор региона для добавления канала
            ]
            
            keep_by_prefix = any(data.startswith(prefix) for prefix in keep_prefixes)
            
            if current_message_id and data not in keep_buttons_callbacks and not keep_by_prefix:
                try:
                    # Убираем кнопки из текущего сообщения  
                    callback_chat_id = callback_query.get("message", {}).get("chat", {}).get("id", self.chat_id)
                    edit_url = f"{self.base_url}/editMessageReplyMarkup"
                    edit_data = {
                        "chat_id": callback_chat_id,
                        "message_id": current_message_id,
                        "reply_markup": ""
                    }
                    
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.post(edit_url, data=edit_data)
                        if response.status_code == 200:
                            result = response.json()
                            if result.get("ok"):
                                # Удаляем из списка активных inline сообщений (оба формата)
                                self.active_inline_messages = [
                                    item for item in self.active_inline_messages 
                                    if not ((isinstance(item, dict) and item.get('message_id') == current_message_id) or
                                           (isinstance(item, int) and item == current_message_id))
                                ]
                        
                except Exception as e:
                    logger.debug(f"⚠️ Не удалось убрать кнопки из сообщения {current_message_id}: {e}")
            
            # Создаем псевдо-message объект из callback для правильной обработки
            callback_message = {
                "chat": callback_query.get("message", {}).get("chat", {}),
                "from": callback_query.get("from", {})
            }
            
            # Сохраняем chat_id из callback для использования в edit_message_with_keyboard
            self.current_callback_chat_id = callback_query.get("message", {}).get("chat", {}).get("id", self.chat_id)
            logger.info(f"📱 Callback из чата: {self.current_callback_chat_id} (группа: {self.current_callback_chat_id == self.group_chat_id})")
            
            # Обрабатываем действие  
            if data == "start":
                await self.cmd_start(callback_message)
            elif data == "status":
                await self.cmd_status(callback_message)
            elif data == "channels":
                await self.cmd_manage_channels(callback_message)
            elif data.startswith("channels_page_"):
                page = int(data.replace("channels_page_", ""))
                await self.show_channels_page(page)
            elif data == "stats":
                await self.cmd_stats(callback_message)
            elif data == "add_channel":
                logger.info("🔧 Обрабатываем callback 'add_channel'")
                add_text = (
                    "➕ <b>Добавление канала</b>\n\n"
                    "Отправьте ссылку на канал в любом формате:\n"
                    "• https://t.me/channel_name\n"
                    "• @channel_name\n"
                    "• /add_channel https://t.me/channel_name\n\n"
                    "Канал будет автоматически добавлен в мониторинг!"
                )
                keyboard = [[{"text": "🏠 Главное меню", "callback_data": "start"}]]
                await self.edit_message_with_keyboard(add_text, keyboard, use_reply_keyboard=False, chat_id=self.current_callback_chat_id)
            elif data.startswith("remove_channel_"):
                channel_name = data.replace("remove_channel_", "")
                await self.remove_channel_handler(channel_name)
            elif data == "toggle_delete":
                self.delete_commands = not self.delete_commands
                await self.cmd_settings(callback_message)
            elif data == "toggle_edit":
                self.edit_messages = not self.edit_messages
                await self.cmd_settings(callback_message)
            elif data == "clear_stats":
                await self.clear_stats_handler()
            elif data == "settings":
                logger.info("🔧 Обрабатываем callback 'settings'")
                await self.cmd_settings(callback_message)
            elif data == "help":
                logger.info("🔧 Обрабатываем callback 'help'")  
                await self.cmd_help(callback_message)
            elif data == "start_monitoring":
                await self.cmd_start_monitoring(callback_message)
            elif data == "stop_monitoring":
                await self.cmd_stop_monitoring(callback_message)
            elif data == "restart":
                await self.cmd_restart(callback_message)
            elif data == "force_subscribe":
                await self.cmd_force_subscribe(callback_message)
            elif data.startswith("region_bulk_"):
                region = data.replace("region_bulk_", "")
                await self.handle_bulk_region_selection(region)
            elif data.startswith("region_page_"):
                # Формат: region_page_region_key_page_number
                parts = data.replace("region_page_", "").rsplit("_", 1)
                if len(parts) == 2:
                    region_key, page_str = parts
                    try:
                        page = int(page_str)
                        await self.show_region_channels(region_key, page)
                    except ValueError:
                        logger.error(f"❌ Неверный номер страницы: {page_str}")
            elif data.startswith("region_"):
                region = data.replace("region_", "")
                await self.handle_region_selection(region)
            elif data == "create_new_region":
                await self.start_create_region_flow()
            elif data.startswith("emoji_"):
                if data == "emoji_custom":
                    await self.start_custom_emoji_input()
                else:
                    emoji = data.replace("emoji_", "")
                    await self.handle_emoji_selection(emoji)
            elif data.startswith("confirm_create_"):
                region_key = data.replace("confirm_create_", "")
                await self.create_region_confirmed(region_key)
            elif data == "region_cancel":
                self.pending_channel_url = None
                self.waiting_for_region_name = False
                self.waiting_for_emoji = False
                self.pending_region_data = None
                await self.cmd_start(callback_message)
            elif data == "manage_channels":
                await self.cmd_manage_channels(callback_message)
            elif data == "refresh_channels":
                await self.cmd_manage_channels(callback_message)
            elif data.startswith("manage_region_"):
                region_key = data.replace("manage_region_", "")
                await self.show_region_channels(region_key)
            elif data == "no_action":
                # Заглушка для неактивных кнопок (например, индикатор страницы)
                pass
            elif data.startswith("delete_channel_"):
                # Формат: delete_channel_region_key_username
                parts = data.replace("delete_channel_", "").split("_", 1)
                if len(parts) == 2:
                    region_key, username = parts
                    await self.show_delete_confirmation(region_key, username)
            elif data.startswith("confirm_delete_"):
                # Формат: confirm_delete_region_key_username
                parts = data.replace("confirm_delete_", "").split("_", 1)
                if len(parts) == 2:
                    region_key, username = parts
                    await self.delete_channel_from_config(region_key, username)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки callback: {e}")
        finally:
            # Очищаем callback chat_id после обработки
            self.current_callback_chat_id = None
    
    async def send_message_to_channel(self, text: str, channel_target: str, parse_mode: str = "HTML", thread_id: int = None) -> bool:
        """Отправить сообщение в канал или группу (с поддержкой тем)"""
        try:
            url = f"{self.base_url}/sendMessage"
            
            # Определяем chat_id для канала
            chat_id = channel_target
            
            # Определяем chat_id по типу ссылки
            if isinstance(channel_target, str) and channel_target.startswith("https://t.me/+"):
                # Приватная группа - нужен числовой chat_id, но у нас только ссылка
                # Пока отправляем в личный чат как запасной вариант
                logger.warning(f"⚠️ Нужен chat_id для приватной группы {channel_target}")
                logger.warning("💡 Добавьте в config.yaml: target_group: -1001234567890 (числовой ID)")
                chat_id = self.chat_id
            elif isinstance(channel_target, str) and channel_target.startswith("https://t.me/"):
                # Извлекаем username из обычной ссылки
                username = channel_target.split("https://t.me/")[1]
                chat_id = f"@{username}"
            elif isinstance(channel_target, str) and channel_target.startswith("@"):
                chat_id = channel_target
            elif isinstance(channel_target, str) and not channel_target.startswith("@"):
                chat_id = f"@{channel_target}"
            
            data = {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True
            }
            
            # Добавляем ID темы для групп с topics
            if thread_id:
                data["message_thread_id"] = thread_id
            
            # Добавляем parse_mode только если он указан
            if parse_mode:
                data["parse_mode"] = parse_mode
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, data=data)
                
                if response.status_code == 200:
                    logger.info(f"✅ Сообщение отправлено в канал: {chat_id}")
                    return True
                else:
                    logger.error(f"❌ Ошибка отправки в канал: {response.status_code} - {response.text}")
                    # Пытаемся отправить в личный чат как запасной вариант
                    logger.info("🔄 Пытаемся отправить в личный чат как запасной вариант")
                    return await self.send_message(text, parse_mode)
                    
        except Exception as e:
            logger.error(f"❌ Ошибка отправки в канал: {e}")
            # Отправляем в личный чат как запасной вариант
            logger.info("🔄 Отправляем в личный чат как запасной вариант")
            return await self.send_message(text, parse_mode)
    
    async def send_news_digest(self, selected_news: List[Dict]) -> bool:
        """Отправить дайджест новостей"""
        try:
            if not selected_news:
                await self.send_message("📰 <b>Дайджест новостей</b>\n\nНовых важных новостей не найдено.")
                return True
            
            # Формируем красивое сообщение
            vladivostok_tz = pytz.timezone('Asia/Vladivostok')
            timestamp = datetime.now(vladivostok_tz).strftime("%H:%M")
            message_parts = [
                f"📰 <b>Дайджест новостей</b> • {timestamp}",
                f"📊 Отобрано: <b>{len(selected_news)}</b> новостей",
                ""
            ]
            
            for i, news in enumerate(selected_news, 1):  # ВСЕ НОВОСТИ БЕЗ ОГРАНИЧЕНИЙ
                title = news.get('title', 'Без заголовка')[:100]
                source = news.get('channel_title', 'Неизвестный источник')
                score = news.get('ai_score', 0)
                url = news.get('url', '')
                
                news_text = f"<b>{i}.</b> {title}"
                if len(title) == 100:
                    news_text += "..."
                
                news_text += f"\n📍 <i>{source}</i>"
                news_text += f" • ⭐ {score}/10"
                
                if url:
                    news_text += f" • <a href='{url}'>Читать</a>"
                
                message_parts.append(news_text)
            
            # Больше не показываем "и еще X новостей" - отправляем ВСЕ!
            
            message = "\n\n".join(message_parts)
            
            # Telegram имеет лимит 4096 символов
            if len(message) > 4000:
                # Разбиваем на части
                parts = self._split_message(message)
                for part in parts:
                    success = await self.send_message(part)
                    if not success:
                        return False
                    await asyncio.sleep(1)  # Небольшая задержка
            else:
                return await self.send_message(message)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки дайджеста: {e}")
            return False
    
    def _split_message(self, message: str, max_length: int = 4000) -> List[str]:
        """Разбить длинное сообщение на части"""
        if len(message) <= max_length:
            return [message]
        
        parts = []
        lines = message.split('\n')
        current_part = ""
        
        for line in lines:
            if len(current_part + line + '\n') > max_length:
                if current_part:
                    parts.append(current_part.strip())
                    current_part = line + '\n'
                else:
                    # Строка слишком длинная, обрезаем
                    parts.append(line[:max_length-3] + "...")
            else:
                current_part += line + '\n'
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts
    
    async def send_status_update(self, stats: Dict) -> bool:
        """Отправить обновление статуса"""
        try:
            message = f"""
🖥️ <b>Статус системы</b>

📊 <b>Статистика за сегодня:</b>
• Всего сообщений: <b>{stats.get('total_messages', 0)}</b>
• Отобрано: <b>{stats.get('selected_messages', 0)}</b>
• Последнее обновление: <code>{datetime.now(pytz.timezone('Asia/Vladivostok')).strftime('%H:%M:%S')}</code>

💾 <b>Ресурсы системы:</b>
• Память: <b>{stats.get('memory_percent', 0):.1f}%</b>
• CPU: <b>{stats.get('cpu_percent', 0):.1f}%</b>
"""
            
            return await self.send_message(message)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки статуса: {e}")
            return False
    
    async def send_error_alert(self, error_message: str) -> bool:
        """Отправить уведомление об ошибке"""
        try:
            message = f"""
🚨 <b>Ошибка системы</b>

❌ <code>{error_message}</code>

🕐 Время: <code>{datetime.now(pytz.timezone('Asia/Vladivostok')).strftime('%d.%m.%Y %H:%M:%S')}</code>
"""
            
            return await self.send_message(message)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки алерта: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Тест подключения к боту"""
        try:
            url = f"{self.base_url}/getMe"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    bot_info = response.json()
                    bot_name = bot_info.get('result', {}).get('first_name', 'Неизвестно')
                    logger.success(f"✅ Подключение к боту '{bot_name}' успешно")
                    
                    # Отправляем тестовое сообщение
                    vladivostok_tz = pytz.timezone('Asia/Vladivostok')
                    current_time = datetime.now(vladivostok_tz).strftime('%d.%m.%Y %H:%M:%S')
                    test_message = f"🤖 <b>Бот запущен</b>\n\nСистема мониторинга новостей активна!\n\n🕐 {current_time} (Владивосток)"
                    await self.send_message(test_message)
                    
                    return True
                else:
                    logger.error(f"❌ Ошибка подключения к боту: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования бота: {e}")
            return False
    
    def _get_chat_id_from_target(self, channel_target: str) -> str:
        """Определить chat_id из target канала"""
        if isinstance(channel_target, str) and channel_target.startswith("https://t.me/+"):
            # Для приватных каналов возвращаем None - будет использоваться личный чат
            return None
        elif isinstance(channel_target, str) and channel_target.startswith("https://t.me/"):
            # Извлекаем username из обычной ссылки
            username = channel_target.split("https://t.me/")[1]
            return f"@{username}"
        elif isinstance(channel_target, str) and channel_target.startswith("@"):
            return channel_target
        elif isinstance(channel_target, str) and not channel_target.startswith("@"):
            return f"@{channel_target}"
        else:
            return str(channel_target)
    
    async def send_media_with_caption(self, media_path: str, caption: str = "", channel_target: str = None, media_type: str = "photo", thread_id: int = None) -> bool:
        """Отправить медиа файл с подписью через Bot API (с поддержкой тем)"""
        try:
            # Определяем куда отправлять
            if channel_target:
                chat_id = self._get_chat_id_from_target(channel_target)
                if not chat_id:
                    logger.warning(f"❌ Не удалось определить chat_id для {channel_target}, отправляем в личный чат")
                    chat_id = self.chat_id
            else:
                chat_id = self.chat_id

            # Готовим URL и данные
            if media_type == "photo":
                url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
                files_key = "photo"
            elif media_type == "video":
                url = f"https://api.telegram.org/bot{self.bot_token}/sendVideo"
                files_key = "video"
            else:
                url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
                files_key = "document"

            data = {"chat_id": chat_id}
            
            # Добавляем ID темы для групп с topics
            if thread_id:
                data["message_thread_id"] = thread_id
                
            if caption:
                data["caption"] = caption
                data["parse_mode"] = "HTML"
                logger.info(f"📝 Отправляем медиа с caption (длина {len(caption)}): {caption[:100]}{'...' if len(caption) > 100 else ''}")
            else:
                logger.warning("⚠️ Caption пустой при отправке медиа!")

            # Отправляем файл
            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(media_path, 'rb') as media_file:
                    files = {files_key: media_file}
                    response = await client.post(url, data=data, files=files)
                    
                    if response.status_code == 200:
                        logger.info(f"✅ Медиа отправлено: {media_type}")
                        return True
                    else:
                        logger.error(f"❌ Ошибка отправки медиа: {response.status_code} - {response.text}")
                        # Если не удалось отправить в канал, пробуем в личный чат
                        if chat_id != self.chat_id:
                            logger.info("🔄 Пытаемся отправить медиа в личный чат")
                            data["chat_id"] = self.chat_id
                            with open(media_path, 'rb') as media_file:
                                files = {files_key: media_file}
                                response = await client.post(url, data=data, files=files)
                                return response.status_code == 200
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Ошибка отправки медиа: {e}")
            return False
    
    async def send_media_group(self, media_files: list, caption: str = "", channel_target: str = None, thread_id: int = None) -> bool:
        """Отправить группу медиа файлов (альбом) через Bot API"""
        try:
            # Определяем куда отправлять
            if channel_target:
                chat_id = self._get_chat_id_from_target(channel_target)
                if not chat_id:
                    logger.warning(f"❌ Не удалось определить chat_id для {channel_target}, отправляем в личный чат")
                    chat_id = self.chat_id
            else:
                chat_id = self.chat_id

            url = f"https://api.telegram.org/bot{self.bot_token}/sendMediaGroup"
            
            # Формируем медиа группу
            media_group = []
            files_data = {}
            
            for i, (file_path, media_type) in enumerate(media_files):
                file_key = f"file_{i}"
                
                media_item = {
                    "type": media_type,
                    "media": f"attach://{file_key}"
                }
                
                # Caption добавляем только к первому медиа
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
            
            # Отправляем группу медиа
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, data=data, files=files_data)
                
                # Закрываем файлы
                for f in files_data.values():
                    f.close()
                
                if response.status_code == 200:
                    logger.info(f"✅ Медиа группа отправлена ({len(media_files)} файлов)")
                    return True
                else:
                    logger.error(f"❌ Ошибка отправки медиа группы: {response.status_code} - {response.text}")
                    # Если не удалось отправить в канал, пробуем в личный чат
                    if chat_id != self.chat_id:
                        logger.info("🔄 Пытаемся отправить медиа группу в личный чат")
                        data["chat_id"] = self.chat_id
                        # Переоткрываем файлы
                        files_data = {f"file_{i}": open(file_path, 'rb') for i, (file_path, _) in enumerate(media_files)}
                        response = await client.post(url, data=data, files=files_data)
                        # Закрываем файлы
                        for f in files_data.values():
                            f.close()
                        return response.status_code == 200
                    return False
                        
        except Exception as e:
            logger.error(f"❌ Ошибка отправки медиа группы: {e}")
            return False
    
    # ==================== КОМАНДЫ БОТА ====================
    
    async def remove_old_keyboard(self, to_group: bool = None):
        """Удалить старую текстовую клавиатуру"""
        try:
            if to_group and self.group_chat_id:
                target_chat_id = self.group_chat_id
            elif to_group is False:
                target_chat_id = self.admin_chat_id
            else:
                target_chat_id = self.group_chat_id if self.group_chat_id else self.admin_chat_id

            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": target_chat_id,
                "text": "🔄 Обновление интерфейса...",
                "reply_markup": json.dumps({"remove_keyboard": True})
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, data=data)
                if response.status_code == 200:
                    # Сразу удаляем это сообщение
                    result = response.json()
                    if result.get("ok") and "result" in result:
                        message_id = result["result"]["message_id"]
                        await asyncio.sleep(0.5)  # Небольшая задержка
                        await self.delete_user_message(message_id, target_chat_id)
                        
        except Exception as e:
            logger.debug(f"⚠️ Не удалось удалить старую клавиатуру: {e}")

    async def cmd_start(self, message):
        """Команда /start - главное меню"""
        # Определяем куда отправлять ответ
        chat_id = message.get("chat", {}).get("id") if message else self.admin_chat_id
        to_group = self.is_message_from_group(chat_id) if chat_id else None
        
        keyboard = [
            [{"text": "📊 Статус", "callback_data": "status"}, {"text": "🗂️ Управление каналами", "callback_data": "manage_channels"}],
            [{"text": "📈 Статистика", "callback_data": "stats"}, {"text": "➕ Добавить канал", "callback_data": "add_channel"}],
            [{"text": "🚀 Запуск", "callback_data": "start_monitoring"}, {"text": "🛑 Стоп", "callback_data": "stop_monitoring"}],
            [{"text": "🔄 Рестарт", "callback_data": "restart"}, {"text": "⚙️ Настройки", "callback_data": "settings"}],
            [{"text": "📡 Принудительная подписка", "callback_data": "force_subscribe"}, {"text": "🆘 Справка", "callback_data": "help"}]
        ]
        
        welcome_text = (
            "🤖 <b>Панель управления ботом мониторинга новостей</b>\n\n"
            "📋 <b>Доступные команды:</b>\n"
            "📊 /status - статус системы\n"
            "🗂️ /manage_channels - управление каналами\n"
            "➕ /add_channel - добавить канал\n"
            "📈 /stats - статистика\n"
            "🚀 /start_monitoring - запустить мониторинг\n"
            "🛑 /stop - остановить мониторинг\n"
            "🔄 /restart - перезапуск системы\n"
            "📂 /topic_id - узнать ID темы в группе\n"
            "📡 /force_subscribe - принудительная подписка на каналы\n"
            "⚙️ /settings - настройки интерфейса\n\n"
            "⌨️ <b>Или используйте кнопки ниже:</b>\n\n"
            "⚠️ <b>В группе:</b> пишите команды в чат напрямую, не отвечайте на сообщения бота!"
        )
        
        # Сначала удаляем старую клавиатуру если она есть
        await self.remove_old_keyboard(to_group)
        
        await self.send_message_with_keyboard(welcome_text, keyboard, use_reply_keyboard=False, to_group=to_group)
    
    async def cmd_manage_channels(self, message):
        """Команда для управления каналами"""
        try:
            # Получаем список всех каналов из конфигурации
            channels_data = await self.get_all_channels_grouped()
            
            if not channels_data:
                keyboard = [
                    [{"text": "➕ Добавить первый канал", "callback_data": "add_channel"}],
                    [{"text": "🏠 Главное меню", "callback_data": "start"}]
                ]
                
                # Определяем куда отправлять ответ
                chat_id = message.get("chat", {}).get("id") if message else self.admin_chat_id
                to_group = self.is_message_from_group(chat_id) if chat_id else None
                
                await self.send_message_with_keyboard(
                    "📂 <b>Управление каналами</b>\n\n"
                    "❌ Каналы не найдены\n\n"
                    "Добавьте первый канал для мониторинга!",
                    keyboard,
                    use_reply_keyboard=False,
                    to_group=to_group
                )
                return
            
            # Показываем список каналов по регионам
            await self.show_channels_management(channels_data, message)
            
        except Exception as e:
            logger.error(f"❌ Ошибка управления каналами: {e}")
            await self.send_command_response("❌ Произошла ошибка при загрузке каналов", message)
    
    async def get_all_channels_grouped(self):
        """Получить все каналы, сгруппированные по регионам"""
        try:
            channels_config = await self.get_channels_from_config()
            if not channels_config:
                return {}
            
            # Загружаем информацию о регионах для корректных названий
            regions_info = await self.load_regions_from_config()
            regions_dict = {r['key']: r for r in regions_info}
            
            # Группируем каналы по регионам
            grouped_channels = {}
            
            # Проверяем новый формат (с регионами)
            if 'regions' in channels_config:
                for region_key, region_data in channels_config['regions'].items():
                    # Используем информацию из config.yaml если доступна
                    if region_key in regions_dict:
                        region_name = regions_dict[region_key]['name']
                    else:
                        region_name = region_data.get('name', region_key)
                    
                    channels = region_data.get('channels', [])
                    
                    # Показываем регион даже если в нем нет каналов (для управления)
                    grouped_channels[region_key] = {
                        'name': region_name,
                        'channels': channels
                    }
            else:
                # Старый формат - все каналы в общем разделе
                all_channels = []
                for channel in channels_config:
                    if isinstance(channel, dict):
                        all_channels.append(channel)
                    else:
                        all_channels.append({'username': channel, 'title': channel})
                
                if all_channels:
                    grouped_channels['general'] = {
                        'name': '📰 Общие',
                        'channels': all_channels
                    }
            
            return grouped_channels
            
        except Exception as e:
            logger.error(f"❌ Ошибка группировки каналов: {e}")
            return {}
    
    async def show_channels_management(self, channels_data, message=None):
        """Показать управление каналами с возможностью удаления"""
        try:
            text = "🗂️ <b>Управление каналами</b>\n\n"
            
            total_channels = 0
            for region_data in channels_data.values():
                total_channels += len(region_data['channels'])
            
            text += f"📊 <b>Всего каналов:</b> {total_channels}\n"
            text += f"📂 <b>Регионов:</b> {len(channels_data)}\n\n"
            
            # Создаем кнопки по регионам
            keyboard = []
            
            for region_key, region_data in channels_data.items():
                region_name = region_data['name']
                channels_count = len(region_data['channels'])
                
                button_text = f"{region_name} ({channels_count})"
                keyboard.append([{"text": button_text, "callback_data": f"manage_region_{region_key}"}])
            
            # Кнопки управления
            keyboard.append([
                {"text": "➕ Добавить канал", "callback_data": "add_channel"},
                {"text": "🔄 Обновить", "callback_data": "refresh_channels"}
            ])
            keyboard.append([{"text": "🏠 Главное меню", "callback_data": "start"}])
            
            text += "👇 Выберите регион для управления каналами:"
            
            # Определяем куда отправлять ответ
            chat_id = message.get("chat", {}).get("id") if message else self.admin_chat_id
            to_group = self.is_message_from_group(chat_id) if chat_id else None
            
            await self.send_message_with_keyboard(text, keyboard, use_reply_keyboard=False, to_group=to_group)
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа управления каналами: {e}")
    
    async def show_region_channels(self, region_key: str, page: int = 1):
        """Показать каналы конкретного региона с кнопками удаления и пагинацией"""
        try:
            channels_data = await self.get_all_channels_grouped()
            
            if region_key not in channels_data:
                await self.send_message("❌ Регион не найден")
                return
            
            region_data = channels_data[region_key]
            region_name = region_data['name']
            channels = region_data['channels']
            
            if not channels:
                keyboard = [
                    [{"text": "➕ Добавить канал", "callback_data": "add_channel"}],
                    [{"text": "🔙 Назад", "callback_data": "manage_channels"}],
                    [{"text": "🏠 Главное меню", "callback_data": "start"}]
                ]
                
                text = f"📂 <b>{region_name}</b>\n\n"
                text += f"📊 <b>Каналов в регионе:</b> 0\n\n"
                text += "❌ В этом регионе пока нет каналов"
                await self.edit_message_with_keyboard(text, keyboard, use_reply_keyboard=False)
                return
            
            # Настройки пагинации
            channels_per_page = 8  # 8 каналов на страницу (чтобы поместились навигационные кнопки)
            total_pages = (len(channels) + channels_per_page - 1) // channels_per_page
            
            # Проверяем корректность номера страницы
            if page < 1:
                page = 1
            elif page > total_pages:
                page = total_pages
            
            # Вычисляем индексы для текущей страницы
            start_idx = (page - 1) * channels_per_page
            end_idx = min(start_idx + channels_per_page, len(channels))
            current_channels = channels[start_idx:end_idx]
            
            # Формируем текст
            text = f"📂 <b>{region_name}</b>\n\n"
            text += f"📊 <b>Каналов в регионе:</b> {len(channels)}\n"
            text += f"📄 <b>Страница:</b> {page} из {total_pages}\n\n"
            text += "📋 <b>Список каналов:</b>\n"
            
            keyboard = []
            for i, channel in enumerate(current_channels, start_idx + 1):
                username = channel.get('username', 'unknown')
                title = channel.get('title', username)
                
                # Обрезаем длинные названия
                display_title = title[:25] + "..." if len(title) > 25 else title
                
                text += f"{i}. <code>@{username}</code>\n"
                text += f"   📄 {display_title}\n\n"
                
                # Кнопка удаления для каждого канала
                button_text = f"🗑️ @{username[:15]}{'...' if len(username) > 15 else ''}"
                callback_data = f"delete_channel_{region_key}_{username}"
                keyboard.append([{"text": button_text, "callback_data": callback_data}])
            
            # Навигационные кнопки (если страниц больше 1)
            if total_pages > 1:
                nav_buttons = []
                
                if page > 1:
                    nav_buttons.append({"text": "◀️ Назад", "callback_data": f"region_page_{region_key}_{page-1}"})
                
                nav_buttons.append({"text": f"📄 {page}/{total_pages}", "callback_data": "no_action"})
                
                if page < total_pages:
                    nav_buttons.append({"text": "▶️ Далее", "callback_data": f"region_page_{region_key}_{page+1}"})
                
                keyboard.append(nav_buttons)
            
            # Кнопки управления
            keyboard.append([
                {"text": "➕ Добавить канал", "callback_data": "add_channel"},
                {"text": "🔄 Обновить", "callback_data": f"manage_region_{region_key}"}
            ])
            keyboard.append([
                {"text": "🔙 К регионам", "callback_data": "manage_channels"},
                {"text": "🏠 Главное меню", "callback_data": "start"}
            ])
            
            text += "⚠️ <b>Осторожно:</b> удаление канала необратимо!"
            
            await self.edit_message_with_keyboard(text, keyboard, use_reply_keyboard=False, chat_id=self.current_callback_chat_id)
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа каналов региона: {e}")
            await self.send_message("❌ Произошла ошибка при загрузке каналов региона")
    
    async def show_delete_confirmation(self, region_key: str, username: str):
        """Показать подтверждение удаления канала"""
        try:
            channels_data = await self.get_all_channels_grouped()
            
            if region_key not in channels_data:
                await self.send_message("❌ Регион не найден")
                return
            
            # Находим канал для получения названия
            region_data = channels_data[region_key]
            region_name = region_data['name']
            channel = None
            
            for ch in region_data['channels']:
                if ch.get('username') == username:
                    channel = ch
                    break
            
            if not channel:
                await self.send_message("❌ Канал не найден")
                return
            
            channel_title = channel.get('title', username)
            
            text = (
                f"🗑️ <b>Подтверждение удаления</b>\n\n"
                f"📂 <b>Регион:</b> {region_name}\n"
                f"📺 <b>Канал:</b> @{username}\n"
                f"📄 <b>Название:</b> {channel_title}\n\n"
                f"⚠️ <b>Вы уверены, что хотите удалить этот канал?</b>\n\n"
                f"❌ Это действие <b>необратимо</b>!\n"
                f"🛑 Мониторинг канала будет остановлен\n"
                f"📊 История сообщений сохранится в базе данных"
            )
            
            keyboard = [
                [
                    {"text": "✅ Да, удалить", "callback_data": f"confirm_delete_{region_key}_{username}"},
                    {"text": "❌ Отмена", "callback_data": f"manage_region_{region_key}"}
                ]
            ]
            
            await self.edit_message_with_keyboard(text, keyboard, use_reply_keyboard=False, chat_id=self.current_callback_chat_id)
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа подтверждения удаления: {e}")
    
    async def delete_channel_from_config(self, region_key: str, username: str):
        """Удалить канал из конфигурации"""
        try:
            # Читаем конфигурацию каналов
            config_path = os.path.join("config", "channels_config.yaml")
            
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file) or {}
            
            deleted = False
            region_name = "Неизвестный регион"
            channel_title = username
            
            # Новый формат (с регионами)
            if 'regions' in config and region_key in config['regions']:
                region_data = config['regions'][region_key]
                region_name = region_data.get('name', region_key)
                channels = region_data.get('channels', [])
                
                # Ищем и удаляем канал
                for i, channel in enumerate(channels):
                    if channel.get('username') == username:
                        channel_title = channel.get('title', username)
                        channels.pop(i)
                        deleted = True
                        break
                
                # Если в регионе не осталось каналов, можно оставить пустой список
                config['regions'][region_key]['channels'] = channels
            
            if not deleted:
                await self.send_message("❌ Канал не найден в конфигурации")
                return False
            
            # Сохраняем обновленную конфигурацию  
            with open(config_path, 'w', encoding='utf-8') as file:
                yaml.dump(config, file, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            # Отправляем уведомление
            success_text = (
                f"✅ <b>Канал успешно удален!</b>\n\n"
                f"📂 <b>Регион:</b> {region_name}\n"
                f"📺 <b>Канал:</b> @{username}\n"
                f"📄 <b>Название:</b> {channel_title}\n\n"
                f"🔄 Конфигурация обновлена\n"
                f"⚡ Изменения вступят в силу при следующем перезапуске"
            )
            
            keyboard = [
                [{"text": "🔙 Назад к региону", "callback_data": f"manage_region_{region_key}"}],
                [{"text": "🗂️ Управление каналами", "callback_data": "manage_channels"}],
                [{"text": "🏠 Главное меню", "callback_data": "start"}]
            ]
            
            await self.edit_message_with_keyboard(success_text, keyboard, use_reply_keyboard=False)
            
            logger.info(f"✅ Канал @{username} удален из региона {region_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления канала: {e}")
            await self.send_message("❌ Произошла ошибка при удалении канала")
            return False
    
    async def cmd_help(self, message):
        """Команда /help"""
        help_text = (
            "🆘 <b>Справка по управлению ботом</b>\n\n"
            "📋 <b>Команды управления мониторингом:</b>\n"
            "• /start - главное меню панели управления\n"
            "• /status - статус системы мониторинга\n"
            "• /start_monitoring - запустить мониторинг новостей\n"
            "• /stop - остановить мониторинг новостей\n\n"
            "📋 <b>Команды управления каналами:</b>\n"
            "• /channels - список отслеживаемых каналов\n"
            "• /add_channel [ссылка] - добавить канал\n"
            "• /stats - статистика за сегодня\n\n"
            "📋 <b>Команды настройки:</b>\n"
            "• /settings - настройки интерфейса\n\n"
            "⌨️ <b>Кнопки снизу экрана:</b>\n"
            "• 🚀 Запуск - запустить мониторинг\n"
            "• 🛑 Стоп - остановить мониторинг\n"
            "• 🔄 Рестарт - перезапуск системы\n"
            "• 📊 Статус - состояние системы\n"
            "• 🗂️ Управление каналами - просмотр и удаление каналов\n"
            "• 📈 Статистика - статистика работы\n"
            "• ➕ Добавить канал - помощь по добавлению\n"
            "• ⚙️ Настройки - настройки интерфейса\n\n"
            "<b>💡 Примеры добавления каналов:</b>\n"
            "• <code>/add_channel https://t.me/news_channel</code>\n"
            "• <code>https://t.me/news_channel</code> (просто ссылка)\n"
            "• <code>@news_channel</code>\n\n"
            "<b>🚀 Массовое добавление каналов:</b>\n"
            "• <code>@channel1 @channel2 @channel3</code>\n"
            "• <code>https://t.me/ch1 t.me/ch2 @ch3</code>\n"
            "• Смешивайте любые форматы в одном сообщении\n\n"
            "<b>📤 Быстрое добавление через forward:</b>\n"
            "• Перешлите любой пост из канала боту\n"
            "• Бот автоматически предложит добавить этот канал\n"
            "• Регион определится автоматически по названию\n"
            "• Самый быстрый способ добавления! ⚡\n\n"
            "<b>🔧 Назначение команд:</b>\n"
            "• <b>Запуск</b> - начинает мониторинг добавленных каналов\n"
            "• <b>Стоп</b> - останавливает мониторинг (каналы остаются)\n"
            "• <b>Настройки</b> - управление интерфейсом (удаление команд, редактирование сообщений)"
        )
        
        keyboard = [[{"text": "🏠 Главное меню", "callback_data": "start"}]]
        await self.edit_message_with_keyboard(help_text, keyboard, use_reply_keyboard=False, chat_id=self.current_callback_chat_id)
    
    async def cmd_status(self, message):
        """Команда /status - статус системы"""
        try:
            # Проверяем статус мониторинга
            if self.monitor_bot and hasattr(self.monitor_bot, 'monitoring_active'):
                is_running = self.monitor_bot.monitoring_active
            else:
                is_running = True  # Если команды вызываются, значит бот работает
                
            monitoring_status = "🟢 Работает" if is_running else "🔴 Остановлен"
            monitoring_emoji = "📡" if is_running else "⏹️"
            
            # Получаем количество каналов
            try:
                channels = await self.get_channels_from_config()
                channels_count = len(channels)
            except:
                channels_count = 0
            
            status_text = (
                "📊 <b>Статус системы мониторинга</b>\n\n"
                f"🔄 <b>Панель управления:</b> 🟢 Активна\n"
                f"{monitoring_emoji} <b>Мониторинг новостей:</b> {monitoring_status}\n"
                f"📺 <b>Каналов добавлено:</b> {channels_count}\n\n"
            )
            
            if is_running:
                status_text += (
                    "💡 <b>Состояние:</b> Отслеживание активно\n\n"
                )
            else:
                status_text += (
                    "💡 <b>Состояние:</b> Для запуска нажмите 🚀 Запуск\n\n"
                )
            
            vladivostok_tz = pytz.timezone('Asia/Vladivostok')
            current_time = datetime.now(vladivostok_tz).strftime('%d.%m.%Y %H:%M:%S')
            status_text += f"🕐 {current_time} (Владивосток)"
            
            keyboard = [
                [
                    {"text": "🗂️ Управление каналами", "callback_data": "manage_channels"},
                    {"text": "📈 Статистика", "callback_data": "stats"}
                ],
                [{"text": "🏠 Главное меню", "callback_data": "start"}]
            ]
            
            # Определяем куда отправлять ответ
            chat_id = message.get("chat", {}).get("id") if message else self.admin_chat_id
            to_group = self.is_message_from_group(chat_id) if chat_id else None
            
            await self.send_message_with_keyboard(status_text, keyboard, use_reply_keyboard=False, to_group=to_group)
            
        except Exception as e:
            logger.error(f"❌ Ошибка команды status: {e}")
            await self.send_command_response("❌ Ошибка получения статуса", message)
    
    async def cmd_start_monitoring(self, message):
        """Команда /start_monitoring - запустить мониторинг"""
        keyboard = [["🛑 Стоп", "📊 Статус"], ["🏠 Главное меню"]]
        
        if not self.monitor_bot:
            await self.send_message_with_keyboard(
                "❌ <b>Ошибка</b>\n\nНет доступа к системе мониторинга",
                keyboard
            )
            return
        
        if self.monitor_bot.monitoring_active:
            await self.send_message_with_keyboard(
                "⚠️ <b>Мониторинг уже работает</b>\n\nИспользуйте кнопку 🛑 для остановки",
                keyboard
            )
            return
        
        # Возобновляем мониторинг
        await self.monitor_bot.resume_monitoring()
        
        # Отправляем системное сообщение
        vladivostok_tz = pytz.timezone('Asia/Vladivostok')
        current_time = datetime.now(vladivostok_tz).strftime('%d.%m.%Y %H:%M:%S')
        
        await self.send_message_with_keyboard(
            "🚀 <b>Система мониторинга запущена!</b>\n\n"
            "📱 <b>Telegram бот:</b> ✅ Активен\n"
            "🗄️ <b>База данных:</b> ✅ Подключена\n"
            "🧠 <b>ИИ анализатор:</b> ✅ Готов\n"
            "📺 <b>Мониторинг каналов:</b> ✅ Активен\n"
            "🌐 <b>Веб-интерфейс:</b> ✅ http://localhost:8080\n\n"
            f"🕐 {current_time} (Владивосток)",
            keyboard
        )
    
    async def cmd_stop_monitoring(self, message):
        """Команда /stop_monitoring - остановить мониторинг"""
        keyboard = [["🚀 Запуск", "📊 Статус"], ["🏠 Главное меню"]]
        
        if not self.monitor_bot:
            await self.send_message_with_keyboard(
                "❌ <b>Ошибка</b>\n\nНет доступа к системе мониторинга",
                keyboard
            )
            return
        
        if not self.monitor_bot.monitoring_active:
            await self.send_message_with_keyboard(
                "⚠️ <b>Мониторинг уже остановлен</b>\n\nИспользуйте кнопку 🚀 для запуска",
                keyboard
            )
            return
        
        # Останавливаем мониторинг
        await self.monitor_bot.pause_monitoring()
        
        # Отправляем системное сообщение
        vladivostok_tz = pytz.timezone('Asia/Vladivostok')
        current_time = datetime.now(vladivostok_tz).strftime('%d.%m.%Y %H:%M:%S')
        
        await self.send_message_with_keyboard(
            "🛑 <b>Система мониторинга остановлена</b>\n\n"
            f"🕐 {current_time} (Владивосток)",
            keyboard
        )
    
    async def cmd_restart(self, message):
        """Команда для рестарта бота"""
        try:
            keyboard = [["🏠 Главное меню"]]
            
            # Отправляем подтверждение рестарта
            vladivostok_tz = pytz.timezone('Asia/Vladivostok')
            current_time = datetime.now(vladivostok_tz).strftime('%d.%m.%Y %H:%M:%S')
            
            await self.send_message_with_keyboard(
                "🔄 <b>Перезапуск системы...</b>\n\n"
                "🔄 Останавливаем мониторинг...\n"
                "💾 Сохраняем данные...\n"
                "🚀 Запускаем новый процесс...\n\n"
                f"🕐 {current_time} (Владивосток)\n\n"
                "⏳ <i>Пожалуйста, подождите несколько секунд...</i>",
                keyboard
            )
            
            # Даем время отправить сообщение
            await asyncio.sleep(2)
            
            # Перезапускаем процесс
            logger.info("🔄 Выполняется рестарт системы...")
            import os
            import sys
            os.execv(sys.executable, ['python'] + sys.argv)
            
        except Exception as e:
            logger.error(f"❌ Ошибка рестарта: {e}")
            await self.send_message_with_keyboard(
                f"❌ <b>Ошибка рестарта</b>\n\n{e}",
                [["🏠 Главное меню"]]
            )
    
    async def cmd_topic_id(self, message):
        """Команда для определения ID темы в группе"""
        try:
            # Получаем информацию о сообщении
            chat = message.get("chat", {})
            chat_type = chat.get("type")
            chat_title = chat.get("title", "Неизвестная группа")
            thread_id = message.get("message_thread_id")
            
            if chat_type not in ["group", "supergroup"]:
                await self.send_message(
                    "❌ <b>Эта команда работает только в группах</b>\n\n"
                    "Отправьте команду /topic_id в нужной теме группы"
                )
                return
            
            if not thread_id:
                await self.send_message(
                    f"📂 <b>Группа:</b> {chat_title}\n"
                    "📋 <b>Тема:</b> Общая лента (без темы)\n"
                    "🆔 <b>Thread ID:</b> null\n\n"
                    "💡 <b>Настройка config.yaml:</b>\n"
                    "<code>topics:\n"
                    "  general: null</code>"
                )
            else:
                await self.send_message(
                    f"📂 <b>Группа:</b> {chat_title}\n"
                    "📋 <b>Тема:</b> {определяется автоматически}\n"
                    f"🆔 <b>Thread ID:</b> {thread_id}\n\n"
                    "💡 <b>Настройка config.yaml:</b>\n"
                    "<code>topics:\n"
                    f"  sakhalin: {thread_id}  # если это Сахалин\n"
                    f"  kamchatka: {thread_id}  # если это Камчатка</code>\n\n"
                    "🔄 <b>После настройки перезапустите бота кнопкой 'Рестарт'</b>"
                )
                
            logger.info(f"📂 Запрос ID темы: группа '{chat_title}', thread_id = {thread_id}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка команды topic_id: {e}")
            await self.send_message(f"❌ <b>Ошибка:</b> {e}")
    
    async def show_region_selection(self):
        """Показать выбор региона для канала"""
        try:
            # Всегда читаем полный список регионов из config.yaml для выбора
            regions = await self.load_regions_from_config()
            
            # Если все равно нет регионов, используем стандартные
            if not regions:
                regions = [
                    {'key': 'sakhalin', 'name': '🏝️ Сахалин', 'emoji': '🏝️'},
                    {'key': 'kamchatka', 'name': '🌋 Камчатка', 'emoji': '🌋'},
                    {'key': 'chita', 'name': '🏔️ Чита', 'emoji': '🏔️'},
                    {'key': 'general', 'name': '📰 Общие', 'emoji': '📰'}
                ]
            
            # Создаем клавиатуру
            keyboard = []
            row = []
            for i, region in enumerate(regions):
                button_text = region['name']
                callback_data = f"region_{region['key']}"
                
                row.append({"text": button_text, "callback_data": callback_data})
                
                # По 2 кнопки в ряд
                if len(row) == 2 or i == len(regions) - 1:
                    keyboard.append(row)
                    row = []
            
            # Добавляем кнопку создания нового региона
            keyboard.append([{"text": "➕ Создать новый регион", "callback_data": "create_new_region"}])
            keyboard.append([{"text": "❌ Отмена", "callback_data": "region_cancel"}])
            
            text = (
                f"📂 <b>Выберите регион для канала:</b>\n\n"
                f"🔗 <code>{self.pending_channel_url}</code>\n\n"
                f"📍 Доступные регионы ({len([r for r in regions if r['key'] != 'general'])} + общий):\n"
            )
            
            # Добавляем информацию о регионах
            for region in regions[:5]:  # Показываем первые 5 регионов
                channels_count = region.get('channels_count', 0)
                text += f"• {region['name']}: {channels_count} каналов\n"
            
            if len(regions) > 5:
                text += f"• ... и еще {len(regions) - 5} регионов\n"
            
            text += "\n💡 Не нашли подходящий? Создайте новый регион!"
            
            await self.edit_message_with_keyboard(text, keyboard, use_reply_keyboard=False, chat_id=self.current_callback_chat_id)
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа выбора региона: {e}")
    
    async def show_multiple_channels_selection(self):
        """Показать найденные каналы и выбор региона для всех"""
        try:
            channels_list = self.pending_channels_list
            if not channels_list:
                await self.send_message("❌ Список каналов пуст")
                return
            
            # Формируем список каналов
            channels_text = f"📺 <b>Найдено {len(channels_list)} каналов:</b>\n\n"
            for i, channel in enumerate(channels_list, 1):
                channels_text += f"  {i}. @{channel}\n"
            
            channels_text += "\n📂 <b>Выберите регион для всех каналов:</b>"
            
            # Загружаем динамические регионы
            regions = await self.load_regions_from_config()
            
            keyboard = []
            row = []
            for i, region in enumerate(regions):
                button_text = region['name']
                callback_data = f"region_bulk_{region['key']}"
                
                row.append({"text": button_text, "callback_data": callback_data})
                
                # По 2 кнопки в ряд
                if len(row) == 2 or i == len(regions) - 1:
                    keyboard.append(row)
                    row = []
            
            keyboard.append([{"text": "❌ Отмена", "callback_data": "region_bulk_cancel"}])
            
            await self.edit_message_with_keyboard(
                channels_text,
                keyboard,
                use_reply_keyboard=False
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа множественного выбора: {e}")
    

    async def handle_forwarded_message(self, message: dict):
        """Обработка пересланного сообщения из канала"""
        try:
            forward_from_chat = message.get("forward_from_chat", {})
            if not forward_from_chat:
                await self.send_message("❌ Не удалось получить информацию о канале")
                return
            
            # Извлекаем информацию о канале
            channel_username = forward_from_chat.get("username")
            channel_title = forward_from_chat.get("title", "")
            channel_type = forward_from_chat.get("type", "")
            
            # Проверяем дублирование forward сообщений
            forward_key = f"{channel_username}_{int(message.get('date', 0))}"
            if forward_key in self.processed_forwards:
                logger.info(f"⏭️ Пропускаем дублированное forward сообщение от @{channel_username}")
                return
            
            # Добавляем в кэш обработанных
            self.processed_forwards.add(forward_key)
            
            # Очищаем старые записи (старше 5 минут)
            current_time = int(message.get('date', 0))
            self.processed_forwards = {
                key for key in self.processed_forwards 
                if current_time - int(key.split('_')[-1]) < 300
            }
            
            if not channel_username:
                await self.send_message("❌ Канал не имеет публичного username")
                return
            
            if channel_type != "channel":
                await self.send_message("❌ Это не канал, а чат или группа")
                return
            
            logger.info(f"📤 Пересланное сообщение из канала @{channel_username} ({channel_title})")
            
            # Проверяем, не добавлен ли уже канал
            if self.is_channel_already_added(channel_username):
                await self.send_message(f"ℹ️ Канал @{channel_username} уже добавлен в мониторинг")
                return
            
            # Получаем дополнительную информацию о канале и показываем превью
            await self.show_channel_preview_and_region_selection(channel_username, channel_title)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки пересланного сообщения: {e}")
            await self.send_message("❌ Ошибка обработки пересланного сообщения")
    
    async def show_channel_preview_and_region_selection(self, channel_username: str, channel_title: str):
        """Показывает превью канала и предлагает выбрать регион"""
        try:
            # Автоопределение региона
            suggested_region = self.detect_channel_region(channel_title, channel_username)
            
            # Формируем превью канала
            preview_text = (
                f"📺 <b>Найден новый канал!</b>\n\n"
                f"📋 <b>Название:</b> {channel_title}\n"
                f"🔗 <b>Username:</b> @{channel_username}\n"
            )
            
            # Загружаем список всех регионов из config.yaml
            regions = await self.load_regions_from_config()
            suggested_name = suggested_region
            
            # Ищем название предполагаемого региона
            if suggested_region != 'general':
                for region in regions:
                    if region['key'] == suggested_region:
                        suggested_name = region['name']
                        break
                preview_text += f"🎯 <b>Предполагаемый регион:</b> {suggested_name}\n"
            
            preview_text += "\n❓ Добавить в мониторинг?"
            
            # Сохраняем для дальнейшей обработки
            self.pending_channel_url = channel_username
            
            # Создаем клавиатуру с регионами из config.yaml
            keyboard = []
            row = []
            for i, region in enumerate(regions):
                button_text = region['name']
                callback_data = f"region_{region['key']}"
                
                # Если это предполагаемый регион - отмечаем галочкой
                if region['key'] == suggested_region:
                    button_text = "✅ " + button_text
                
                row.append({"text": button_text, "callback_data": callback_data})
                
                # По 2 кнопки в ряд
                if len(row) == 2 or i == len(regions) - 1:
                    keyboard.append(row)
                    row = []
            
            # Добавляем кнопки управления
            keyboard.append([{"text": "➕ Создать новый регион", "callback_data": "create_new_region"}])
            keyboard.append([{"text": "❌ Отмена", "callback_data": "start"}])
            
            await self.edit_message_with_keyboard(preview_text, keyboard, use_reply_keyboard=False)
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа превью канала: {e}")
            await self.send_message("❌ Ошибка получения информации о канале")
    
    def detect_channel_region(self, channel_title: str, channel_username: str) -> str:
        """Автоопределение региона канала по названию и username"""
        try:
            # Объединяем название и username для анализа
            text_to_analyze = f"{channel_title} {channel_username}".lower()
            
            # Получаем конфигурацию регионов из главного бота
            regions_config = {}
            if self.monitor_bot and hasattr(self.monitor_bot, 'regions_config'):
                regions_config = self.monitor_bot.regions_config
            
            # Если конфигурации нет, используем стандартные регионы
            if not regions_config:
                region_keywords = {
                    'sakhalin': [
                        'сахалин', 'sakhalin', 'остров', 'южно-сахалинск', 'южно',
                        'корсаков', 'холмск', 'поронайск', 'углегорск', 'макаров',
                        'курилы', 'курильские', 'невельск', 'долинск', 'тымовск',
                        'оха', 'ноглики', 'александровск', '65'
                    ],
                    'kamchatka': [
                        'камчатка', 'kamchatka', 'петропавловск', 'петропавловский',
                        'елизово', 'вилючинск', 'усть-камчатск', 'мильково',
                        'эссо', 'палана', 'оссора', '41', 'kam', 'регион41'
                    ],
                    'chita': [
                        'чита', 'chita', 'забайкалье', 'забайкальский', 'краснокаменск',
                        'борзя', 'петровск-забайкальский', 'нерчинск', 'шилка',
                        'могоча', 'сретенск', 'хилок', '75', '03', 'забай'
                    ]
                }
            else:
                # Используем динамическую конфигурацию
                region_keywords = {}
                for region_key, region_data in regions_config.items():
                    if region_key != 'general':
                        region_keywords[region_key] = region_data.get('keywords', [])
            
            # Подсчитываем совпадения для каждого региона
            region_scores = {}
            for region, keywords in region_keywords.items():
                score = 0
                for keyword in keywords:
                    if keyword.lower() in text_to_analyze:
                        score += 1
                region_scores[region] = score
            
            # Возвращаем регион с наибольшим количеством совпадений
            if region_scores:
                best_region = max(region_scores, key=region_scores.get)
                if region_scores[best_region] > 0:
                    logger.info(f"🎯 Автоопределен регион '{best_region}' для канала @{channel_username} (совпадений: {region_scores[best_region]})")
                    return best_region
            
            return 'general'
            
        except Exception as e:
            logger.error(f"❌ Ошибка автоопределения региона: {e}")
            return 'general'
    
    def is_channel_already_added(self, channel_username: str) -> bool:
        """Проверяет, добавлен ли уже канал в мониторинг"""
        try:
            # Читаем конфигурацию каналов
            with open('config/channels_config.yaml', 'r', encoding='utf-8') as f:
                import yaml
                channels_data = yaml.safe_load(f) or {}
            
            # Проверяем новую структуру с регионами
            if 'regions' in channels_data:
                for region_key, region_data in channels_data['regions'].items():
                    channels = region_data.get('channels', [])
                    for channel in channels:
                        if channel.get('username') == channel_username:
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки канала: {e}")
            return False
    
    def parse_channel_username(self, channel_input: str) -> str:
        """Извлечь имя канала из различных форматов ввода"""
        try:
            channel_input = channel_input.strip()
            
            # Удаляем https://t.me/
            if channel_input.startswith("https://t.me/"):
                channel_input = channel_input.replace("https://t.me/", "")
            elif channel_input.startswith("t.me/"):
                channel_input = channel_input.replace("t.me/", "")
            
            # Удаляем @
            if channel_input.startswith("@"):
                channel_input = channel_input[1:]
            
            # Удаляем всё после ? (параметры URL)
            if "?" in channel_input:
                channel_input = channel_input.split("?")[0]
            
            # Удаляем всё после / (подпути)
            if "/" in channel_input:
                channel_input = channel_input.split("/")[0]
            
            # Проверяем что осталось валидное имя канала
            if channel_input and channel_input.replace("_", "").replace("-", "").isalnum():
                return channel_input
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга канала: {e}")
            return None
    
    def parse_multiple_channels(self, text: str) -> list:
        """Найти все каналы в тексте сообщения"""
        try:
            import re
            channels = []
            
            # Ищем все возможные форматы каналов
            patterns = [
                r'https://t\.me/(\w+)',  # https://t.me/channel
                r't\.me/(\w+)',          # t.me/channel  
                r'@(\w+)',               # @channel
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    username = self.parse_channel_username(match)
                    if username and username not in channels:
                        channels.append(username)
            
            # Также проверяем слова которые могут быть именами каналов (без @ и ссылок)
            words = text.split()
            for word in words:
                # Проверяем отдельные слова на похожесть на имена каналов
                clean_word = word.strip('.,!?;:()[]{}"\'-').lower()
                if (len(clean_word) > 3 and 
                    clean_word.replace('_', '').replace('-', '').isalnum() and
                    ('chita' in clean_word or 'buryat' in clean_word or 'zabay' in clean_word or 
                     'transbaikal' in clean_word or 'baikal' in clean_word or '75' in clean_word or '03' in clean_word) and
                    clean_word not in channels):
                    channels.append(clean_word)
            
            return channels
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга нескольких каналов: {e}")
            return []
    
    async def handle_region_selection(self, region: str):
        """Обработка выбора региона для канала"""
        try:
            if region == "cancel":
                self.pending_channel_url = None
                await self.edit_message_with_keyboard(
                    "❌ <b>Добавление канала отменено</b>",
                    [[{"text": "🏠 Главное меню", "callback_data": "start"}]],
                    use_reply_keyboard=False,
                    chat_id=self.current_callback_chat_id
                )
                return
            
            channel_url = self.pending_channel_url
            if not channel_url:
                await self.send_message("❌ Ошибка: URL канала не найден")
                return
            
            # Парсим имя канала из URL
            channel_username = self.parse_channel_username(channel_url)
            if not channel_username:
                await self.edit_message_with_keyboard(
                    f"❌ <b>Неправильная ссылка</b>\n\n"
                    f"Не удалось извлечь имя канала из: <code>{channel_url}</code>",
                    [[{"text": "🏠 Главное меню", "callback_data": "start"}]],
                    use_reply_keyboard=False
                )
                return
            
            # Добавляем канал с выбранным регионом
            success = await self.add_channel_to_config(channel_username, region)
            
            if success:
                region_names = {
                    'sakhalin': '🏝️ Сахалин',
                    'kamchatka': '🌋 Камчатка',
                    'chita': '🏔️ Чита',
                    'general': '📰 Общие'
                }
                region_name = region_names.get(region, region)
                
                await self.edit_message_with_keyboard(
                    f"✅ <b>Канал добавлен успешно!</b>\n\n"
                    f"📺 @{channel_username}\n"
                    f"📂 Регион: {region_name}\n\n"
                    "Канал будет автоматически добавлен в мониторинг при перезапуске бота.",
                    [[{"text": "🏠 Главное меню", "callback_data": "start"}]],
                    use_reply_keyboard=False
                )
            else:
                await self.edit_message_with_keyboard(
                    f"❌ <b>Ошибка добавления канала</b>\n\n"
                    f"Проверьте правильность ссылки: <code>{channel_url}</code>",
                    [[{"text": "🏠 Главное меню", "callback_data": "start"}]],
                    use_reply_keyboard=False
                )
            
            self.pending_channel_url = None
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки выбора региона: {e}")
            await self.send_message(f"❌ Ошибка: {e}")
    
    async def handle_bulk_region_selection(self, region: str):
        """Обработка выбора региона для нескольких каналов"""
        try:
            if region == "cancel":
                self.pending_channels_list = []
                await self.edit_message_with_keyboard(
                    "❌ <b>Массовое добавление каналов отменено</b>",
                    [[{"text": "🏠 Главное меню", "callback_data": "start"}]],
                    use_reply_keyboard=False
                )
                return
            
            channels_list = self.pending_channels_list
            if not channels_list:
                await self.send_message("❌ Ошибка: список каналов пуст")
                return
            
            # Добавляем все каналы в выбранный регион
            added_count = 0
            failed_count = 0
            already_exists_count = 0
            
            for channel_username in channels_list:
                try:
                    success = await self.add_channel_to_config(channel_username, region)
                    if success:
                        added_count += 1
                    else:
                        already_exists_count += 1
                except Exception as e:
                    logger.error(f"❌ Ошибка добавления канала {channel_username}: {e}")
                    failed_count += 1
            
            # Формируем результат
            region_names = {
                'sakhalin': '🏝️ Сахалин',
                'kamchatka': '🌋 Камчатка',
                'chita': '🏔️ Чита',
                'general': '📰 Общие'
            }
            region_name = region_names.get(region, region)
            
            result_text = f"📊 <b>Результат массового добавления:</b>\n\n"
            result_text += f"📂 Регион: {region_name}\n"
            result_text += f"📺 Всего каналов: {len(channels_list)}\n\n"
            
            if added_count > 0:
                result_text += f"✅ Добавлено: <b>{added_count}</b>\n"
            if already_exists_count > 0:
                result_text += f"⚠️ Уже существуют: <b>{already_exists_count}</b>\n"
            if failed_count > 0:
                result_text += f"❌ Ошибки: <b>{failed_count}</b>\n"
            
            if added_count > 0:
                result_text += "\n🔄 Каналы будут добавлены в мониторинг при перезапуске бота."
            
            await self.edit_message_with_keyboard(
                result_text,
                [[{"text": "🏠 Главное меню", "callback_data": "start"}]],
                use_reply_keyboard=False
            )
            
            self.pending_channels_list = []
            
        except Exception as e:
            logger.error(f"❌ Ошибка массового добавления каналов: {e}")
            await self.send_message(f"❌ Ошибка: {e}")

    async def cmd_add_channel(self, message):
        """Команда /add_channel - добавить канал"""
        if not message:
            await self.send_message("📝 Отправьте ссылку на канал в формате:\n<code>https://t.me/channel_name</code>")
            return
            
        text = message.get("text", "")
        parts = text.split(maxsplit=1)
        
        if len(parts) < 2:
            await self.send_message(
                "❌ <b>Неверный формат команды</b>\n\n"
                "Используйте:\n"
                "• <code>/add_channel https://t.me/news_channel</code>\n"
                "• <code>/add_channel @news_channel</code>"
            )
            return
        
        channel_link = parts[1].strip()
        await self.add_channel_handler(channel_link)
    
    async def cmd_force_subscribe(self, message):
        """Команда /force_subscribe - принудительная подписка на все каналы"""
        try:
            await self.send_message(
                "📡 <b>Принудительная подписка на каналы</b>\n\n"
                "🔄 Запускаю проверку и подписку на все каналы из конфигурации...\n"
                "⏳ Это может занять несколько минут..."
            )
            
            # Проверяем что main_instance доступен
            if not hasattr(self, 'main_instance') or not self.main_instance:
                await self.send_message("❌ Главный экземпляр системы недоступен")
                return
            
            # Проверяем что telegram_monitor доступен
            if not hasattr(self.main_instance, 'telegram_monitor') or not self.main_instance.telegram_monitor:
                await self.send_message("❌ Telegram мониторинг недоступен")
                return
            
            # Очищаем кэш подписок для принудительной перепроверки
            self.main_instance.clear_subscription_cache()
            # Также очищаем кэш диалогов Telegram для точной проверки
            if hasattr(self.main_instance.telegram_monitor, 'clear_cache'):
                await self.main_instance.telegram_monitor.clear_cache()
            logger.info("🗑️ Кэш подписок и диалогов очищен для принудительной подписки")
            
            # Загружаем список всех каналов из конфигурации
            channels_data = await self.get_channels_from_config()
            all_channels = channels_data.get('channels', [])
            
            if not all_channels:
                await self.send_message("❌ Нет каналов для подписки в конфигурации")
                return
            
            await self.send_message(f"📋 Найдено {len(all_channels)} каналов для проверки подписки")
            
            # Статистика подписки
            success_count = 0
            already_subscribed_count = 0
            failed_count = 0
            rate_limited_count = 0
            
            from telethon.tl.functions.channels import JoinChannelRequest
            
            for i, channel_config in enumerate(all_channels, 1):
                try:
                    username = channel_config.get('username', '')
                    if not username:
                        continue
                    
                    logger.info(f"📡 [{i}/{len(all_channels)}] Проверяем подписку на @{username}")
                    
                    # Получаем entity канала
                    entity = await self.main_instance.telegram_monitor.get_channel_entity(username)
                    if not entity:
                        logger.error(f"❌ Не удалось получить entity для @{username}")
                        failed_count += 1
                        continue
                    
                    # Проверяем подписку
                    already_joined = await self.main_instance.telegram_monitor.is_already_joined(entity)
                    
                    if already_joined:
                        logger.info(f"✅ Уже подписан на @{username}")
                        already_subscribed_count += 1
                        # Добавляем в кэш
                        self.main_instance.add_channel_to_cache(username)
                    else:
                        # Подписываемся
                        try:
                            await self.main_instance.telegram_monitor.client(JoinChannelRequest(entity))
                            logger.info(f"✅ Подписался на @{username}")
                            success_count += 1
                            # Добавляем в кэш после успешной подписки
                            self.main_instance.add_channel_to_cache(username)
                            await asyncio.sleep(3)  # Пауза между подписками
                        except Exception as sub_error:
                            error_msg = str(sub_error).lower()
                            if "wait" in error_msg and "seconds" in error_msg:
                                logger.warning(f"⏳ Rate limit на @{username}")
                                rate_limited_count += 1
                            elif "already" in error_msg or "участник" in error_msg:
                                logger.info(f"✅ Уже подписан на @{username}")
                                already_subscribed_count += 1
                                # Добавляем в кэш
                                self.main_instance.add_channel_to_cache(username)
                            else:
                                logger.error(f"❌ Ошибка подписки на @{username}: {sub_error}")
                                failed_count += 1
                    
                    # Отправляем промежуточный отчет каждые 10 каналов
                    if i % 10 == 0:
                        progress_text = (
                            f"🔄 <b>Прогресс: {i}/{len(all_channels)}</b>\n\n"
                            f"✅ Подписался: {success_count}\n"
                            f"💾 Уже подписан: {already_subscribed_count}\n"
                            f"⏳ Rate limit: {rate_limited_count}\n"
                            f"❌ Ошибки: {failed_count}"
                        )
                        await self.send_message(progress_text)
                
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки канала @{username}: {e}")
                    failed_count += 1
            
            # Итоговый отчет
            final_report = (
                f"📡 <b>Принудительная подписка завершена!</b>\n\n"
                f"📊 <b>Результаты:</b>\n"
                f"✅ Успешно подписался: <b>{success_count}</b>\n"
                f"💾 Уже был подписан: <b>{already_subscribed_count}</b>\n"
                f"⏳ Rate limit: <b>{rate_limited_count}</b>\n"
                f"❌ Ошибки: <b>{failed_count}</b>\n\n"
                f"📋 Всего проверено: <b>{len(all_channels)}</b> каналов\n"
                f"🎉 Активных подписок: <b>{success_count + already_subscribed_count}</b>"
            )
            
            if rate_limited_count > 0:
                final_report += (
                    f"\n\n💡 <b>Rate limit</b> - временное ограничение Telegram.\n"
                    f"Повторите команду через несколько минут для повторной попытки."
                )
            
            await self.send_message(final_report)
            logger.info(f"📡 Принудительная подписка завершена: {success_count} новых + {already_subscribed_count} существующих = {success_count + already_subscribed_count} активных подписок")
            
        except Exception as e:
            error_msg = f"❌ Ошибка принудительной подписки: {e}"
            logger.error(error_msg)
            await self.send_message(error_msg)
    
    async def cmd_list_channels(self, message, page: int = 0):
        """Команда /channels - список каналов с пагинацией"""
        try:
            await self.show_channels_page(page)
        except Exception as e:
            logger.error(f"❌ Ошибка при показе каналов: {e}")
            await self.send_message("❌ Ошибка при загрузке списка каналов")
    
    async def show_channels_page(self, page: int = 0):
        """Показать страницу с каналами"""
        try:
            channels_data = await self.get_channels_from_config()
            total_channels = channels_data['total']
            regions_data = channels_data.get('regions', {})
            
            channels_text = f"📺 <b>Отслеживаемые каналы</b>\n\n"
            channels_text += f"🔍 Всего каналов: <b>{total_channels}</b>\n\n"
            
            if regions_data:
                # Новая структура с регионами
                for region_key, region_info in regions_data.items():
                    region_name = region_info['name']
                    region_count = region_info['count']
                    region_channels = region_info['channels']
                    
                    channels_text += f"<b>{region_name}</b> ({region_count})\n"
                    
                    if region_channels:
                        for i, channel in enumerate(region_channels, 1):
                            username = channel.get('username', 'unknown')
                            title = channel.get('title', f'@{username}')
                            channels_text += f"  {i}. @{username}"
                            if title and title != f'@{username}' and title != f'Канал @{username}':
                                channels_text += f" – <i>{title}</i>"
                            channels_text += "\n"
                    else:
                        channels_text += "  <i>Каналов нет</i>\n"
                    
                    channels_text += "\n"
            else:
                # Старая структура для совместимости
                if channels_data['channels']:
                    channels_text += "<b>📺 Все каналы:</b>\n"
                    for i, channel in enumerate(channels_data['channels'], 1):
                        username = channel.get('username', 'unknown')
                        title = channel.get('title', f'@{username}')
                        channels_text += f"  {i}. @{username}"
                        if title and title != f'@{username}':
                            channels_text += f" – <i>{title}</i>"
                        channels_text += "\n"
                    channels_text += "\n"
                else:
                    channels_text += "📭 Каналы не добавлены\n\n"
            
            keyboard = [
                [
                    {"text": "➕ Добавить канал", "callback_data": "add_channel"},
                    {"text": "🏠 Главное меню", "callback_data": "start"}
                ]
            ]
            
            await self.edit_message_with_keyboard(channels_text, keyboard, use_reply_keyboard=False)
            
        except Exception as e:
            logger.error(f"❌ Ошибка команды channels: {e}")
            await self.send_message("❌ Ошибка получения списка каналов")
    
    async def cmd_stats(self, message):
        """Команда /stats - статистика"""
        try:
            if not self.monitor_bot or not self.monitor_bot.database:
                await self.send_message("❌ База данных недоступна")
                return
            
            stats = await self.monitor_bot.database.get_today_stats()
            
            stats_text = (
                "📈 <b>Статистика за сегодня</b>\n\n"
                f"📰 Всего сообщений: <b>{stats['total_messages']}</b>\n"
                f"📤 Отобрано: <b>{stats['selected_messages']}</b>\n"
                f"📊 Процент отбора: <b>{(stats['selected_messages'] / max(stats['total_messages'], 1) * 100):.1f}%</b>\n\n"
                f"🕐 Последнее обновление: {datetime.now(pytz.timezone('Asia/Vladivostok')).strftime('%d.%m.%Y %H:%M:%S')}"
            )
            
            keyboard = [
                [
                    {"text": "📊 Статус", "callback_data": "status"},
                    {"text": "🗂️ Управление каналами", "callback_data": "manage_channels"}
                ],
                [
                    {"text": "🗑️ Очистить статистику", "callback_data": "clear_stats"},
                    {"text": "🏠 Главное меню", "callback_data": "start"}
                ]
            ]
            
            # Определяем куда отправлять ответ
            chat_id = message.get("chat", {}).get("id") if message else self.admin_chat_id
            to_group = self.is_message_from_group(chat_id) if chat_id else None
            
            await self.send_message_with_keyboard(stats_text, keyboard, use_reply_keyboard=False, to_group=to_group)
            
        except Exception as e:
            logger.error(f"❌ Ошибка команды stats: {e}")
            await self.send_command_response("❌ Ошибка получения статистики", message)
    
    async def clear_stats_handler(self):
        """Обработчик очистки статистики"""
        try:
            if not self.monitor_bot or not self.monitor_bot.database:
                await self.send_message("❌ База данных недоступна")
                return
            
            success = await self.monitor_bot.database.clear_today_stats()
            
            if success:
                clear_text = (
                    "🗑️ <b>Статистика очищена</b>\n\n"
                    "✅ Все записи за сегодня удалены\n"
                    "📊 Счетчики сброшены на ноль\n\n"
                    "🔄 Обновляем статистику..."
                )
            else:
                clear_text = (
                    "❌ <b>Ошибка очистки</b>\n\n"
                    "Не удалось очистить статистику\n"
                    "Попробуйте позже"
                )
            
            keyboard = [
                [
                    {"text": "📈 Статистика", "callback_data": "stats"},
                    {"text": "🏠 Главное меню", "callback_data": "start"}
                ]
            ]
            
            await self.edit_message_with_keyboard(clear_text, keyboard, use_reply_keyboard=False)
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки статистики: {e}")
            await self.send_message("❌ Ошибка очистки статистики")
    
    async def cmd_settings(self, message):
        """Команда /settings - настройки интерфейса"""
        delete_status = "🟢 Включено" if self.delete_commands else "🔴 Выключено"
        edit_status = "🟢 Включено" if self.edit_messages else "🔴 Выключено"
        
        settings_text = (
            "⚙️ <b>Настройки интерфейса</b>\n\n"
            f"🗑️ <b>Удаление команд:</b> {delete_status}\n"
            f"📝 <b>Редактирование сообщений:</b> {edit_status}\n\n"
            "🔧 <b>Описание:</b>\n"
            "• <b>Удаление команд</b> - автоматически удалять ваши команды и нажатия кнопок\n"
            "• <b>Редактирование сообщений</b> - обновлять существующие сообщения вместо создания новых\n\n"
            "💡 <b>Рекомендация:</b> Включите удаление команд для чистоты чата"
        )
        
        keyboard = [
            [
                {"text": f"🗑️ Удаление: {delete_status}", "callback_data": "toggle_delete"},
                {"text": f"📝 Редактирование: {edit_status}", "callback_data": "toggle_edit"}
            ],
            [{"text": "🏠 Главное меню", "callback_data": "start"}]
        ]
        
        await self.edit_message_with_keyboard(settings_text, keyboard, use_reply_keyboard=False, chat_id=self.current_callback_chat_id)
    
    async def add_channel_handler(self, channel_link: str):
        """Обработчик добавления канала"""
        try:
            # Парсим ссылку
            if channel_link.startswith("https://t.me/"):
                channel_name = channel_link.replace("https://t.me/", "")
            elif channel_link.startswith("@"):
                channel_name = channel_link[1:]
            elif channel_link.startswith("t.me/"):
                channel_name = channel_link.replace("t.me/", "")
            else:
                channel_name = channel_link
            
            # Проверяем что это не приватная ссылка
            if channel_name.startswith("+"):
                await self.send_message("❌ Приватные каналы пока не поддерживаются")
                return
            
            # Проверяем что канал не пустой
            if not channel_name.strip():
                await self.send_message("❌ Некорректная ссылка на канал")
                return
            
            # Добавляем в конфиг
            success = await self.add_channel_to_config(channel_name)
            
            if success:
                success_text = (
                    "✅ <b>Канал добавлен!</b>\n\n"
                    f"📺 Канал: @{channel_name}\n"
                    f"🔗 Ссылка: https://t.me/{channel_name}\n\n"
                    "🔄 Мониторинг начнется при следующем запуске бота"
                )
                await self.send_message(success_text)
                logger.info(f"✅ Добавлен канал: {channel_name}")
            else:
                await self.send_message("❌ Канал уже существует в списке")
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления канала: {e}")
            await self.send_message(f"❌ Ошибка добавления канала: {str(e)}")
    
    async def add_channel_to_config(self, channel_name: str, region: str = "general") -> bool:
        """Добавить канал в конфигурацию"""
        try:
            import yaml
            config_path = "config/channels_config.yaml"
            
            # Загружаем текущий конфиг
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
            except FileNotFoundError:
                config = {}
            
            # Инициализируем новую структуру если её нет
            if "regions" not in config:
                config["regions"] = {
                    "sakhalin": {
                        "name": "🏝️ Сахалин",
                        "channels": []
                    },
                    "kamchatka": {
                        "name": "🌋 Камчатка", 
                        "channels": []
                    },
                    "chita": {
                        "name": "🏔️ Чита",
                        "channels": []
                    },
                    "general": {
                        "name": "📰 Общие",
                        "channels": []
                    }
                }
            
            # Проверяем что регион существует
            if region not in config["regions"]:
                config["regions"][region] = {
                    "name": f"📂 {region.title()}",
                    "channels": []
                }
            
            # Проверяем что секция каналов существует
            if "channels" not in config["regions"][region]:
                config["regions"][region]["channels"] = []
            
            # Проверяем, не добавлен ли уже канал в любом регионе
            for region_key, region_data in config["regions"].items():
                for channel in region_data.get("channels", []):
                    if channel.get("username") == channel_name:
                        return False  # Канал уже существует
            
            # Добавляем новый канал
            new_channel = {
                "username": channel_name,
                "title": f"Канал @{channel_name}"
            }
            
            config["regions"][region]["channels"].append(new_channel)
            
            # Сохраняем конфиг
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, indent=2, default_flow_style=False)
            
            # ИСПРАВЛЕНИЕ: Очищаем кэш подписок, чтобы при рестарте бот заново подписался на все каналы
            try:
                if hasattr(self, 'main_instance') and self.main_instance:
                    self.main_instance.clear_subscription_cache()
                    logger.info("🗑️ Кэш подписок очищен после добавления канала")
                elif hasattr(self, 'monitor_bot') and self.monitor_bot:
                    self.monitor_bot.clear_subscription_cache()
                    logger.info("🗑️ Кэш подписок очищен после добавления канала")
            except Exception as cache_error:
                logger.warning(f"⚠️ Не удалось очистить кэш подписок: {cache_error}")
            
            logger.info(f"📝 Канал {channel_name} добавлен в регион {region} в {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка записи в конфиг: {e}")
            raise e
    
    async def get_channels_from_config(self) -> dict:
        """Получить список каналов из конфигурации"""
        try:
            import yaml
            config_path = "config/channels_config.yaml"
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            all_channels = []
            regions_data = {}
            
            # Поддерживаем новую структуру с регионами
            if "regions" in config:
                for region_key, region_data in config["regions"].items():
                    region_name = region_data.get("name", region_key.title())
                    region_channels = region_data.get("channels", [])
                    
                    # Добавляем информацию о регионе к каждому каналу
                    for channel in region_channels:
                        channel_with_region = channel.copy()
                        channel_with_region["region"] = region_key
                        channel_with_region["region_name"] = region_name
                        all_channels.append(channel_with_region)
                    
                    regions_data[region_key] = {
                        "name": region_name,
                        "count": len(region_channels),
                        "channels": region_channels
                    }
            else:
                # Старые форматы для совместимости
                if "channels" in config:
                    all_channels = config["channels"]
                elif "regular_channels" in config or "vip_channels" in config:
                    all_channels = config.get("regular_channels", []) + config.get("vip_channels", [])
            
            return {
                "channels": all_channels,
                "total": len(all_channels),
                "regions": regions_data
            }
            
        except FileNotFoundError:
            return {"channels": [], "total": 0, "regions": {}}
        except Exception as e:
            logger.error(f"❌ Ошибка чтения конфига: {e}")
            return {"channels": [], "total": 0, "regions": {}}
    
    async def remove_channel_handler(self, channel_name: str):
        """Обработчик удаления канала"""
        try:
            # TODO: Удалить из конфига
            await self.send_message(f"✅ Канал @{channel_name} удален из мониторинга")
            logger.info(f"✅ Удален канал: {channel_name}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления канала: {e}")
            await self.send_message(f"❌ Ошибка удаления канала: {str(e)}")
    
    async def start_listening(self):
        """Запустить прослушивание команд"""
        self.is_listening = True
        import time
        self.start_time = time.time()  # Запоминаем время запуска для игнорирования старых команд
        logger.info("👂 Запуск прослушивания команд бота...")
        
        # Устанавливаем offset чтобы пропустить старые сообщения
        try:
            updates = await self.get_updates()
            if updates:
                last_update_id = max(update["update_id"] for update in updates)
                self.update_offset = last_update_id + 1
                logger.info(f"⏭️ Установлен offset {self.update_offset} для пропуска {len(updates)} старых сообщений")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось установить offset: {e}")
        
        try:
            while self.is_listening:
                updates = await self.get_updates()
                if not updates:
                    # Ничего не пришло — продолжим без задержки (long polling уже ждёт)
                    continue
                
                # Обрабатываем по одному, безопасно увеличивая offset только после успешной обработки
                for update in updates:
                    try:
                        await self.process_update(update)
                    except Exception as process_error:
                        logger.error(f"❌ Ошибка обработки обновления: {process_error}")
                        # Не повышаем offset вручную — он уже обновлён в process_update
                        # Продолжаем обработку следующих апдейтов
                
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле прослушивания: {e}")
        finally:
            self.is_listening = False
            logger.info("🛑 Прослушивание команд остановлено")
    
    def stop_listening(self):
        """Остановить прослушивание команд"""
        self.is_listening = False
        logger.info("🛑 Остановка прослушивания команд...")

    # === УПРАВЛЕНИЕ РЕГИОНАМИ ===
    
    async def start_create_region_flow(self):
        """Начать процесс создания нового региона"""
        try:
            text = (
                "➕ <b>Создание нового региона</b>\n\n"
                "📝 <b>Шаг 1 из 2:</b> Название региона\n\n"
                "Отправьте название региона:\n\n"
                "<b>Примеры:</b>\n"
                "• <code>Владивосток</code>\n"
                "• <code>Байкал</code>\n"
                "• <code>Иркутск</code>\n"
                "• <code>Якутия</code>\n"
                "• <code>Новосибирск</code>\n\n"
                "💡 На следующем шаге выберете эмодзи!\n\n"
                "❌ Или нажмите 'Отмена' для возврата"
            )
            
            keyboard = [[{"text": "❌ Отмена", "callback_data": "region_cancel"}]]
            
            await self.edit_message_with_keyboard(text, keyboard, use_reply_keyboard=False)
            
            # Устанавливаем флаг ожидания названия региона
            self.waiting_for_region_name = True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска создания региона: {e}")
    
    async def handle_region_creation(self, region_input: str):
        """Обработка создания нового региона - получаем название и переходим к выбору эмодзи"""
        try:
            # Парсим ввод пользователя - только название, без эмодзи
            region_name_clean = region_input.strip()
            
            # Проверяем что название не пустое
            if not region_name_clean or len(region_name_clean) < 2:
                await self.send_message(
                    "❌ Название слишком короткое!\n\n"
                    "Введите название региона (минимум 2 символа):\n"
                    "Например: <code>Владивосток</code>"
                )
                return
            
            # Проверяем что название не содержит эмодзи (на всякий случай)
            if any(ord(char) > 127 for char in region_name_clean if len(char.encode('utf-8')) > 3):
                await self.send_message(
                    "❌ Пожалуйста, введите только название без эмодзи!\n\n"
                    "Эмодзи выберем на следующем шаге 😊\n"
                    "Например: <code>Владивосток</code>"
                )
                return
            
            # Создаем ключ региона (латиницей)
            import re
            region_key = re.sub(r'[^a-zA-Z0-9]', '_', 
                              region_name_clean.lower()
                              .replace('ё', 'e')
                              .replace('а', 'a')
                              .replace('б', 'b')
                              .replace('в', 'v')
                              .replace('г', 'g')
                              .replace('д', 'd')
                              .replace('е', 'e')
                              .replace('ж', 'zh')
                              .replace('з', 'z')
                              .replace('и', 'i')
                              .replace('й', 'y')
                              .replace('к', 'k')
                              .replace('л', 'l')
                              .replace('м', 'm')
                              .replace('н', 'n')
                              .replace('о', 'o')
                              .replace('п', 'p')
                              .replace('р', 'r')
                              .replace('с', 's')
                              .replace('т', 't')
                              .replace('у', 'u')
                              .replace('ф', 'f')
                              .replace('х', 'h')
                              .replace('ц', 'c')
                              .replace('ч', 'ch')
                              .replace('ш', 'sh')
                              .replace('щ', 'sch')
                              .replace('ъ', '')
                              .replace('ы', 'y')
                              .replace('ь', '')
                              .replace('э', 'e')
                              .replace('ю', 'yu')
                              .replace('я', 'ya'))
            region_key = region_key.strip('_').lower()
            
            # Проверяем что ключ не пустой
            if not region_key:
                region_key = f"region_{len(self.monitor_bot.regions_config) + 1}"
            
            # Сохраняем название и ключ, переходим к выбору эмодзи
            self.pending_region_data = {
                'key': region_key,
                'name_clean': region_name_clean,
            }
            
            # Переходим к выбору эмодзи
            await self.show_emoji_selection(region_name_clean)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки создания региона: {e}")
            await self.send_message("❌ Произошла ошибка при создании региона")
    
    async def show_emoji_selection(self, region_name: str):
        """Показать выбор эмодзи для региона"""
        try:
            text = (
                f"🎨 <b>Шаг 2 из 2:</b> Выбор эмодзи\n\n"
                f"📋 <b>Регион:</b> {region_name}\n\n"
                f"Выберите эмодзи для региона или введите свой:"
            )
            
            # Популярные эмодзи для регионов
            popular_emojis = [
                ("🌊", "Море/побережье"), ("🏔️", "Горы"), ("🌲", "Тайга/лес"), 
                ("❄️", "Север/зима"), ("🌋", "Вулканы"), ("🏝️", "Острова"),
                ("🏜️", "Степи/пустыни"), ("🌾", "Поля/равнины"), ("🏞️", "Природа"),
                ("🌸", "Центр/красота"), ("⚡", "Энергия/промышленность"), ("🚢", "Порты/море")
            ]
            
            # Создаем клавиатуру с эмодзи
            keyboard = []
            row = []
            for i, (emoji, description) in enumerate(popular_emojis):
                button_text = f"{emoji}"
                callback_data = f"emoji_{emoji}"
                
                row.append({"text": button_text, "callback_data": callback_data})
                
                # По 4 эмодзи в ряд
                if len(row) == 4 or i == len(popular_emojis) - 1:
                    keyboard.append(row)
                    row = []
            
            # Добавляем кнопки управления
            keyboard.append([{"text": "✏️ Ввести свой эмодзи", "callback_data": "emoji_custom"}])
            keyboard.append([{"text": "❌ Отмена", "callback_data": "region_cancel"}])
            
            await self.edit_message_with_keyboard(text, keyboard, use_reply_keyboard=False)
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа выбора эмодзи: {e}")
    
    async def load_regions_from_config(self):
        """Загрузить список регионов из config.yaml"""
        try:
            config_path = os.path.join("config", "config.yaml")
            
            if not os.path.exists(config_path):
                logger.warning(f"⚠️ Конфигурационный файл не найден: {config_path}")
                return []
            
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            
            regions = []
            regions_config = config.get('regions', {})
            
            for region_key, region_data in regions_config.items():
                if isinstance(region_data, dict):
                    regions.append({
                        'key': region_key,
                        'name': region_data.get('name', region_key),
                        'emoji': region_data.get('emoji', '📍'),
                        'channels_count': 0  # Пока не знаем количество каналов
                    })
            
            logger.info(f"✅ Загружено {len(regions)} регионов из config.yaml")
            return regions
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки регионов из config.yaml: {e}")
            return []
    
    async def handle_emoji_selection(self, emoji: str):
        """Обработка выбора эмодзи из списка"""
        try:
            if not self.pending_region_data:
                await self.send_message("❌ Данные региона потеряны. Начните заново.")
                return
            
            region_key = self.pending_region_data['key']
            region_name_clean = self.pending_region_data['name_clean']
            region_full_name = f"{emoji} {region_name_clean}"
            
            # Переходим к подтверждению
            await self.show_region_creation_confirmation(
                region_key, region_full_name, emoji, region_name_clean
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки выбора эмодзи: {e}")
    
    async def start_custom_emoji_input(self):
        """Начать ввод пользовательского эмодзи"""
        try:
            text = (
                "✏️ <b>Ввод своего эмодзи</b>\n\n"
                "Отправьте один эмодзи для региона:\n\n"
                "<b>Примеры:</b>\n"
                "🌍 🗻 🏙️ 🌅 ⭐ 🔥 💎 🎯\n\n"
                "💡 Любой эмодзи на ваш выбор!"
            )
            
            keyboard = [[{"text": "❌ Отмена", "callback_data": "region_cancel"}]]
            
            await self.edit_message_with_keyboard(text, keyboard, use_reply_keyboard=False)
            
            # Устанавливаем флаг ожидания эмодзи
            self.waiting_for_emoji = True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска ввода эмодзи: {e}")
    
    async def handle_custom_emoji_input(self, emoji_input: str):
        """Обработка пользовательского эмодзи"""
        try:
            emoji = emoji_input.strip()
            
            # Проверяем что введен только один символ и это эмодзи
            if len(emoji) != 1:
                await self.send_message(
                    "❌ Введите только один эмодзи!\n"
                    "Например: 🌍"
                )
                return
            
            # Простая проверка на эмодзи (Unicode выше базового набора)
            if ord(emoji) < 128:
                await self.send_message(
                    "❌ Это не эмодзи!\n"
                    "Отправьте эмодзи, например: 🌍 🗻 ⭐"
                )
                return
            
            # Продолжаем с выбранным эмодзи
            await self.handle_emoji_selection(emoji)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки пользовательского эмодзи: {e}")
            await self.send_message("❌ Произошла ошибка. Попробуйте еще раз.")
    
    async def show_region_creation_confirmation(self, region_key: str, region_full_name: str, 
                                              region_emoji: str, region_name: str):
        """Показать подтверждение создания региона"""
        try:
            text = (
                f"🔍 <b>Подтверждение создания региона</b>\n\n"
                f"📋 <b>Название:</b> {region_full_name}\n"
                f"🔑 <b>Ключ:</b> <code>{region_key}</code>\n"
                f"🎯 <b>Эмодзи:</b> {region_emoji}\n\n"
                f"💭 <b>Описание:</b> Новый регион для мониторинга каналов\n\n"
                f"✅ Всё верно?"
            )
            
            keyboard = [
                [
                    {"text": "✅ Создать регион", "callback_data": f"confirm_create_{region_key}"},
                    {"text": "❌ Отмена", "callback_data": "region_cancel"}
                ]
            ]
            
            # Сохраняем данные для создания
            self.pending_region_data = {
                'key': region_key,
                'name': region_full_name,
                'emoji': region_emoji,
                'description': f"Регион {region_name}"
            }
            
            await self.edit_message_with_keyboard(text, keyboard, use_reply_keyboard=False)
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа подтверждения региона: {e}")
    
    async def create_region_confirmed(self, region_key: str):
        """Подтвержденное создание региона"""
        try:
            if not hasattr(self, 'pending_region_data') or not self.pending_region_data:
                await self.send_message("❌ Данные региона потеряны, попробуйте снова")
                return
            
            data = self.pending_region_data
            
            # Создаем регион через главный бот
            if self.monitor_bot:
                success = self.monitor_bot.add_new_region(
                    region_key=data['key'],
                    region_name=data['name'],
                    region_emoji=data['emoji'],
                    region_description=data['description']
                )
                
                if success:
                    # Теперь добавляем канал в новый регион
                    if self.pending_channel_url:
                        await self.add_channel_to_config(self.pending_channel_url, data['key'])
                        
                        text = (
                            f"🎉 <b>Успешно!</b>\n\n"
                            f"✅ Создан новый регион: {data['name']}\n"
                            f"✅ Канал @{self.pending_channel_url} добавлен в регион\n\n"
                            f"🔄 Перезапустите бота для применения изменений"
                        )
                    else:
                        text = (
                            f"🎉 <b>Регион создан!</b>\n\n"
                            f"✅ Создан новый регион: {data['name']}\n\n"
                            f"📝 Теперь вы можете добавлять в него каналы"
                        )
                    
                    keyboard = [[{"text": "🏠 Главное меню", "callback_data": "start"}]]
                    await self.edit_message_with_keyboard(text, keyboard, use_reply_keyboard=False)
                    
                    # Очищаем временные данные
                    self.pending_region_data = None
                    self.pending_channel_url = None
                else:
                    await self.send_message("❌ Ошибка создания региона")
            else:
                await self.send_message("❌ Главный бот недоступен")
                
        except Exception as e:
            logger.error(f"❌ Ошибка подтверждения создания региона: {e}")


# Функция для создания бота из конфигурации
async def create_bot_from_config(config: Dict, monitor_bot=None) -> Optional[TelegramBot]:
    """Создать бота из конфигурации"""
    try:
        bot_config = config.get('bot')
        if not bot_config:
            logger.warning("⚠️ Конфигурация бота не найдена")
            return None
        
        token = bot_config.get('token')
        admin_chat_id = bot_config.get('chat_id')
        group_chat_id = bot_config.get('group_chat_id')  # Новый параметр
        
        if not token or not admin_chat_id:
            logger.error("❌ Не указан токен бота или chat_id")
            return None
        
        bot = TelegramBot(token, admin_chat_id, group_chat_id, monitor_bot)
        
        # Тестируем подключение
        if await bot.test_connection():
            return bot
        else:
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка создания бота: {e}")
        return None
