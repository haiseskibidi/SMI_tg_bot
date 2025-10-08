



Система включает набор вспомогательных инструментов для обслуживания, диагностики и деплоя News Monitor Bot. Утилиты покрывают все аспекты администрирования: от авторизации до мониторинга и резервного копирования.

**Расположение**: `tools/` папка  
**Деплой**: systemd сервис + командные справочники  
**Управление**: Kill Switch система + веб-интерфейс

---





```
UTILITIES ECOSYSTEM
├── Setup & Auth               
│   ├── setup_user_auth.py    
│   └── safe_mode.py          
├── Maintenance               
│   ├── cleanup_database.py   
│   ├── backup_channels_config.py 
│   └── add_news_manual.py    
├── Monitoring & Control     
│   ├── Kill Switch система   
│   ├── Web Interface        
│   └── System Commands      
└── Deployment              
    ├── systemd service      
    ├── server_commands.txt  
    └── Environment setup   
```



```python

1. Автономность - каждая утилита работает независимо
2. Безопасность - проверки перед критическими операциями  
3. Логирование - детальная информация о выполнении
4. Интерактивность - пользовательский ввод где необходимо
5. Откат изменений - возможность отмены опасных операций
```

---





**Назначение**: Настройка Telethon авторизации для чтения каналов  
**Файл**: `tools/setup_user_auth.py` (124 строки)



```bash

python tools/setup_user_auth.py


RESET_TELETHON_SESSION=1 python tools/setup_user_auth.py
```



```python
async def setup_user_authentication():
    """Пошаговая настройка авторизации"""
    
    
    api_id = int(os.getenv('TELEGRAM_API_ID'))
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    
    session_path = repo_root / 'sessions' / 'news_monitor_session'
    client = TelegramClient(str(session_path), api_id, api_hash)
    
    
    await client.start()  
    
    
    me = await client.get_me()
    if hasattr(me, 'phone') and me.phone:
        print("✅ УСПЕШНО! Авторизация пользователя настроена")
        
        
        test_channel = "@SMIzametki"
        entity = await client.get_entity(test_channel)
        
        
        async for message in client.iter_messages(entity, limit=3):
            if message.text:
                print(f"📄 Сообщение: {message.text[:80]}...")
```



- **Сохранение сессии**: по умолчанию сессия НЕ удаляется для избежания частых авторизаций
- **Сброс сессии**: через переменную `RESET_TELETHON_SESSION=1`  
- **Проверка корректности**: различение пользователя от бота по наличию номера телефона
- **Тестирование доступа**: автоматическая проверка чтения канала после авторизации



**Назначение**: Запуск системы без мониторинга каналов  
**Файл**: `tools/safe_mode.py` (58 строк)



```bash

python tools/safe_mode.py
```



```python
async def run_safe_mode():
    """Ограниченная функциональность без мониторинга"""
    
    print("🛡️ БЕЗОПАСНЫЙ РЕЖИМ - без мониторинга каналов")
    
    
    db = DatabaseManager("news_monitor.db")
    await db.initialize()
    
    bot = TelegramBot(
        token=config['bot']['token'],
        chat_id=config['bot']['chat_id']
    )
    
    
    if await bot.test_connection():
        await bot.send_message(
            "🛡️ Система запущена в БЕЗОПАСНОМ РЕЖИМЕ\n\n"
            "✅ Мониторинг каналов ОТКЛЮЧЕН\n"
            "📱 Уведомления работают\n"  
            "🖥️ Веб-интерфейс доступен на http://localhost:8080"
        )
```



- ✅ Telegram уведомления  
- ✅ Веб-интерфейс на http://localhost:8080
- ✅ База данных
- ❌ Мониторинг каналов **ОТКЛЮЧЕН**



- **Отладка конфигурации**: проверка настроек без нагрузки на Telegram API
- **Техническое обслуживание**: доступ к данным без активного мониторинга  
- **Восстановление после блокировок**: избежание дополнительных rate limits
- **Тестирование компонентов**: изолированная проверка бота и базы данных

---





**Назначение**: Управление размером базы данных через удаление старых записей  
**Файл**: `tools/cleanup_database.py` (155 строк)



```bash

python tools/cleanup_database.py


python tools/cleanup_database.py 3


python tools/cleanup_database.py all
```



