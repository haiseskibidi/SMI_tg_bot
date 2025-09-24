# 📡 MONITORING - Система мониторинга каналов

## 🎯 Обзор

Система мониторинга обеспечивает real-time отслеживание 80+ Telegram каналов через Telethon API с защитой от rate limits и оптимизацией для быстрого запуска.

### Основные компоненты
- **`ChannelMonitor`** - управление подписками и настройки таймаутов
- **`MessageProcessor`** - обработка входящих сообщений в реальном времени
- **`SubscriptionCacheManager`** - кэш подписок для быстрого старта (30 сек вместо 30 мин)
- **`TelegramMonitor`** - Telethon клиент для подключения к Telegram API

---

## 🏗️ Архитектура системы мониторинга

### Схема компонентов
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

### Поток обработки сообщений
```
1. Telegram Channel → 2. Telethon Event → 3. MessageProcessor
                                              ↓
4. App.send_message_to_target ← 5. Database.save_message ← 6. Alert Check
```

---

## 📡 ChannelMonitor - Управление подписками

**Файл**: `src/monitoring/channel_monitor.py` (407 строк)  
**Функция**: Подписка на каналы, защита от rate limits, оптимизация запуска

### Ключевые настройки таймаутов

```python
class ChannelMonitor:
    def __init__(self, telegram_monitor, subscription_cache, message_processor, config_loader):
        # ⏱️ ЗАЩИТА ОТ БЛОКИРОВОК TELEGRAM
        self.batch_size = 6                    # Каналов в одном пакете
        self.delay_cached_channel = 1          # Задержка для кешированных (сек)
        self.delay_already_joined = 2          # Для уже подписанных (сек)
        self.delay_verification = 3            # Между попытками верификации (сек)
        self.delay_after_subscribe = 5         # После успешной подписки (сек)
        self.delay_between_batches = 8         # Между пакетами каналов (сек)
        self.delay_retry_wait = 300            # Rate limit ожидание (5 мин)
        
        # 🚀 ОПТИМИЗАЦИЯ ЗАПУСКА
        self.fast_start_mode = True            # Приоритет кешированным каналам
        self.skip_new_on_startup = False       # Пропускать новые при запуске
```

### Алгоритм подписки на каналы

#### 🚀 Быстрый старт (fast_start_mode)
```python
async def _subscribe_to_channels(self, all_channels: List[str]) -> List[str]:
    """Оптимизированная подписка: кеш → новые каналы"""
    
    if self.fast_start_mode:
        # 1. ПРИОРИТЕТ: быстрая обработка кешированных каналов
        cached_channels, new_channels = self._separate_cached_channels(all_channels)
        
        logger.info(f"🚀 БЫСТРЫЙ СТАРТ: {len(cached_channels)} кешированных, {len(new_channels)} новых")
        
        # Быстро обрабатываем кешированные (1 сек задержки)
        await self._fast_load_cached_channels(cached_channels)
        
        # Медленно и безопасно обрабатываем новые
        if not self.skip_new_on_startup:
            await self._slow_process_new_channels(new_channels)
```

#### 📦 Пакетная обработка
```python
async def _process_channels_batch(self, channels: List[str], delay: int):
    """Обработка каналов пакетами для избежания rate limits"""
    
    for i in range(0, len(channels), self.batch_size):
        batch = channels[i:i + self.batch_size]
        
        logger.info(f"📦 Обрабатываем пакет {i//self.batch_size + 1}: {len(batch)} каналов")
        
        for channel_username in batch:
            try:
                # Попытка подписки с обработкой ошибок
                await self._subscribe_to_single_channel(channel_username)
                await asyncio.sleep(delay)
                
            except FloodWaitError as e:
                # Обработка rate limit от Telegram
                wait_time = self._extract_wait_time(str(e))
                logger.warning(f"⏳ Rate limit: ожидание {wait_time} сек")
                await asyncio.sleep(wait_time)
        
        # Пауза между пакетами
        if i + self.batch_size < len(channels):
            logger.info(f"⏸️ Пауза {self.delay_between_batches}с между пакетами...")
            await asyncio.sleep(self.delay_between_batches)
```

### Обработка rate limits

