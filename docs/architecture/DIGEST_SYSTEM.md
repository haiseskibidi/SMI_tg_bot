# 📰 DIGEST SYSTEM - Генерация дайджестов

## 🎯 Обзор

Система генерации дайджестов создает топ-новости за период с умной фильтрацией контента, региональными бонусами и пагинацией результатов. Поддерживает как чтение из базы данных, так и live-анализ Telegram каналов.

**Файл**: `src/digest_generator.py` (737 строк)  
**Интерфейс**: команда `/digest` в Telegram боте  
**Источники данных**: База данных + Live чтение через Telethon

---

## 🏗️ Архитектура системы

### Основные компоненты

```
DigestGenerator (Главный класс)
├── Database Mode              # Чтение из сохраненных новостей
│   ├── generate_weekly_digest() # Дайджест по базе данных
│   └── get_top_news_for_period() # Запрос к БД с фильтрами
├── Live Mode                  # Прямое чтение из Telegram
│   ├── generate_channel_digest_live() # Live чтение канала
│   └── telegram_monitor.client # Telethon для доступа к API
├── Content Filtering         # Умная фильтрация контента  
│   ├── _is_chat_message()    # Исключение "ночного чата"
│   ├── Politics Filter      # Блокировка #политика
│   └── Activity Filter      # Минимальная активность
├── Ranking System           # Система рейтингования
│   ├── Popularity Score     # Формула популярности
│   ├── Regional Bonus       # +30% за региональность
│   └── Channel Tag Bonus    # +50% за упоминание канала
└── Pagination System       # Разбивка на страницы
    ├── _format_live_digest_with_pagination()
    └── get_digest_page()    # Навигация по страницам
```

### Поток генерации дайджеста

```
1. Команда /digest → BasicCommands.digest()
2. Парсинг параметров (период, регион, канал)
3. Выбор режима:
   ├── Database Mode → generate_weekly_digest()
   └── Live Mode → generate_channel_digest_live()
4. Фильтрация контента
5. Расчет рейтинга популярности  
6. Сортировка и пагинация
7. Форматирование + inline кнопки
8. Отправка в Telegram
```

---

## 🎛️ Класс DigestGenerator

### Инициализация

```python
class DigestGenerator:
    def __init__(self, database_manager, telegram_monitor=None):
        self.db = database_manager                    # Доступ к базе данных
        self.telegram_monitor = telegram_monitor      # Telethon для live чтения
        self.vladivostok_tz = pytz.timezone("Asia/Vladivostok")  # Часовой пояс
        self._last_digest_data = None                 # Кэш для пагинации
```

### Режимы работы

#### 📊 Database Mode - чтение из базы
```python
async def generate_weekly_digest(
    self, 
    region: Optional[str] = None,        # Фильтр по региону
    channel: Optional[str] = None,       # Конкретный канал (приоритет)
    days: int = 7,                      # Количество дней назад
    limit: int = 10,                    # Максимум новостей
    custom_start_date: Optional[str] = None,  # Кастомный период
    custom_end_date: Optional[str] = None
) -> str:
    """Генерация дайджеста из сохраненных в БД новостей"""
    
    # Определение периода
    if custom_start_date and custom_end_date:
        start_date = datetime.strptime(custom_start_date, '%Y-%m-%d')
        end_date = datetime.strptime(custom_end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now(self.vladivostok_tz)
        start_date = end_date - timedelta(days=days)
    
    # Запрос к базе данных с фильтрами
    news_data = await self.db.get_top_news_for_period(
        start_date, end_date, 
        region=region, 
        channel=channel, 
        limit=limit
    )
```

#### 🔴 Live Mode - прямое чтение из Telegram
```python
async def generate_channel_digest_live(
    self, 
    channel_username: str,
    days: int = 7,
    limit: int = 10
) -> str:
    """Live чтение канала через Telethon API"""
    
    # Получение entity канала
    entity = await self.telegram_monitor.get_channel_entity(channel_username)
    
    # Итерация по сообщениям
    total_messages_checked = 0
    messages = []
    
    async for message in self.telegram_monitor.client.iter_messages(
        entity, limit=200, offset_date=end_date
    ):
        total_messages_checked += 1
        
        # Проверка периода
        message_date = message.date.replace(tzinfo=pytz.UTC)
        if message_date < start_date:
            break
            
        # Применение фильтров
        if not self._passes_content_filters(message):
            continue
            
        # Расчет рейтинга и сохранение
        message_data = self._calculate_message_score(message, channel_username)
        messages.append(message_data)
```

