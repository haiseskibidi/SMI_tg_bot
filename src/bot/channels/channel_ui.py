"""
🎨 Channel UI
Пользовательский интерфейс для управления каналами
"""

from typing import Dict, List, Optional, Any
from loguru import logger


class ChannelUI:
    """Интерфейс управления каналами"""
    
    def __init__(self, bot: "TelegramBot"):
        self.bot = bot
    
    async def show_channels_management(self, channels_data: Dict, message: Optional[Dict] = None):
        """Главный интерфейс управления каналами"""
        try:
            text = "🗂️ <b>Управление каналами</b>\n\n"
            
            # Подсчет общей статистики
            total_channels = 0
            for region_data in channels_data.values():
                total_channels += len(region_data.get('channels', []))
            
            text += f"📊 <b>Всего каналов:</b> {total_channels}\n"
            text += f"📂 <b>Регионов:</b> {len(channels_data)}\n\n"
            
            # Создание кнопок по регионам
            keyboard = []
            
            for region_key, region_data in channels_data.items():
                region_name = region_data.get('name', f'📍 {region_key.title()}')
                channels_count = len(region_data.get('channels', []))
                
                button_text = f"{region_name} ({channels_count})"
                callback_data = f"manage_region_{region_key}"
                keyboard.append([{"text": button_text, "callback_data": callback_data}])
            
            # Кнопки управления
            keyboard.append([
                {"text": "➕ Добавить канал", "callback_data": "add_channel"},
                {"text": "🔄 Обновить", "callback_data": "refresh_channels"}
            ])
            keyboard.append([{"text": "🏠 Главное меню", "callback_data": "start"}])
            
            text += "👇 Выберите регион для управления каналами:"
            
            # Определение получателя
            chat_id = message.get("chat", {}).get("id") if message else self.bot.admin_chat_id
            to_group = self.bot.is_message_from_group(chat_id) if chat_id else None
            
            await self.bot.keyboard_builder.send_message_with_keyboard(
                text, keyboard, use_reply_keyboard=False, to_group=to_group
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка отображения управления каналами: {e}")
            await self.bot.send_message(f"❌ Ошибка интерфейса каналов: {e}")
    
    async def show_region_channels(self, region_key: str, page: int = 1):
        """Отображение каналов конкретного региона с пагинацией"""
        try:
            # Получение каналов региона
            channels_data = await self.bot.channel_manager.get_all_channels_grouped()
            
            if region_key not in channels_data:
                await self.bot.send_message(f"❌ Регион '{region_key}' не найден")
                return
            
            region_info = channels_data[region_key]
            region_name = region_info.get('name', f'📍 {region_key.title()}')
            channels = region_info.get('channels', [])
            
            if not channels:
                await self._show_empty_region(region_key, region_name)
                return
            
            # Пагинация
            channels_per_page = 10
            total_pages = (len(channels) + channels_per_page - 1) // channels_per_page
            
            # Валидация страницы
            if page < 1:
                page = 1
            elif page > total_pages:
                page = total_pages
            
            # Вычисление индексов для текущей страницы
            start_idx = (page - 1) * channels_per_page
            end_idx = min(start_idx + channels_per_page, len(channels))
            current_channels = channels[start_idx:end_idx]
            
            # Формирование текста
            text = f"📂 <b>{region_name}</b>\n\n"
            text += f"📊 <b>Каналов в регионе:</b> {len(channels)}\n"
            text += f"📄 <b>Страница:</b> {page} из {total_pages}\n\n"
            text += "📋 <b>Список каналов:</b>\n"
            
            keyboard = []
            for i, channel in enumerate(current_channels, start_idx + 1):
                username = channel.get('username', 'unknown')
                
                text += f"{i}. <a href=\"https://t.me/{username}\">@{username}</a>\n"
                
                button_text = f"🗑️ @{username[:15]}{'...' if len(username) > 15 else ''}"
                callback_data = f"delete_channel|{region_key}|{username}"
                keyboard.append([{"text": button_text, "callback_data": callback_data}])
            
            # Навигационные кнопки (если страниц больше 1)
            if total_pages > 1:
                nav_buttons = []
                
                if page > 1:
                    nav_buttons.append({
                        "text": f"⬅️ Стр. {page-1}",
                        "callback_data": f"manage_region_{region_key}_page_{page-1}"
                    })
                
                if page < total_pages:
                    nav_buttons.append({
                        "text": f"Стр. {page+1} ➡️",
                        "callback_data": f"manage_region_{region_key}_page_{page+1}"
                    })
                
                if nav_buttons:
                    keyboard.append(nav_buttons)
            
            # Кнопки навигации
            keyboard.append([
                {"text": "↩️ К списку регионов", "callback_data": "manage_channels"},
                {"text": "🏠 Главное меню", "callback_data": "start"}
            ])
            
            await self.bot.keyboard_builder.send_or_edit_message_with_keyboard(
                text, keyboard, should_edit=True
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка отображения каналов региона {region_key}: {e}")
            await self.bot.send_message(f"❌ Ошибка отображения региона: {e}")
    
    async def show_delete_confirmation(self, region_key: str, username: str):
        """Подтверждение удаления канала"""
        try:
            # Получение информации о канале
            channels_data = await self.bot.channel_manager.get_all_channels_grouped()
            
            region_info = channels_data.get(region_key, {})
            region_name = region_info.get('name', f'📍 {region_key.title()}')
            
            # Поиск информации о канале
            channel_title = f"@{username}"
            channels = region_info.get('channels', [])
            for channel in channels:
                if channel.get('username') == username:
                    channel_title = channel.get('title', f"@{username}")
                    break
            
            text = f"🗑️ <b>Удаление канала</b>\n\n"
            text += f"📂 <b>Регион:</b> {region_name}\n"
            text += f"📺 <b>Канал:</b> {channel_title}\n"
            text += f"🔗 <b>Username:</b> @{username}\n\n"
            text += "⚠️ <b>Вы уверены, что хотите удалить канал?</b>\n"
            text += "Канал будет удален из конфигурации и мониторинга."
            
            keyboard = [
                [{"text": "❌ Да, удалить", "callback_data": f"delete_channel_confirmed|{region_key}|{username}"}],
                [{"text": "↩️ Отмена", "callback_data": f"manage_region_{region_key}"}]
            ]
            
            await self.bot.keyboard_builder.send_message_with_keyboard(
                text, keyboard, use_reply_keyboard=False
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка отображения подтверждения удаления: {e}")
            await self.bot.send_message(f"❌ Ошибка подтверждения удаления: {e}")
    
    async def show_channel_preview_and_region_selection(self, channel_username: str, channel_title: str):
        """Превью канала и выбор региона"""
        try:
            # Загрузка конфигурации регионов
            regions_config = await self._load_regions_config()
            
            if not regions_config:
                await self.bot.send_message("❌ Регионы не настроены в конфигурации")
                return
            
            # Автоопределение региона
            auto_region = self._detect_channel_region(channel_title, channel_username, regions_config)
            
            # Формирование текста превью
            text = f"➕ <b>Добавление канала</b>\n\n"
            text += f"📄 <b>Название:</b> {channel_title}\n"
            text += f"🔗 <b>Username:</b> @{channel_username}\n\n"
            
            if auto_region:
                auto_region_info = regions_config.get(auto_region, {})
                auto_region_name = auto_region_info.get('name', auto_region.title())
                text += f"🎯 <b>Автоопределение:</b> {auto_region_name} ⭐\n\n"
            
            text += "🌏 <b>Выберите регион для канала:</b>"
            
            # Построение клавиатуры выбора
            keyboard = []
            for region_key, region_data in regions_config.items():
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
            
            keyboard.append([{
                "text": "❌ Отмена",
                "callback_data": "start"
            }])
            
            await self.bot.keyboard_builder.send_message_with_keyboard(
                text, keyboard, use_reply_keyboard=False
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа превью канала: {e}")
            await self.bot.send_message(f"❌ Ошибка превью канала: {e}")
    
    async def show_multiple_channels_selection(self):
        try:
            channels_list = self.bot.pending_channels_list
            if not channels_list:
                await self.bot.send_message("❌ Список каналов пуст")
                return
            
            channels_text = f"📺 <b>Найдено {len(channels_list)} каналов:</b>\n\n"
            for i, channel in enumerate(channels_list, 1):
                channels_text += f"  {i}. @{channel}\n"
            
            channels_text += "\n📂 <b>Выберите регион для всех каналов:</b>"
            
            regions = await self._load_regions_config()
            
            keyboard = []
            row = []
            for i, (region_key, region_info) in enumerate(regions.items()):
                emoji = region_info.get('emoji', '📍')
                region_name = region_info.get('name', region_key.title())
                
                if not region_name.startswith(emoji):
                    display_name = f"{emoji} {region_name}"
                else:
                    display_name = region_name
                
                callback_data = f"region_bulk_{region_key}"
                row.append({"text": display_name, "callback_data": callback_data})
                
                if len(row) == 2 or i == len(regions) - 1:
                    keyboard.append(row)
                    row = []
            
            keyboard.extend([
                [{"text": "➕ Создать новый регион", "callback_data": "create_new_region"}],
                [{"text": "❌ Отмена", "callback_data": "manage_channels"}],
                [{"text": "🏠 Главное меню", "callback_data": "start"}]
            ])
            
            await self.bot.keyboard_builder.send_message_with_keyboard(
                channels_text, keyboard, use_reply_keyboard=False
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка интерфейса массового добавления: {e}")
    
    async def show_channel_added_success(self, username: str, region: str, region_name: str):
        """Уведомление об успешном добавлении канала"""
        try:
            text = f"✅ <b>Канал успешно добавлен!</b>\n\n"
            text += f"📺 <b>Канал:</b> @{username}\n"
            text += f"🌍 <b>Регион:</b> {region_name}\n\n"
            text += "🔄 Система автоматически подпишется на канал при следующем обновлении"
            
            keyboard = [
                [{"text": "➕ Добавить еще канал", "callback_data": "add_channel"}],
                [{"text": "🗂️ Управление каналами", "callback_data": "manage_channels"}],
                [{"text": "🏠 Главное меню", "callback_data": "start"}]
            ]
            
            await self.bot.keyboard_builder.send_message_with_keyboard(
                text, keyboard, use_reply_keyboard=False
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления об успехе: {e}")
    
    async def show_channel_delete_success(self, username: str, region_key: str, region_name: str):
        """Уведомление об успешном удалении канала"""
        try:
            text = f"🗑️ <b>Канал успешно удален!</b>\n\n"
            text += f"📺 <b>Канал:</b> @{username}\n"
            text += f"🌍 <b>Регион:</b> {region_name}\n\n"
            text += "ℹ️ Канал удален из конфигурации и мониторинга"
            
            keyboard = [
                [{"text": "↩️ Назад к региону", "callback_data": f"manage_region_{region_key}"}],
                [{"text": "🗂️ Управление каналами", "callback_data": "manage_channels"}],
                [{"text": "🏠 Главное меню", "callback_data": "start"}]
            ]
            
            await self.bot.keyboard_builder.send_message_with_keyboard(
                text, keyboard, use_reply_keyboard=False
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления об удалении: {e}")
    
    async def show_add_channel_help(self):
        """Справка по добавлению каналов"""
        try:
            text = (
                "➕ <b>Добавление канала</b>\n\n"
                "📝 <b>Отправьте ссылку на канал в любом формате:</b>\n\n"
                "🔗 <b>Поддерживаемые форматы:</b>\n"
                "• <code>https://t.me/channel_name</code>\n"
                "• <code>@channel_name</code>\n"
                "• <code>tg://resolve?domain=channel_name</code>\n\n"
                "🌍 После отправки ссылки вы сможете выбрать регион для канала\n\n"
                "💡 <b>Примеры:</b>\n"
                "• <code>https://t.me/news_kamchatka</code>\n"
                "• <code>@sakhalin_news</code>"
            )
            
            keyboard = [
                [{"text": "🗂️ Управление каналами", "callback_data": "manage_channels"}],
                [{"text": "🏠 Главное меню", "callback_data": "start"}]
            ]
            
            await self.bot.keyboard_builder.send_message_with_keyboard(
                text, keyboard, use_reply_keyboard=False
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка справки по добавлению: {e}")
    
    async def _show_empty_region(self, region_key: str, region_name: str):
        """Отображение пустого региона"""
        try:
            text = f"📂 <b>{region_name}</b>\n\n"
            text += "📭 <b>В этом регионе пока нет каналов</b>\n\n"
            text += "Добавьте первый канал для мониторинга!"
            
            keyboard = [
                [{"text": "➕ Добавить канал", "callback_data": f"add_to_region_{region_key}"}],
                [{"text": "↩️ К списку регионов", "callback_data": "manage_channels"}],
                [{"text": "🏠 Главное меню", "callback_data": "start"}]
            ]
            
            await self.bot.keyboard_builder.send_message_with_keyboard(
                text, keyboard, use_reply_keyboard=False
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка отображения пустого региона: {e}")
    
    async def show_region_stats(self, region_key: str):
        """Статистика каналов региона"""
        try:
            # Получение данных из базы через monitor_bot
            if not self.bot.monitor_bot or not self.bot.monitor_bot.database:
                await self.bot.send_message("❌ База данных недоступна для статистики")
                return
            
            # Получение каналов региона
            channels_data = await self.bot.channel_manager.get_all_channels_grouped()
            region_info = channels_data.get(region_key, {})
            region_name = region_info.get('name', f'📍 {region_key.title()}')
            channels = region_info.get('channels', [])
            
            if not channels:
                await self.bot.send_message(f"📊 В регионе {region_name} нет каналов для статистики")
                return
            
            text = f"📊 <b>Статистика региона {region_name}</b>\n\n"
            text += f"📂 <b>Каналов в регионе:</b> {len(channels)}\n\n"
            
            # Статистика по каналам (упрощенная версия)
            text += "📋 <b>Активность каналов за сегодня:</b>\n"
            
            active_count = 0
            for channel in channels[:10]:  # Показываем первые 10
                username = channel.get('username')
                try:
                    # Простой подсчет сообщений (можно расширить)
                    count = 0  # Здесь мог бы быть запрос к БД
                    status = "🟢" if count > 0 else "⚪"
                    text += f"{status} @{username}: {count} сообщений\n"
                    if count > 0:
                        active_count += 1
                except:
                    text += f"⚪ @{username}: данные недоступны\n"
            
            if len(channels) > 10:
                text += f"... и еще {len(channels) - 10} каналов\n"
            
            text += f"\n📈 <b>Активных каналов:</b> {active_count}/{len(channels)}"
            
            keyboard = [
                [{"text": "🔄 Обновить статистику", "callback_data": f"region_stats_{region_key}"}],
                [{"text": "↩️ К каналам региона", "callback_data": f"manage_region_{region_key}"}],
                [{"text": "🏠 Главное меню", "callback_data": "start"}]
            ]
            
            await self.bot.keyboard_builder.send_message_with_keyboard(
                text, keyboard, use_reply_keyboard=False
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка статистики региона: {e}")
            await self.bot.send_message(f"❌ Ошибка получения статистики: {e}")
    
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
                        logger.info(f"🎯 Автоопределение: @{username} → {region_key} (по '{keyword}')")
                        return region_key
            
            logger.info(f"❓ Регион для @{username} не определен автоматически")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка автоопределения региона: {e}")
            return None
    
    async def _load_regions_config(self) -> Dict:
        """Загрузка конфигурации регионов"""
        try:
            if self.bot.monitor_bot and hasattr(self.bot.monitor_bot, 'config_loader'):
                config_loader = self.bot.monitor_bot.config_loader
                return config_loader.get_regions_config()
            
            # Fallback - прямое чтение файла
            import yaml
            with open('config/config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get('regions', {})
                
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки конфигурации регионов: {e}")
            return {}
