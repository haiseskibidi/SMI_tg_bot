



Система генерации дайджестов создает топ-новости за период с умной фильтрацией контента, региональными бонусами и пагинацией результатов. Поддерживает как чтение из базы данных, так и live-анализ Telegram каналов.

**Файл**: `src/digest_generator.py` (737 строк)  
**Интерфейс**: команда `/digest` в Telegram боте  
**Источники данных**: База данных + Live чтение через Telethon

---





```
DigestGenerator (Главный класс)
├── Database Mode              
│   ├── generate_weekly_digest() 
│   └── get_top_news_for_period() 
├── Live Mode                  
│   ├── generate_channel_digest_live() 
│   └── telegram_monitor.client 
├── Content Filtering         
│   ├── _is_chat_message()    
│   ├── Politics Filter      
│   └── Activity Filter      
├── Ranking System           
│   ├── Popularity Score     
│   ├── Regional Bonus       
│   └── Channel Tag Bonus    
└── Pagination System       
    ├── _format_live_digest_with_pagination()
    └── get_digest_page()    
```



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





```python
class DigestGenerator:
    def __init__(self, database_manager, telegram_monitor=None):
        self.db = database_manager                    
        self.telegram_monitor = telegram_monitor      
        self.vladivostok_tz = pytz.timezone("Asia/Vladivostok")  
        self._last_digest_data = None                 
```




```python
async def generate_weekly_digest(
    self, 
    region: Optional[str] = None,        
    channel: Optional[str] = None,       
    days: int = 7,                      
    limit: int = 10,                    
    custom_start_date: Optional[str] = None,  
    custom_end_date: Optional[str] = None
) -> str:
    """Генерация дайджеста из сохраненных в БД новостей"""
    
    
    if custom_start_date and custom_end_date:
        start_date = datetime.strptime(custom_start_date, '%Y-%m-%d')
        end_date = datetime.strptime(custom_end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now(self.vladivostok_tz)
        start_date = end_date - timedelta(days=days)
    
    
    news_data = await self.db.get_top_news_for_period(
        start_date, end_date, 
        region=region, 
        channel=channel, 
        limit=limit
    )
```


```python
async def generate_channel_digest_live(
    self, 
    channel_username: str,
    days: int = 7,
    limit: int = 10
) -> str:
    """Live чтение канала через Telethon API"""
    
    
    entity = await self.telegram_monitor.get_channel_entity(channel_username)
    
    
    total_messages_checked = 0
    messages = []
    
    async for message in self.telegram_monitor.client.iter_messages(
        entity, limit=200, offset_date=end_date
    ):
        total_messages_checked += 1
        
        
        message_date = message.date.replace(tzinfo=pytz.UTC)
        if message_date < start_date:
            break
            
        
        if not self._passes_content_filters(message):
            continue
            
        
        message_data = self._calculate_message_score(message, channel_username)
        messages.append(message_data)
```

---





```python

def _check_activity_filter(self, message) -> bool:
    """Фильтр по минимальной активности"""
    views = getattr(message, 'views', 0) or 0
    forwards = getattr(message, 'forwards', 0) or 0
    replies = getattr(message.replies, 'replies', 0) if message.replies else 0
    reactions_count = 0
    
    if hasattr(message, 'reactions') and message.reactions:
        for reaction in message.reactions.results:
            reactions_count += reaction.count
    
    
    engagement = replies + reactions_count
    if engagement == 0 and views < 1000:
        return False  
    
    return True
```



```python  
def _is_chat_message(self, text_lower: str) -> bool:
    """Проверка на обычное общение (не новости)"""
    chat_keywords = [
        
        "ночной чат", "night chat", "доброй ночи", "спокойной ночи", 
        "всем сладких снов", "приятных снов",
        
        
        "доброе утро", "с добрым утром", "всем доброго утра",
        
        
        "всем привет", "привет всем", "добрый день", "добрый вечер",
        
        
        "как дела", "что нового", "как погода", "кто онлайн",
        
        
        "опрос:", "голосование:", "вопрос дня", "обсуждение:"
    ]
    
    
    if any(keyword in text_lower for keyword in chat_keywords):
        return True
    
    
    words = text_lower.split()
    if len(words) <= 3 and all(len(word) <= 4 for word in words):
        return True
    
    return False
```



```python

if "
    continue  
```



```python

if not message.text or len(message.text.strip()) < 10:
    continue  
```

---





