
"""
🔐 Настройка пользовательской авторизации для мониторинга каналов
ВАЖНО: Боты не могут читать каналы, нужен пользовательский аккаунт
"""

import asyncio
import yaml
from telethon import TelegramClient
from loguru import logger
import os
from pathlib import Path
from dotenv import load_dotenv

async def setup_user_authentication():
    """Настройка авторизации пользователя для чтения каналов"""
    
    print("🔐 Настройка авторизации пользователя для мониторинга каналов")
    print("=" * 60)
    print()
    
    
    load_dotenv()

    
    current_dir = Path(__file__).resolve().parent
    repo_root = current_dir.parent if (current_dir.parent / 'config').exists() else current_dir
    config_path = repo_root / 'config' / 'config.yaml'

    print(f"🔗 Путь к конфигурации: {config_path}")

    
    api_id = int(os.getenv('TELEGRAM_API_ID'))
    api_hash = os.getenv('TELEGRAM_API_HASH')

    print(f"📱 API ID: {api_id}")
    print(f"🔑 API Hash: {api_hash[:10]}...")
    print()
    
    try:
        
        
        delete_sessions = str(os.getenv('RESET_TELETHON_SESSION', '0')).lower() in ('1', 'true', 'yes')
        if delete_sessions:
            
            current_dir = Path(__file__).resolve().parent
            repo_root = current_dir.parent if (current_dir.parent / 'config').exists() else current_dir
            sessions_dir = repo_root / 'sessions'
            session_file = sessions_dir / 'news_monitor_session.session'
            try:
                if session_file.exists():
                    session_file.unlink()
                    print(f"🗑️ Удалена старая сессия: {session_file}")
            except Exception as e:
                print(f"⚠️ Не удалось удалить сессию: {e}")
        else:
            print("🔒 Сессия сохраняется: авто-удаление отключено (установите RESET_TELETHON_SESSION=1 для очистки)")
        
        
        current_dir = Path(__file__).resolve().parent
        
        repo_root = current_dir.parent if (current_dir.parent / 'config').exists() else current_dir
        sessions_dir = repo_root / 'sessions'
        sessions_dir.mkdir(exist_ok=True)
        session_path = sessions_dir / 'news_monitor_session'
        
        print(f"🔗 Путь к сессии: {session_path}")
        client = TelegramClient(str(session_path), api_id, api_hash)
        
        print("🔄 Подключение к Telegram...")
        print("💡 ВАЖНО: Вводите НОМЕР ТЕЛЕФОНА, а НЕ bot token!")
        print()
        
        
        await client.start()
        
        
        me = await client.get_me()
        
        if hasattr(me, 'phone') and me.phone:
            print("✅ УСПЕШНО! Авторизация пользователя настроена")
            print(f"👤 Пользователь: {me.first_name} {me.last_name or ''}")
            print(f"📞 Телефон: {me.phone}")
            print()
            
            
            test_channel = "@SMIzametki"
            print(f"🔍 Тестируем доступ к каналу {test_channel}...")
            
            try:
                entity = await client.get_entity(test_channel)
                print(f"✅ Канал найден: {entity.title}")
                
                
                count = 0
                async for message in client.iter_messages(entity, limit=3):
                    if message.text:
                        count += 1
                        print(f"📄 Сообщение {count}: {message.text[:80]}...")
                
                print(f"✅ Успешно получено {count} сообщений")
                print()
                print("🎉 НАСТРОЙКА ЗАВЕРШЕНА! Теперь система может мониторить каналы")
                
            except Exception as e:
                print(f"❌ Ошибка доступа к тестовому каналу: {e}")
                
        else:
            print("❌ ОШИБКА: Подключен бот, а не пользователь")
            print("💡 Перезапустите и введите номер телефона")
        
        await client.disconnect()
        
    except Exception as e:
        print(f"❌ Ошибка настройки: {e}")
        print()
        print("💡 Возможные решения:")
        print("   1. Проверьте API ключи в config.yaml")
        print("   2. Убедитесь что вводите номер телефона, а не bot token")
        print("   3. Проверьте интернет соединение")

if __name__ == "__main__":
    asyncio.run(setup_user_authentication())
