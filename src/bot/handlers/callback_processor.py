import asyncio
from typing import Dict, Optional, Any
from loguru import logger


class CallbackProcessor:
    
    def __init__(self, bot: "TelegramBot"):
        self.bot = bot
    
    async def handle_callback(self, data: str, callback_query: Dict):
        try:
            callback_user_id = callback_query.get("from", {}).get("id")
            callback_chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
            
            if not (self.bot.is_admin_user(callback_user_id) or self.bot.is_message_from_group(callback_chat_id)):
                return
            
            self.bot.current_callback_chat_id = callback_chat_id
            
            await self._route_callback(data, callback_query)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки callback: {e}")
        finally:
            self.bot.current_callback_chat_id = None
    
    async def _route_callback(self, data: str, callback_query: Dict):
        message = {"message": {"chat": {"id": self.bot.current_callback_chat_id}}}
        
        # Сброс флагов ожидания при переходе в главные разделы меню
        main_menus = {
            "start", "status", "help", "digest", "start_monitoring", 
            "stop_monitoring", "restart", "stats", "manage_channels", 
            "refresh_channels", "force_subscribe"
        }
        if data in main_menus:
            self.bot.clear_waiting_states()
            
        if data == "start":
            await self.bot.basic_commands.start(message)
        
        elif data == "status":
            await self.bot.basic_commands.status(message)
        
        elif data == "help":
            await self.bot.basic_commands.help(message)
        
        elif data == "digest":
            await self.bot.basic_commands.digest(message)
        
        elif data == "start_monitoring":
            await self.bot.basic_commands.start_monitoring(message)
        
        elif data == "stop_monitoring":
            await self.bot.basic_commands.stop_monitoring(message)
        
        elif data == "restart":
            await self.bot.basic_commands.restart(message)
        
        elif data == "stats":
            await self.bot.management_commands.stats(message)
        
        elif data == "manage_channels":
            await self.bot.management_commands.manage_channels(message)
        
        elif data == "refresh_channels":
            await self.bot.management_commands.manage_channels(message)
        
        elif data == "add_channel":
            await self._handle_add_channel_callback()
        
        elif data == "force_subscribe":
            await self.bot.channel_commands.force_subscribe(message)
        
        elif data.startswith("manage_region_"):
            await self._handle_manage_region_callback(data)
        
        elif data.startswith("region_selected_"):
            region = data.replace("region_selected_", "")
            await self.bot.region_manager.handle_region_selection(region)
        
        elif data.startswith("bulk_region_selected_"):
            region = data.replace("bulk_region_selected_", "")
            await self.bot.region_manager.handle_bulk_region_selection(region)
        
        elif data.startswith("region_bulk_"):
            region = data.replace("region_bulk_", "")
            await self.bot.region_manager.handle_bulk_region_selection(region)
        
        elif data.startswith("delete_channel|"):
            await self._handle_delete_channel_callback(data)
        
        elif data.startswith("delete_channel_confirmed|"):
            await self._handle_delete_confirmed_callback(data)
        
        elif data.startswith("emoji_"):
            emoji = data.replace("emoji_", "")
            await self._handle_emoji_selection(emoji)
        
        elif data == "custom_emoji":
            from ..regions.region_ui import RegionUI
            region_ui = RegionUI(self.bot)
            await region_ui.start_custom_emoji_input()
        
        elif data == "create_new_region":
            await self.bot.region_manager.start_create_region_flow()
        
        elif data.startswith("create_region_confirmed_"):
            region_key = data.replace("create_region_confirmed_", "")
            await self.bot.region_manager.create_region_confirmed(region_key)
        
        elif data.startswith("auto_add_topic_"):
            region_key = data.replace("auto_add_topic_", "")
            await self.bot.region_manager.auto_add_topic_to_config(region_key)
        
        elif data == "region_cancel":
            await self._handle_region_cancel()
        
        elif data.startswith("digest_"):
            await self._handle_digest_callbacks(data, message)
        
        else:
            logger.warning(f"❓ Неизвестный callback: {data}")
            await self.bot.send_message("❓ Неизвестная команда кнопки")
    
    async def _handle_add_channel_callback(self):
        from ..channels.channel_ui import ChannelUI
        channel_ui = ChannelUI(self.bot)
        await channel_ui.show_add_channel_help()
    
    async def _handle_manage_region_callback(self, data: str):
        parts = data.split("_")
        
        if len(parts) >= 3:
            region_key = parts[2]
            
            page = 1
            if len(parts) >= 5 and parts[3] == "page":
                try:
                    page = int(parts[4])
                except ValueError:
                    page = 1
            
            from ..channels.channel_ui import ChannelUI
            channel_ui = ChannelUI(self.bot)
            await channel_ui.show_region_channels(region_key, page)
    
    async def _handle_delete_channel_callback(self, data: str):
        parts = data.split("|")
        if len(parts) >= 3:
            region_key = parts[1]
            username = parts[2]
            
            from ..channels.channel_ui import ChannelUI
            channel_ui = ChannelUI(self.bot)
            await channel_ui.show_delete_confirmation(region_key, username)
    
    async def _handle_delete_confirmed_callback(self, data: str):
        parts = data.split("|")
        if len(parts) >= 3:
            region_key = parts[1]
            username = parts[2]
            
            logger.info(f"🗑️ Удаление канала: регион='{region_key}', username='{username}'")
            
            success = await self.bot.channel_manager.delete_channel_from_config(region_key, username)
            
            if success:
                regions_data = await self.bot.channel_manager.get_all_channels_grouped()
                region_info = regions_data.get(region_key, {})
                region_name = region_info.get('name', f'📍 {region_key.title()}')
                
                from ..channels.channel_ui import ChannelUI
                channel_ui = ChannelUI(self.bot)
                await channel_ui.show_channel_delete_success(username, region_key, region_name)
            else:
                await self.bot.send_message(f"❌ Не удалось удалить канал @{username}")
    
    async def _handle_emoji_selection(self, emoji: str):
        try:
            if not self.bot.pending_region_data:
                await self.bot.send_message("❌ Данные региона потеряны. Начните заново.")
                return
            
            region_key = self.bot.pending_region_data['key']
            region_name_clean = self.bot.pending_region_data['name_clean']
            region_full_name = f"{emoji} {region_name_clean}"
            
            from ..regions.region_ui import RegionUI
            region_ui = RegionUI(self.bot)
            await region_ui.show_region_creation_confirmation(
                region_key, region_full_name, emoji, region_name_clean
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки выбора эмодзи: {e}")
    
    async def _handle_region_cancel(self):
        self.bot.pending_channel_url = None
        self.bot.waiting_for_region_name = False
        self.bot.waiting_for_emoji = False
        self.bot.pending_region_data = None
        self.bot.pending_topic_data = None
        
        callback_message = {"message": {"chat": {"id": self.bot.current_callback_chat_id}}}
        await self.bot.basic_commands.start(callback_message)
    
    async def _handle_digest_callbacks(self, data: str, message: Dict):
        if data.startswith("digest_period_"):
            days = int(data.split("_")[-1])
            await self._handle_digest_period_selection(days)
        
        elif data == "digest_channel_link":
            await self._handle_digest_channel_link_request()
        
        elif data.startswith("digest_page_"):
            await self._handle_digest_page_callback(data, message)
    
    async def _handle_digest_period_selection(self, days: int):
        try:
            await self.bot.send_message(f"📰 Генерируем дайджест за {days} дней из базы данных...")
            
            if hasattr(self.bot.basic_commands, 'digest_generator') and self.bot.basic_commands.digest_generator:
                digest_result = await self.bot.basic_commands.digest_generator.generate_weekly_digest(days=days)
                await self.bot.send_message(digest_result)
            else:
                await self.bot.send_message("❌ Генератор дайджестов недоступен")
                
        except Exception as e:
            logger.error(f"❌ Ошибка генерации дайджеста: {e}")
            await self.bot.send_message(f"❌ Ошибка генерации дайджеста: {e}")
    
    async def _handle_digest_channel_link_request(self):
        self.bot.waiting_for_digest_channel = True
        await self.bot.send_message(
            "🔗 <b>Дайджест конкретного канала</b>\n\n" 
            "Отправьте ссылку на канал для live-анализа:\n"
            "• <code>https://t.me/channel_name</code>\n"
            "• <code>@channel_name</code>\n\n"
            "📰 Будет создан дайджест топ-новостей из этого канала"
        )
    
    async def _handle_digest_page_callback(self, data: str, message: Dict):
        try:
            parts = data.split("_")
            if len(parts) < 4:
                await self.bot.send_message("❌ Некорректный формат callback для пагинации")
                return
            
            page = int(parts[-1])
            channel_username = "_".join(parts[2:-1])
            
            logger.info(f"📄 Запрос страницы {page} дайджеста для @{channel_username}")
            
            if hasattr(self.bot.basic_commands, 'digest_generator') and self.bot.basic_commands.digest_generator:
                page_result = await self.bot.basic_commands.digest_generator.get_digest_page(channel_username, page)
                
                if isinstance(page_result, dict):
                    await self.bot.keyboard_builder.send_message_with_keyboard(
                        page_result['text'], page_result['keyboard'], use_reply_keyboard=False
                    )
                else:
                    await self.bot.send_message("❌ Ошибка получения страницы дайджеста")
            else:
                await self.bot.send_message("❌ Генератор дайджестов недоступен")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки пагинации дайджеста: {e}")
            await self.bot.send_message(f"❌ Ошибка получения страницы: {e}")
    
    
    