---

## 🔍 Система фильтрации контента

### Фильтр активности

```python
# Минимальные требования к активности  
def _check_activity_filter(self, message) -> bool:
    """Фильтр по минимальной активности"""
    views = getattr(message, 'views', 0) or 0
    forwards = getattr(message, 'forwards', 0) or 0
    replies = getattr(message.replies, 'replies', 0) if message.replies else 0
    reactions_count = 0
    
    if hasattr(message, 'reactions') and message.reactions:
        for reaction in message.reactions.results:
            reactions_count += reaction.count
    
    # Ослабленный фильтр: либо много просмотров, либо есть реакции/комментарии
    engagement = replies + reactions_count
    if engagement == 0 and views < 1000:
        return False  # Слишком низкая активность
    
    return True
```

### Исключение "ночного чата"

```python  
def _is_chat_message(self, text_lower: str) -> bool:
    """Проверка на обычное общение (не новости)"""
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
        "опрос:", "голосование:", "вопрос дня", "обсуждение:"
    ]
    
    # Проверка ключевых слов
    if any(keyword in text_lower for keyword in chat_keywords):
        return True
    
    # Проверка коротких сообщений (до 3 слов по 4 символа = общение)
    words = text_lower.split()
    if len(words) <= 3 and all(len(word) <= 4 for word in words):
        return True
    
    return False
```

### Политический фильтр

```python
# Простое исключение политического контента
if "#политика" in text_lower or "#политик" in text_lower:
    continue  # Пропускаем политические посты
```

### Фильтр длины контента

```python
# Минимальная длина для новостей
if not message.text or len(message.text.strip()) < 10:
    continue  # Слишком короткое сообщение
```

---

## 📊 Система рейтингования

### Формула популярности

```python
def _calculate_message_score(self, message, channel_username: str) -> Dict[str, Any]:
    """Расчет рейтинга сообщения"""
    
    # Базовая формула активности
    views = getattr(message, 'views', 0) or 0
    forwards = getattr(message, 'forwards', 0) or 0  
    replies = getattr(message.replies, 'replies', 0) if message.replies else 0
    reactions_count = 0
    
    if hasattr(message, 'reactions') and message.reactions:
        for reaction in message.reactions.results:
            reactions_count += reaction.count
    
    # Весовая формула: реакции и комментарии важнее просмотров
    popularity_base = (
        views * 0.1 +           # Просмотры (низкий вес)
        forwards * 2 +          # Пересылки (средний вес)  
        replies * 3 +           # Комментарии (высокий вес)
        reactions_count * 5     # Реакции (максимальный вес)
    )
    
    # Бонусная система
    has_channel_tag = f"@{channel_username}" in message.text.lower()
    is_regional_news = self._check_regional_relevance(message.text, channel_username)
    
    channel_tag_bonus = 1.5 if has_channel_tag else 1.0    # +50% за упоминание канала
    regional_bonus = 1.3 if is_regional_news else 1.0      # +30% за региональность
    
    # Итоговый рейтинг
    final_score = popularity_base * channel_tag_bonus * regional_bonus
    
    return {
        'text': message.text,
        'url': f"https://t.me/{channel_username}/{message.id}",
        'views': views,
        'forwards': forwards, 
        'replies': replies,
        'reactions_count': reactions_count,
        'popularity_score': final_score
    }
```

### Региональные бонусы

```python
def _get_regional_keywords(self, channel_username: str) -> List[str]:
    """Получение региональных ключевых слов для бонусов"""
    channel_lower = channel_username.lower()
    
    # Камчатка
    if "kamchatka" in channel_lower or "камчатк" in channel_lower:
        return [
            "петропавловск", "камчатк", "елизово", "вилючинск", "ключи", 
            "усть-камчатск", "мильково", "эссо", "авача", "корякский"
        ]
    
    # Хабаровск    
    elif "khabarovsk" in channel_lower or "хабаровск" in channel_lower:
        return [
            "хабаровск", "комсомольск", "амурск", "николаевск", "охотск",
            "ванино", "советская гавань", "бикин", "вяземский"
        ]
    
    # Владивосток
    elif "vladivostok" in channel_lower or "владивосток" in channel_lower:
        return [
            "владивосток", "уссурийск", "находка", "артем", "большой камень",
            "партизанск", "лесозаводск", "дальнегорск", "спасск"
        ]
    
    # ... остальные регионы
    
    return []  # Нет региональных бонусов для неопознанных каналов
```

