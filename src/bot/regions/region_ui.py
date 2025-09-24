from typing import Dict, List, Optional, Any
from loguru import logger


class RegionUI:
    
    def __init__(self, bot: "TelegramBot"):
        self.bot = bot
    
    async def show_emoji_selection(self, region_name: str):
        try:
            text = (
                f"🎨 <b>Выбор эмодзи для региона</b>\n\n"
                f"📍 <b>Регион:</b> {region_name}\n\n"
                "Выберите эмодзи из списка:"
            )
            
            keyboard = [
                [
                    {"text": "🌋", "callback_data": "emoji_🌋"},
                    {"text": "🏔️", "callback_data": "emoji_🏔️"},  
                    {"text": "🏝️", "callback_data": "emoji_🏝️"}
                ],
                [
                    {"text": "❄️", "callback_data": "emoji_❄️"},
                    {"text": "🌊", "callback_data": "emoji_🌊"},
                    {"text": "🌲", "callback_data": "emoji_🌲"}
                ],
                [
                    {"text": "🏙️", "callback_data": "emoji_🏙️"},
                    {"text": "🌅", "callback_data": "emoji_🌅"},
                    {"text": "🎯", "callback_data": "emoji_🎯"}
                ],
                [
                    {"text": "⭐", "callback_data": "emoji_⭐"},
                    {"text": "💎", "callback_data": "emoji_💎"},
                    {"text": "🔥", "callback_data": "emoji_🔥"}
                ],
                [{"text": "✏️ Ввести свой эмодзи", "callback_data": "custom_emoji"}],
                [{"text": "❌ Отмена", "callback_data": "region_cancel"}]
            ]
            
            await self.bot.keyboard_builder.send_message_with_keyboard(
                text, keyboard, use_reply_keyboard=False
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа выбора эмодзи: {e}")
    
    async def show_region_creation_confirmation(self, region_key: str, region_full_name: str, region_emoji: str, region_name: str):
        try:
            text = (
                f"✅ <b>Подтверждение создания региона</b>\n\n"
                f"🌍 <b>Название:</b> {region_full_name}\n"
                f"🔑 <b>Ключ:</b> {region_key}\n"
                f"📝 <b>Описание:</b> Регион {region_name}\n\n"
                "Создать этот регион?"
            )
            
            keyboard = [
                [{"text": "✅ Да, создать", "callback_data": f"create_region_confirmed_{region_key}"}],
                [{"text": "❌ Отмена", "callback_data": "region_cancel"}]
            ]
            
            self.bot.pending_region_data.update({
                'name': region_full_name,
                'emoji': region_emoji,
                'description': f"Регион {region_name}"
            })
            
            await self.bot.keyboard_builder.send_message_with_keyboard(
                text, keyboard, use_reply_keyboard=False
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа подтверждения региона: {e}")
    
    async def show_region_selection(self):
        try:
            regions_config = await self._load_regions_config()
            
            if not regions_config:
                await self.bot.send_message("❌ Регионы не настроены")
                return
            
            text = (
                "🌏 <b>Выбор региона для канала</b>\n\n"
                f"📺 <b>Канал:</b> @{self.bot.pending_channel_url}\n\n"
                "Выберите регион:"
            )
            
            keyboard = []
            for region_key, region_data in regions_config.items():
                emoji = region_data.get('emoji', '📍')
                name = region_data.get('name', region_key.title())
                
                display_name = name if name.startswith(emoji) else f"{emoji} {name}"
                
                keyboard.append([{
                    "text": display_name,
                    "callback_data": f"region_selected_{region_key}"
                }])
            
            keyboard.append([{
                "text": "➕ Создать новый регион",
                "callback_data": "create_new_region"
            }])
            
            await self.bot.keyboard_builder.send_message_with_keyboard(
                text, keyboard, use_reply_keyboard=False
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа выбора региона: {e}")
    
    async def show_multiple_channels_selection(self):
        try:
            text = (
                "📝 <b>Массовое добавление каналов</b>\n\n"
                "📋 Отправьте список каналов (по одному на строке):\n\n"
                "<b>Поддерживаемые форматы:</b>\n"
                "• <code>https://t.me/channel_name</code>\n"
                "• <code>@channel_name</code>\n"
                "• <code>channel_name</code>\n\n"
                "<b>Пример:</b>\n"
                "<code>@news_channel1\n"
                "https://t.me/news_channel2\n"
                "news_channel3</code>"
            )
            
            keyboard = [
                [{"text": "❌ Отмена", "callback_data": "start"}]
            ]
            
            await self.bot.keyboard_builder.send_message_with_keyboard(
                text, keyboard, use_reply_keyboard=False
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка интерфейса массового добавления: {e}")
    
    async def handle_emoji_selection(self, emoji: str):
        try:
            if not self.bot.pending_region_data:
                await self.bot.send_message("❌ Данные региона потеряны. Начните заново.")
                return
            
            region_key = self.bot.pending_region_data['key']
            region_name_clean = self.bot.pending_region_data['name_clean']
            region_full_name = f"{emoji} {region_name_clean}"
            
            await self.show_region_creation_confirmation(
                region_key, region_full_name, emoji, region_name_clean
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки выбора эмодзи: {e}")
    
    async def start_custom_emoji_input(self):
        try:
            text = (
                "✏️ <b>Ввод своего эмодзи</b>\n\n"
                "Отправьте один эмодзи для региона:\n\n"
                "<b>Примеры:</b>\n"
                "🌍 🗻 🏙️ 🌅 ⭐ 🔥 💎 🎯\n\n"
                "💡 Любой эмодзи на ваш выбор!"
            )
            
            keyboard = [[{"text": "❌ Отмена", "callback_data": "region_cancel"}]]
            
            success = await self.bot.keyboard_builder.edit_message_with_keyboard(text, keyboard, use_reply_keyboard=False)
            if not success:
                await self.bot.keyboard_builder.send_message_with_keyboard(text, keyboard, use_reply_keyboard=False)
            
            self.bot.waiting_for_emoji = True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска ввода эмодзи: {e}")
    
    async def handle_custom_emoji_input(self, emoji_input: str):
        try:
            emoji = emoji_input.strip()
            
            if not emoji or len(emoji) > 10:
                await self.bot.send_message(
                    "❌ Неверный эмодзи!\n\n"
                    "Отправьте один эмодзи для региона"
                )
                return
            
            if not self.bot.pending_region_data:
                await self.bot.send_message("❌ Данные региона потеряны. Начните заново.")
                return
            
            region_key = self.bot.pending_region_data['key']
            region_name_clean = self.bot.pending_region_data['name_clean']
            region_full_name = f"{emoji} {region_name_clean}"
            
            await self.show_region_creation_confirmation(
                region_key, region_full_name, emoji, region_name_clean
            )
            
            self.bot.waiting_for_emoji = False
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки пользовательского эмодзи: {e}")
    
    async def _load_regions_config(self) -> Dict:
        try:
            if self.bot.monitor_bot and hasattr(self.bot.monitor_bot, 'config_loader'):
                config_loader = self.bot.monitor_bot.config_loader
                return config_loader.get_regions_config()
            
            import yaml
            with open('config/config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get('regions', {})
                
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки конфигурации регионов: {e}")
            return {}
