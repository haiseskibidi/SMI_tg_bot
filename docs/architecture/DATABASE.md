



SQLite база данных оптимизированная для VPS с ограниченными ресурсами. Хранит новости, метаданные каналов, статистику работы и обеспечивает дедупликацию сообщений.

**Файл**: `src/database.py` (790 строк)  
**База данных**: `news_monitor.db` (SQLite)  
**Подключение**: `aiosqlite` для асинхронных операций

---





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


```sql
CREATE INDEX idx_messages_channel ON messages(channel_username);
CREATE INDEX idx_messages_date ON messages(date);
CREATE INDEX idx_messages_score ON messages(ai_score);
CREATE INDEX idx_messages_selected ON messages(selected_for_output);
CREATE INDEX idx_hash_lookup ON processed_hashes(content_hash);
```

---





```python
class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = threading.Lock()  
        
    async def initialize(self):
        """Создание таблиц + оптимизация SQLite"""
        
        conn.execute("PRAGMA journal_mode = WAL")    
        conn.execute("PRAGMA synchronous = NORMAL")  
        conn.execute("PRAGMA cache_size = 10000")    
        conn.execute("PRAGMA temp_store = MEMORY")   
```




- **aiosqlite**: неблокирующие операции с базой
- **executor**: тяжелые операции в отдельном потоке
- **connection pooling**: переиспользование соединений


- **threading.Lock**: защита от гонки потоков
- **SQLite WAL mode**: поддержка concurrent reads
- **Timeout 30s**: защита от deadlocks


- **Ограниченный кэш**: 10MB для экономии RAM
- **Batch operations**: пакетные вставки для скорости
- **Smart indexing**: индексы только на нужные поля

---






```python
async def save_message(self, message_data: Dict) -> bool:
    """Сохранение одного сообщения с проверкой дубликатов"""
    
    if content_hash:
        cursor = await db.execute(
            "SELECT id FROM messages WHERE content_hash = ?", 
            (content_hash,)
        )
        if await cursor.fetchone():
            logger.debug(f"🔄 Дубликат сообщения: {message_data['id']}")
            return False
    
    
    ai_analysis_json = None
    if message_data.get('ai_analysis'):
        ai_analysis_json = json.dumps(message_data['ai_analysis'], ensure_ascii=False)
    
    
    await db.execute("""INSERT OR REPLACE INTO messages (...) VALUES (...)""")
    
    
    await db.execute("""
        INSERT OR REPLACE INTO processed_hashes (content_hash, first_seen, count)
        VALUES (?, ?, COALESCE((SELECT count + 1 FROM processed_hashes WHERE content_hash = ?), 1))
    """, (content_hash, datetime.now(), content_hash))
```


```python
async def save_messages_batch(self, messages: List[Dict]) -> int:
    """Эффективное сохранение большого количества сообщений"""
    saved_count = 0
    async with aiosqlite.connect(self.db_path) as db:
        for message_data in messages:
            
            
            saved_count += 1
        await db.commit()  
    
    logger.info(f"💾 Пакетное сохранение: {saved_count}/{len(messages)} сообщений")
    return saved_count
```




```python
async def get_top_news_for_period(
    self, start_date, end_date, 
    region: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Получить самые популярные новости с гибкой фильтрацией"""
    
    
    query = """
        SELECT *, 
        (views + forwards * 2 + replies * 3 + reactions_count * 5) as popularity_score
        FROM messages 
        WHERE date >= ? AND date <= ? AND text IS NOT NULL AND text != ''
    """
    
    
    if channel:          
        query += " AND channel_username = ?"
    elif region:         
        query += " AND channel_region = ?"
    
    
    query += " ORDER BY popularity_score DESC, date DESC LIMIT ?"
```


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
    
    
    words = text.split()[:3]
    preview = ' '.join(words) + ('...' if len(words) == 3 else '')
```

---





```python
def generate_content_hash(message_text: str, channel_username: str) -> str:
    """Генерация уникального хэша для дедупликации"""
    content = f"{channel_username}:{message_text}"
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


content_hash = message_data.get('content_hash')
if content_hash:
    cursor = await db.execute(
        "SELECT id FROM messages WHERE content_hash = ?",
        (content_hash,)
    )
    if await cursor.fetchone():
        return False  
