# 🗄️ DATABASE - Система хранения данных

## 🎯 Обзор

SQLite база данных оптимизированная для VPS с ограниченными ресурсами. Хранит новости, метаданные каналов, статистику работы и обеспечивает дедупликацию сообщений.

**Файл**: `src/database.py` (790 строк)  
**База данных**: `news_monitor.db` (SQLite)  
**Подключение**: `aiosqlite` для асинхронных операций

---

## 🏗️ Архитектура базы данных

### Схема таблиц

```sql
-- 📰 ОСНОВНАЯ ТАБЛИЦА: Сообщения и новости
messages (
    id TEXT PRIMARY KEY,              -- Уникальный ID сообщения
    channel_username TEXT NOT NULL,   -- @channel_name
    channel_name TEXT,                -- Человекочитаемое название
    channel_region TEXT,              -- Регион (kamchatka, sakhalin, etc)
    channel_category TEXT,            -- Категория канала
    message_id INTEGER,               -- ID сообщения в Telegram
    text TEXT,                        -- Содержимое сообщения
    date TIMESTAMP,                   -- Дата публикации
    views INTEGER DEFAULT 0,          -- Количество просмотров
    forwards INTEGER DEFAULT 0,       -- Количество пересылок
    replies INTEGER DEFAULT 0,        -- Количество ответов
    reactions_count INTEGER DEFAULT 0, -- Количество реакций
    url TEXT,                         -- Ссылка на сообщение
    content_hash TEXT UNIQUE,         -- Хэш для дедупликации
    processed BOOLEAN DEFAULT FALSE,  -- Обработано ли сообщение
    ai_score INTEGER DEFAULT 0,       -- AI оценка важности
    ai_analysis TEXT,                 -- JSON с анализом AI
    ai_suitable BOOLEAN DEFAULT FALSE, -- Подходящее для публикации
    ai_priority TEXT DEFAULT 'low',   -- Приоритет (low/medium/high)
    selected_for_output BOOLEAN DEFAULT FALSE, -- Выбрано для вывода
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

-- 📡 СОСТОЯНИЕ КАНАЛОВ: Последние проверки
channel_checks (
    channel_username TEXT PRIMARY KEY,
    last_check_time TIMESTAMP,        -- Время последней проверки
    last_message_id INTEGER,          -- Последний обработанный ID
    messages_processed INTEGER DEFAULT 0, -- Количество обработанных
    errors_count INTEGER DEFAULT 0,   -- Количество ошибок
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

-- 📊 СТАТИСТИКА: Ежедневная аналитика
statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE,                        -- Дата статистики
    total_messages INTEGER DEFAULT 0, -- Всего сообщений
    processed_messages INTEGER DEFAULT 0, -- Обработано
    selected_messages INTEGER DEFAULT 0,  -- Отобрано для вывода
    ai_requests INTEGER DEFAULT 0,    -- Запросы к AI
    tokens_used INTEGER DEFAULT 0,    -- Потраченные токены
    channels_checked INTEGER DEFAULT 0, -- Проверено каналов
    errors_count INTEGER DEFAULT 0,   -- Количество ошибок
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

-- 🔄 ДЕДУПЛИКАЦИЯ: Предотвращение дубликатов
processed_hashes (
    content_hash TEXT PRIMARY KEY,    -- SHA256 хэш содержимого
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Первое обнаружение
    count INTEGER DEFAULT 1          -- Количество повторов
)

-- 📰 ДАЙДЖЕСТЫ: Отслеживание отправленных дайджестов
sent_digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE,                        -- Дата дайджеста
    news_count INTEGER,               -- Количество новостей
    news_ids TEXT,                    -- Список ID новостей (CSV)
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Индексы для оптимизации
```sql
CREATE INDEX idx_messages_channel ON messages(channel_username);
CREATE INDEX idx_messages_date ON messages(date);
CREATE INDEX idx_messages_score ON messages(ai_score);
CREATE INDEX idx_messages_selected ON messages(selected_for_output);
CREATE INDEX idx_hash_lookup ON processed_hashes(content_hash);
```

---

## ⚙️ Класс DatabaseManager

### Инициализация и оптимизация

```python
class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = threading.Lock()  # Thread safety
        
    async def initialize(self):
        """Создание таблиц + оптимизация SQLite"""
        # Настройки производительности
        conn.execute("PRAGMA journal_mode = WAL")    # Write-Ahead Logging
        conn.execute("PRAGMA synchronous = NORMAL")  # Баланс скорости/надежности  
        conn.execute("PRAGMA cache_size = 10000")    # 10MB кэш
        conn.execute("PRAGMA temp_store = MEMORY")   # Временные данные в RAM
