import asyncio
import httpx
import json
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from ..core.bot_client import TelegramBot


class KeyboardBuilder:
    
    def __init__(self, bot: "TelegramBot"):
        self.bot = bot
    
    async def send_message_with_keyboard(
        self, 
        text: str, 
        keyboard: List = None, 
        parse_mode: str = "HTML", 
        use_reply_keyboard: bool = False, 
        to_group: bool = None, 
        to_user: int = None
    ) -> bool:
        try:
            if to_user:
                target_chat_id = to_user
            elif to_group is False:
                target_chat_id = self.bot.admin_chat_id
            elif self.bot.group_chat_id:
                target_chat_id = self.bot.group_chat_id
            else:
                target_chat_id = self.bot.admin_chat_id
            
            
            if keyboard and not use_reply_keyboard:
                await self.bot.deactivate_old_inline_messages()
            
            return await self._send_new_message_with_keyboard(
                text, keyboard, parse_mode, use_reply_keyboard, target_chat_id
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения с клавиатурой: {e}")
            return False
    
    async def edit_message_with_keyboard(
        self, 
        text: str, 
        keyboard: List = None, 
        message_id: int = None, 
        parse_mode: str = "HTML", 
        use_reply_keyboard: bool = False, 
        chat_id: int = None
    ) -> bool:
        try:
            target_message_id = message_id or self.bot.last_message_id
            target_chat_id = chat_id or self.bot.admin_chat_id
            
            if not target_message_id:
                return False
            
            data = {
                "chat_id": target_chat_id,
                "message_id": target_message_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            if keyboard:
                if use_reply_keyboard:
                    return False
                else:
                    data["reply_markup"] = {"inline_keyboard": keyboard}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.bot.base_url}/editMessageText", json=data)
                
                if response.status_code == 200:
                    logger.debug(f"✏️ Сообщение {target_message_id} отредактировано")
                    return True
                else:
                    error_text = response.text
                    if "message is not modified" in error_text:
                        logger.debug("⚠️ Сообщение не изменилось")
                        return True
                    
                    logger.warning(f"⚠️ Не удалось отредактировать сообщение: {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка редактирования сообщения: {e}")
            return False
    
    async def _send_new_message_with_keyboard(
        self, 
        text: str, 
        keyboard: List, 
        parse_mode: str, 
        use_reply_keyboard: bool, 
        chat_id: int
    ) -> bool:
        try:
            data = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            if keyboard:
                if use_reply_keyboard:
                    data["reply_markup"] = {
                        "keyboard": keyboard,
                        "resize_keyboard": True,
                        "one_time_keyboard": False
                    }
                else:
                    data["reply_markup"] = {"inline_keyboard": keyboard}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.bot.base_url}/sendMessage", json=data)
                
                if response.status_code == 200:
                    response_data = response.json()
                    message_id = response_data["result"]["message_id"]
                    
                    if keyboard and not use_reply_keyboard:
                        self.bot.active_inline_messages.append({
                            'chat_id': chat_id,
                            'message_id': message_id
                        })
                        
                    if chat_id == self.bot.group_chat_id or chat_id == self.bot.admin_chat_id:
                        self.bot.last_message_id = message_id
                    
                    logger.debug(f"📤 Сообщение отправлено с ID: {message_id}")
                    return True
                else:
                    logger.error(f"❌ Ошибка отправки: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка отправки нового сообщения: {e}")
            return False
    
    async def deactivate_old_inline_messages(self, exclude_message_id: int = None):
        try:
            logger.debug("🔄 Деактивация старых inline сообщений")
            
        except Exception as e:
            logger.error(f"❌ Ошибка деактивации inline сообщений: {e}")
    
    async def remove_old_keyboard(self, to_group: bool = None):
        try:
            if to_group and self.bot.group_chat_id:
                target_chat_id = self.bot.group_chat_id
            elif to_group is False:
                target_chat_id = self.bot.admin_chat_id
            else:
                target_chat_id = self.bot.group_chat_id if self.bot.group_chat_id else self.bot.admin_chat_id

            data = {
                "chat_id": target_chat_id,
                "text": "🔄 Обновление интерфейса...",
                "reply_markup": {"remove_keyboard": True}
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{self.bot.base_url}/sendMessage", json=data)
                if response.status_code == 200:
                    logger.debug("🧹 Клавиатура снизу экрана удалена")
                        
        except Exception as e:
            logger.debug(f"⚠️ Не удалось удалить старую клавиатуру: {e}")
    
    def build_main_menu_keyboard(self) -> List[List[Dict]]:
        return [
            [{"text": "🗂️ Управление каналами", "callback_data": "manage_channels"}],
            [{"text": "➕ Добавить канал", "callback_data": "add_channel"}],
            [{"text": "🚀 Запуск", "callback_data": "start_monitoring"}, 
             {"text": "🛑 Стоп", "callback_data": "stop_monitoring"}],
            [{"text": "📰 Дайджест", "callback_data": "digest"}, 
             {"text": "🆘 Справка", "callback_data": "help"}]
        ]
    
    def build_pagination_keyboard(self, current_page: int, total_pages: int, callback_prefix: str) -> List[List[Dict]]:
        keyboard = []
        nav_buttons = []
        
        if current_page > 1:
            nav_buttons.append({
                "text": f"⬅️ Стр. {current_page-1}",
                "callback_data": f"{callback_prefix}_{current_page-1}"
            })
        
        if current_page < total_pages:
            nav_buttons.append({
                "text": f"Стр. {current_page+1} ➡️", 
                "callback_data": f"{callback_prefix}_{current_page+1}"
            })
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        return keyboard
    
    def build_confirmation_keyboard(self, confirm_callback: str, cancel_callback: str = "start") -> List[List[Dict]]:
        return [
            [{"text": "✅ Подтвердить", "callback_data": confirm_callback}],
            [{"text": "❌ Отмена", "callback_data": cancel_callback}]
        ]
    
    async def send_or_edit_message_with_keyboard(
        self, 
        text: str, 
        keyboard: List = None, 
        should_edit: bool = False,
        **kwargs
    ) -> bool:
        if should_edit and self.bot.last_message_id and keyboard and not kwargs.get('use_reply_keyboard', False):
            chat_id = kwargs.get('to_group') 
            if chat_id is True and self.bot.group_chat_id:
                target_chat_id = self.bot.group_chat_id
            elif chat_id is False:
                target_chat_id = self.bot.admin_chat_id
            elif self.bot.group_chat_id:
                target_chat_id = self.bot.group_chat_id
            else:
                target_chat_id = self.bot.admin_chat_id
                
            success = await self.edit_message_with_keyboard(
                text, keyboard, message_id=self.bot.last_message_id, 
                parse_mode="HTML", use_reply_keyboard=False, chat_id=target_chat_id
            )
            if success:
                return True
        
        return await self.send_message_with_keyboard(text, keyboard, use_reply_keyboard=False, **kwargs)