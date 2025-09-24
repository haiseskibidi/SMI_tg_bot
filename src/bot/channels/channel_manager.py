"""
📺 Channel Manager
Логика управления каналами без UI
"""

import yaml
import os
from typing import Dict, List, Optional, Any
from loguru import logger
from datetime import datetime
from .channel_parser import ChannelParser


class ChannelManager:
    """Менеджер для управления каналами"""
    
    def __init__(self, bot: "TelegramBot"):
        self.bot = bot
        self.parser = ChannelParser()
    
    async def add_channel_handler(self, channel_link: str):
        """Обработка добавления канала по ссылке"""
        try:
            logger.info(f"➕ Обработка добавления канала: {channel_link}")
            
            # Парсинг ссылки
            channel_username = self.parser.parse_channel_username(channel_link)
            if not channel_username:
                await self.bot.send_message(
                    "❌ <b>Некорректная ссылка на канал</b>\n\n"
                    "Поддерживаемые форматы:\n"
                    "• <code>https://t.me/channel_name</code>\n"
                    "• <code>@channel_name</code>\n"
                    "• <code>channel_name</code>"
                )
                return
            
            # Проверка на дубликат
            if self.is_channel_already_added(channel_username):
                await self.bot.send_message(f"ℹ️ Канал @{channel_username} уже добавлен в мониторинг")
                return
            
            # Получение информации о канале
            channel_title = await self._get_channel_title(channel_username)
            
            # Сохранение для выбора региона
            self.bot.pending_channel_url = channel_username
            
            # Показ интерфейса выбора региона
            from ..ui.keyboard_builder import KeyboardBuilder
            keyboard_builder = KeyboardBuilder(self.bot)
            from ..channels.channel_ui import ChannelUI
            channel_ui = ChannelUI(self.bot)
            await channel_ui.show_channel_preview_and_region_selection(channel_username, channel_title)
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления канала: {e}")
            await self.bot.send_message(f"❌ Ошибка добавления канала: {e}")
    
    async def add_channel_to_config(self, channel_username: str, region: str = "general") -> bool:
        """Добавление канала в конфигурационный файл"""
        try:
            config_path = "config/channels_config.yaml"
            
            # Загрузка существующей конфигурации
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
            else:
                config = {}
            
            # Инициализация структуры
            if 'regions' not in config:
                config['regions'] = {}
            if region not in config['regions']:
                config['regions'][region] = {
                    'name': f'📍 {region.title()}',
                    'channels': []
                }
            
            # Проверка на дубликат
            existing_channels = config['regions'][region].get('channels', [])
            for channel in existing_channels:
                if channel.get('username') == channel_username:
                    logger.warning(f"⚠️ Канал @{channel_username} уже существует в регионе {region}")
                    return False
            
            # Добавление нового канала
            new_channel = {
                'title': f'Канал @{channel_username}',
                'username': channel_username
            }
            config['regions'][region]['channels'].append(new_channel)
            
            # Сохранение конфигурации
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, indent=2, default_flow_style=False)
            
            logger.info(f"✅ Канал @{channel_username} добавлен в регион {region}")
            
            # Автоматический коммит изменений
            await self._auto_commit_config(
                f"Add channel @{channel_username} to {region}",
                ["config/channels_config.yaml"]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления канала в конфиг: {e}")
            return False
    
    async def delete_channel_from_config(self, region_key: str, username: str) -> bool:
        """Удаление канала из конфигурации"""
        try:
            config_path = "config/channels_config.yaml"
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if 'regions' not in config or region_key not in config['regions']:
                return False
            
            channels = config['regions'][region_key].get('channels', [])
            original_count = len(channels)
            
            # Удаление канала
            config['regions'][region_key]['channels'] = [
                ch for ch in channels if ch.get('username') != username
            ]
            
            new_count = len(config['regions'][region_key]['channels'])
            
            if original_count == new_count:
                logger.warning(f"⚠️ Канал @{username} не найден в регионе {region_key}")
                return False
            
            # Сохранение обновленной конфигурации
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, indent=2, default_flow_style=False)
            
            logger.info(f"🗑️ Канал @{username} удален из региона {region_key}")
            
            # Автоматический коммит
            await self._auto_commit_config(
                f"Remove channel @{username} from {region_key}",
                ["config/channels_config.yaml"]  
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления канала: {e}")
            return False
    
    async def get_all_channels_grouped(self) -> Dict:
        """Получение всех каналов, сгруппированных по регионам"""
        try:
            config_path = "config/channels_config.yaml"
            
            if not os.path.exists(config_path):
                return {}
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config or 'regions' not in config:
                return {}
            
            # Обогащение данных из основной конфигурации
            main_config = await self._load_main_config()
            regions_info = main_config.get('regions', {})
            
            result = {}
            for region_key, region_data in config['regions'].items():
                channels = region_data.get('channels', [])
                
                # Получение метаданных региона
                region_info = regions_info.get(region_key, {})
                
                result[region_key] = {
                    'name': region_data.get('name') or region_info.get('name', f'📍 {region_key.title()}'),
                    'emoji': region_info.get('emoji', '📍'),
                    'channels': channels,
                    'count': len(channels)
                }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка каналов: {e}")
            return {}
    
    async def get_channels_from_config(self) -> Dict:
        """Получение конфигурации каналов"""
        try:
            config_path = "config/channels_config.yaml"
            
            if not os.path.exists(config_path):
                return {"channels": []}
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Преобразование в плоский список
            all_channels = []
            for region_key, region_data in config.get('regions', {}).items():
                channels = region_data.get('channels', [])
                for channel in channels:
                    channel_copy = channel.copy()
                    channel_copy['region'] = region_key
                    all_channels.append(channel_copy)
            
            return {"channels": all_channels}
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки конфигурации каналов: {e}")
            return {"channels": []}
    
    def is_channel_already_added(self, username: str) -> bool:
        """Проверка, добавлен ли канал уже в систему"""
        try:
            config_path = "config/channels_config.yaml"
            
            if not os.path.exists(config_path):
                return False
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            for region_key, region_data in config.get('regions', {}).items():
                channels = region_data.get('channels', [])
                for channel in channels:
                    if channel.get('username') == username:
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки канала: {e}")
            return False
    
    async def _get_channel_title(self, username: str) -> str:
        """Получение названия канала"""
        try:
            # Попытка получить название через monitor_bot
            if self.bot.monitor_bot and hasattr(self.bot.monitor_bot, 'telegram_monitor'):
                telegram_monitor = self.bot.monitor_bot.telegram_monitor
                if telegram_monitor and telegram_monitor.is_connected:
                    entity = await telegram_monitor.get_channel_entity(username)
                    if entity and hasattr(entity, 'title'):
                        return entity.title
            
            # Fallback название
            return f"Канал @{username}"
            
        except Exception as e:
            logger.warning(f"⚠️ Не удалось получить название канала @{username}: {e}")
            return f"Канал @{username}"
    
    async def _show_region_selection_for_channel(self, username: str, title: str):
        """Показ выбора региона для канала"""
        try:
            regions_config = await self._load_main_config()
            regions = regions_config.get('regions', {})
            
            if not regions:
                await self.bot.send_message("❌ Регионы не настроены в конфигурации")
                return
            
            # Автоопределение региона
            auto_region = self._detect_channel_region(title, username, regions)
            
            # Построение клавиатуры выбора
            keyboard = []
            for region_key, region_data in regions.items():
                emoji = region_data.get('emoji', '📍')
                name = region_data.get('name', region_key.title())
                
                # Отмечаем автоопределенный регион
                if region_key == auto_region:
                    name += " ⭐"
                
                display_name = name if name.startswith(emoji) else f"{emoji} {name}"
                
                keyboard.append([{
                    "text": display_name,
                    "callback_data": f"region_selected_{region_key}"
                }])
            
            # Кнопка создания нового региона
            keyboard.append([{
                "text": "➕ Создать новый регион",
                "callback_data": "create_new_region"
            }])
            
            text = f"🌏 <b>Выберите регион для канала:</b>\n\n📺 <b>{title}</b>\n@{username}"
            if auto_region:
                text += f"\n\n💡 Автоопределение: {regions[auto_region].get('name', auto_region)} ⭐"
            
            await self.bot.keyboard_builder.send_message_with_keyboard(
                text, keyboard, use_reply_keyboard=False
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа выбора региона: {e}")
            await self.bot.send_message(f"❌ Ошибка выбора региона: {e}")
    
    def _detect_channel_region(self, channel_title: str, username: str, regions: Dict) -> Optional[str]:
        """Автоопределение региона канала по ключевым словам"""
        try:
            title_lower = channel_title.lower()
            username_lower = username.lower()
            combined_text = f"{title_lower} {username_lower}"
            
            # Поиск по ключевым словам каждого региона
            for region_key, region_data in regions.items():
                keywords = region_data.get('keywords', [])
                for keyword in keywords:
                    if str(keyword).lower() in combined_text:
                        logger.info(f"🎯 Автоопределение региона: @{username} → {region_key} (по слову '{keyword}')")
                        return region_key
            
            logger.info(f"❓ Регион для @{username} не определен автоматически")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка автоопределения региона: {e}")
            return None
    
    async def _load_main_config(self) -> Dict:
        """Загрузка основной конфигурации"""
        try:
            config_path = "config/config.yaml"
            
            if not os.path.exists(config_path):
                return {}
            
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
                
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки основной конфигурации: {e}")
            return {}
    
    async def _auto_commit_config(self, action_description: str, files_changed: List[str] = None):
        """Автоматический коммит изменений конфигурации"""
        try:
            if not files_changed:
                files_changed = ["config/channels_config.yaml"]
            
            # Проверка наличия git
            import subprocess
            try:
                subprocess.run(["git", "--version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.debug("📝 Git не найден, пропускаем автокоммит")
                return True
            
            # Добавление файлов в git
            for file_path in files_changed:
                result = subprocess.run(
                    ["git", "add", file_path], 
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    logger.warning(f"⚠️ Не удалось добавить {file_path} в git: {result.stderr}")
            
            # Коммит изменений
            commit_message = f"Update configuration: {action_description}"
            result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                logger.info(f"📝 Автокоммит выполнен: {action_description}")
                return True
            else:
                logger.debug(f"📝 Нет изменений для коммита: {action_description}")
                return True
                
        except Exception as e:
            logger.warning(f"⚠️ Ошибка автокоммита: {e}")
            return False
    
    async def _show_region_selection_for_channel(self, username: str, title: str):
        """Показ интерфейса выбора региона"""
        # Эта логика будет перенесена в ChannelUI
        # Пока используем упрощенную версию
        await self.bot.send_message(
            f"🌏 <b>Выберите регион для канала:</b>\n\n"
            f"📺 <b>{title}</b>\n@{username}\n\n"
            "Используйте /manage_channels для выбора региона"
        )