```

### Ключевые концепции

#### 🔄 Асинхронность
- **aiosqlite**: неблокирующие операции с базой
- **executor**: тяжелые операции в отдельном потоке
- **connection pooling**: переиспользование соединений

#### 🛡️ Thread Safety
- **threading.Lock**: защита от гонки потоков
- **SQLite WAL mode**: поддержка concurrent reads
- **Timeout 30s**: защита от deadlocks

#### 🎯 Оптимизация для VPS
- **Ограниченный кэш**: 10MB для экономии RAM
- **Batch operations**: пакетные вставки для скорости
- **Smart indexing**: индексы только на нужные поля

---

## 📝 Основные операции с данными

### Сохранение сообщений

#### Одиночное сохранение
```python
async def save_message(self, message_data: Dict) -> bool:
    """Сохранение одного сообщения с проверкой дубликатов"""
    # 1. Проверка дедупликации по content_hash
    if content_hash:
        cursor = await db.execute(
            "SELECT id FROM messages WHERE content_hash = ?", 
            (content_hash,)
        )
        if await cursor.fetchone():
            logger.debug(f"🔄 Дубликат сообщения: {message_data['id']}")
            return False
    
    # 2. Подготовка JSON данных (AI анализ)
    ai_analysis_json = None
    if message_data.get('ai_analysis'):
        ai_analysis_json = json.dumps(message_data['ai_analysis'], ensure_ascii=False)
    
    # 3. Вставка в messages таблицу
    await db.execute("""INSERT OR REPLACE INTO messages (...) VALUES (...)""")
    
    # 4. Сохранение хэша для дедупликации
    await db.execute("""
        INSERT OR REPLACE INTO processed_hashes (content_hash, first_seen, count)
        VALUES (?, ?, COALESCE((SELECT count + 1 FROM processed_hashes WHERE content_hash = ?), 1))
    """, (content_hash, datetime.now(), content_hash))
```

#### Пакетное сохранение
```python
async def save_messages_batch(self, messages: List[Dict]) -> int:
    """Эффективное сохранение большого количества сообщений"""
    saved_count = 0
    async with aiosqlite.connect(self.db_path) as db:
        for message_data in messages:
            # Проверка дубликатов + вставка
            # ... аналогично save_message
            saved_count += 1
        await db.commit()  # Один коммит для всей пачки
    
    logger.info(f"💾 Пакетное сохранение: {saved_count}/{len(messages)} сообщений")
    return saved_count