```python
def _calculate_message_score(self, message, channel_username: str) -> Dict[str, Any]:
    """Расчет рейтинга сообщения"""
    
    
    views = getattr(message, 'views', 0) or 0
    forwards = getattr(message, 'forwards', 0) or 0  
    replies = getattr(message.replies, 'replies', 0) if message.replies else 0
    reactions_count = 0
    
    if hasattr(message, 'reactions') and message.reactions:
        for reaction in message.reactions.results:
            reactions_count += reaction.count
    
    
    popularity_base = (
        views * 0.1 +           
        forwards * 2 +          
        replies * 3 +           
        reactions_count * 5     
    )
    
    
    has_channel_tag = f"@{channel_username}" in message.text.lower()
    is_regional_news = self._check_regional_relevance(message.text, channel_username)
    
    channel_tag_bonus = 1.5 if has_channel_tag else 1.0    
    regional_bonus = 1.3 if is_regional_news else 1.0      
    
    
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



```python
def _get_regional_keywords(self, channel_username: str) -> List[str]:
    """Получение региональных ключевых слов для бонусов"""
    channel_lower = channel_username.lower()
    
    
    if "kamchatka" in channel_lower or "камчатк" in channel_lower:
        return [
            "петропавловск", "камчатк", "елизово", "вилючинск", "ключи", 
            "усть-камчатск", "мильково", "эссо", "авача", "корякский"
        ]
    
    
    elif "khabarovsk" in channel_lower or "хабаровск" in channel_lower:
        return [
            "хабаровск", "комсомольск", "амурск", "николаевск", "охотск",
            "ванино", "советская гавань", "бикин", "вяземский"
        ]
    
    
    elif "vladivostok" in channel_lower or "владивосток" in channel_lower:
        return [
            "владивосток", "уссурийск", "находка", "артем", "большой камень",
            "партизанск", "лесозаводск", "дальнегорск", "спасск"
        ]
    
    
    
    return []  
```

---





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
    
    
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    page_messages = all_messages[start_idx:end_idx]
    
    
    header = f"📰 Топ новостей @{channel_username}\n"
    header += f"📅 {start_date} - {end_date}\n"
    header += f"📄 Страница {page}/{total_pages} (всего {total_count} новостей)\n\n"
    
    
    digest_lines = []
    for i, msg in enumerate(page_messages, start_idx + 1):
        text_preview = self._smart_truncate(self._clean_message_text(msg['text']), 80)
        
        
        activity_parts = []
        if msg['reactions_count'] > 0:
            activity_parts.append(f"👍{msg['reactions_count']}")
        if msg['replies'] > 0:
            activity_parts.append(f"💬{msg['replies']}")
        
        activity_str = " ".join(activity_parts) if activity_parts else "0 активности"
        
        line = f"{i}. {text_preview}\n   🔗 {msg['url']} [{activity_str}]"
        digest_lines.append(line)
    
    
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
    
    
    keyboard.append([
        {"text": "📰 Новый дайджест", "callback_data": "digest"},
        {"text": "🏠 Главное меню", "callback_data": "start"}
    ])
    
    return {
        'text': header + "\n\n".join(digest_lines) + "\n\nЭти новости собрали больше всего реакций от читателей.",
        'keyboard': keyboard
    }
```



```python
async def get_digest_page(self, channel_username: str, page: int) -> Dict[str, Any]:
    """Получение конкретной страницы из кэша"""
    
    
    if not hasattr(self, '_last_digest_data') or not self._last_digest_data:
        return {
            'text': "❌ Данные дайджеста не найдены. Сгенерируйте новый дайджест.",
            'keyboard': [[{"text": "📰 Новый дайджест", "callback_data": "digest"}]]
        }
    
    data = self._last_digest_data
    
    
    if data['channel_username'] != channel_username:
        return {
            'text': "❌ Данные дайджеста устарели. Сгенерируйте новый дайджест.",
            'keyboard': [[{"text": "📰 Новый дайджест", "callback_data": "digest"}]]
        }
    
    
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





```python

async def digest(self, message: Optional[Dict[str, Any]]) -> None:
    """Главная команда для генерации дайджестов"""
    
    
    command_text = message.get("text", "") if message else ""
    params = command_text.split()[1:] if command_text else []
    
    days = 7  
    custom_start = None
    custom_end = None
    
    
    if len(params) == 1 and params[0].isdigit():
        days = int(params[0])
    elif len(params) == 2:
        custom_start = params[0] 
        custom_end = params[1]
    
    
    period_text = self.digest_generator.format_period_selection()
    
    keyboard = [
        [{"text": "📅 За 3 дня", "callback_data": "digest_period_3"}],
        [{"text": "📅 За неделю", "callback_data": "digest_period_7"}], 
        [{"text": "📅 За 2 недели", "callback_data": "digest_period_14"}],
        [{"text": "🔗 Ввести ссылку на канал", "callback_data": "digest_channel_link"}]
    ]
    
    await self.bot.send_message_with_keyboard(period_text, keyboard)
```



```python