---

## 📄 Система пагинации

### Разбиение на страницы

```python
def _format_live_digest_with_pagination(
    self, 
    all_messages: List[Dict[str, Any]], 
    start_date: str,
    end_date: str,
    channel_username: str,
    page: int = 1,
    limit: int = 10
) -> Dict[str, Any]:
    """Форматирование дайджеста с пагинацией"""
    
    total_count = len(all_messages)
    total_pages = (total_count + limit - 1) // limit
    
    # Вычисляем границы текущей страницы
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    page_messages = all_messages[start_idx:end_idx]
    
    # Формируем заголовок с информацией о странице
    header = f"📰 Топ новостей @{channel_username}\n"
    header += f"📅 {start_date} - {end_date}\n"
    header += f"📄 Страница {page}/{total_pages} (всего {total_count} новостей)\n\n"
    
    # Форматируем новости на текущей странице
    digest_lines = []
    for i, msg in enumerate(page_messages, start_idx + 1):
        text_preview = self._smart_truncate(self._clean_message_text(msg['text']), 80)
        
        # Статистика активности
        activity_parts = []
        if msg['reactions_count'] > 0:
            activity_parts.append(f"👍{msg['reactions_count']}")
        if msg['replies'] > 0:
            activity_parts.append(f"💬{msg['replies']}")
        
        activity_str = " ".join(activity_parts) if activity_parts else "0 активности"
        
        line = f"{i}. {text_preview}\n   🔗 {msg['url']} [{activity_str}]"
        digest_lines.append(line)
    
    # Создаем кнопки навигации
    keyboard = []
    nav_buttons = []
    
    if page > 1:
        nav_buttons.append({
            "text": f"⬅️ Стр. {page-1}",
            "callback_data": f"digest_page_{channel_username}_{page-1}"
        })
    
    if page < total_pages:
        nav_buttons.append({
            "text": f"Стр. {page+1} ➡️", 
            "callback_data": f"digest_page_{channel_username}_{page+1}"
        })
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Кнопки управления
    keyboard.append([
        {"text": "📰 Новый дайджест", "callback_data": "digest"},
        {"text": "🏠 Главное меню", "callback_data": "start"}
    ])
    
    return {
        'text': header + "\n\n".join(digest_lines) + "\n\nЭти новости собрали больше всего реакций от читателей.",
        'keyboard': keyboard
    }
```

### Навигация между страницами

```python
async def get_digest_page(self, channel_username: str, page: int) -> Dict[str, Any]:
    """Получение конкретной страницы из кэша"""
    
    # Проверяем наличие сохраненных данных
    if not hasattr(self, '_last_digest_data') or not self._last_digest_data:
        return {
            'text': "❌ Данные дайджеста не найдены. Сгенерируйте новый дайджест.",
            'keyboard': [[{"text": "📰 Новый дайджест", "callback_data": "digest"}]]
        }
    
    data = self._last_digest_data
    
    # Проверяем актуальность (тот ли канал)
    if data['channel_username'] != channel_username:
        return {
            'text': "❌ Данные дайджеста устарели. Сгенерируйте новый дайджест.",
            'keyboard': [[{"text": "📰 Новый дайджест", "callback_data": "digest"}]]
        }
    
    # Форматируем запрошенную страницу
    return self._format_live_digest_with_pagination(
        data['messages'],
        data['start_date'],
        data['end_date'],
        data['channel_username'],
        page=page,
        limit=10
    )
```

---

## 🎯 Интерфейс в Telegram боте

### Команда /digest