```


```python

INSERT OR REPLACE INTO processed_hashes (content_hash, first_seen, count)
VALUES (?, ?, COALESCE((SELECT count + 1 FROM processed_hashes WHERE content_hash = ?), 1))
```

**Результат**: система автоматически отбрасывает повторные публикации одного и того же контента.

---




```python
async def get_today_stats(self) -> Dict[str, int]:
    """Статистика за текущий день"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    
    total_query = "SELECT COUNT(*) FROM messages WHERE DATE(created_at) = ?"
    selected_query = "SELECT COUNT(*) FROM messages WHERE DATE(created_at) = ? AND selected_for_output = 1"
    
    return {
        'total_messages': total_count,
        'selected_messages': selected_count,
        'date': today
    }
```


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


```python
async def get_unsent_news_today(self, limit: int = 999999) -> List[Dict]:
    """Получить новости, которые еще не включались в дайджесты"""
    
    sent_ids = set()
    for row in sent_results:
        if row[0]:
            sent_ids.update(row[0].split(','))
    
    
    for row in rows:
        message_data = dict(zip(columns, row))
        if message_data['id'] in sent_ids:
            continue  
        results.append(message_data)
```

---




```python
async def cleanup_old_data(self, days_to_keep: int = 30):
    """Автоматическая очистка для экономии места"""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    
    cursor = await db.execute("DELETE FROM messages WHERE date < ?", (cutoff_date,))
    deleted_messages = cursor.rowcount
    
    
    await db.execute("DELETE FROM processed_hashes WHERE first_seen < ?", (cutoff_date,))
    
    
    await db.execute("VACUUM")
    
    logger.info(f"🧹 Очистка БД: удалено {deleted_messages} старых сообщений")
```


```python
async def clear_cache(self):
    """Очистка кэша SQLite"""
    async with aiosqlite.connect(self.db_path) as db:
        await db.execute("PRAGMA optimize")
```

---




- **← MessageProcessor**: сохранение новых сообщений
- **← ChannelMonitor**: обновление статуса каналов
- **← TelegramBot**: запросы статистики и команд


- **→ DigestGenerator**: данные для генерации дайджестов
- **→ TelegramBot**: статистика для команд (/status, /stats)
- **→ WebInterface**: данные для веб-панели


```
Telegram Channel → MessageProcessor → Database.save_message()
                                          ↓
TelegramBot.digest() → DigestGenerator → Database.get_top_news_for_period()
                                          ↓
TelegramBot.status() ← Database.get_statistics() ← Database
```

---




```bash

ls -lh news_monitor.db


sqlite3 news_monitor.db


.tables                                    
SELECT COUNT(*) FROM messages;            
SELECT COUNT(*) FROM channel_checks;      
SELECT * FROM statistics ORDER BY date DESC LIMIT 5;  
```


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




```sql
-- Проверить использование индексов
EXPLAIN QUERY PLAN SELECT * FROM messages WHERE date > '2025-01-01';

-- Пересоздать индексы если нужно
DROP INDEX IF EXISTS idx_messages_date;
CREATE INDEX idx_messages_date ON messages(date);
```


```bash

ls -la news_monitor.db*


fuser news_monitor.db        
kill -9 <PID>               
```


```python

await database.cleanup_old_data(days_to_keep=30)


DELETE FROM messages WHERE date < datetime('now', '-30 days');
VACUUM;
```

---




- **Вставка сообщения**: < 10ms
- **Batch вставка 100 сообщений**: < 100ms  
- **Топ новости за неделю**: < 500ms
- **Размер базы**: < 500MB для 30 дней данных
- **Использование RAM**: < 50MB кэша


```python

logger.info(f"💾 Пакетное сохранение: {saved_count}/{len(messages)} сообщений")
logger.info(f"📊 Найдено {len(results)} топ новостей за период")


db_size = os.path.getsize(self.db_path) / (1024 * 1024)  
if db_size > 1000:  
    logger.warning(f"⚠️ База данных большая: {db_size:.1f}MB")
```

---

*Документация Database актуальна на: январь 2025*  
*SQLite версия: 3.31+ с поддержкой WAL mode*
