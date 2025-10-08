
"""
🧹 Утилита очистки базы данных
Удаляет старые сообщения, дайджесты и хэши
"""

import asyncio
import sqlite3
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path


sys.path.append(str(Path(__file__).parent.parent))

from src.database import DatabaseManager

async def cleanup_database(days_to_keep: int = 7, clear_all: bool = False):
    """Очистка базы данных от старых записей"""
    
    db_path = "news_monitor.db"
    if not os.path.exists(db_path):
        print(f"❌ База данных {db_path} не найдена")
        return
    
    print(f"🧹 Начинаем очистку базы данных...")
    print(f"📅 Сохраняем данные за последние {days_to_keep} дней")
    
    try:
        
        db_manager = DatabaseManager(db_path)
        await db_manager.initialize()
        
        if clear_all:
            print("⚠️  ПОЛНАЯ ОЧИСТКА ВСЕХ ДАННЫХ!")
            confirm = input("Вы уверены? Введите 'YES' для подтверждения: ")
            if confirm != "YES":
                print("❌ Операция отменена")
                return
            
            
            with db_manager._get_connection() as conn:
                tables = ['messages', 'sent_digests', 'processed_hashes', 'channel_checks', 'statistics']
                for table in tables:
                    result = conn.execute(f"DELETE FROM {table}")
                    print(f"🗑️  Очищена таблица {table}: {result.rowcount} записей")
                conn.commit()
                
                
                conn.execute("VACUUM")
                print("🗜️  База данных сжата")
        else:
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            print(f"📅 Удаляем данные старше {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
            
            with db_manager._get_connection() as conn:
                
                result = conn.execute(
                    "DELETE FROM messages WHERE created_at < ?",
                    (cutoff_date,)
                )
                print(f"📰 Удалено старых сообщений: {result.rowcount}")
                
                
                result = conn.execute(
                    "DELETE FROM sent_digests WHERE sent_at < ?",
                    (cutoff_date,)
                )
                print(f"📨 Удалено старых дайджестов: {result.rowcount}")
                
                
                result = conn.execute(
                    "DELETE FROM processed_hashes WHERE first_seen < ?",
                    (cutoff_date,)
                )
                print(f"🔗 Удалено старых хэшей: {result.rowcount}")
                
                
                result = conn.execute(
                    "DELETE FROM channel_checks WHERE updated_at < ?",
                    (cutoff_date,)
                )
                print(f"📺 Удалено старых проверок каналов: {result.rowcount}")
                
                conn.commit()
                
                
                conn.execute("VACUUM")
                print("🗜️  База данных сжата")
        
        
        with db_manager._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM messages")
            messages_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM sent_digests")
            digests_count = cursor.fetchone()[0]
            
            print(f"\n📊 Текущее состояние базы:")
            print(f"📰 Сообщений: {messages_count}")
            print(f"📨 Дайджестов: {digests_count}")
            
            
            db_size = os.path.getsize(db_path) / 1024 / 1024
            print(f"💾 Размер базы: {db_size:.2f} MB")
        
        print("✅ Очистка завершена!")
        
    except Exception as e:
        print(f"❌ Ошибка очистки: {e}")
        return False
    
    return True

async def main():
    """Главная функция"""
    print("🧹 Утилита очистки базы данных")
    print("="*50)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "all":
            
            await cleanup_database(clear_all=True)
        else:
            
            try:
                days = int(sys.argv[1])
                await cleanup_database(days_to_keep=days)
            except ValueError:
                print("❌ Неверный параметр. Используйте число дней или 'all'")
    else:
        
        print("Выберите режим очистки:")
        print("1. Удалить данные старше N дней")
        print("2. Полная очистка всех данных")
        print("3. Отмена")
        
        choice = input("Ваш выбор (1-3): ")
        
        if choice == "1":
            try:
                days = int(input("Количество дней для сохранения (по умолчанию 7): ") or "7")
                await cleanup_database(days_to_keep=days)
            except ValueError:
                print("❌ Неверное число дней")
        elif choice == "2":
            await cleanup_database(clear_all=True)
        else:
            print("❌ Операция отменена")

if __name__ == "__main__":
    asyncio.run(main())