```python
# В BasicCommands.digest()
async def digest(self, message: Optional[Dict[str, Any]]) -> None:
    """Главная команда для генерации дайджестов"""
    
    # Парсинг параметров команды
    command_text = message.get("text", "") if message else ""
    params = command_text.split()[1:] if command_text else []
    
    days = 7  # По умолчанию неделя
    custom_start = None
    custom_end = None
    
    # Обработка параметров: /digest 3 или /digest 2025-01-15 2025-01-20
    if len(params) == 1 and params[0].isdigit():
        days = int(params[0])
    elif len(params) == 2:
        custom_start = params[0] 
        custom_end = params[1]
    
    # Показ меню выбора периода
    period_text = self.digest_generator.format_period_selection()
    
    keyboard = [
        [{"text": "📅 За 3 дня", "callback_data": "digest_period_3"}],
        [{"text": "📅 За неделю", "callback_data": "digest_period_7"}], 
        [{"text": "📅 За 2 недели", "callback_data": "digest_period_14"}],
        [{"text": "🔗 Ввести ссылку на канал", "callback_data": "digest_channel_link"}]
    ]
    
    await self.bot.send_message_with_keyboard(period_text, keyboard)
```

### Обработка callback-ов

```python
# В TelegramBot.handle_digest_callback()
async def handle_digest_callback(self, data: str, message: Optional[Dict[str, Any]]) -> None:
    """Обработка выбора периода и каналов"""
    
    if data.startswith("digest_period_"):
        # Выбран стандартный период
        days = int(data.split("_")[-1])
        await self.send_message(f"📰 Генерируем дайджест за {days} дней из базы данных...")
        
        # Генерация из базы
        digest_result = await self.basic_commands.digest_generator.generate_weekly_digest(days=days)
        await self.send_message(digest_result)
        
    elif data == "digest_channel_link":
        # Запрос ссылки на канал для live чтения
        await self.send_message(
            "🔗 <b>Дайджест конкретного канала</b>\n\n" 
            "Отправьте ссылку на канал для live-анализа:\n"
            "• <code>https://t.me/channel_name</code>\n"
            "• <code>@channel_name</code>"
        )

# Обработка пагинации
async def handle_digest_page_callback(self, data: str, message: Optional[Dict[str, Any]]) -> None:
    """Навигация по страницам дайджеста"""
    
    # Формат: digest_page_channel_username_page_number
    parts = data.split("_")
    page = int(parts[-1])
    channel_username = "_".join(parts[2:-1])
    
    # Получение страницы из кэша
    page_result = await self.basic_commands.digest_generator.get_digest_page(
        channel_username, page
    )
    
    if isinstance(page_result, dict):
        await self.send_message_with_keyboard(
            page_result['text'], 
            page_result['keyboard'], 
            use_reply_keyboard=False
        )
```

---

## 🧹 Очистка и форматирование текста

### Умная обрезка контента

```python
def _smart_truncate(self, text: str, max_length: int) -> str:
    """Умная обрезка текста по словам"""
    if len(text) <= max_length:
        return text
    
    # Обрезаем по словам, а не по символам
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
```

### Очистка от форматирования

```python
def _clean_message_text(self, text: str) -> str:
    """Очистка текста от Markdown и лишних символов"""
    
    # Убираем markdown форматирование
    text = text.replace('**', '').replace('__', '').replace('*', '').replace('_', '')
    
    # Убираем повторяющиеся эмодзи в начале строки
    text = re.sub(r'^(\s*[^\w\s]+\s*){2,}', '', text)
    
    # Убираем лишние пробелы и переносы
    text = ' '.join(text.split())
    
    # Убираем упоминания каналов (они уже в статистике)
    text = re.sub(r'@\w+', '', text)
    
    return text.strip()
```

---

## 🔗 Интеграция с другими компонентами

### Связи с системой

```
DigestGenerator
├── ← TelegramBot (команды /digest)
├── → DatabaseManager (get_top_news_for_period) 
├── → TelegramMonitor (live чтение через Telethon)
└── ← BasicCommands (digest_generator instance)

Поток данных:
User → /digest → BasicCommands → DigestGenerator → Database/Telethon → Formatted Result
```

### Инициализация в боте

```python
# В BasicCommands.__init__()
def _init_digest_generator(self):
    """Инициализация генератора дайджестов"""
    try:
        if self.bot.monitor_bot and self.bot.monitor_bot.database:
            from src.digest_generator import DigestGenerator
            self.digest_generator = DigestGenerator(
                self.bot.monitor_bot.database,
                self.bot.monitor_bot.telegram_monitor  # Для live режима
            )
            logger.info("✅ DigestGenerator инициализирован")
        else:
            logger.warning("⚠️ DigestGenerator не может быть инициализирован: нет database или monitor_bot")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации DigestGenerator: {e}")
```

