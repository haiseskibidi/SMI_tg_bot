



Система мониторинга обеспечивает real-time отслеживание 80+ Telegram каналов через Telethon API с защитой от rate limits и оптимизацией для быстрого запуска.


- **`ChannelMonitor`** - управление подписками и настройки таймаутов
- **`MessageProcessor`** - обработка входящих сообщений в реальном времени
- **`SubscriptionCacheManager`** - кэш подписок для быстрого старта (30 сек вместо 30 мин)
- **`TelegramMonitor`** - Telethon клиент для подключения к Telegram API

---




```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  TelegramMonitor│    │  ChannelMonitor │    │ MessageProcessor│
│                 │    │                 │    │                 │
│ • Telethon      │◄──►│ • Подписки      │◄──►│ • Real-time     │
│ • Sessions      │    │ • Rate Limits   │    │ • Обработка     │
│ • Connections   │    │ • Timeouts      │    │ • Алерты        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│SubscriptionCache│    │ Config Loader   │    │    Database     │
│                 │    │                 │    │                 │
│ • Быстрый старт │    │ • Timeouts      │    │ • Сохранение    │
│ • 30 сек vs 30м │    │ • Channels      │    │ • Статистика    │
│ • JSON кэш      │    │ • Защита        │    │ • Дедупликация  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```


```
1. Telegram Channel → 2. Telethon Event → 3. MessageProcessor
                                              ↓
4. App.send_message_to_target ← 5. Database.save_message ← 6. Alert Check
```

---



**Файл**: `src/monitoring/channel_monitor.py` (407 строк)  
**Функция**: Подписка на каналы, защита от rate limits, оптимизация запуска



```python
class ChannelMonitor:
    def __init__(self, telegram_monitor, subscription_cache, message_processor, config_loader):
        
        self.batch_size = 6                    
        self.delay_cached_channel = 1          
        self.delay_already_joined = 2          
        self.delay_verification = 3            
        self.delay_after_subscribe = 5         
        self.delay_between_batches = 8         
        self.delay_retry_wait = 300            
        
        
        self.fast_start_mode = True            
        self.skip_new_on_startup = False       
```




```python
async def _subscribe_to_channels(self, all_channels: List[str]) -> List[str]:
    """Оптимизированная подписка: кеш → новые каналы"""
    
    if self.fast_start_mode:
        
        cached_channels, new_channels = self._separate_cached_channels(all_channels)
        
        logger.info(f"🚀 БЫСТРЫЙ СТАРТ: {len(cached_channels)} кешированных, {len(new_channels)} новых")
        
        
        await self._fast_load_cached_channels(cached_channels)
        
        
        if not self.skip_new_on_startup:
            await self._slow_process_new_channels(new_channels)
```


```python
async def _process_channels_batch(self, channels: List[str], delay: int):
    """Обработка каналов пакетами для избежания rate limits"""
    
    for i in range(0, len(channels), self.batch_size):
        batch = channels[i:i + self.batch_size]
        
        logger.info(f"📦 Обрабатываем пакет {i//self.batch_size + 1}: {len(batch)} каналов")
        
        for channel_username in batch:
            try:
                
                await self._subscribe_to_single_channel(channel_username)
                await asyncio.sleep(delay)
                
            except FloodWaitError as e:
                
                wait_time = self._extract_wait_time(str(e))
                logger.warning(f"⏳ Rate limit: ожидание {wait_time} сек")
                await asyncio.sleep(wait_time)
        
        
        if i + self.batch_size < len(channels):
            logger.info(f"⏸️ Пауза {self.delay_between_batches}с между пакетами...")
            await asyncio.sleep(self.delay_between_batches)
```




```python
def _extract_wait_time(self, error_message: str) -> int:
    """Извлечение времени ожидания из ошибки Telegram"""
    match = re.search(r'wait of (\d+) seconds', error_message)
    if match:
        wait_seconds = int(match.group(1))
        
        
        if wait_seconds > 3600:  
            hours = wait_seconds // 3600
            logger.error(f"🚨 ДЛИТЕЛЬНАЯ БЛОКИРОВКА: {hours} часов ({wait_seconds} сек)")
        
        return min(wait_seconds, self.delay_retry_wait)  
    
    return self.delay_retry_wait  
```