#### 🛡️ Защита от блокировок
```python
def _extract_wait_time(self, error_message: str) -> int:
    """Извлечение времени ожидания из ошибки Telegram"""
    match = re.search(r'wait of (\d+) seconds', error_message)
    if match:
        wait_seconds = int(match.group(1))
        
        # Логирование длительных блокировок
        if wait_seconds > 3600:  # Больше часа
            hours = wait_seconds // 3600
            logger.error(f"🚨 ДЛИТЕЛЬНАЯ БЛОКИРОВКА: {hours} часов ({wait_seconds} сек)")
        
        return min(wait_seconds, self.delay_retry_wait)  # Максимум 5 минут
    
    return self.delay_retry_wait  # Дефолтное ожидание
```

### Setup real-time handlers

#### ⚡ Настройка событий в реальном времени
```python
async def setup_realtime_handlers(self):
    """Установка обработчиков новых сообщений"""
    from telethon import events
    
    # Загрузка списка каналов из конфигурации
    all_channels = await self._load_channels_config()
    
    # Подписка на каналы с оптимизацией
    monitored_channels = await self._subscribe_to_channels(all_channels)
    
    # Регистрация обработчика новых сообщений
    @self.telegram_monitor.client.on(events.NewMessage)
    async def new_message_handler(event):
        await self.message_processor.handle_new_message(event)
    
    logger.info(f"⚡ Настроены real-time обработчики для {len(monitored_channels)} каналов")
```

---

## ⚡ MessageProcessor - Обработка сообщений

**Файл**: `src/monitoring/message_processor.py` (177 строк)  
**Функция**: Real-time обработка входящих сообщений, алерты, фильтрация

### Основной цикл обработки

```python
class MessageProcessor:
    def __init__(self, database, app_instance):
        self.database = database
        self.app_instance = app_instance
        self.processed_media_groups: Set[int] = set()  # Дедупликация медиа групп

async def handle_new_message(self, event):
    """Главный обработчик новых сообщений"""
    try:
        # 1. Проверка состояния мониторинга
        if not self.app_instance.monitoring_active:
            logger.debug("⏸️ Мониторинг приостановлен, пропускаем сообщение")
            return
        
        # 2. Извлечение данных сообщения
        message = event.message
        chat = await event.get_chat()
        channel_username = getattr(chat, 'username', None)
        
        # 3. Фильтрация и валидация
        if not await self._validate_message_time(message):
            return
        
        if not await self._process_media_group(message, has_media):
            return
        
        # 4. Создание структуры данных
        message_data = self._create_message_data(message, channel_username)
        
        # 5. Проверка алертов
        message_data = await self._check_alerts(message_data, message.text)
        
        # 6. Сохранение в базу данных
        await self._save_to_database(message_data)
        
        # 7. Отправка в целевые каналы
        await self._send_message(message_data, has_text, has_media)
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки нового сообщения: {e}")
```

### Создание структуры данных сообщения

```python
def _create_message_data(self, message, channel_username: str) -> Dict[str, Any]:
    """Преобразование Telegram сообщения в стандартную структуру"""
    
    # Генерация уникального ID
    message_id = str(getattr(message, 'id', 0))
    unique_id = f"{channel_username}_{message_id}_{int(message.date.timestamp())}"
    
    # Извлечение метаданных
    views = getattr(message, 'views', 0) or 0
    forwards = getattr(message, 'forwards', 0) or 0
    
    # Подсчет реакций
    reactions_count = 0
    if hasattr(message, 'reactions') and message.reactions:
        for reaction in message.reactions.results:
            reactions_count += reaction.count
    
    # Подсчет ответов
    replies = 0
    if hasattr(message, 'replies') and message.replies:
        replies = getattr(message.replies, 'replies', 0) or 0
    
    # Формирование URL
    url = f"https://t.me/{channel_username}/{message_id}"
    
    # Генерация хэша для дедупликации
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

### Система алертов

```python
async def _check_alerts(self, message_data: Dict[str, Any], text: str) -> Dict[str, Any]:
    """Проверка сообщения на алерт-ключевые слова"""
    
    if not text:
        return message_data
    
    # Проверка через систему алертов приложения
    is_alert, category, emoji, priority, matched_words = self.app_instance.check_alert_keywords(text)
    
    if is_alert:
        logger.warning(f"🚨 АЛЕРТ обнаружен: {category} в @{message_data['channel_username']}")
        
        # Добавление алерт метаданных
        message_data.update({
            'is_alert': True,
            'alert_category': category,
            'alert_emoji': emoji,
            'alert_priority': priority,
            'alert_keywords': matched_words
        })
        
        # Форматирование текста с алерт заголовком
        original_text = message_data.get('text', '')
        alert_text = self.app_instance.format_alert_message(
            original_text, message_data['channel_username'], 
            emoji, category, matched_words
        )
        message_data['text'] = alert_text
    
    return message_data