---

## 🔍 Диагностика проблем

### Проверка работы дайджестов

#### 📊 Логи системы
```bash
# Команды дайджестов
grep "📰 Вызов команды digest" logs/news_monitor.log

# Live чтение каналов  
grep "📊 Найдено.*сообщений в канале" logs/news_monitor.log

# Пагинация
grep "📄 Запрос страницы.*дайджеста" logs/news_monitor.log

# Ошибки генерации
grep "❌ Ошибка генерации.*дайджеста" logs/news_monitor.log
```

#### 🔧 Команды для диагностики
```bash
/digest              # Проверка основной функции
/digest 3            # Дайджест за 3 дня
/status              # Проверка доступности компонентов
```

### Типичные проблемы

#### 📰 "Генератор дайджестов недоступен"
```python
# Проверить инициализацию
if not self.digest_generator:
    # Причины:
    # 1. Monitor bot не инициализирован
    # 2. База данных недоступна  
    # 3. Ошибка импорта DigestGenerator

# Решение: повторная инициализация
self._init_digest_generator()
```

#### 🔍 "Нет новостей за период"
```python
# Проверить данные в базе
SELECT COUNT(*) FROM messages WHERE date >= '2025-01-15';

# Проверить фильтры активности
SELECT COUNT(*) FROM messages 
WHERE date >= '2025-01-15' 
AND (views > 1000 OR reactions_count > 0 OR replies > 0);
```

#### 📄 "Ошибка пагинации"  
```python
# Проверить кэш данных
if not hasattr(self, '_last_digest_data') or not self._last_digest_data:
    # Кэш очищен или не создавался
    
# Проверить формат callback
# Правильно: "digest_page_channel_name_2"
# Неправильно: "digest_page_2" (нет имени канала)
```

#### 🚫 "Канал недоступен для live чтения"
```bash
# Проверить подключение Telethon
grep "✅ Telegram клиент подключен" logs/news_monitor.log

# Проверить доступ к каналу
grep "❌ Ошибка получения entity" logs/news_monitor.log
```

---

## ⚙️ Настройки и конфигурация

### Параметры фильтрации
```python
# В методах DigestGenerator можно настроить:

# Минимальная активность
if engagement == 0 and views < 1000:  # Изменить порог просмотров

# Количество сообщений для анализа  
async for message in self.telegram_monitor.client.iter_messages(
    entity, limit=200  # Увеличить для большего охвата
):

# Максимум новостей в результате
all_top_messages = sorted(messages, key=lambda x: x['popularity_score'], reverse=True)[:30]
```

### Весовые коэффициенты популярности
```python
# Формула может быть настроена:
popularity_base = (
    views * 0.1 +           # Вес просмотров (по умолчанию 0.1)
    forwards * 2 +          # Вес пересылок (по умолчанию 2)  
    replies * 3 +           # Вес комментариев (по умолчанию 3)
    reactions_count * 5     # Вес реакций (по умолчанию 5)
)

# Бонусы:
channel_tag_bonus = 1.5    # +50% за упоминание канала (настраивается)
regional_bonus = 1.3       # +30% за региональность (настраивается)
```

---

## 📈 Метрики и производительность

### Ключевые показатели
- **Время генерации**: < 10 секунд для database режима, < 30 секунд для live
- **Охват анализа**: до 200 последних сообщений в live режиме  
- **Эффективность фильтров**: 60-80% сообщений отсеивается как нерелевантные
- **Точность рейтинга**: приоритет реакциям и комментариям над просмотрами

### Оптимизация производительности
```python
# Кэширование результатов для пагинации
self._last_digest_data = {
    'messages': all_top_messages,
    'start_date': start_date.strftime('%d.%m.%Y'),
    'end_date': end_date.strftime('%d.%m.%Y'),
    'channel_username': channel_username
}

# Ограничение количества анализируемых сообщений
async for message in client.iter_messages(entity, limit=200):  # Не больше 200

# Умная обрезка текста для экономии трафика
text_preview = self._smart_truncate(clean_text, 80)  # Максимум 80 символов
```

---

*Документация Digest System актуальна на: январь 2025*  
*Поддерживаемые источники: База данных + Live Telethon*
