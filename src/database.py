"""
🗄️ Database Manager Module
Модуль для работы с SQLite базой данных
Оптимизирован под VPS с ограниченными ресурсами
"""

import sqlite3
import aiosqlite
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from loguru import logger
import json
import asyncio
import threading
from pathlib import Path


class DatabaseManager:
    """Менеджер базы данных для хранения новостей и метаданных"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = threading.Lock()
        
        # Создаем директорию если не существует
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🗄️ DatabaseManager инициализирован: {db_path}")
    
    def _get_connection(self):
        """Получение соединения с базой данных"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row  # Доступ к колонкам по имени
        return conn
    
    async def initialize(self):
        """Инициализация базы данных и создание таблиц"""
        try:
            def _init_db():
                with self._get_connection() as conn:
                    # Создаем таблицы
                    self._create_tables_sync(conn)
                    
                    # Настройки оптимизации SQLite
                    conn.execute("PRAGMA journal_mode = WAL")  # Улучшенная производительность
                    conn.execute("PRAGMA synchronous = NORMAL")  # Баланс скорости и надежности
                    conn.execute("PRAGMA cache_size = 10000")  # 10MB кэш
                    conn.execute("PRAGMA temp_store = MEMORY")  # Временные данные в RAM
                    
                    conn.commit()
            
            # Выполняем в отдельном потоке чтобы не блокировать event loop
            await asyncio.get_event_loop().run_in_executor(None, _init_db)
            
            logger.info("✅ База данных инициализирована")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации БД: {e}")
            raise
    
    def _create_tables_sync(self, conn: sqlite3.Connection):
        """Создание таблиц базы данных (синхронная версия)"""
        
        # Таблица сообщений
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                channel_username TEXT NOT NULL,
                channel_name TEXT,
                channel_region TEXT,
                channel_category TEXT,
                message_id INTEGER,
                text TEXT,
                date TIMESTAMP,
                views INTEGER DEFAULT 0,
                forwards INTEGER DEFAULT 0,
                replies INTEGER DEFAULT 0,
                reactions_count INTEGER DEFAULT 0,
                url TEXT,
                content_hash TEXT UNIQUE,
                processed BOOLEAN DEFAULT FALSE,
                ai_score INTEGER DEFAULT 0,
                ai_analysis TEXT,  -- JSON
                ai_suitable BOOLEAN DEFAULT FALSE,
                ai_priority TEXT DEFAULT 'low',
                selected_for_output BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица для отслеживания последних проверок каналов
        conn.execute("""
            CREATE TABLE IF NOT EXISTS channel_checks (
                channel_username TEXT PRIMARY KEY,
                last_check_time TIMESTAMP,
                last_message_id INTEGER,
                messages_processed INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица статистики
        conn.execute("""
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                total_messages INTEGER DEFAULT 0,
                processed_messages INTEGER DEFAULT 0,
                selected_messages INTEGER DEFAULT 0,
                ai_requests INTEGER DEFAULT 0,
                tokens_used INTEGER DEFAULT 0,
                channels_checked INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица для дедупликации
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_hashes (
                content_hash TEXT PRIMARY KEY,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                count INTEGER DEFAULT 1
            )
        """)
        
        # Таблица для отслеживания отправленных дайджестов
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sent_digests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                news_count INTEGER,
                news_ids TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Создаем индексы для оптимизации
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel_username)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_date ON messages(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_score ON messages(ai_score)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_selected ON messages(selected_for_output)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hash_lookup ON processed_hashes(content_hash)")
    
    async def save_message(self, message_data: Dict) -> bool:
        """Сохранение сообщения в базу данных"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Проверяем дубликаты по хэшу
                content_hash = message_data.get('content_hash')
                if content_hash:
                    cursor = await db.execute(
                        "SELECT id FROM messages WHERE content_hash = ?",
                        (content_hash,)
                    )
                    if await cursor.fetchone():
                        logger.debug(f"🔄 Дубликат сообщения: {message_data['id']}")
                        return False
                
                # Подготавливаем данные
                ai_analysis_json = None
                if message_data.get('ai_analysis'):
                    ai_analysis_json = json.dumps(message_data['ai_analysis'], ensure_ascii=False)
                
                # Сохраняем сообщение
                await db.execute("""
                    INSERT OR REPLACE INTO messages (
                        id, channel_username, channel_name, channel_region, channel_category,
                        message_id, text, date, views, forwards, replies, reactions_count,
                        url, content_hash, processed, ai_score, ai_analysis, ai_suitable,
                        ai_priority, selected_for_output
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    message_data['id'],
                    message_data['channel_username'],
                    message_data.get('channel_name'),
                    message_data.get('channel_region'),
                    message_data.get('channel_category'),
                    message_data.get('message_id'),
                    message_data.get('text'),
                    message_data.get('date'),
                    message_data.get('views', 0),
                    message_data.get('forwards', 0),
                    message_data.get('replies', 0),
                    message_data.get('reactions_count', 0),
                    message_data.get('url'),
                    content_hash,
                    message_data.get('processed', False),
                    message_data.get('ai_score', 0),
                    ai_analysis_json,
                    message_data.get('ai_suitable', False),
                    message_data.get('ai_priority', 'low'),
                    message_data.get('selected_for_output', False)
                ))
                
                # Сохраняем хэш для дедупликации
                if content_hash:
                    await db.execute("""
                        INSERT OR REPLACE INTO processed_hashes (content_hash, first_seen, count)
                        VALUES (?, ?, COALESCE((SELECT count + 1 FROM processed_hashes WHERE content_hash = ?), 1))
                    """, (content_hash, datetime.now(), content_hash))
                
                await db.commit()
                
                logger.debug(f"💾 Сообщение сохранено: {message_data['id']}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения сообщения: {e}")
            return False
    
    async def save_messages_batch(self, messages: List[Dict]) -> int:
        """Пакетное сохранение сообщений"""
        saved_count = 0
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                for message_data in messages:
                    try:
                        # Проверяем дубликаты
                        content_hash = message_data.get('content_hash')
                        if content_hash:
                            cursor = await db.execute(
                                "SELECT id FROM messages WHERE content_hash = ?",
                                (content_hash,)
                            )
                            if await cursor.fetchone():
                                continue
                        
                        # Подготавливаем данные
                        ai_analysis_json = None
                        if message_data.get('ai_analysis'):
                            ai_analysis_json = json.dumps(message_data['ai_analysis'], ensure_ascii=False)
                        
                        # Сохраняем
                        await db.execute("""
                            INSERT OR REPLACE INTO messages (
                                id, channel_username, channel_name, channel_region, channel_category,
                                message_id, text, date, views, forwards, replies, reactions_count,
                                url, content_hash, processed, ai_score, ai_analysis, ai_suitable,
                                ai_priority, selected_for_output
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            message_data['id'], message_data['channel_username'],
                            message_data.get('channel_name'), message_data.get('channel_region'),
                            message_data.get('channel_category'), message_data.get('message_id'),
                            message_data.get('text'), message_data.get('date'),
                            message_data.get('views', 0), message_data.get('forwards', 0),
                            message_data.get('replies', 0), message_data.get('reactions_count', 0),
                            message_data.get('url'), content_hash,
                            message_data.get('processed', False), message_data.get('ai_score', 0),
                            ai_analysis_json, message_data.get('ai_suitable', False),
                            message_data.get('ai_priority', 'low'), message_data.get('selected_for_output', False)
                        ))
                        
                        saved_count += 1
                        
                    except Exception as e:
                        logger.error(f"❌ Ошибка сохранения сообщения {message_data.get('id')}: {e}")
                
                await db.commit()
                
            logger.info(f"💾 Пакетное сохранение: {saved_count}/{len(messages)} сообщений")
            return saved_count
            
        except Exception as e:
            logger.error(f"❌ Ошибка пакетного сохранения: {e}")
            return 0
    
    async def get_last_check_time(self, channel_username: str) -> Optional[datetime]:
        """Получение времени последней проверки канала"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT last_check_time FROM channel_checks WHERE channel_username = ?",
                    (channel_username,)
                )
                result = await cursor.fetchone()
                
                if result and result[0]:
                    return datetime.fromisoformat(result[0])
                
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения времени проверки для {channel_username}: {e}")
            return None
    
    async def update_last_check_time(self, channel_username: str, check_time: datetime):
        """Обновление времени последней проверки канала"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO channel_checks (
                        channel_username, last_check_time, updated_at
                    ) VALUES (?, ?, ?)
                """, (channel_username, check_time.isoformat(), datetime.now()))
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления времени проверки для {channel_username}: {e}")
    
    async def get_selected_news_today(self, limit: int = 999999) -> List[Dict]:
        """Получение отобранных новостей за сегодня"""
        try:
            today = datetime.now().date()
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT * FROM messages 
                    WHERE selected_for_output = TRUE 
                    AND DATE(created_at) = DATE(?)
                    ORDER BY ai_score DESC, reactions_count DESC
                    LIMIT ?
                """, (today, limit))
                
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                results = []
                for row in rows:
                    message_data = dict(zip(columns, row))
                    
                    # Парсим JSON данные
                    if message_data.get('ai_analysis'):
                        try:
                            message_data['ai_analysis'] = json.loads(message_data['ai_analysis'])
                        except:
                            message_data['ai_analysis'] = None
                    
                    results.append(message_data)
                
                return results
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения отобранных новостей: {e}")
            return []
    
    async def mark_as_selected(self, message_ids: List[str]):
        """Отметка сообщений как отобранных для публикации"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                for message_id in message_ids:
                    await db.execute(
                        "UPDATE messages SET selected_for_output = TRUE WHERE id = ?",
                        (message_id,)
                    )
                
                await db.commit()
                logger.info(f"✅ Отмечено как отобранные: {len(message_ids)} сообщений")
                
        except Exception as e:
            logger.error(f"❌ Ошибка отметки сообщений: {e}")
    
    async def cleanup_old_data(self, days_to_keep: int = 30):
        """Очистка старых данных для экономии места"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            async with aiosqlite.connect(self.db_path) as db:
                # Удаляем старые сообщения
                cursor = await db.execute(
                    "DELETE FROM messages WHERE date < ?",
                    (cutoff_date,)
                )
                deleted_messages = cursor.rowcount
                
                # Удаляем старые хэши
                await db.execute(
                    "DELETE FROM processed_hashes WHERE first_seen < ?",
                    (cutoff_date,)
                )
                
                # Оптимизируем базу
                await db.execute("VACUUM")
                
                await db.commit()
                
                logger.info(f"🧹 Очистка БД: удалено {deleted_messages} старых сообщений")
                
        except Exception as e:
            logger.error(f"❌ Ошибка очистки БД: {e}")
    
    async def get_statistics(self) -> Dict:
        """Получение статистики работы"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Общие счетчики
                cursor = await db.execute("SELECT COUNT(*) FROM messages")
                total_messages = (await cursor.fetchone())[0]
                
                cursor = await db.execute("SELECT COUNT(*) FROM messages WHERE processed = TRUE")
                processed_messages = (await cursor.fetchone())[0]
                
                cursor = await db.execute("SELECT COUNT(*) FROM messages WHERE selected_for_output = TRUE")
                selected_messages = (await cursor.fetchone())[0]
                
                # Статистика за сегодня
                today = datetime.now().date()
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM messages WHERE DATE(created_at) = DATE(?)",
                    (today,)
                )
                today_messages = (await cursor.fetchone())[0]
                
                return {
                    'total_messages': total_messages,
                    'processed_messages': processed_messages,
                    'selected_messages': selected_messages,
                    'today_messages': today_messages,
                    'processing_rate': round(processed_messages / max(total_messages, 1) * 100, 2),
                    'selection_rate': round(selected_messages / max(processed_messages, 1) * 100, 2)
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {}
    
    async def clear_cache(self):
        """Очистка кэша базы данных"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("PRAGMA optimize")
            
            logger.info("🧹 Кэш базы данных очищен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки кэша БД: {e}")
    
    async def get_today_stats(self) -> Dict[str, int]:
        """Получить статистику за сегодня"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Подсчитываем статистику
            total_query = """
                SELECT COUNT(*) FROM messages 
                WHERE DATE(created_at) = ?
            """
            
            selected_query = """
                SELECT COUNT(*) FROM messages 
                WHERE DATE(created_at) = ? AND selected_for_output = 1
            """
            
            async with aiosqlite.connect(self.db_path) as db:
                # Общее количество сообщений
                async with db.execute(total_query, (today,)) as cursor:
                    total_result = await cursor.fetchone()
                    total_messages = total_result[0] if total_result else 0
                
                # Количество отобранных сообщений
                async with db.execute(selected_query, (today,)) as cursor:
                    selected_result = await cursor.fetchone()
                    selected_messages = selected_result[0] if selected_result else 0
                
                stats = {
                    'total_messages': total_messages,
                    'selected_messages': selected_messages,
                    'date': today
                }
                
                logger.info(f"📊 Статистика за {today}: {stats}")
                return stats
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {'total_messages': 0, 'selected_messages': 0, 'date': today}

    async def clear_today_stats(self) -> bool:
        """Очистить статистику за сегодня"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            delete_query = """
                DELETE FROM messages 
                WHERE DATE(created_at) = ?
            """
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(delete_query, (today,)) as cursor:
                    deleted_count = cursor.rowcount
                await db.commit()
                
                logger.info(f"🗑️ Очищена статистика за {today}: удалено {deleted_count} записей")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка очистки статистики: {e}")
            return False

    async def mark_digest_sent(self, news_ids: List[str]) -> bool:
        """Отметить дайджест как отправленный"""
        try:
            today = datetime.now().date()
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO sent_digests (date, news_count, news_ids)
                    VALUES (?, ?, ?)
                """, (today, len(news_ids), ','.join(news_ids)))
                
                await db.commit()
                logger.info(f"✅ Дайджест отмечен как отправленный: {len(news_ids)} новостей")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка отметки дайджеста: {e}")
            return False
    
    async def was_digest_sent_today(self) -> bool:
        """Проверить, был ли дайджест отправлен сегодня"""
        try:
            today = datetime.now().date()
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM sent_digests WHERE date = ?",
                    (today,)
                )
                result = await cursor.fetchone()
                
                return result[0] > 0 if result else False
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки дайджеста: {e}")
            return False
    
    async def get_unsent_news_today(self, limit: int = 999999) -> List[Dict]:
        """Получить неотправленные новости за сегодня"""
        try:
            today = datetime.now().date()
            
            # Получаем ID новостей, которые уже были отправлены
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT news_ids FROM sent_digests WHERE date = ?",
                    (today,)
                )
                sent_results = await cursor.fetchall()
                
                sent_ids = set()
                for row in sent_results:
                    if row[0]:
                        sent_ids.update(row[0].split(','))
                
                # Получаем отобранные новости, исключая уже отправленные
                cursor = await db.execute("""
                    SELECT * FROM messages 
                    WHERE selected_for_output = TRUE 
                    AND DATE(created_at) = DATE(?)
                    ORDER BY ai_score DESC, reactions_count DESC
                    LIMIT ?
                """, (today, limit))
                
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                results = []
                for row in rows:
                    message_data = dict(zip(columns, row))
                    
                    # Пропускаем уже отправленные новости
                    if message_data['id'] in sent_ids:
                        continue
                    
                    # Парсим JSON данные
                    if message_data.get('ai_analysis'):
                        try:
                            message_data['ai_analysis'] = json.loads(message_data['ai_analysis'])
                        except:
                            message_data['ai_analysis'] = None
                    
                    results.append(message_data)
                
                return results
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения неотправленных новостей: {e}")
            return []

    async def get_latest_message_info(self) -> Dict[str, Any]:
        """Получить информацию о последнем сообщении"""
        try:
            query = """
                SELECT 
                    channel_username,
                    channel_name,
                    text,
                    date,
                    created_at
                FROM messages 
                WHERE text IS NOT NULL AND text != ''
                ORDER BY created_at DESC 
                LIMIT 1
            """
            
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute(query) as cursor:
                    row = await cursor.fetchone()
                    
                    if row:
                        text = row['text'] or ''
                        words = text.split()[:3]
                        preview = ' '.join(words) + ('...' if len(words) == 3 and len(text.split()) > 3 else '')
                        
                        return {
                            'channel_username': row['channel_username'],
                            'channel_name': row['channel_name'] or row['channel_username'],
                            'text_preview': preview,
                            'date': row['date'],
                            'created_at': row['created_at']
                        }
                    else:
                        return {
                            'channel_username': None,
                            'channel_name': 'Нет данных',
                            'text_preview': 'Сообщений пока нет',
                            'date': None,
                            'created_at': None
                        }
                        
        except Exception as e:
            logger.error(f"❌ Ошибка получения последнего сообщения: {e}")
            return {
                'channel_username': None,
                'channel_name': 'Ошибка БД',
                'text_preview': 'Не удалось получить данные',
                'date': None,
                'created_at': None
            }

    async def get_active_channels_count(self) -> int:
        """Получить количество активных каналов за последние 24 часа"""
        try:
            query = """
                SELECT COUNT(DISTINCT channel_username) as active_count
                FROM messages 
                WHERE date >= datetime('now', '-24 hours')
            """
            
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute(query) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row and row[0] else 0
                    
        except Exception as e:
            logger.error(f"❌ Ошибка подсчета активных каналов: {e}")
            return 0

    async def close(self):
        """Закрытие соединений с базой данных"""
        logger.info("👋 База данных закрыта")