```python
async def setup_realtime_handlers(self):
    """Установка обработчиков новых сообщений"""
    from telethon import events
    
    
    all_channels = await self._load_channels_config()
    
    
    monitored_channels = await self._subscribe_to_channels(all_channels)
    
    
    @self.telegram_monitor.client.on(events.NewMessage)
    async def new_message_handler(event):
        await self.message_processor.handle_new_message(event)
    
    logger.info(f"⚡ Настроены real-time обработчики для {len(monitored_channels)} каналов")
```

---



**Файл**: `src/monitoring/message_processor.py` (177 строк)  
**Функция**: Real-time обработка входящих сообщений, алерты, фильтрация



```python
class MessageProcessor:
    def __init__(self, database, app_instance):
        self.database = database
        self.app_instance = app_instance
        self.processed_media_groups: Set[int] = set()  

async def handle_new_message(self, event):
    """Главный обработчик новых сообщений"""
    try:
        
        if not self.app_instance.monitoring_active:
            logger.debug("⏸️ Мониторинг приостановлен, пропускаем сообщение")
            return
        
        
        message = event.message
        chat = await event.get_chat()
        channel_username = getattr(chat, 'username', None)
        
        
        if not await self._validate_message_time(message):
            return
        
        if not await self._process_media_group(message, has_media):
            return
        
        
        message_data = self._create_message_data(message, channel_username)
        
        
        message_data = await self._check_alerts(message_data, message.text)
        
        
        await self._save_to_database(message_data)
        
        
        await self._send_message(message_data, has_text, has_media)
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки нового сообщения: {e}")
```



```python
def _create_message_data(self, message, channel_username: str) -> Dict[str, Any]:
    """Преобразование Telegram сообщения в стандартную структуру"""
    
    
    message_id = str(getattr(message, 'id', 0))
    unique_id = f"{channel_username}_{message_id}_{int(message.date.timestamp())}"
    
    
    views = getattr(message, 'views', 0) or 0
    forwards = getattr(message, 'forwards', 0) or 0
    
    
    reactions_count = 0
    if hasattr(message, 'reactions') and message.reactions:
        for reaction in message.reactions.results:
            reactions_count += reaction.count
    
    
    replies = 0
    if hasattr(message, 'replies') and message.replies:
        replies = getattr(message.replies, 'replies', 0) or 0
    
    
    url = f"https://t.me/{channel_username}/{message_id}"
    
    
    content_hash = None
    if message.text:
        content = f"{channel_username}:{message.text}"
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    return {
        'id': unique_id,
        'channel_username': channel_username,
        'message_id': int(message_id),
        'text': message.text,
        'date': message.date,
        'views': views,
        'forwards': forwards,
        'replies': replies,
        'reactions_count': reactions_count,
        'url': url,
        'content_hash': content_hash,
        'channel_region': self.app_instance.get_channel_region(channel_username)
    }
```



```python
async def _check_alerts(self, message_data: Dict[str, Any], text: str) -> Dict[str, Any]:
    """Проверка сообщения на алерт-ключевые слова"""
    
    if not text:
        return message_data
    
    
    is_alert, category, emoji, priority, matched_words = self.app_instance.check_alert_keywords(text)
    
    if is_alert:
        logger.warning(f"🚨 АЛЕРТ обнаружен: {category} в @{message_data['channel_username']}")
        
        
        message_data.update({
            'is_alert': True,
            'alert_category': category,
            'alert_emoji': emoji,
            'alert_priority': priority,
            'alert_keywords': matched_words
        })
        
        
        original_text = message_data.get('text', '')
        alert_text = self.app_instance.format_alert_message(
            original_text, message_data['channel_username'], 
            emoji, category, matched_words
        )
        message_data['text'] = alert_text
    
    return message_data
```