```python
async def cleanup_database(days_to_keep: int = 7, clear_all: bool = False):
    """Селективная или полная очистка данных"""
    
    if clear_all:
        
        confirm = input("Вы уверены? Введите 'YES' для подтверждения: ")
        if confirm != "YES":
            return
            
        
        tables = ['messages', 'sent_digests', 'processed_hashes', 'channel_checks', 'statistics']
        for table in tables:
            result = conn.execute(f"DELETE FROM {table}")
            print(f"🗑️ Очищена таблица {table}: {result.rowcount} записей")
    else:
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        
        result = conn.execute("DELETE FROM messages WHERE created_at < ?", (cutoff_date,))
        print(f"📰 Удалено старых сообщений: {result.rowcount}")
        
        
        result = conn.execute("DELETE FROM sent_digests WHERE sent_at < ?", (cutoff_date,))
        print(f"📨 Удалено старых дайджестов: {result.rowcount}")
        
        
        result = conn.execute("DELETE FROM processed_hashes WHERE first_seen < ?", (cutoff_date,))
        print(f"🔗 Удалено старых хэшей: {result.rowcount}")
        
        
        result = conn.execute("DELETE FROM channel_checks WHERE updated_at < ?", (cutoff_date,))
        print(f"📺 Удалено старых проверок каналов: {result.rowcount}")
    
    
    conn.execute("VACUUM")
    print("🗜️ База данных сжата")
```



```python

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
```



- **Подтверждение полной очистки**: требуется ввод 'YES' для необратимых операций
- **Остановка бота**: рекомендуется остановить систему перед очисткой
- **Резервное копирование**: создание бэкапа важных данных перед операцией
- **Проверка размера**: контроль объема удаляемых данных



**Назначение**: Добавление новостей в систему без мониторинга каналов  
**Файл**: `tools/add_news_manual.py` (96 строк)



```bash

python tools/add_news_manual.py
```



```python
async def add_manual_news():
    """Интерактивное создание новости"""
    
    print("💬 Введите данные новости:")
    
    
    title = input("📰 Заголовок: ").strip()
    text = input("📄 Текст новости: ").strip()
    
    
    source = input("📍 Источник (по умолчанию 'Ручной ввод'): ").strip() or "Ручной ввод"
    region = input("🌍 Регион (sakhalin/kamchatka/other): ").strip() or "other"  
    url = input("🔗 Ссылка (необязательно): ").strip()
    
    
    now = datetime.now()
    message_data = {
        "id": f"manual_{int(now.timestamp())}",
        "channel_username": "@manual",
        "channel_name": source,
        "text": text,
        "date": now,
        "selected_for_output": True,  
        "ai_score": 10,              
        "ai_priority": "high",       
        "content_hash": f"manual_{now.timestamp()}"
    }
    
    
    await db.save_message(message_data)
    
    if await bot.test_connection():
        message = f"📰 **Новая новость добавлена**\n\n**{title}**\n\n{text}"
        if url:
            message += f"\n\n🔗 [Читать полностью]({url})"
        message += f"\n\n📍 {source}"
        
        await bot.send_message(message)
        print("✅ Уведомление отправлено в Telegram")
```



- **Автоматический отбор**: `selected_for_output = True` 
- **Максимальный рейтинг**: `ai_score = 10`
- **Высокий приоритет**: `ai_priority = "high"`
- **Уникальная идентификация**: префикс `manual_` в ID
- **Мгновенное уведомление**: отправка в Telegram после добавления

---





**Назначение**: Автоматическое резервное копирование настроек каналов  
**Файл**: `tools/backup_channels_config.py` (65 строк)



```bash

python tools/backup_channels_config.py
```



```python
def backup_channels_config():
    """Создание резервной копии с управлением версиями"""
    
    
    source = Path('config/channels_config.yaml')
    backup_dir = Path('backups/channels_config')
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    backup_name = f'channels_config_{timestamp}.yaml'
    backup_path = backup_dir / backup_name
    
    
    shutil.copy2(source, backup_path)
    
    
    latest_link = backup_dir / 'latest.yaml'
    if latest_link.exists():
        latest_link.unlink()
    shutil.copy2(backup_path, latest_link)  
    
    print(f'✅ Бэкап создан: {backup_name}')
    print(f'📁 Путь: {backup_path}')
    
    
    cleanup_old_backups(backup_dir)
```



```python
def cleanup_old_backups(backup_dir, keep_count=10):
    """Автоматическое удаление старых бэкапов"""
    
    backup_files = list(backup_dir.glob('channels_config_*.yaml'))
    
    
    backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    
    for file in backup_files[keep_count:]:
        file.unlink()
        print(f'🗑️ Удален старый бэкап: {file.name}')
```



```
backups/channels_config/
├── channels_config_2025-01-20_14-30-15.yaml
├── channels_config_2025-01-20_10-15-22.yaml
├── channels_config_2025-01-19_18-45-33.yaml
├── ...
└── latest.yaml → последний бэкап
```



