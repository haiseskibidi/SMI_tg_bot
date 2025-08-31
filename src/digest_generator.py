"""
📰 Digest Generator Module
Модуль для генерации дайджестов топ-новостей за период
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from loguru import logger
import pytz


class DigestGenerator:
    """Генератор дайджестов новостей"""
    
    def __init__(self, database_manager, telegram_monitor=None):
        self.db = database_manager
        self.telegram_monitor = telegram_monitor
        self.vladivostok_tz = pytz.timezone("Asia/Vladivostok")
    
    async def generate_weekly_digest(
        self, 
        region: Optional[str] = None,
        channel: Optional[str] = None,
        days: int = 7,
        limit: int = 10,
        custom_start_date: Optional[str] = None,
        custom_end_date: Optional[str] = None
    ) -> str:
        """
        Генерировать недельный дайджест топ-новостей
        
        Args:
            region: Регион для фильтрации (None = все регионы) 
            channel: Конкретный канал для фильтрации (приоритет над region)
            days: Количество дней назад (по умолчанию 7)
            limit: Максимальное количество новостей (по умолчанию 10)
            custom_start_date: Начальная дата в формате 'YYYY-MM-DD'
            custom_end_date: Конечная дата в формате 'YYYY-MM-DD'
        """
        try:
            # Определяем период
            if custom_start_date and custom_end_date:
                start_date = datetime.strptime(custom_start_date, '%Y-%m-%d')
                end_date = datetime.strptime(custom_end_date, '%Y-%m-%d')
            else:
                end_date = datetime.now(self.vladivostok_tz)
                start_date = end_date - timedelta(days=days)
            
            # Форматируем даты для отображения
            start_formatted = start_date.strftime('%d.%m.%Y')
            end_formatted = end_date.strftime('%d.%m.%Y')
            
            # Получаем топ новости
            top_news = await self.db.get_top_news_for_period(
                start_date=start_date,
                end_date=end_date,
                region=region,
                channel=channel,
                limit=limit
            )
            
            if not top_news:
                return self._generate_empty_digest(start_formatted, end_formatted, region, channel)
            
            # Генерируем текст дайджеста
            digest_text = self._format_digest(
                top_news, 
                start_formatted, 
                end_formatted, 
                region,
                channel
            )
            
            logger.info(f"📰 Дайджест сгенерирован: {len(top_news)} новостей за {start_formatted}-{end_formatted}")
            return digest_text
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации дайджеста: {e}")
            return "❌ Не удалось сгенерировать дайджест. Попробуйте позже."
    
    def _format_digest(
        self, 
        news_list: List[Dict[str, Any]], 
        start_date: str, 
        end_date: str, 
        region: Optional[str],
        channel: Optional[str] = None
    ) -> str:
        """Форматирование дайджеста в нужный вид"""
        
        # Заголовок
        if channel:
            channel_text = f" из канала @{channel}"
            header = f"📰 Собрали топ самых обсуждаемых новостей{channel_text} за неделю\n"
        elif region:
            region_text = f" в регионе {region}"
            header = f"📰 Собрали топ самых обсуждаемых новостей{region_text} за неделю\n"
        else:
            header = f"📰 Собрали топ самых обсуждаемых новостей за неделю\n"
        
        header += f"📅 Период: {start_date} - {end_date}\n\n"
        
        # Новости
        news_items = []
        for news in news_list:
            # Формируем ссылку на сообщение
            link = self._create_message_link(news)
            
            # Ограничиваем длину заголовка
            title = news.get('text', 'Без заголовка')[:100]
            if len(title) == 100:
                title += "..."
            
            # Статистика
            views = news.get('views', 0)
            forwards = news.get('forwards', 0)
            popularity = views + forwards * 2  # Пересылки важнее просмотров
            
            news_item = f"⚡️ {title}"
            if link:
                news_item += f" ({link})"
            
            # Добавляем статистику если есть
            if popularity > 0:
                news_item += f" [{popularity} реакций]"
            
            news_items.append(news_item)
        
        # Заключение
        footer = "\n\nЭти новости собрали больше всего реакций и комментариев от наших читателей. А вам что больше всего запомнилось?"
        
        return header + "\n".join(news_items) + footer
    
    def _create_message_link(self, news: Dict[str, Any]) -> Optional[str]:
        """Создание ссылки на сообщение в Telegram"""
        try:
            channel_username = news.get('channel_username')
            message_id = news.get('message_id')
            
            if not channel_username or not message_id:
                return None
            
            # Убираем @ если есть
            if channel_username.startswith('@'):
                channel_username = channel_username[1:]
            
            return f"https://t.me/{channel_username}/{message_id}"
            
        except Exception as e:
            logger.warning(f"⚠️ Не удалось создать ссылку: {e}")
            return None
    
    def _generate_empty_digest(self, start_date: str, end_date: str, region: Optional[str], channel: Optional[str] = None) -> str:
        """Генерация сообщения при отсутствии новостей"""
        if channel:
            source_text = f" из канала @{channel}"
        elif region:
            source_text = f" в регионе {region}"
        else:
            source_text = ""
        
        return (
            f"📰 Дайджест новостей{source_text}\n"
            f"📅 Период: {start_date} - {end_date}\n\n"
            "🤷‍♂️ За указанный период новостей не найдено.\n\n"
            "Попробуйте:\n"
            "• Увеличить период поиска\n"
            "• Выбрать другой канал/регион\n"
            "• Проверить позже"
        )
    
    async def get_available_regions(self) -> List[str]:
        """Получить список доступных регионов"""
        try:
            return await self.db.get_regions_with_news()
        except Exception as e:
            logger.error(f"❌ Ошибка получения регионов: {e}")
            return []

    async def get_available_channels(self, days: int = 30) -> List[Dict[str, Any]]:
        """Получить список доступных каналов с новостями"""
        try:
            return await self.db.get_channels_with_news(days)
        except Exception as e:
            logger.error(f"❌ Ошибка получения каналов: {e}")
            return []
    
    def format_period_selection(self) -> str:
        """Форматирование сообщения для выбора периода"""
        return (
            "📅 <b>Выберите период для дайджеста:</b>\n\n"
            "• <code>7 дней</code> - последняя неделя (по умолчанию)\n"
            "• <code>14 дней</code> - последние 2 недели\n"
            "• <code>30 дней</code> - последний месяц\n"
            "• <code>Свой период</code> - укажите даты\n\n"
            "Или отправьте команду:\n"
            "<code>/digest 14</code> - для 14 дней\n"
            "<code>/digest 2025-01-01 2025-01-07</code> - для своего периода"
        )

    async def generate_channel_digest_live(
        self, 
        channel_username: str,
        days: int = 7,
        limit: int = 10,
        custom_start_date: Optional[str] = None,
        custom_end_date: Optional[str] = None
    ) -> str:
        """
        Генерировать дайджест канала, читая сообщения напрямую из Telegram
        
        Args:
            channel_username: Username канала (без @)
            days: Количество дней назад (по умолчанию 7)
            limit: Максимальное количество новостей (по умолчанию 10)
            custom_start_date: Начальная дата в формате 'YYYY-MM-DD'
            custom_end_date: Конечная дата в формате 'YYYY-MM-DD'
        """
        try:
            if not self.telegram_monitor or not hasattr(self.telegram_monitor, 'client'):
                logger.error("❌ Telegram monitor или client недоступен")
                return "❌ Не удалось подключиться к Telegram для чтения канала"

            # Определяем период (с учетом timezone)
            if custom_start_date and custom_end_date:
                start_date = datetime.strptime(custom_start_date, '%Y-%m-%d')
                end_date = datetime.strptime(custom_end_date, '%Y-%m-%d')
                # Добавляем timezone для корректного сравнения
                start_date = self.vladivostok_tz.localize(start_date)
                end_date = self.vladivostok_tz.localize(end_date.replace(hour=23, minute=59, second=59))
            else:
                end_date = datetime.now(self.vladivostok_tz)
                start_date = end_date - timedelta(days=days)
            
            logger.info(f"📰 Читаем сообщения из @{channel_username} за период {start_date.date()} - {end_date.date()}")

            # Получаем entity канала
            try:
                if channel_username.startswith('@'):
                    channel_username = channel_username[1:]
                
                entity = await self.telegram_monitor.client.get_entity(channel_username)
                logger.info(f"✅ Получили entity для канала @{channel_username}")
            except Exception as e:
                logger.error(f"❌ Не удалось получить канал @{channel_username}: {e}")
                return f"❌ Канал @{channel_username} не найден или недоступен"

            # Читаем сообщения
            messages = []
            async for message in self.telegram_monitor.client.iter_messages(
                entity, 
                limit=None,
                offset_date=start_date,
                reverse=False
            ):
                # Конвертируем дату сообщения в нужный timezone для корректного сравнения
                message_date = message.date
                if message_date.tzinfo is None:
                    # Если дата без timezone, считаем что это UTC
                    message_date = pytz.UTC.localize(message_date)
                
                # Конвертируем в наш timezone для сравнения
                message_date = message_date.astimezone(self.vladivostok_tz)
                
                # Фильтруем по дате
                if message_date < start_date or message_date > end_date:
                    continue
                    
                # Пропускаем сообщения без текста
                if not message.text or len(message.text.strip()) < 10:
                    continue
                
                # Собираем данные о сообщении
                message_data = {
                    'id': message.id,
                    'text': message.text,
                    'date': message_date,  # Используем уже сконвертированную дату
                    'views': getattr(message, 'views', 0) or 0,
                    'forwards': getattr(message, 'forwards', 0) or 0,
                    'replies': getattr(message.replies, 'replies', 0) if message.replies else 0,
                    'reactions_count': 0,
                    'url': f"https://t.me/{channel_username}/{message.id}"
                }
                
                # Подсчитываем реакции
                if hasattr(message, 'reactions') and message.reactions:
                    reactions_count = 0
                    for reaction in message.reactions.results:
                        reactions_count += reaction.count
                    message_data['reactions_count'] = reactions_count
                
                # Вычисляем популярность
                message_data['popularity_score'] = (
                    message_data['views'] + 
                    message_data['forwards'] * 2 + 
                    message_data['replies'] * 3 + 
                    message_data['reactions_count'] * 5
                )
                
                messages.append(message_data)
                
                # Если дошли до начала периода
                if message.date < start_date:
                    break

            logger.info(f"📊 Найдено {len(messages)} сообщений в канале @{channel_username}")
            
            if not messages:
                return self._generate_empty_digest_for_channel(channel_username, start_date, end_date)
            
            # Сортируем по популярности
            top_messages = sorted(messages, key=lambda x: x['popularity_score'], reverse=True)[:limit]
            
            # Форматируем результат
            return self._format_live_digest(
                top_messages, 
                start_date.strftime('%d.%m.%Y'),
                end_date.strftime('%d.%m.%Y'),
                channel_username
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации live дайджеста: {e}")
            return f"❌ Ошибка чтения канала: {e}"

    def _format_live_digest(
        self, 
        messages: List[Dict[str, Any]], 
        start_date: str, 
        end_date: str,
        channel_username: str
    ) -> str:
        """Форматирование дайджеста для канала (live)"""
        header = f"📰 Собрали топ самых обсуждаемых новостей из канала @{channel_username} за неделю\n"
        header += f"📅 Период: {start_date} - {end_date}\n\n"
        
        digest_lines = []
        for i, msg in enumerate(messages, 1):
            # Первые 50 символов текста
            text_preview = msg['text'][:50].replace('\n', ' ').strip()
            if len(msg['text']) > 50:
                text_preview += "..."
            
            # Статистика
            total_engagement = msg['views'] + msg['forwards'] + msg['replies'] + msg['reactions_count']
            
            line = f"⚡️ {text_preview} ({msg['url']}) [{total_engagement} реакций]"
            digest_lines.append(line)
        
        footer = "\n\nЭти новости собрали больше всего реакций и комментариев от читателей. А вам что больше всего запомнилось?"
        
        return header + "\n".join(digest_lines) + footer

    def _generate_empty_digest_for_channel(
        self, 
        channel_username: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> str:
        """Генерация пустого дайджеста для канала"""
        return (
            f"📰 Дайджест канала @{channel_username}\n"
            f"📅 Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n\n"
            f"😔 В канале @{channel_username} не найдено новостей за указанный период.\n\n"
            f"💡 Попробуйте:\n"
            f"• Увеличить период поиска\n"
            f"• Проверить правильность названия канала\n"
            f"• Убедиться, что канал публичный"
        )