```

### Фильтрация медиа групп

```python
async def _process_media_group(self, message, has_media: bool) -> bool:
    """Предотвращение дублирования медиа групп"""
    
    if has_media and hasattr(message, 'grouped_id') and message.grouped_id:
        grouped_id = message.grouped_id
        
        if grouped_id in self.processed_media_groups:
            logger.debug(f"🔄 Медиа группа {grouped_id} уже обработана, пропускаем")
            return False
        
        # Отмечаем группу как обработанную
        self.processed_media_groups.add(grouped_id)
        
        # Очистка старых групп (память)
        if len(self.processed_media_groups) > 1000:
            self.processed_media_groups.clear()
            logger.debug("🧹 Очищен кэш медиа групп")
    
    return True
```

---

## 💾 SubscriptionCacheManager - Кэш подписок

**Файл**: `src/monitoring/subscription_cache.py` (68 строк)  
**Функция**: Кэширование подписок для быстрого старта системы

### Архитектура кэша

```python
class SubscriptionCacheManager:
    def __init__(self, cache_file: str = "config/subscriptions_cache.json"):
        self.subscription_cache_file = cache_file
        self.subscribed_channels: Set[str] = set()
```

### Операции с кэшем

#### 📄 Загрузка кэша
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

#### 💾 Сохранение кэша
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

### Методы управления

```python
# Проверка наличия в кэше
def is_channel_cached_as_subscribed(self, channel_username: str) -> bool:
    return channel_username in self.subscribed_channels

# Добавление в кэш
def add_channel_to_cache(self, channel_username: str):
    self.subscribed_channels.add(channel_username)
    self.save_subscription_cache()

# Получение статистики
def get_cache_stats(self) -> dict:
    return {
        'total_subscribed': len(self.subscribed_channels),
        'cache_file': self.subscription_cache_file,
        'file_exists': os.path.exists(self.subscription_cache_file)
    }
```

### Преимущества кэширования

#### ⚡ Оптимизация времени запуска
- **Без кэша**: 30+ минут для 80 каналов (проверка каждого)
- **С кэшем**: ~30 секунд (быстрая загрузка известных каналов)
- **Приоритизация**: кешированные каналы обрабатываются первыми

#### 🛡️ Защита от блокировок
- **Минимум запросов**: не проверяем уже известные подписки
- **Rate limit**: меньше нагрузки на Telegram API
- **Graceful degradation**: система работает даже без кэша

---

## 📱 TelegramMonitor - Telethon клиент

**Файл**: `src/telegram_client.py` (414 строк)  
**Функция**: Подключение к Telegram API, управление сессиями

### Инициализация клиента

```python
class TelegramMonitor:
    def __init__(self, api_id: int, api_hash: str, database):
        self.api_id = api_id
        self.api_hash = api_hash
        self.database = database
        self.client = None
        self.is_connected = False
        
        # Кэш для оптимизации (ограниченный размер для VPS)
        self.channels_cache = {}
        self.messages_cache = {}
        self.cache_max_size = 1000
        
    async def initialize(self):
        """Инициализация Telethon клиента с сессией"""
        try:
            # Путь к файлу сессии
            session_path = Path('sessions/news_monitor_session')
            session_path.parent.mkdir(exist_ok=True)
            
            # Создание клиента
            self.client = TelegramClient(
                str(session_path),
                self.api_id,
                self.api_hash,
                device_model="News Monitor Bot",
                system_version="1.0",
                app_version="1.0"
            )
            
            # Подключение
            await self.client.start()
            
            if await self.client.is_user_authorized():
                self.is_connected = True
                logger.info("✅ Telegram клиент подключен и авторизован")
            else:
                logger.error("❌ Telegram клиент не авторизован")
                
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Telegram клиента: {e}")
```

### Управление подключениями

```python
async def get_channel_entity(self, channel_username: str):
    """Получение entity канала с кэшированием"""
    
    # Проверяем кэш
    if channel_username in self.channels_cache:
        return self.channels_cache[channel_username]
    
    try:
        # Получаем entity от Telegram
        entity = await self.client.get_entity(channel_username)
        
        # Кэшируем с ограничением размера
        if len(self.channels_cache) >= self.cache_max_size:
            # Удаляем старые записи
            oldest_key = next(iter(self.channels_cache))
            del self.channels_cache[oldest_key]
        
        self.channels_cache[channel_username] = entity
        return entity
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения entity для {channel_username}: {e}")
        return None
