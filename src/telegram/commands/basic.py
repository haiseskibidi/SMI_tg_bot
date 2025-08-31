from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING
from datetime import datetime
import pytz
import asyncio
from loguru import logger

if TYPE_CHECKING:
    from src.telegram_bot import TelegramBot


class BasicCommands:
    def __init__(self, bot: "TelegramBot") -> None:
        self.bot = bot
        self.digest_generator = None
        # Инициализируем генератор дайджестов
        self._init_digest_generator()

    async def start(self, message: Optional[Dict[str, Any]]) -> None:
        chat_id = message.get("chat", {}).get("id") if message else self.bot.admin_chat_id
        to_group = self.bot.is_message_from_group(chat_id) if chat_id else None

        keyboard = [
            [{"text": "📊 Статус", "callback_data": "status"}, {"text": "🗂️ Управление каналами", "callback_data": "manage_channels"}],
            [{"text": "➕ Добавить канал", "callback_data": "add_channel"}, {"text": "📡 Принудительная подписка", "callback_data": "force_subscribe"}],
            [{"text": "🚀 Запуск", "callback_data": "start_monitoring"}, {"text": "🛑 Стоп", "callback_data": "stop_monitoring"}],
            [{"text": "🔄 Рестарт", "callback_data": "restart"}, {"text": "⚙️ Настройки", "callback_data": "settings"}],
            [{"text": "📰 Дайджест", "callback_data": "digest"}, {"text": "🆘 Справка", "callback_data": "help"}],
        ]

        welcome_text = (
            "🤖 <b>Панель управления ботом мониторинга новостей</b>\n\n"
            "📋 <b>Доступные команды:</b>\n"
            "📊 /status - статус системы\n"
            "🗂️ /manage_channels - управление каналами\n"
            "➕ /add_channel - добавить канал\n"
            "🚀 /start_monitoring - запустить мониторинг\n"
            "🛑 /stop - остановить мониторинг\n"
            "🔄 /restart - перезапуск системы\n"
            "📰 /digest - дайджест топ новостей\n"
            "🛑 /kill_switch - полная блокировка\n"
            "🔓 /unlock - разблокировать бота\n"
            "📂 /topic_id - узнать ID темы в группе\n"
            "📡 /force_subscribe - принудительная подписка на каналы\n"
            "⚙️ /settings - настройки интерфейса\n\n"
            "⌨️ <b>Или используйте кнопки ниже:</b>\n\n"
            "⚠️ <b>В группе:</b> пишите команды в чат напрямую, не отвечайте на сообщения бота!"
        )

        await self.bot.remove_old_keyboard(to_group)
        await self.bot.send_message_with_keyboard(welcome_text, keyboard, use_reply_keyboard=False, to_group=to_group)

    async def help(self, message: Optional[Dict[str, Any]]) -> None:
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
            "• ➕ Добавить канал - помощь по добавлению\n"
            "• 📡 Принудительная подписка - подключить каналы\n"
            "• 📰 Дайджест - топ новостей за период\n"
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
        await self.bot.edit_message_with_keyboard(help_text, keyboard, use_reply_keyboard=False, chat_id=self.bot.current_callback_chat_id)

    async def status(self, message: Optional[Dict[str, Any]]) -> None:
        if self.bot.monitor_bot and hasattr(self.bot.monitor_bot, "monitoring_active"):
            is_running = self.bot.monitor_bot.monitoring_active
        else:
            is_running = True

        monitoring_status = "🟢 Работает" if is_running else "🔴 Остановлен"
        monitoring_emoji = "📡" if is_running else "⏹️"

        try:
            channels = await self.bot.get_channels_from_config()  # type: ignore[attr-defined]
            channels_count = len(channels)
        except Exception:
            channels_count = 0

        active_channels_count = 0
        latest_message_info = {
            'channel_name': 'Нет данных',
            'text_preview': 'Сообщений пока нет'
        }

        if self.bot.monitor_bot and hasattr(self.bot.monitor_bot, 'database'):
            try:
                active_channels_count = await self.bot.monitor_bot.database.get_active_channels_count()
                latest_message_info = await self.bot.monitor_bot.database.get_latest_message_info()
            except Exception as e:
                logger.warning(f"⚠️ Не удалось получить расширенную статистику: {e}")

        status_text = (
            "📊 <b>Статус системы мониторинга</b>\n\n"
            f"🔄 <b>Панель управления:</b> 🟢 Активна\n"
            f"{monitoring_emoji} <b>Мониторинг новостей:</b> {monitoring_status}\n"
            f"📺 <b>Каналов добавлено:</b> {channels_count}\n"
            f"📡 <b>Активно за 24ч:</b> {active_channels_count}\n\n"
        )

        if latest_message_info['channel_name'] != 'Нет данных':
            status_text += (
                f"📰 <b>Последнее сообщение:</b>\n"
                f"📣 Канал: {latest_message_info['channel_name']}\n"
                f"💬 Текст: {latest_message_info['text_preview']}\n\n"
            )

        if is_running:
            status_text += "💡 <b>Состояние:</b> Отслеживание активно\n\n"
        else:
            status_text += "💡 <b>Состояние:</b> Для запуска нажмите 🚀 Запуск\n\n"

        vladivostok_tz = pytz.timezone("Asia/Vladivostok")
        current_time = datetime.now(vladivostok_tz).strftime("%d.%m.%Y %H:%M:%S")
        status_text += f"🕐 {current_time} (Владивосток)"

        keyboard = [
            [{"text": "🗂️ Управление каналами", "callback_data": "manage_channels"}],
            [{"text": "🏠 Главное меню", "callback_data": "start"}],
        ]

        chat_id = message.get("chat", {}).get("id") if message else self.bot.admin_chat_id
        to_group = self.bot.is_message_from_group(chat_id) if chat_id else None
        await self.bot.send_message_with_keyboard(status_text, keyboard, use_reply_keyboard=False, to_group=to_group)

    async def start_monitoring(self, message: Optional[Dict[str, Any]]) -> None:
        keyboard = [["🛑 Стоп", "📊 Статус"], ["🏠 Главное меню"]]
        if not self.bot.monitor_bot:
            await self.bot.send_message_with_keyboard("❌ <b>Ошибка</b>\n\nНет доступа к системе мониторинга", keyboard)
            return
        if self.bot.monitor_bot.monitoring_active:
            await self.bot.send_message_with_keyboard(
                "⚠️ <b>Мониторинг уже работает</b>\n\nИспользуйте кнопку 🛑 для остановки",
                keyboard,
            )
            return
        await self.bot.monitor_bot.resume_monitoring()
        vladivostok_tz = pytz.timezone("Asia/Vladivostok")
        current_time = datetime.now(vladivostok_tz).strftime("%d.%m.%Y %H:%M:%S")
        await self.bot.send_message_with_keyboard(
            "🚀 <b>Система мониторинга запущена!</b>\n\n"
            "📱 <b>Telegram бот:</b> ✅ Активен\n"
            "🗄️ <b>База данных:</b> ✅ Подключена\n"
            "🧠 <b>ИИ анализатор:</b> ✅ Готов\n"
            "📺 <b>Мониторинг каналов:</b> ✅ Активен\n"
            "🌐 <b>Веб-интерфейс:</b> ✅ http://localhost:8080\n\n"
            f"🕐 {current_time} (Владивосток)",
            keyboard,
        )

    async def stop_monitoring(self, message: Optional[Dict[str, Any]]) -> None:
        keyboard = [["🚀 Запуск", "📊 Статус"], ["🏠 Главное меню"]]
        if not self.bot.monitor_bot:
            await self.bot.send_message_with_keyboard("❌ <b>Ошибка</b>\n\nНет доступа к системе мониторинга", keyboard)
            return
        if not self.bot.monitor_bot.monitoring_active:
            await self.bot.send_message_with_keyboard(
                "⚠️ <b>Мониторинг уже остановлен</b>\n\nИспользуйте кнопку 🚀 для запуска",
                keyboard,
            )
            return
        await self.bot.monitor_bot.pause_monitoring()
        vladivostok_tz = pytz.timezone("Asia/Vladivосток")
        current_time = datetime.now(vladivostok_tz).strftime("%d.%m.%Y %H:%M:%S")
        await self.bot.send_message_with_keyboard(
            "🛑 <b>Система мониторинга остановлена</b>\n\n"
            f"🕐 {current_time} (Владивосток)",
            keyboard,
        )

    async def restart(self, message: Optional[Dict[str, Any]]) -> None:
        keyboard = [["🏠 Главное меню"]]
        vladivostok_tz = pytz.timezone("Asia/Vladivostok")
        current_time = datetime.now(vladivostok_tz).strftime("%d.%m.%Y %H:%M:%S")
        await self.bot.send_message_with_keyboard(
            "🔄 <b>Перезапуск системы...</b>\n\n"
            "🔄 Останавливаем мониторинг...\n"
            "💾 Сохраняем данные...\n"
            "🚀 Запускаем новый процесс...\n\n"
            f"🕐 {current_time} (Владивосток)\n\n"
            "⏳ <i>Пожалуйста, подождите несколько секунд...</i>",
            keyboard,
        )
        await asyncio.sleep(2)
        import os
        import sys
        os.execv(sys.executable, ["python"] + sys.argv)

    async def kill_switch(self, message: Optional[Dict[str, Any]]) -> None:
        """Создать файл полной блокировки бота"""
        try:
            keyboard = [
                ["✅ ДА, ЗАБЛОКИРОВАТЬ", "❌ Отмена"],
                ["🏠 Главное меню"]
            ]
            await self.bot.send_message_with_keyboard(
                "🛑 <b>KILL SWITCH - Полная блокировка</b>\n\n"
                "⚠️ <b>ВНИМАНИЕ!</b> Эта команда:\n"
                "• Остановит бота НАВСЕГДА\n"
                "• Заблокирует любые автоперезапуски\n"
                "• Потребует ручной разблокировки через /unlock\n\n"
                "🤔 <b>Вы действительно хотите заблокировать бота?</b>",
                keyboard,
            )
        except Exception as e:
            await self.bot.send_message(f"❌ Ошибка Kill Switch: {e}")

    async def unlock(self, message: Optional[Dict[str, Any]]) -> None:
        """Разблокировать бота (удалить файл STOP_BOT)"""
        try:
            import os
            stop_file = "STOP_BOT"
            
            if os.path.exists(stop_file):
                os.remove(stop_file)
                keyboard = [["🏠 Главное меню"]]
                vladivostok_tz = pytz.timezone("Asia/Vladivосток")
                current_time = datetime.now(vladivostok_tz).strftime("%d.%m.%Y %H:%M:%S")
                await self.bot.send_message_with_keyboard(
                    "🔓 <b>БОТ РАЗБЛОКИРОВАН!</b>\n\n"
                    "✅ Файл блокировки удален\n"
                    "✅ Бот готов к запуску\n\n"
                    f"🕐 {current_time} (Владивосток)\n\n"
                    "💡 <i>Systemd может автоматически перезапустить бота</i>",
                    keyboard,
                )
            else:
                keyboard = [["🏠 Главное меню"]]
                await self.bot.send_message_with_keyboard(
                    "ℹ️ <b>Бот не заблокирован</b>\n\n"
                    "Файл блокировки STOP_BOT отсутствует",
                    keyboard,
                )
        except Exception as e:
            await self.bot.send_message(f"❌ Ошибка разблокировки: {e}")

    def _init_digest_generator(self):
        """Инициализация генератора дайджестов"""
        try:
            logger.debug(f"🔍 Проверяем доступ к monitor_bot: {self.bot.monitor_bot}")
            
            if self.bot.monitor_bot:
                logger.debug(f"🔍 Monitor_bot найден, проверяем database: {hasattr(self.bot.monitor_bot, 'database')}")
                
                if hasattr(self.bot.monitor_bot, 'database'):
                    logger.debug(f"🔍 Database найдена: {self.bot.monitor_bot.database}")
                    
                    from src.digest_generator import DigestGenerator
                    self.digest_generator = DigestGenerator(self.bot.monitor_bot.database)
                    logger.info("✅ Генератор дайджестов инициализирован успешно")
                else:
                    logger.warning("⚠️ У monitor_bot нет атрибута 'database'")
            else:
                logger.warning("⚠️ monitor_bot равен None")
                
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации генератора дайджестов: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")

    async def digest(self, message: Optional[Dict[str, Any]]) -> None:
        """Генерация дайджеста топ новостей"""
        try:
            logger.info("📰 Вызов команды digest")
            
            if not self.digest_generator:
                logger.warning("⚠️ Генератор дайджестов не инициализирован, пытаемся повторно")
                self._init_digest_generator()
            
            if not self.digest_generator:
                error_msg = "❌ Генератор дайджестов недоступен\n\n"
                if not self.bot.monitor_bot:
                    error_msg += "Причина: Monitor bot не инициализирован"
                elif not hasattr(self.bot.monitor_bot, 'database'):
                    error_msg += "Причина: База данных не найдена"
                else:
                    error_msg += "Причина: Неизвестная ошибка инициализации"
                
                await self.bot.send_message(error_msg)
                return

            # Разбираем параметры команды если есть
            command_text = message.get("text", "") if message else ""
            params = command_text.split()[1:] if command_text else []
            
            days = 7  # по умолчанию неделя
            custom_start = None
            custom_end = None
            
            # Парсим параметры
            if len(params) == 1:
                try:
                    days = int(params[0])
                except ValueError:
                    pass
            elif len(params) == 2:
                try:
                    custom_start = params[0]
                    custom_end = params[1]
                except ValueError:
                    pass

            # Получаем список каналов с новостями  
            available_channels = await self.digest_generator.get_available_channels(days)
            
            if not available_channels:
                await self.bot.send_message("❌ Каналы с новостями не найдены")
                return

            # Показываем меню выбора канала (топ-10 самых активных)
            keyboard = []
            
            # Добавляем "Все каналы" как первую опцию
            keyboard.append([{"text": "🌍 Все каналы", "callback_data": f"digest_all_channels_{days}"}])
            
            # Добавляем топ каналов (максимум 8)
            for i, channel in enumerate(available_channels[:8]):
                name = channel['name'][:25] + "..." if len(channel['name']) > 25 else channel['name']
                emoji = "📺"
                
                # Показываем количество сообщений для понимания
                msg_count = channel['messages_count']
                text = f"{emoji} {name} ({msg_count})"
                
                keyboard.append([{"text": text, "callback_data": f"digest_channel_{channel['username']}_{days}"}])
            
            keyboard.append([{"text": "🏠 Главное меню", "callback_data": "start"}])

            channel_text = "📰 <b>Выберите канал для дайджеста:</b>\n\n"
            channel_text += f"📅 Период: {days} дней\n"
            channel_text += f"📊 Найдено каналов: {len(available_channels)}\n\n"
            channel_text += "💡 <b>Примеры команд:</b>\n"
            channel_text += "• <code>/digest</code> - неделя, все каналы\n"
            channel_text += "• <code>/digest 14</code> - 14 дней\n"
            channel_text += "• <code>/digest 2025-01-01 2025-01-07</code> - свой период"

            await self.bot.send_message_with_keyboard(channel_text, keyboard)

        except Exception as e:
            logger.error(f"❌ Ошибка команды digest: {e}")
            await self.bot.send_message(f"❌ Ошибка генерации дайджеста: {e}")

    async def generate_digest_for_channel(self, channel: Optional[str], days: int = 7) -> str:
        """Генерация дайджеста для конкретного канала"""
        try:
            if not self.digest_generator:
                self._init_digest_generator()
            
            if not self.digest_generator:
                return "❌ Генератор дайджестов недоступен"

            # Генерируем дайджест
            digest_text = await self.digest_generator.generate_weekly_digest(
                channel=channel,
                days=days,
                limit=10
            )
            
            return digest_text

        except Exception as e:
            logger.error(f"❌ Ошибка генерации дайджеста для канала {channel}: {e}")
            return f"❌ Не удалось сгенерировать дайджест: {e}"

    async def topic_id(self, message: Optional[Dict[str, Any]]) -> None:
        chat = message.get("chat", {}) if message else {}
        chat_type = chat.get("type")
        chat_title = chat.get("title", "Неизвестная группа")
        chat_id = chat.get("id")
        thread_id = message.get("message_thread_id") if message else None

        if chat_type not in ["group", "supergroup"]:
            await self.bot.send_message(
                "❌ <b>Эта команда работает только в группах</b>\n\n"
                "Отправьте команду /topic_id в нужной теме группы"
            )
            return

        self.bot.pending_topic_data = {  # type: ignore[attr-defined]
            "chat_title": chat_title,
            "chat_id": chat_id,
            "thread_id": thread_id,
        }

        if not thread_id:
            response_text = (
                f"🎯 <b>ID ТЕМЫ ПОЛУЧЕН!</b>\n\n"
                f"📂 <b>Группа:</b> {chat_title}\n"
                f"🏠 <b>Chat ID:</b> <code>{chat_id}</code>\n"
                f"📋 <b>Тема:</b> Общая лента (главная)\n"
                f"🆔 <b>Topic ID:</b> <code>null</code>\n\n"
                f"📝 <b>Ручная настройка:</b>\n"
                f"<code>general: null</code>"
            )
            keyboard = [
                [{"text": "🤖 Автоматически добавить в конфиг", "callback_data": "auto_add_topic_general"}],
                [{"text": "📋 Только показать информацию", "callback_data": "no_action"}],
            ]
        else:
            response_text = (
                f"🎯 <b>ID ТЕМЫ ПОЛУЧЕН!</b>\n\n"
                f"📂 <b>Группа:</b> {chat_title}\n"
                f"🏠 <b>Chat ID:</b> <code>{chat_id}</code>\n"
                f"📋 <b>Тема:</b> Текущая тема\n"
                f"🆔 <b>Topic ID:</b> <code>{thread_id}</code>\n\n"
                f"📝 <b>Выберите регион для автоматического добавления:</b>"
            )
            regions = await self.bot.load_regions_from_config()  # type: ignore[attr-defined]
            keyboard = [[{"text": f"{r['emoji']} {r['name']}", "callback_data": f"auto_add_topic_{r['key']}"}] for r in regions]
            keyboard.append([{"text": "📋 Только показать информацию", "callback_data": "no_action"}])

        await self.bot.send_message_with_keyboard(response_text, keyboard, use_reply_keyboard=False)