```

### Получение данных

#### Топ новости за период
```python
async def get_top_news_for_period(
    self, start_date, end_date, 
    region: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Получить самые популярные новости с гибкой фильтрацией"""
    
    # Формула популярности
    query = """
        SELECT *, 
        (views + forwards * 2 + replies * 3 + reactions_count * 5) as popularity_score
        FROM messages 
        WHERE date >= ? AND date <= ? AND text IS NOT NULL AND text != ''
    """
    
    # Фильтры
    if channel:          # Приоритет конкретному каналу
        query += " AND channel_username = ?"
    elif region:         # Или по региону
        query += " AND channel_region = ?"
    
    # Сортировка по популярности
    query += " ORDER BY popularity_score DESC, date DESC LIMIT ?"
```

#### Статистика и аналитика
```python
async def get_active_channels_count(self) -> int:
    """Количество активных каналов за последние 24 часа"""
    query = """
        SELECT COUNT(DISTINCT channel_username) as active_count
        FROM messages 
        WHERE date >= datetime('now', '-24 hours')
    """

async def get_latest_message_info(self) -> Dict[str, Any]:
    """Информация о последнем сообщении для статуса"""
    query = """
        SELECT channel_username, channel_name, text, date, created_at
        FROM messages 
        WHERE text IS NOT NULL AND text != ''
        ORDER BY created_at DESC LIMIT 1
    """
    
    # Формирование превью (первые 3 слова)
    words = text.split()[:3]
    preview = ' '.join(words) + ('...' if len(words) == 3 else '')
```

---

## 🔄 Дедупликация сообщений

### Алгоритм предотвращения дубликатов

```python
def generate_content_hash(message_text: str, channel_username: str) -> str:
    """Генерация уникального хэша для дедупликации"""
    content = f"{channel_username}:{message_text}"
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

# Проверка при сохранении
content_hash = message_data.get('content_hash')
if content_hash:
    cursor = await db.execute(
        "SELECT id FROM messages WHERE content_hash = ?",
        (content_hash,)
    )
    if await cursor.fetchone():
        return False  # Дубликат найден, не сохраняем
```

### Статистика дубликатов
```python
# Таблица processed_hashes ведет счетчик повторов
INSERT OR REPLACE INTO processed_hashes (content_hash, first_seen, count)
VALUES (?, ?, COALESCE((SELECT count + 1 FROM processed_hashes WHERE content_hash = ?), 1))
```

**Результат**: система автоматически отбрасывает повторные публикации одного и того же контента.

---

## 📊 Система статистики

### Ежедневная аналитика
```python
async def get_today_stats(self) -> Dict[str, int]:
    """Статистика за текущий день"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Подсчет сообщений
    total_query = "SELECT COUNT(*) FROM messages WHERE DATE(created_at) = ?"
    selected_query = "SELECT COUNT(*) FROM messages WHERE DATE(created_at) = ? AND selected_for_output = 1"
    
    return {
        'total_messages': total_count,
        'selected_messages': selected_count,
        'date': today
    }
```

### Мониторинг каналов
```python
async def update_last_check_time(self, channel_username: str, check_time: datetime):
    """Обновление времени последней проверки канала"""
    await db.execute("""
        INSERT OR REPLACE INTO channel_checks (
            channel_username, last_check_time, updated_at
        ) VALUES (?, ?, ?)
    """, (channel_username, check_time.isoformat(), datetime.now()))
```

---

## 📰 Дайджест система

### Отслеживание отправленных дайджестов
```python
async def mark_digest_sent(self, news_ids: List[str]) -> bool:
    """Отметить дайджест как отправленный"""
    today = datetime.now().date()
    await db.execute("""
        INSERT INTO sent_digests (date, news_count, news_ids)
        VALUES (?, ?, ?)
    """, (today, len(news_ids), ','.join(news_ids)))

async def was_digest_sent_today(self) -> bool:
    """Проверить, был ли дайджест отправлен сегодня"""
    today = datetime.now().date()
    cursor = await db.execute(
        "SELECT COUNT(*) FROM sent_digests WHERE date = ?", (today,)
    )
    result = await cursor.fetchone()
    return result[0] > 0
```

### Неотправленные новости
```python
async def get_unsent_news_today(self, limit: int = 999999) -> List[Dict]:
    """Получить новости, которые еще не включались в дайджесты"""
    # 1. Получаем ID уже отправленных новостей
    sent_ids = set()
    for row in sent_results:
        if row[0]:
            sent_ids.update(row[0].split(','))
    
    # 2. Исключаем их из выборки
    for row in rows:
        message_data = dict(zip(columns, row))
        if message_data['id'] in sent_ids:
            continue  # Пропускаем уже отправленные
        results.append(message_data)
```

---

## 🛠️ Обслуживание базы данных

### Очистка старых данных
```python
async def cleanup_old_data(self, days_to_keep: int = 30):
    """Автоматическая очистка для экономии места"""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    # Удаляем старые сообщения
    cursor = await db.execute("DELETE FROM messages WHERE date < ?", (cutoff_date,))
    deleted_messages = cursor.rowcount
    
    # Удаляем старые хэши
    await db.execute("DELETE FROM processed_hashes WHERE first_seen < ?", (cutoff_date,))
    
    # Оптимизируем базу
    await db.execute("VACUUM")
    
    logger.info(f"🧹 Очистка БД: удалено {deleted_messages} старых сообщений")
```

### Оптимизация производительности
```python
async def clear_cache(self):
    """Очистка кэша SQLite"""
    async with aiosqlite.connect(self.db_path) as db:
        await db.execute("PRAGMA optimize")
```

---

## 🔗 Связи с другими модулями

### Входящие данные
- **← MessageProcessor**: сохранение новых сообщений
- **← ChannelMonitor**: обновление статуса каналов
- **← TelegramBot**: запросы статистики и команд

### Исходящие данные  
- **→ DigestGenerator**: данные для генерации дайджестов
- **→ TelegramBot**: статистика для команд (/status, /stats)
- **→ WebInterface**: данные для веб-панели

### Схема потока данных
```
Telegram Channel → MessageProcessor → Database.save_message()
                                          ↓
TelegramBot.digest() → DigestGenerator → Database.get_top_news_for_period()
                                          ↓
TelegramBot.status() ← Database.get_statistics() ← Database
```

---

## 🔍 Диагностика проблем

### Проверка состояния базы
```bash
# Размер базы данных
ls -lh news_monitor.db

# Подключение к базе
sqlite3 news_monitor.db

# Основные запросы
.tables                                    # Список таблиц
SELECT COUNT(*) FROM messages;            # Количество сообщений
SELECT COUNT(*) FROM channel_checks;      # Количество каналов
SELECT * FROM statistics ORDER BY date DESC LIMIT 5;  # Последняя статистика
```

### Анализ производительности
```sql
-- Самые активные каналы
SELECT channel_username, COUNT(*) as msg_count 
FROM messages 
WHERE date >= datetime('now', '-7 days')
GROUP BY channel_username 
ORDER BY msg_count DESC 
LIMIT 10;

-- Размер таблиц
SELECT name, SUM(pgsize) as size_bytes 
FROM dbstat 
GROUP BY name 
ORDER BY size_bytes DESC;

-- Эффективность индексов
EXPLAIN QUERY PLAN SELECT * FROM messages WHERE channel_username = 'test';
```

### Типичные проблемы

#### Медленные запросы
```sql
-- Проверить использование индексов
EXPLAIN QUERY PLAN SELECT * FROM messages WHERE date > '2025-01-01';

-- Пересоздать индексы если нужно
DROP INDEX IF EXISTS idx_messages_date;
CREATE INDEX idx_messages_date ON messages(date);
```

#### Блокировки базы
```bash
# Проверить WAL файлы
ls -la news_monitor.db*

# Если база заблокирована
fuser news_monitor.db        # Найти процессы
kill -9 <PID>               # Завершить если нужно
```

#### Переполнение диска
```python
# В коде есть автоочистка
await database.cleanup_old_data(days_to_keep=30)

# Или вручную
DELETE FROM messages WHERE date < datetime('now', '-30 days');
VACUUM;
```

---

## 📈 Метрики производительности

### Целевые показатели
- **Вставка сообщения**: < 10ms
- **Batch вставка 100 сообщений**: < 100ms  
- **Топ новости за неделю**: < 500ms
- **Размер базы**: < 500MB для 30 дней данных
- **Использование RAM**: < 50MB кэша

### Мониторинг в продакшене
```python
# Логи производительности
logger.info(f"💾 Пакетное сохранение: {saved_count}/{len(messages)} сообщений")
logger.info(f"📊 Найдено {len(results)} топ новостей за период")

# Проверка размера базы
db_size = os.path.getsize(self.db_path) / (1024 * 1024)  # MB
if db_size > 1000:  # Больше 1GB
    logger.warning(f"⚠️ База данных большая: {db_size:.1f}MB")
```

---

*Документация Database актуальна на: январь 2025*  
*SQLite версия: 3.31+ с поддержкой WAL mode*
