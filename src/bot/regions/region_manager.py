import yaml
import os
import re
import subprocess
import asyncio
from typing import Dict, List, Optional, Any
from loguru import logger
from datetime import datetime


class RegionManager:
    
    def __init__(self, bot: "TelegramBot"):
        self.bot = bot
    
    async def start_create_region_flow(self):
        try:
            self.bot.waiting_for_region_name = True
            self.bot.pending_region_data = None
            
            text = (
                "🌏 <b>Создание нового региона</b>\n\n"
                "📝 Введите название региона:\n\n"
                "<b>Примеры:</b>\n"
                "• Владивосток\n"
                "• Приморье\n"
                "• Магадан\n"
                "• Благовещенск\n\n"
                "💡 Введите только название, эмодзи выберем на следующем шаге"
            )
            
            keyboard = [[{"text": "❌ Отмена", "callback_data": "start"}]]
            
            await self.bot.keyboard_builder.send_message_with_keyboard(
                text, keyboard, use_reply_keyboard=False
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска создания региона: {e}")
            await self.bot.send_message(f"❌ Ошибка создания региона: {e}")
    
    async def handle_region_creation(self, region_input: str):
        try:
            region_name_clean = region_input.strip()
            
            if not region_name_clean or len(region_name_clean) < 2:
                await self.bot.send_message(
                    "❌ Название слишком короткое!\n\n"
                    "Введите название региона (минимум 2 символа):\n"
                    "Например: <code>Владивосток</code>"
                )
                return
            
            if any(ord(char) > 127 for char in region_name_clean if len(char.encode('utf-8')) > 3):
                await self.bot.send_message(
                    "❌ Пожалуйста, введите только название без эмодзи!\n\n"
                    "Эмодзи выберем на следующем шаге 😊\n"
                    "Например: <code>Владивосток</code>"
                )
                return
            
            region_key = self._create_region_key(region_name_clean)
            
            if await self._is_region_exists(region_key):
                await self.bot.send_message(
                    f"❌ Регион '{region_name_clean}' уже существует!\n\n"
                    "Попробуйте другое название или используйте существующий регион."
                )
                return
            
            self.bot.pending_region_data = {
                'key': region_key,
                'name_clean': region_name_clean,
                'description': f"Регион {region_name_clean}"
            }
            
            from .region_ui import RegionUI
            region_ui = RegionUI(self.bot)
            await region_ui.show_emoji_selection(region_name_clean)
            
            self.bot.waiting_for_region_name = False
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки создания региона: {e}")
            await self.bot.send_message(f"❌ Ошибка создания региона: {e}")
    
    async def create_region_confirmed(self, region_key: str) -> bool:
        try:
            if not hasattr(self.bot, 'pending_region_data') or not self.bot.pending_region_data:
                await self.bot.send_message("❌ Данные региона потеряны, попробуйте снова")
                return False
            
            data = self.bot.pending_region_data
            
            if self.bot.monitor_bot and hasattr(self.bot.monitor_bot, 'add_new_region'):
                success = await self.bot.monitor_bot.add_new_region(
                    region_key=data['key'],
                    region_name=data['name'],
                    region_emoji=data['emoji'],
                    region_description=data['description']
                )
                
                if success:
                    await self._show_region_created_success(data)
                    return True
            
            success = await self._create_region_in_config(data)
            
            if success:
                await self._show_region_created_success(data)
                
                if hasattr(self.bot, 'pending_channel_url') and self.bot.pending_channel_url:
                    channel_username = self.bot.pending_channel_url
                    try:
                        channel_success = await self.bot.channel_manager.add_channel_to_config(channel_username, region_key)
                        if channel_success:
                            logger.info(f"✅ Канал @{channel_username} автоматически добавлен в новый регион {region_key}")
                            
                            if self.bot.monitor_bot and hasattr(self.bot.monitor_bot, 'channel_monitor'):
                                try:
                                    success = await self.bot.monitor_bot.channel_monitor.add_single_channel_to_monitoring(channel_username)
                                    if success:
                                        logger.info(f"✅ Подписка на @{channel_username} активирована")
                                    else:
                                        logger.warning(f"⚠️ Не удалось подписаться на @{channel_username}")
                                except Exception as sub_e:
                                    logger.warning(f"⚠️ Не удалось подписаться на @{channel_username}: {sub_e}")
                            
                            await self.bot.send_message(
                                f"🎯 <b>Канал добавлен в новый регион!</b>\n\n"
                                f"📺 <b>Канал:</b> @{channel_username}\n"
                                f"🌍 <b>Регион:</b> {data['name']}\n\n"
                                f"📝 Канал добавлен в конфигурацию\n"
                                f"🔄 <b>Для активации мониторинга новых каналов выполните /restart</b>"
                            )
                            
                            self.bot.pending_channel_url = None
                        else:
                            logger.error(f"❌ Не удалось добавить канал @{channel_username} в регион {region_key}")
                    except Exception as channel_e:
                        logger.error(f"❌ Ошибка добавления канала в новый регион: {channel_e}")
                
                if hasattr(self.bot, 'pending_channels_list') and self.bot.pending_channels_list:
                    channels_to_add = self.bot.pending_channels_list.copy()
                    logger.info(f"📝 Массовое добавление {len(channels_to_add)} каналов в новый регион {region_key}")
                    
                    added_count = 0
                    failed_channels = []
                    
                    for channel_username in channels_to_add:
                        try:
                            channel_success = await self.bot.channel_manager.add_channel_to_config(channel_username, region_key)
                            if channel_success:
                                added_count += 1
                                logger.info(f"✅ Канал @{channel_username} добавлен в новый регион {region_key}")
                                
                                if self.bot.monitor_bot and hasattr(self.bot.monitor_bot, 'channel_monitor'):
                                    try:
                                        success = await self.bot.monitor_bot.channel_monitor.add_single_channel_to_monitoring(channel_username)
                                        if success:
                                            logger.info(f"✅ @{channel_username} добавлен в мониторинг")
                                        await asyncio.sleep(1)
                                    except Exception as sub_e:
                                        logger.warning(f"⚠️ Подписка @{channel_username}: {sub_e}")
                                        await asyncio.sleep(0.5)
                            else:
                                failed_channels.append(channel_username)
                        except Exception as e:
                            logger.warning(f"⚠️ Ошибка добавления @{channel_username}: {e}")
                            failed_channels.append(channel_username)
                    
                    region_info = data
                    region_name = region_info.get('name', region_key.title())
                    
                    result_text = f"🎉 <b>Массовое добавление завершено!</b>\n\n"
                    result_text += f"📂 <b>Новый регион:</b> {region_name}\n"
                    result_text += f"✅ <b>Добавлено каналов:</b> {added_count}\n"
                    
                    if failed_channels:
                        result_text += f"❌ <b>Не удалось добавить:</b> {len(failed_channels)}\n"
                        result_text += "🔗 " + ", ".join([f"@{ch}" for ch in failed_channels[:5]])
                        if len(failed_channels) > 5:
                            result_text += f" и еще {len(failed_channels) - 5}..."
                    
                    keyboard = [
                        [{"text": "🗂️ Управление каналами", "callback_data": "manage_channels"}],
                        [{"text": "🏠 Главное меню", "callback_data": "start"}]
                    ]
                    
                    await self.bot.keyboard_builder.send_message_with_keyboard(
                        result_text, keyboard, use_reply_keyboard=False
                    )
                    
                    self.bot.pending_channels_list = []
                
                await self.auto_add_topic_to_config(region_key)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка подтверждения создания региона: {e}")
            await self.bot.send_message(f"❌ Ошибка создания региона: {e}")
            return False
    
    async def auto_add_topic_to_config(self, region_key: str):
        try:
            if not hasattr(self.bot, 'pending_topic_id') or not self.bot.pending_topic_id:
                self.bot.waiting_for_topic_id = True
                
                text = (
                    f"🔗 <b>Настройка темы для региона {region_key}</b>\n\n"
                    "📱 <b>Для добавления topic_id:</b>\n"
                    "1. Откройте нужную тему в супергруппе\n"
                    "2. Используйте команду /topic_id в этой теме\n"
                    "3. Выберите этот регион для автоматического добавления\n\n"
                    "💡 Topic ID нужен для автоматической сортировки новостей по темам"
                )
                
                keyboard = [
                    [{"text": "🏠 Главное меню", "callback_data": "start"}]
                ]
                
                await self.bot.keyboard_builder.send_message_with_keyboard(
                    text, keyboard, use_reply_keyboard=False
                )
                return
            
            topic_id = self.bot.pending_topic_id
            
            success = await self._update_region_topic_id(region_key, topic_id)
            
            if success:
                if self.bot.monitor_bot and hasattr(self.bot.monitor_bot, 'config_loader'):
                    regions = self.bot.monitor_bot.config_loader.get_regions_config()
                    region_info = regions.get(region_key, {})
                    region_name = region_info.get('name', region_key.title())
                else:
                    region_name = region_key.title()
                
                text = f"✅ <b>Topic ID добавлен!</b>\n\n"
                text += f"🌍 <b>Регион:</b> {region_name}\n"
                text += f"🆔 <b>Topic ID:</b> {topic_id}\n\n"
                text += "📝 Topic ID добавлен в конфигурацию\n"
                text += "🔄 <b>Для применения изменений выполните /restart</b>\n\n"
                text += "🎯 После рестарта новости этого региона будут автоматически отправляться в указанную тему"
                
                keyboard = [
                    [{"text": "🏠 Главное меню", "callback_data": "start"}]
                ]
                
                await self.bot.keyboard_builder.send_message_with_keyboard(
                    text, keyboard, use_reply_keyboard=False
                )
                
                self.bot.pending_topic_id = None
                self.bot.waiting_for_topic_id = False
            else:
                await self.bot.send_message(f"❌ Не удалось добавить topic_id для региона {region_key}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка автодобавления topic: {e}")
    
    async def handle_region_selection(self, region: str):
        try:
            if not self.bot.pending_channel_url:
                await self.bot.send_message("❌ Данные канала потеряны. Попробуйте добавить канал заново.")
                return
            
            channel_username = self.bot.pending_channel_url
            
            success = await self.bot.channel_manager.add_channel_to_config(channel_username, region)
            
            if success:
                regions_config = await self._load_regions_config()
                region_info = regions_config.get(region, {})
                region_name = region_info.get('name', f'📍 {region.title()}')
                
                from ..channels.channel_ui import ChannelUI
                channel_ui = ChannelUI(self.bot)
                await channel_ui.show_channel_added_success(channel_username, region, region_name)
                
                self.bot.pending_channel_url = None
                
                if self.bot.monitor_bot and hasattr(self.bot.monitor_bot, 'channel_monitor'):
                    try:
                        success = await self.bot.monitor_bot.channel_monitor.add_single_channel_to_monitoring(channel_username)
                        if success:
                            logger.info(f"✅ Подписка на @{channel_username} инициирована")
                        else:
                            logger.warning(f"⚠️ Не удалось подписаться на @{channel_username}")
                        
                    except Exception as sub_e:
                        logger.warning(f"⚠️ Не удалось подписаться на @{channel_username}: {sub_e}")
            else:
                await self.bot.send_message(f"❌ Не удалось добавить канал @{channel_username} в регион {region}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка выбора региона: {e}")
            await self.bot.send_message(f"❌ Ошибка выбора региона: {e}")
    
    async def handle_bulk_region_selection(self, region: str):
        try:
            if not self.bot.pending_channels_list:
                await self.bot.send_message("❌ Список каналов пуст")
                return
            
            channels_to_add = self.bot.pending_channels_list.copy()
            added_count = 0
            failed_channels = []
            
            regions_config = await self._load_regions_config()
            region_info = regions_config.get(region, {})
            region_name = region_info.get('name', f'📍 {region.title()}')
            
            await self.bot.send_message(f"📝 Добавляем {len(channels_to_add)} каналов в регион {region_name}...")
            
            for channel_username in channels_to_add:
                try:
                    success = await self.bot.channel_manager.add_channel_to_config(channel_username, region)
                    if success:
                        added_count += 1
                        
                        if self.bot.monitor_bot and hasattr(self.bot.monitor_bot, 'channel_monitor'):
                            try:
                                success = await self.bot.monitor_bot.channel_monitor.add_single_channel_to_monitoring(channel_username)
                                if success:
                                    logger.info(f"✅ @{channel_username} добавлен в мониторинг")
                                else:
                                    logger.warning(f"⚠️ Подписка @{channel_username}: неудачно")
                                await asyncio.sleep(1)
                            except Exception as sub_e:
                                logger.warning(f"⚠️ Подписка @{channel_username}: {sub_e}")
                                await asyncio.sleep(0.5)
                    else:
                        failed_channels.append(channel_username)
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка добавления @{channel_username}: {e}")
                    failed_channels.append(channel_username)
            
            result_text = f"✅ <b>Массовое добавление завершено!</b>\n\n"
            result_text += f"📂 <b>Регион:</b> {region_name}\n"
            result_text += f"✅ <b>Добавлено каналов:</b> {added_count}\n"
            
            if failed_channels:
                result_text += f"❌ <b>Не удалось добавить:</b> {len(failed_channels)}\n"
                result_text += "🔗 " + ", ".join([f"@{ch}" for ch in failed_channels[:5]])
                if len(failed_channels) > 5:
                    result_text += f" и еще {len(failed_channels) - 5}..."
            
            keyboard = [
                [{"text": "🗂️ Управление каналами", "callback_data": "manage_channels"}],
                [{"text": "🏠 Главное меню", "callback_data": "start"}]
            ]
            
            await self.bot.keyboard_builder.send_message_with_keyboard(
                result_text, keyboard, use_reply_keyboard=False
            )
            
            self.bot.pending_channels_list = []
            
        except Exception as e:
            logger.error(f"❌ Ошибка массового добавления: {e}")
            await self.bot.send_message(f"❌ Ошибка массового добавления: {e}")
    
    def _create_region_key(self, region_name: str) -> str:
        try:
            translit_map = {
                'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
                'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
                'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
                'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
                'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
            }
            
            region_lower = region_name.lower()
            
            region_key = ""
            for char in region_lower:
                region_key += translit_map.get(char, char)
            
            region_key = re.sub(r'[^a-zA-Z0-9_]', '_', region_key)
            region_key = re.sub(r'_+', '_', region_key).strip('_')
            
            if len(region_key) < 3:
                region_key = f"region_{region_key}"
            
            return region_key
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания ключа региона: {e}")
            return f"region_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def _is_region_exists(self, region_key: str) -> bool:
        try:
            regions_config = await self._load_regions_config()
            return region_key in regions_config
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки существования региона: {e}")
            return False
    
    async def _create_region_in_config(self, region_data: Dict) -> bool:
        try:
            success_main = await self._add_region_to_main_config(region_data)
            success_channels = await self._add_region_to_channels_config(region_data)
            
            if success_main and success_channels:
                logger.info(f"✅ Регион {region_data['key']} создан в конфигурации")
                
                await self._auto_commit_config(
                    f"Create new region: {region_data['name']}",
                    ["config/config.yaml", "config/channels_config.yaml"]
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания региона в конфиге: {e}")
            return False
    
    async def _add_region_to_main_config(self, region_data: Dict) -> bool:
        try:
            config_path = "config/config.yaml"
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            if 'regions' not in config:
                config['regions'] = {}
            
            config['regions'][region_data['key']] = {
                'name': region_data['name'],
                'emoji': region_data['emoji'],
                'description': region_data['description'],
                'keywords': [region_data['name'].lower()],
                'topic_id': None,
                'created_at': datetime.now().strftime('%Y-%m-%d')
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, indent=2, default_flow_style=False)
            
            logger.info(f"✅ Регион добавлен в config.yaml: {region_data['key']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления региона в config.yaml: {e}")
            return False
    
    async def _add_region_to_channels_config(self, region_data: Dict) -> bool:
        try:
            config_path = "config/channels_config.yaml"
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
            else:
                config = {}
            
            if 'regions' not in config:
                config['regions'] = {}
            
            config['regions'][region_data['key']] = {
                'name': region_data['name'],
                'channels': []
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, indent=2, default_flow_style=False)
            
            logger.info(f"✅ Регион добавлен в channels_config.yaml: {region_data['key']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления региона в channels_config.yaml: {e}")
            return False
    
    async def _show_region_created_success(self, region_data: Dict):
        try:
            text = f"🎉 <b>Регион успешно создан!</b>\n\n"
            text += f"🌍 <b>Название:</b> {region_data['name']}\n"
            text += f"🔑 <b>Ключ:</b> {region_data['key']}\n"
            text += f"📝 <b>Описание:</b> {region_data['description']}\n\n"
            text += "✅ Регион добавлен в конфигурацию\n"
            text += "📱 Теперь можно добавлять каналы в этот регион"
            
            keyboard = [
                [{"text": "➕ Добавить канал в регион", "callback_data": f"add_to_region_{region_data['key']}"}],
                [{"text": "🗂️ Управление каналами", "callback_data": "manage_channels"}],
                [{"text": "🏠 Главное меню", "callback_data": "start"}]
            ]
            
            await self.bot.keyboard_builder.send_message_with_keyboard(
                text, keyboard, use_reply_keyboard=False
            )
            
            self.bot.pending_region_data = None
            self.bot.waiting_for_region_name = False
            self.bot.waiting_for_emoji = False
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления о создании: {e}")
    
    async def _update_region_topic_id(self, region_key: str, topic_id: int) -> bool:
        try:
            config_path = "config/config.yaml"
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            if 'regions' not in config:
                config['regions'] = {}
            
            if region_key not in config['regions']:
                logger.error(f"❌ Регион {region_key} не найден в конфигурации")
                return False
            
            config['regions'][region_key]['topic_id'] = topic_id
            
            if 'output' not in config:
                config['output'] = {}
            if 'topics' not in config['output']:
                config['output']['topics'] = {}
            
            config['output']['topics'][region_key] = topic_id
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, indent=2, default_flow_style=False)
            
            logger.info(f"✅ Topic ID {topic_id} добавлен для региона {region_key}")
            
            await self._auto_commit_config(
                f"Add topic_id {topic_id} for region {region_key}",
                ["config/config.yaml"]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления topic_id: {e}")
            return False
    
    async def _load_regions_config(self) -> Dict:
        try:
            if self.bot.monitor_bot and hasattr(self.bot.monitor_bot, 'config_loader'):
                config_loader = self.bot.monitor_bot.config_loader
                return config_loader.get_regions_config()
            
            config_path = "config/config.yaml"
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get('regions', {})
                
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки конфигурации регионов: {e}")
            return {}
    
    async def _auto_commit_config(self, action_description: str, files_changed: List[str]):
        try:
            try:
                subprocess.run(["git", "--version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.debug("📝 Git не найден, пропускаем автокоммит")
                return True
            
            for file_path in files_changed:
                result = subprocess.run(
                    ["git", "add", file_path], 
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    logger.warning(f"⚠️ Не удалось добавить {file_path} в git")
            
            commit_message = f"Add new region: {action_description}"
            result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                logger.info(f"📝 Автокоммит: {action_description}")
            
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка автокоммита: {e}")
            return False
    