- **Автоматизация**: добавить в cron для регулярного выполнения
- **Перед изменениями**: создание бэкапа перед редактированием конфигурации
- **Контроль версий**: сохранение истории изменений настроек каналов
- **Быстрое восстановление**: использование latest.yaml для отката

---





**Назначение**: Полная блокировка системы с предотвращением автоперезапусков  
**Файлы**: `src/handlers/commands/basic.py`, `main.py`



```bash

/kill_switch

"✅ ДА, ЗАБЛОКИРОВАТЬ"
```



```python

if __name__ == "__main__":
    
    if os.path.exists("STOP_BOT"):
        print("🛑 НАЙДЕН ФАЙЛ БЛОКИРОВКИ: STOP_BOT")
        print("🚫 БОТ ЗАБЛОКИРОВАН ОТ ЗАПУСКА")  
        print("💡 Удалите файл STOP_BOT для разблокировки")
        exit(0)
    
    asyncio.run(NewsMonitorWithBot().run())


async def confirm_kill_switch(self, message):
    """Выполнение kill switch"""
    
    
    with open("STOP_BOT", "w") as f:
        f.write(f"Kill Switch activated at {datetime.now()}\n")
        f.write("Bot permanently blocked from starting\n")
    
    
    await self.send_message_with_keyboard(
        "🛑 <b>KILL SWITCH АКТИВИРОВАН!</b>\n\n"
        "🔒 Файл блокировки создан\n"
        "🚫 Бот заблокирован от запуска\n\n"
        "💡 Для разблокировки: /unlock",
        keyboard
    )
    
    await asyncio.sleep(3)
    
    
    if self.monitor_bot:
        self.monitor_bot.running = False
    sys.exit(0)
```



```python
async def unlock(self, message: Optional[Dict[str, Any]]) -> None:
    """Разблокировка системы"""
    try:
        if os.path.exists("STOP_BOT"):
            os.remove("STOP_BOT")
            await self.bot.send_message(
                "🔓 <b>Система разблокирована!</b>\n\n"
                "✅ Файл блокировки удален\n"
                "🚀 Теперь можно запустить бота\n\n"
                "💡 Перезапустите: <code>systemctl restart news-monitor.service</code>"
            )
        else:
            await self.bot.send_message("ℹ️ Система не заблокирована")
    except Exception as e:
        await self.bot.send_message(f"❌ Ошибка разблокировки: {e}")
```



- **Приоритет проверки**: Kill Switch проверяется ПЕРЕД инициализацией системы
- **Предотвращение автозапуска**: блокирует systemd и cron перезапуски
- **Подтверждение действия**: требует явного подтверждения пользователя
- **Корректное завершение**: graceful shutdown с уведомлением

---





**Назначение**: Веб-панель для мониторинга системы и базы данных  
**Файл**: `src/web_interface.py` (350+ строк)



```python
class WebInterface:
    def __init__(self, database, system_monitor, port: int = 8080):
        self.database = database
        self.system_monitor = system_monitor
        self.port = port
        
        if not FLASK_AVAILABLE:
            logger.warning("⚠️ Flask не установлен. Веб-интерфейс недоступен.")
            return
        
        self.setup_flask()
```



```python

@app.route('/')
def index():
    return render_template_string(self.get_main_template())


@app.route('/api/stats')  
def get_stats():
    
    stats = loop.run_until_complete(self.database.get_today_stats())
    system_stats = {
        'memory': self.system_monitor.get_memory_usage(),
        'cpu': self.system_monitor.get_cpu_usage(),
        'disk': self.system_monitor.get_disk_usage()
    }
    
    return jsonify({
        'database': stats,
        'system': system_stats,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/news')
def get_news():
    
    
```



- **Статистика базы данных**: количество сообщений, дайджестов, активных каналов
- **Системные метрики**: использование CPU, памяти, дискового пространства  
- **Последние новости**: список с возможностью фильтрации по региону
- **Состояние компонентов**: статус Telegram подключений, мониторинга
- **Live обновления**: автоматическое обновление данных через AJAX



```bash

pip install flask


curl http://localhost:8080
```

---





**Назначение**: Автоматический запуск и управление системой через systemd  
**Конфигурация**: создается при деплое на сервер



```bash

systemctl start news-monitor.service      
systemctl stop news-monitor.service       
systemctl restart news-monitor.service    
systemctl status news-monitor.service     


systemctl enable news-monitor.service     
systemctl disable news-monitor.service    


journalctl -u news-monitor.service -f     
journalctl -u news-monitor.service --since "1 hour ago"  
```



```ini
[Unit]
Description=News Monitor Bot
After=network.target

[Service]
Type=simple
User=news-monitor
WorkingDirectory=/opt/news-monitor/SMI_tg_bot
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=/opt/news-monitor/SMI_tg_bot

[Install]
WantedBy=multi-user.target
```



