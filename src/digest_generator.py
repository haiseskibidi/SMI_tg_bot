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
    
    def __init__(self, database_manager):
        self.db = database_manager
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
