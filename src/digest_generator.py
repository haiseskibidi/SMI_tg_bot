"""
📰 Digest Generator Module
Модуль для генерации дайджестов топ-новостей за период
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from loguru import logger
import pytz
import re


class DigestGenerator:
    """Генератор дайджестов новостей"""
    
    def __init__(self, database_manager, telegram_monitor=None):
        self.db = database_manager
        self.telegram_monitor = telegram_monitor
        self.moscow_tz = pytz.timezone("Europe/Moscow")
        self._last_digest_data = None  # Для хранения данных пагинации
    
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
                end_date = datetime.now(self.moscow_tz)
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
                start_date = self.moscow_tz.localize(start_date)
                end_date = self.moscow_tz.localize(end_date.replace(hour=23, minute=59, second=59))
            else:
                # Правильная логика: полные дни
                end_date = datetime.now(self.moscow_tz).replace(hour=23, minute=59, second=59, microsecond=0)
                start_date = (end_date - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
            
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
            total_messages_checked = 0
            
            logger.info(f"🔍 Начинаем поиск сообщений. Период: {start_date} - {end_date}")
            
            async for message in self.telegram_monitor.client.iter_messages(
                entity, 
                limit=None  # Проверяем ВСЕ сообщения
            ):
                total_messages_checked += 1
                
                if total_messages_checked <= 5:  # Логируем первые 5 сообщений для отладки
                    logger.info(f"📄 Сообщение #{total_messages_checked}: дата={message.date}, текст='{message.text[:30] if message.text else 'НЕТ ТЕКСТА'}'")
                
                # Конвертируем дату сообщения в нужный timezone для корректного сравнения
                message_date = message.date
                if message_date.tzinfo is None:
                    # Если дата без timezone, считаем что это UTC
                    message_date = pytz.UTC.localize(message_date)
                
                # Конвертируем в наш timezone для сравнения
                message_date = message_date.astimezone(self.moscow_tz)
                
                # Фильтруем по дате
                if message_date < start_date or message_date > end_date:
                    if total_messages_checked <= 5:  # Логируем причины фильтрации для первых сообщений
                        logger.info(f"⏭️ Сообщение #{total_messages_checked} отфильтровано по дате: {message_date} не в периоде {start_date} - {end_date}")
                    continue
                    
                # Пропускаем сообщения без текста
                if not message.text or len(message.text.strip()) < 10:
                    if total_messages_checked <= 5:
                        logger.info(f"⏭️ Сообщение #{total_messages_checked} отфильтровано: нет текста или слишком короткое")
                    continue
                
                # Исключаем "ночной чат" и подобные посты
                text_lower = message.text.lower()
                if self._is_chat_message(text_lower):
                    if total_messages_checked <= 10:
                        logger.info(f"⏭️ Сообщение #{total_messages_checked} отфильтровано: ночной чат/общение")
                    continue

                # Исключаем политические посты
                if "#политика" in text_lower or "#политик" in text_lower:
                    if total_messages_checked <= 10:
                        logger.info(f"⏭️ Сообщение #{total_messages_checked} отфильтровано: политика")
                    continue
                
                # Подсчитываем активность (реакции + комментарии)
                views = getattr(message, 'views', 0) or 0
                forwards = getattr(message, 'forwards', 0) or 0
                replies = getattr(message.replies, 'replies', 0) if message.replies else 0
                reactions_count = 0
                
                if hasattr(message, 'reactions') and message.reactions:
                    for reaction in message.reactions.results:
                        reactions_count += reaction.count
                
                # Ослабленный фильтр активности: либо много просмотров, либо есть реакции/комментарии
                engagement = replies + reactions_count
                if engagement == 0 and views < 1000:  # Разрешаем посты с большими просмотрами
                    if total_messages_checked <= 10:
                        logger.info(f"⏭️ Сообщение #{total_messages_checked} отфильтровано: мало активности (views={views}, replies={replies}, reactions={reactions_count})")
                    continue
                
                # Проверка тега канала (бонус к популярности, но не обязательно)
                channel_tag = f"@{channel_username}"
                has_channel_tag = channel_tag in text_lower

                # Региональная проверка (бонус к популярности, но не обязательно)
                regional_keywords = self._get_regional_keywords(channel_username)
                is_regional_news = False
                if regional_keywords:
                    is_regional_news = any(keyword in text_lower for keyword in regional_keywords)
                
                logger.info(f"✅ Сообщение #{total_messages_checked} подходит! Дата: {message_date}, реакции: {reactions_count}, комментарии: {replies}, текст: '{message.text[:50]}'")
                
                # Собираем данные о сообщении (используем уже вычисленные значения)
                message_data = {
                    'id': message.id,
                    'text': message.text,
                    'date': message_date,  # Используем уже сконвертированную дату
                    'views': views,
                    'forwards': forwards,
                    'replies': replies,
                    'reactions_count': reactions_count,
                    'url': f"https://t.me/{channel_username}/{message.id}"
                }
                
                # Вычисляем популярность (акцент на реакции и комментарии)
                popularity_base = (
                    message_data['replies'] * 10 +      # Комментарии - самое важное
                    message_data['reactions_count'] * 8 + # Реакции - очень важно
                    message_data['forwards'] * 3 +       # Репосты - важно
                    message_data['views'] * 0.1          # Просмотры - минимальный вес
                )
                
                # Бонусы за качество контента
                channel_tag_bonus = 1.5 if has_channel_tag else 1.0    # +50% за тег канала
                regional_bonus = 1.3 if is_regional_news else 1.0       # +30% за региональность
                
                message_data['popularity_score'] = popularity_base * channel_tag_bonus * regional_bonus
                
                messages.append(message_data)
                
                # Если дошли до начала периода
                if message_date < start_date:
                    break

            logger.info(f"📊 Найдено {len(messages)} сообщений в канале @{channel_username} из {total_messages_checked} проверенных")
            
            if not messages:
                empty_digest = self._generate_empty_digest_for_channel(channel_username, start_date, end_date)
                return empty_digest
            
            # Сортируем по популярности и берем топ-30 для пагинации
            all_top_messages = sorted(messages, key=lambda x: x['popularity_score'], reverse=True)[:30]
            
            # Сохраняем данные для пагинации (временное решение)
            self._last_digest_data = {
                'messages': all_top_messages,
                'start_date': start_date.strftime('%d.%m.%Y'),
                'end_date': end_date.strftime('%d.%m.%Y'),
                'channel_username': channel_username
            }
            
            # Форматируем результат с пагинацией
            digest_result = self._format_live_digest_with_pagination(
                all_top_messages, 
                start_date.strftime('%d.%m.%Y'),
                end_date.strftime('%d.%m.%Y'),
                channel_username,
                page=1,  # Показываем первую страницу (1-10)
                limit=limit
            )
            
            # Возвращаем только текст для совместимости (кнопки обработаем отдельно)
            return digest_result
            
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
            # Очищаем текст от форматирования и лишних эмодзи
            clean_text = self._clean_message_text(msg['text'])
            
            # Умная обрезка по словам (максимум 80 символов)
            text_preview = self._smart_truncate(clean_text, 80)
            
            # Детальная статистика активности
            reactions = msg['reactions_count']
            replies = msg['replies']
            
            # Формируем строку активности
            activity_parts = []
            if reactions > 0:
                activity_parts.append(f"👍{reactions}")
            if replies > 0:
                activity_parts.append(f"💬{replies}")
            
            activity_str = " ".join(activity_parts) if activity_parts else "0 активности"
            
            line = f"{i}. {text_preview}\n   🔗 {msg['url']} [{activity_str}]"
            digest_lines.append(line)
        
        footer = "\n\nЭти новости собрали больше всего реакций и комментариев от читателей. А вам что больше всего запомнилось?"
        
        return header + "\n\n".join(digest_lines) + footer

    def _format_live_digest_with_pagination(
        self, 
        all_messages: List[Dict[str, Any]], 
        start_date: str, 
        end_date: str,
        channel_username: str,
        page: int = 1,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Форматирование дайджеста для канала с пагинацией"""
        
        # Вычисляем границы для текущей страницы
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        messages_on_page = all_messages[start_idx:end_idx]
        
        # Заголовок с информацией о странице
        total_messages = len(all_messages)
        if page == 1:
            header = f"📰 Топ-{len(messages_on_page)} самых обсуждаемых новостей из канала @{channel_username} за неделю\n"
        else:
            news_range = f"{start_idx + 1}-{min(end_idx, total_messages)}"
            header = f"📰 Новости {news_range} из топ-{total_messages} канала @{channel_username} за неделю\n"
        
        header += f"📅 Период: {start_date} - {end_date}\n\n"
        
        # Форматируем новости на текущей странице
        digest_lines = []
        for i, msg in enumerate(messages_on_page, start_idx + 1):
            # Очищаем текст от форматирования и лишних эмодзи
            clean_text = self._clean_message_text(msg['text'])
            
            # Умная обрезка по словам (максимум 80 символов)
            text_preview = self._smart_truncate(clean_text, 80)
            
            # Детальная статистика активности
            reactions = msg['reactions_count']
            replies = msg['replies']
            
            # Формируем строку активности
            activity_parts = []
            if reactions > 0:
                activity_parts.append(f"👍{reactions}")
            if replies > 0:
                activity_parts.append(f"💬{replies}")
            
            activity_str = " ".join(activity_parts) if activity_parts else "0 активности"
            
            line = f"{i}. {text_preview}\n   🔗 {msg['url']} [{activity_str}]"
            digest_lines.append(line)
        
        # Создаем кнопки пагинации
        pagination_buttons = []
        
        # Кнопка "Показать еще" только если есть следующие страницы
        if page == 1 and total_messages > 10:
            pagination_buttons.append([
                {"text": f"📄 Показать еще (11-{min(20, total_messages)})", 
                 "callback_data": f"digest_page_{channel_username}_{page + 1}"}
            ])
        elif page == 2 and total_messages > 20:
            pagination_buttons.append([
                {"text": f"📄 Показать еще (21-{min(30, total_messages)})", 
                 "callback_data": f"digest_page_{channel_username}_{page + 1}"}
            ])
        
        # Кнопка "Назад" если не первая страница
        if page > 1:
            if page == 2:
                pagination_buttons.append([
                    {"text": "🔙 Вернуться к топ-10", 
                     "callback_data": f"digest_page_{channel_username}_1"}
                ])
            else:
                pagination_buttons.append([
                    {"text": f"🔙 Назад (11-20)", 
                     "callback_data": f"digest_page_{channel_username}_{page - 1}"}
                ])
        
        # Основные кнопки
        main_buttons = [
            [{"text": "📰 Новый дайджест", "callback_data": "digest"}],
            [{"text": "🏠 Главное меню", "callback_data": "start"}]
        ]
        
        footer = "\n\nЭти новости собрали больше всего реакций и комментариев от читателей. А вам что больше всего запомнилось?"
        
        text = header + "\n\n".join(digest_lines) + footer
        keyboard = pagination_buttons + main_buttons
        
        # Возвращаем и текст и клавиатуру
        return {
            'text': text,
            'keyboard': keyboard,
            'all_messages': all_messages,  # Сохраняем для других страниц
            'channel_username': channel_username,
            'start_date': start_date,
            'end_date': end_date
        }

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

    def _get_regional_keywords(self, channel_username: str) -> List[str]:
        """Получить ключевые слова для региональной фильтрации по каналу"""
        channel_lower = channel_username.lower()
        
        # Камчатка
        if "kamchat" in channel_lower or "камчат" in channel_lower:
            return [
                "камчатк", "петропавловск", "елизово", "мильково", "усть-большерецк", 
                "усть-камчатск", "вилючинск", "ключи", "эссо", "палана",
                "командорск", "никольское", "тигиль", "оссора", "пенжино"
            ]
        
        # Владивосток
        elif "vladivostok" in channel_lower or "владивосток" in channel_lower:
            return [
                "владивосток", "приморск", "находка", "уссурийск", "артем", 
                "партизанск", "спасск", "дальнегорск", "лесозаводск", "арсеньев"
            ]
        
        # Хабаровск
        elif "khabarovsk" in channel_lower or "хабаровск" in channel_lower:
            return [
                "хабаровск", "комсомольск", "амурск", "николаевск", "советская гавань",
                "бикин", "вяземский", "охотск", "аян"
            ]
        
        # Благовещенск
        elif "blagoveshchensk" in channel_lower or "благовещенск" in channel_lower:
            return [
                "благовещенск", "белогорск", "свободный", "зея", "тында", 
                "шимановск", "завитинск", "райчихинск"
            ]
        
        # Сахалин
        elif "sakhalin" in channel_lower or "сахалин" in channel_lower:
            return [
                "сахалин", "южно-сахалинск", "холмск", "корсаков", "невельск",
                "александровск", "поронайск", "макаров", "курилы", "оха"
            ]
        
        # Якутск
        elif "yakutsk" in channel_lower or "якутск" in channel_lower:
            return [
                "якутск", "якути", "саха", "мирный", "нерюнгри", "алдан", 
                "ленск", "олекминск", "верхоянск", "магадан"
            ]
        
        # Иркутск
        elif "irkutsk" in channel_lower or "иркутск" in channel_lower:
            return [
                "иркутск", "ангарск", "братск", "усть-илимск", "черемхово",
                "саянск", "шелехов", "тулун", "байкал"
            ]
        
        # Улан-Удэ
        elif "ulan" in channel_lower or "улан" in channel_lower or "buryat" in channel_lower:
            return [
                "улан-удэ", "бурят", "северобайкальск", "гусиноозерск", 
                "закаменск", "кяхта", "баргузин", "турунтаево"
            ]
        
        # Чита
        elif "chita" in channel_lower or "чита" in channel_lower:
            return [
                "чита", "краснокаменск", "борзя", "петровск", "нерчинск",
                "шилка", "сретенск", "балей"
            ]
        
        # Если канал не определен, не фильтруем по региону
        return []

    def _is_chat_message(self, text_lower: str) -> bool:
        """Проверка, является ли сообщение обычным общением (не новостью)"""
        chat_keywords = [
            # Ночной чат
            "ночной чат", "night chat", "доброй ночи", "спокойной ночи", 
            "всем сладких снов", "приятных снов",
            
            # Утренние приветствия
            "доброе утро", "с добрым утром", "всем доброго утра",
            
            # Общие приветствия
            "всем привет", "привет всем", "добрый день", "добрый вечер",
            
            # Вопросы/общение
            "как дела", "что нового", "как погода", "кто онлайн",
            
            # Служебные сообщения
            "опрос:", "голосование:", "вопрос дня", "обсуждение:",
            
            # Эмодзи-сообщения (только эмодзи)
        ]
        
        # Проверяем наличие ключевых слов чата
        if any(keyword in text_lower for keyword in chat_keywords):
            return True
        
        # Проверяем, состоит ли сообщение только из эмодзи и коротких слов
        words = text_lower.split()
        if len(words) <= 3 and all(len(word) <= 4 for word in words):
            return True
        
        return False

    def _clean_message_text(self, text: str) -> str:
        """Очистка текста сообщения от форматирования и лишних символов"""
        # Убираем markdown форматирование
        text = text.replace('**', '').replace('__', '').replace('*', '').replace('_', '')
        
        # Убираем повторяющиеся эмодзи в начале строки
        text = re.sub(r'^(\s*[^\w\s]+\s*){2,}', '', text)
        
        # Убираем лишние пробелы и переносы строк
        text = ' '.join(text.split())
        
        # Убираем упоминания каналов из текста (они уже есть в статистике)
        text = re.sub(r'@\w+', '', text)
        
        return text.strip()

    def _smart_truncate(self, text: str, max_length: int) -> str:
        """Умная обрезка текста по словам"""
        if len(text) <= max_length:
            return text
        
        # Обрезаем по словам
        words = text.split()
        result = ""
        
        for word in words:
            if len(result + " " + word) <= max_length - 3:  # -3 для "..."
                if result:
                    result += " "
                result += word
            else:
                break
        
        return result + "..." if result != text else text

    async def get_digest_page(self, channel_username: str, page: int) -> Dict[str, Any]:
        """Получить конкретную страницу дайджеста"""
        try:
            # Проверяем, есть ли сохраненные данные
            if not hasattr(self, '_last_digest_data') or not self._last_digest_data:
                return {
                    'text': "❌ Данные дайджеста не найдены. Сгенерируйте новый дайджест.",
                    'keyboard': [[{"text": "📰 Новый дайджест", "callback_data": "digest"}]]
                }
            
            data = self._last_digest_data
            
            # Проверяем, тот ли канал
            if data['channel_username'] != channel_username:
                return {
                    'text': "❌ Данные дайджеста устарели. Сгенерируйте новый дайджест.",
                    'keyboard': [[{"text": "📰 Новый дайджест", "callback_data": "digest"}]]
                }
            
            # Форматируем нужную страницу
            return self._format_live_digest_with_pagination(
                data['messages'],
                data['start_date'],
                data['end_date'],
                data['channel_username'],
                page=page,
                limit=10
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения страницы дайджеста: {e}")
            return {
                'text': f"❌ Ошибка получения страницы: {e}",
                'keyboard': [[{"text": "📰 Новый дайджест", "callback_data": "digest"}]]
            }