```python
async def _process_media_group(self, message, has_media: bool) -> bool:
    """Предотвращение дублирования медиа групп"""
    
    if has_media and hasattr(message, 'grouped_id') and message.grouped_id:
        grouped_id = message.grouped_id
        
        if grouped_id in self.processed_media_groups:
            logger.debug(f"🔄 Медиа группа {grouped_id} уже обработана, пропускаем")
            return False
        
        
        self.processed_media_groups.add(grouped_id)
        
        
        if len(self.processed_media_groups) > 1000:
            self.processed_media_groups.clear()
            logger.debug("🧹 Очищен кэш медиа групп")
    
    return True
```

---



**Файл**: `src/monitoring/subscription_cache.py` (68 строк)  
**Функция**: Кэширование подписок для быстрого старта системы



```python
class SubscriptionCacheManager:
    def __init__(self, cache_file: str = "config/subscriptions_cache.json"):
        self.subscription_cache_file = cache_file
        self.subscribed_channels: Set[str] = set()
```




```python
def load_subscription_cache(self):
    """Загрузка кэша подписок при старте"""
    try:
        if os.path.exists(self.subscription_cache_file):
            with open(self.subscription_cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                self.subscribed_channels = set(cache_data.get('subscribed_channels', []))
                logger.info(f"📋 Загружен кэш подписок: {len(self.subscribed_channels)} каналов")
        else:
            self.subscribed_channels = set()
            logger.info("📋 Файл кэша подписок не найден, создаем новый")
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки кэша подписок: {e}")
        self.subscribed_channels = set()
```


```python
def save_subscription_cache(self):
    """Сохранение текущего состояния кэша"""
    try:
        cache_data = {
            'subscribed_channels': list(self.subscribed_channels),
            'last_updated': datetime.now().isoformat()
        }
        
        with open(self.subscription_cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
        logger.debug(f"💾 Сохранен кэш подписок: {len(self.subscribed_channels)} каналов")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения кэша подписок: {e}")
```



```python

def is_channel_cached_as_subscribed(self, channel_username: str) -> bool:
    return channel_username in self.subscribed_channels


def add_channel_to_cache(self, channel_username: str):
    self.subscribed_channels.add(channel_username)
    self.save_subscription_cache()


def get_cache_stats(self) -> dict:
    return {
        'total_subscribed': len(self.subscribed_channels),
        'cache_file': self.subscription_cache_file,
        'file_exists': os.path.exists(self.subscription_cache_file)
    }
```




- **Без кэша**: 30+ минут для 80 каналов (проверка каждого)
- **С кэшем**: ~30 секунд (быстрая загрузка известных каналов)
- **Приоритизация**: кешированные каналы обрабатываются первыми


- **Минимум запросов**: не проверяем уже известные подписки
- **Rate limit**: меньше нагрузки на Telegram API
- **Graceful degradation**: система работает даже без кэша

---



**Файл**: `src/telegram_client.py` (414 строк)  
**Функция**: Подключение к Telegram API, управление сессиями



```python
class TelegramMonitor:
    def __init__(self, api_id: int, api_hash: str, database):
        self.api_id = api_id
        self.api_hash = api_hash
        self.database = database
        self.client = None
        self.is_connected = False
        
        
        self.channels_cache = {}
        self.messages_cache = {}
        self.cache_max_size = 1000
        
    async def initialize(self):
        """Инициализация Telethon клиента с сессией"""
        try:
            
            session_path = Path('sessions/news_monitor_session')
            session_path.parent.mkdir(exist_ok=True)
            
            
            self.client = TelegramClient(
                str(session_path),
                self.api_id,
                self.api_hash,
                device_model="News Monitor Bot",
                system_version="1.0",
                app_version="1.0"
            )
            
            
            await self.client.start()
            
            if await self.client.is_user_authorized():
                self.is_connected = True
                logger.info("✅ Telegram клиент подключен и авторизован")
            else:
                logger.error("❌ Telegram клиент не авторизован")
                
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Telegram клиента: {e}")
```