```

---

## 🔄 Интеграция компонентов

### Схема взаимодействия

```python
# В NewsMonitorWithBot (src/core/app.py)
async def initialize_components(self):
    """Инициализация системы мониторинга"""
    
    # 1. Создание компонентов
    self.telegram_monitor = TelegramMonitor(api_id, api_hash, self.database)
    await self.telegram_monitor.initialize()
    
    # 2. Обработчик сообщений
    self.message_processor = MessageProcessor(self.database, self)
    
    # 3. Мониторинг каналов с настройками
    self.channel_monitor = ChannelMonitor(
        self.telegram_monitor,
        self.subscription_cache,
        self.message_processor,
        self.config_loader  # Передаем для загрузки таймаутов
    )
    
    # 4. Запуск real-time обработки
    await self.channel_monitor.setup_realtime_handlers()
```

### Основной цикл мониторинга

```python
async def monitoring_cycle(self):
    """Главный цикл системы"""
    
    # Загрузка кэша подписок
    self.subscription_cache.load_subscription_cache()
    
    # Настройка real-time обработчиков
    await self.channel_monitor.setup_realtime_handlers()
    
    # Запуск Telegram бота
    if self.telegram_bot:
        bot_listener_task = asyncio.create_task(
            self.telegram_bot.start_listening()
        )
        logger.info("👂 Запущен прослушиватель команд бота")
    
    # Бесконечный цикл с периодическими задачами
    while self.running:
        try:
            # Периодические задачи (каждый час)
            if current_time - last_status_update >= 3600:
                await self.send_status_update()
                last_status_update = current_time
            
            await asyncio.sleep(30)  # Основной цикл проверки
            
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле мониторинга: {e}")
            await asyncio.sleep(60)
```

---

## 🔍 Диагностика проблем

### Проверка состояния мониторинга

#### 📊 Логи системы
```bash
# Статус подписок
grep "📡.*мониторинг" logs/news_monitor.log

# Rate limits
grep "Rate limit\|wait of" logs/news_monitor.log

# Новые сообщения
grep "📥 Получено сообщение" logs/news_monitor.log

# Ошибки обработки
grep "❌.*обработки" logs/news_monitor.log
```

#### 🔧 Команды бота для диагностики
```bash
/status              # Общий статус системы
/force_subscribe     # Принудительная проверка подписок
/channels           # Список мониторимых каналов
```

### Типичные проблемы

#### ⏳ "Wait of X seconds" - Rate limit
```
Причина: Превышение лимитов Telegram API
Решение: Ждать указанное время, увеличить таймауты
```

#### 📡 "Каналы не мониторятся"
```bash
# Проверить кэш подписок
cat config/subscriptions_cache.json

# Очистить кэш
rm config/subscriptions_cache.json

# Принудительная подписка
/force_subscribe
```

#### 🔄 "Сообщения не обрабатываются"
```python
# Проверить состояние мониторинга
if not self.app_instance.monitoring_active:
    # Мониторинг приостановлен

# Проверить подключение Telethon
if not self.telegram_monitor.is_connected:
    # Проблема с подключением
```

### Оптимизация производительности

#### ⚡ Настройки таймаутов (config.yaml)
```yaml
monitoring:
  timeouts:
    batch_size: 6                    # Каналов в пакете (4-8)
    delay_cached_channel: 1          # Для кешированных (1-2 сек)
    delay_between_batches: 8         # Между пакетами (8-15 сек)
    delay_retry_wait: 300            # Rate limit (5-10 мин)
    fast_start_mode: true            # Быстрый старт
    skip_new_on_startup: false       # Пропуск новых при запуске
```

#### 🎯 Профили настроек

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

## 📈 Метрики мониторинга

### Ключевые показатели
- **Время запуска**: 30 секунд (с кэшем) vs 30 минут (без кэша)
- **Активные каналы**: количество каналов с сообщениями за 24ч
- **Скорость обработки**: < 1 секунда от получения до отправки
- **Rate limits**: частота блокировок Telegram API

### Мониторинг в продакшене
```python
# В логах отслеживаем:
logger.info(f"📦 Обрабатываем пакет {batch_num}: {len(batch)} каналов")
logger.info(f"⚡ Настроены real-time обработчики для {len(monitored_channels)} каналов")
logger.warning(f"⏳ Rate limit: ожидание {wait_time} сек")
logger.info(f"📥 Получено сообщение от @{channel_username}")
```

---

*Документация Monitoring актуальна на: январь 2025*  
*Telethon версия: 1.28.0+, Python 3.8+*