**Назначение**: Полный справочник команд для управления сервером  
**Файл**: `server_commands.txt` (255 строк)



```bash

/opt/news-monitor/SMI_tg_bot                    
/opt/news-monitor/SMI_tg_bot/logs/              
/opt/news-monitor/SMI_tg_bot/config/            
/opt/news-monitor/SMI_tg_bot/sessions/          


systemctl restart news-monitor.service         
systemctl status news-monitor.service          


tail -f logs/news_monitor.log                  
grep -i "error" logs/news_monitor.log          
grep "$(date +%Y-%m-%d)" logs/news_monitor.log 


git pull                                       
git status                                     


free -h                                        
df -h                                          
ps aux | grep python                          


rm -f config/subscriptions_cache.json         
rm -f sessions/news_monitor_session.session   
```



```bash

systemctl restart news-monitor.service && tail -f logs/news_monitor.log


git pull && systemctl restart news-monitor.service


rm -f config/subscriptions_cache.json && systemctl restart news-monitor.service


systemctl status news-monitor.service && free -h && df -h && ps aux | grep python
```





```python

logging:
  file: logs/news_monitor.log    
  level: INFO                    


logger.add(
    "logs/news_monitor.log",
    rotation="10 MB",              
    retention="30 days",           
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)
```



```bash

grep "✅" logs/news_monitor.log


grep -E "(❌|⚠️)" logs/news_monitor.log


grep "📊 Статистика" logs/news_monitor.log


grep "Telegram клиент" logs/news_monitor.log


grep "📡.*мониторинг" logs/news_monitor.log
```



```python

class SystemMonitor:
    def get_memory_usage(self) -> Dict[str, float]:
        """Использование памяти в MB"""
        
    def get_cpu_usage(self) -> float:
        """Загрузка CPU в процентах"""
        
    def get_disk_usage(self) -> Dict[str, float]:  
        """Использование диска в GB"""
        
    def get_uptime(self) -> str:
        """Время работы системы"""
```

---







```bash

ls -la STOP_BOT


/unlock


rm STOP_BOT
```



```bash

RESET_TELETHON_SESSION=1 python tools/setup_user_auth.py


rm sessions/news_monitor_session.session
python tools/setup_user_auth.py
```



```bash

ls -lah news_monitor.db


python tools/cleanup_database.py


python tools/cleanup_database.py 7
```



```bash

systemctl status news-monitor.service


tail -50 logs/news_monitor.log


systemctl restart news-monitor.service
```



```bash

grep "wait of.*seconds" logs/news_monitor.log


rm config/subscriptions_cache.json


nano config/config.yaml  
```





```bash

find logs/ -name "*.log.*" -mtime +30 -delete


python tools/cleanup_database.py 14


python tools/backup_channels_config.py


git pull
systemctl restart news-monitor.service
```



```bash

du -sh news_monitor.db


grep -c "❌" logs/news_monitor.log


grep "📊 Найдено.*сообщений" logs/news_monitor.log | tail -20


free -h && df -h
```

---





- [ ] **Клонирование репозитория**
  ```bash
  git clone <repository_url>
  cd news-monitor-bot
  ```

- [ ] **Установка зависимостей**
  ```bash
  pip install -r requirements.txt
  pip install flask  
  ```

- [ ] **Создание .env файла**
  ```bash
  cp env_template.txt .env
  
  ```

- [ ] **Настройка Telegram авторизации**
  ```bash
  python tools/setup_user_auth.py
  ```

- [ ] **Проверка в безопасном режиме**
  ```bash
  python tools/safe_mode.py
  ```

- [ ] **Настройка systemd сервиса**
  ```bash
  sudo systemctl enable news-monitor.service
  sudo systemctl start news-monitor.service
  ```



- [ ] **Проверить статус сервиса**
  ```bash
  systemctl status news-monitor.service
  ```

- [ ] **Проверить логи**
  ```bash
  tail -f logs/news_monitor.log
  ```

- [ ] **Проверить веб-интерфейс**
  ```bash
  curl http://localhost:8080
  ```

- [ ] **Проверить команды бота**
  ```bash
  
  ```

- [ ] **Создать первый бэкап**
  ```bash
  python tools/backup_channels_config.py
  ```



- [ ] **Настроить ротацию логов**
- [ ] **Добавить cron задачи для бэкапов**
- [ ] **Настроить уведомления о проблемах**  
- [ ] **Проверить автозапуск после перезагрузки**
- [ ] **Задокументировать пути и пароли**

---

*Документация Utilities актуальна на: январь 2025*  
*Покрывает полный цикл администрирования системы*