async def handle_digest_callback(self, data: str, message: Optional[Dict[str, Any]]) -> None:
    """Обработка выбора периода и каналов"""
    
    if data.startswith("digest_period_"):
        
        days = int(data.split("_")[-1])
        await self.send_message(f"📰 Генерируем дайджест за {days} дней из базы данных...")
        
        
        digest_result = await self.basic_commands.digest_generator.generate_weekly_digest(days=days)
        await self.send_message(digest_result)
        
    elif data == "digest_channel_link":
        
        await self.send_message(
            "🔗 <b>Дайджест конкретного канала</b>\n\n" 
            "Отправьте ссылку на канал для live-анализа:\n"
            "• <code>https://t.me/channel_name</code>\n"
            "• <code>@channel_name</code>"
        )


async def handle_digest_page_callback(self, data: str, message: Optional[Dict[str, Any]]) -> None:
    """Навигация по страницам дайджеста"""
    
    
    parts = data.split("_")
    page = int(parts[-1])
    channel_username = "_".join(parts[2:-1])
    
    
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





```python
def _smart_truncate(self, text: str, max_length: int) -> str:
    """Умная обрезка текста по словам"""
    if len(text) <= max_length:
        return text
    
    
    words = text.split()
    result = ""
    
    for word in words:
        if len(result + " " + word) <= max_length - 3:  
            if result:
                result += " "
            result += word
        else:
            break
    
    return result + "..." if result != text else text
```



```python
def _clean_message_text(self, text: str) -> str:
    """Очистка текста от Markdown и лишних символов"""
    
    
    text = text.replace('**', '').replace('__', '').replace('*', '').replace('_', '')
    
    
    text = re.sub(r'^(\s*[^\w\s]+\s*){2,}', '', text)
    
    
    text = ' '.join(text.split())
    
    
    text = re.sub(r'@\w+', '', text)
    
    return text.strip()
```

---





```
DigestGenerator
├── ← TelegramBot (команды /digest)
├── → DatabaseManager (get_top_news_for_period) 
├── → TelegramMonitor (live чтение через Telethon)
└── ← BasicCommands (digest_generator instance)

Поток данных:
User → /digest → BasicCommands → DigestGenerator → Database/Telethon → Formatted Result
```



```python

def _init_digest_generator(self):
    """Инициализация генератора дайджестов"""
    try:
        if self.bot.monitor_bot and self.bot.monitor_bot.database:
            from src.digest_generator import DigestGenerator
            self.digest_generator = DigestGenerator(
                self.bot.monitor_bot.database,
                self.bot.monitor_bot.telegram_monitor  
            )
            logger.info("✅ DigestGenerator инициализирован")
        else:
            logger.warning("⚠️ DigestGenerator не может быть инициализирован: нет database или monitor_bot")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации DigestGenerator: {e}")
```

---






```bash

grep "📰 Вызов команды digest" logs/news_monitor.log


grep "📊 Найдено.*сообщений в канале" logs/news_monitor.log


grep "📄 Запрос страницы.*дайджеста" logs/news_monitor.log


grep "❌ Ошибка генерации.*дайджеста" logs/news_monitor.log
```


```bash
/digest              
/digest 3            
/status              
```




```python

if not self.digest_generator:
    
    
    
    


self._init_digest_generator()
```


```python

SELECT COUNT(*) FROM messages WHERE date >= '2025-01-15';


SELECT COUNT(*) FROM messages 
WHERE date >= '2025-01-15' 
AND (views > 1000 OR reactions_count > 0 OR replies > 0);
```


```python

if not hasattr(self, '_last_digest_data') or not self._last_digest_data:
    
    



```


```bash

grep "✅ Telegram клиент подключен" logs/news_monitor.log


grep "❌ Ошибка получения entity" logs/news_monitor.log
```

---




```python



if engagement == 0 and views < 1000:  


async for message in self.telegram_monitor.client.iter_messages(
    entity, limit=200  
):


all_top_messages = sorted(messages, key=lambda x: x['popularity_score'], reverse=True)[:30]
```


```python

popularity_base = (
    views * 0.1 +           
    forwards * 2 +          
    replies * 3 +           
    reactions_count * 5     
)


channel_tag_bonus = 1.5    
regional_bonus = 1.3       
```

---




- **Время генерации**: < 10 секунд для database режима, < 30 секунд для live
- **Охват анализа**: до 200 последних сообщений в live режиме  
- **Эффективность фильтров**: 60-80% сообщений отсеивается как нерелевантные
- **Точность рейтинга**: приоритет реакциям и комментариям над просмотрами


```python

self._last_digest_data = {
    'messages': all_top_messages,
    'start_date': start_date.strftime('%d.%m.%Y'),
    'end_date': end_date.strftime('%d.%m.%Y'),
    'channel_username': channel_username
}


async for message in client.iter_messages(entity, limit=200):  


text_preview = self._smart_truncate(clean_text, 80)  
```

---

*Документация Digest System актуальна на: январь 2025*  
*Поддерживаемые источники: База данных + Live Telethon*