```python
async def get_channel_entity(self, channel_username: str):
    """Получение entity канала с кэшированием"""
    
    
    if channel_username in self.channels_cache:
        return self.channels_cache[channel_username]
    
    try:
        
        entity = await self.client.get_entity(channel_username)
        
        
        if len(self.channels_cache) >= self.cache_max_size:
            
            oldest_key = next(iter(self.channels_cache))
            del self.channels_cache[oldest_key]
        
        self.channels_cache[channel_username] = entity
        return entity
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения entity для {channel_username}: {e}")
        return None
```

---





```python

async def initialize_components(self):
    """Инициализация системы мониторинга"""
    
    
    self.telegram_monitor = TelegramMonitor(api_id, api_hash, self.database)
    await self.telegram_monitor.initialize()
    
    
    self.message_processor = MessageProcessor(self.database, self)
    
    
    self.channel_monitor = ChannelMonitor(
        self.telegram_monitor,
        self.subscription_cache,
        self.message_processor,
        self.config_loader  
    )
    
    
    await self.channel_monitor.setup_realtime_handlers()
```



```python
async def monitoring_cycle(self):
    """Главный цикл системы"""
    
    
    self.subscription_cache.load_subscription_cache()
    
    
    await self.channel_monitor.setup_realtime_handlers()
    
    
    if self.telegram_bot:
        bot_listener_task = asyncio.create_task(
            self.telegram_bot.start_listening()
        )
        logger.info("👂 Запущен прослушиватель команд бота")
    
    
    while self.running:
        try:
            
            if current_time - last_status_update >= 3600:
                await self.send_status_update()
                last_status_update = current_time
            
            await asyncio.sleep(30)  
            
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле мониторинга: {e}")
            await asyncio.sleep(60)
```

---






```bash

grep "📡.*мониторинг" logs/news_monitor.log


grep "Rate limit\|wait of" logs/news_monitor.log


grep "📥 Получено сообщение" logs/news_monitor.log


grep "❌.*обработки" logs/news_monitor.log
```


```bash
/status              
/force_subscribe     
/channels           
```




```
Причина: Превышение лимитов Telegram API
Решение: Ждать указанное время, увеличить таймауты
```


```bash

cat config/subscriptions_cache.json


rm config/subscriptions_cache.json


/force_subscribe
```


```python

if not self.app_instance.monitoring_active:
    


if not self.telegram_monitor.is_connected:
    
```




```yaml
monitoring:
  timeouts:
    batch_size: 6                    
    delay_cached_channel: 1          
    delay_between_batches: 8         
    delay_retry_wait: 300            
    fast_start_mode: true            
    skip_new_on_startup: false       
```



**Безопасный профиль (по умолчанию)**:
- batch_size: 6, delay_between_batches: 8
- Минимальный риск блокировок, запуск 3-5 минут

**Быстрый профиль**:
- batch_size: 10, delay_between_batches: 5  
- Риск блокировок, запуск 1-2 минуты

**Сверхбезопасный профиль**:
- batch_size: 3, delay_between_batches: 15
- Без блокировок, запуск 5-10 минут

---




- **Время запуска**: 30 секунд (с кэшем) vs 30 минут (без кэша)
- **Активные каналы**: количество каналов с сообщениями за 24ч
- **Скорость обработки**: < 1 секунда от получения до отправки
- **Rate limits**: частота блокировок Telegram API


```python

logger.info(f"📦 Обрабатываем пакет {batch_num}: {len(batch)} каналов")
logger.info(f"⚡ Настроены real-time обработчики для {len(monitored_channels)} каналов")
logger.warning(f"⏳ Rate limit: ожидание {wait_time} сек")
logger.info(f"📥 Получено сообщение от @{channel_username}")
```

---

*Документация Monitoring актуальна на: январь 2025*  
*Telethon версия: 1.28.0+, Python 3.8+*
