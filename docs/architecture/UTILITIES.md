# 🛠️ UTILITIES - Вспомогательные инструменты

## 🎯 Обзор

Система включает набор вспомогательных инструментов для обслуживания, диагностики и деплоя News Monitor Bot. Утилиты покрывают все аспекты администрирования: от авторизации до мониторинга и резервного копирования.

**Расположение**: `tools/` папка  
**Деплой**: systemd сервис + командные справочники  
**Управление**: Kill Switch система + веб-интерфейс

---

## 🏗️ Архитектура инструментов

### Категории утилит

```
UTILITIES ECOSYSTEM
├── Setup & Auth               # Первоначальная настройка
│   ├── setup_user_auth.py    # Авторизация Telethon
│   └── safe_mode.py          # Безопасный режим
├── Maintenance               # Обслуживание системы
│   ├── cleanup_database.py   # Очистка базы данных
│   ├── backup_channels_config.py # Резервное копирование
│   └── add_news_manual.py    # Ручное добавление новостей
├── Monitoring & Control     # Мониторинг и управление
│   ├── Kill Switch система   # Экстренная остановка
│   ├── Web Interface        # Веб-панель
│   └── System Commands      # Справочник команд
└── Deployment              # Развертывание
    ├── systemd service      # Автозапуск
    ├── server_commands.txt  # Справочник администратора
    └── Environment setup   # Настройка окружения
```

### Принципы работы утилит

```python
# Общие принципы:
1. Автономность - каждая утилита работает независимо
2. Безопасность - проверки перед критическими операциями  
3. Логирование - детальная информация о выполнении
4. Интерактивность - пользовательский ввод где необходимо
5. Откат изменений - возможность отмены опасных операций
```

---

## 🔐 Настройка и авторизация

### setup_user_auth.py - Авторизация пользователя

**Назначение**: Настройка Telethon авторизации для чтения каналов  
**Файл**: `tools/setup_user_auth.py` (124 строки)

#### 🚀 Использование

```bash
# Стандартная настройка
python tools/setup_user_auth.py

# Сброс сессии и повторная авторизация  
RESET_TELETHON_SESSION=1 python tools/setup_user_auth.py
```

#### 🔧 Функционал

```python
async def setup_user_authentication():
    """Пошаговая настройка авторизации"""
    
    # 1. Загрузка API ключей из .env
    api_id = int(os.getenv('TELEGRAM_API_ID'))
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    # 2. Создание Telethon клиента
    session_path = repo_root / 'sessions' / 'news_monitor_session'
    client = TelegramClient(str(session_path), api_id, api_hash)
    
    # 3. Интерактивная авторизация
    await client.start()  # Запрос номера телефона и кода
    
    # 4. Проверка результата
    me = await client.get_me()
    if hasattr(me, 'phone') and me.phone:
        print("✅ УСПЕШНО! Авторизация пользователя настроена")
        
        # 5. Тестирование доступа к каналу
        test_channel = "@SMIzametki"
        entity = await client.get_entity(test_channel)
        
        # 6. Получение тестовых сообщений
        async for message in client.iter_messages(entity, limit=3):
            if message.text:
                print(f"📄 Сообщение: {message.text[:80]}...")
```

#### ⚠️ Важные особенности

- **Сохранение сессии**: по умолчанию сессия НЕ удаляется для избежания частых авторизаций
- **Сброс сессии**: через переменную `RESET_TELETHON_SESSION=1`  
- **Проверка корректности**: различение пользователя от бота по наличию номера телефона
- **Тестирование доступа**: автоматическая проверка чтения канала после авторизации

### safe_mode.py - Безопасный режим

**Назначение**: Запуск системы без мониторинга каналов  
**Файл**: `tools/safe_mode.py` (58 строк)

#### 🛡️ Использование

```bash
# Запуск в безопасном режиме
python tools/safe_mode.py
```

#### 🎯 Что работает в безопасном режиме

```python
async def run_safe_mode():
    """Ограниченная функциональность без мониторинга"""
    
    print("🛡️ БЕЗОПАСНЫЙ РЕЖИМ - без мониторинга каналов")
    
    # Инициализация компонентов
    db = DatabaseManager("news_monitor.db")
    await db.initialize()
    
    bot = TelegramBot(
        token=config['bot']['token'],
        chat_id=config['bot']['chat_id']
    )
    
    # Тестирование и уведомление
    if await bot.test_connection():
        await bot.send_message(
            "🛡️ Система запущена в БЕЗОПАСНОМ РЕЖИМЕ\n\n"
            "✅ Мониторинг каналов ОТКЛЮЧЕН\n"
            "📱 Уведомления работают\n"  
            "🖥️ Веб-интерфейс доступен на http://localhost:8080"
        )
```

#### ✅ Доступная функциональность

- ✅ Telegram уведомления  
- ✅ Веб-интерфейс на http://localhost:8080
- ✅ База данных
- ❌ Мониторинг каналов **ОТКЛЮЧЕН**

#### 💡 Сценарии использования

- **Отладка конфигурации**: проверка настроек без нагрузки на Telegram API
- **Техническое обслуживание**: доступ к данным без активного мониторинга  
- **Восстановление после блокировок**: избежание дополнительных rate limits
- **Тестирование компонентов**: изолированная проверка бота и базы данных

---

## 🧹 Обслуживание базы данных

### cleanup_database.py - Очистка данных

**Назначение**: Управление размером базы данных через удаление старых записей  
**Файл**: `tools/cleanup_database.py` (155 строк)

#### 🗑️ Режимы использования

```bash
# Интерактивный режим (рекомендуется)
python tools/cleanup_database.py

# Удалить данные старше 3 дней
python tools/cleanup_database.py 3

# Полная очистка всех данных (ОСТОРОЖНО!)
python tools/cleanup_database.py all
```

#### 🎯 Что очищается

```python
async def cleanup_database(days_to_keep: int = 7, clear_all: bool = False):
    """Селективная или полная очистка данных"""
    
    if clear_all:
        # ПОЛНАЯ ОЧИСТКА (с подтверждением)
        confirm = input("Вы уверены? Введите 'YES' для подтверждения: ")
        if confirm != "YES":
            return
            
        # Очистка всех таблиц
        tables = ['messages', 'sent_digests', 'processed_hashes', 'channel_checks', 'statistics']
        for table in tables:
            result = conn.execute(f"DELETE FROM {table}")
            print(f"🗑️ Очищена таблица {table}: {result.rowcount} записей")
    else:
        # ЧАСТИЧНАЯ ОЧИСТКА по дате
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Старые сообщения
        result = conn.execute("DELETE FROM messages WHERE created_at < ?", (cutoff_date,))
        print(f"📰 Удалено старых сообщений: {result.rowcount}")
        
        # Старые дайджесты  
        result = conn.execute("DELETE FROM sent_digests WHERE sent_at < ?", (cutoff_date,))
        print(f"📨 Удалено старых дайджестов: {result.rowcount}")
        
        # Старые хэши дедупликации
        result = conn.execute("DELETE FROM processed_hashes WHERE first_seen < ?", (cutoff_date,))
        print(f"🔗 Удалено старых хэшей: {result.rowcount}")
        
        # Старые проверки каналов
        result = conn.execute("DELETE FROM channel_checks WHERE updated_at < ?", (cutoff_date,))
        print(f"📺 Удалено старых проверок каналов: {result.rowcount}")
    
    # Сжатие базы после очистки
    conn.execute("VACUUM")
    print("🗜️ База данных сжата")
```

#### 📊 Статистика после очистки

```python
# Итоговое состояние базы
with db_manager._get_connection() as conn:
    cursor = conn.execute("SELECT COUNT(*) FROM messages")
    messages_count = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM sent_digests")  
    digests_count = cursor.fetchone()[0]
    
    print(f"\n📊 Текущее состояние базы:")
    print(f"📰 Сообщений: {messages_count}")
    print(f"📨 Дайджестов: {digests_count}")
    
    # Размер файла базы данных
    db_size = os.path.getsize(db_path) / 1024 / 1024
    print(f"💾 Размер базы: {db_size:.2f} MB")
```

#### ⚠️ Меры предосторожности

- **Подтверждение полной очистки**: требуется ввод 'YES' для необратимых операций
- **Остановка бота**: рекомендуется остановить систему перед очисткой
- **Резервное копирование**: создание бэкапа важных данных перед операцией
- **Проверка размера**: контроль объема удаляемых данных

### add_news_manual.py - Ручное добавление новостей

**Назначение**: Добавление новостей в систему без мониторинга каналов  
**Файл**: `tools/add_news_manual.py` (96 строк)

#### ✍️ Использование

```bash
# Интерактивное добавление новости
python tools/add_news_manual.py
```

#### 📝 Процесс добавления

```python
async def add_manual_news():
    """Интерактивное создание новости"""
    
    print("💬 Введите данные новости:")
    
    # Обязательные поля
    title = input("📰 Заголовок: ").strip()
    text = input("📄 Текст новости: ").strip()
    
    # Дополнительные поля
    source = input("📍 Источник (по умолчанию 'Ручной ввод'): ").strip() or "Ручной ввод"
    region = input("🌍 Регион (sakhalin/kamchatka/other): ").strip() or "other"  
    url = input("🔗 Ссылка (необязательно): ").strip()
    
    # Создание структуры сообщения
    now = datetime.now()
    message_data = {
        "id": f"manual_{int(now.timestamp())}",
        "channel_username": "@manual",
        "channel_name": source,
        "text": text,
        "date": now,
        "selected_for_output": True,  # Автоматический отбор ручных новостей
        "ai_score": 10,              # Максимальная оценка
        "ai_priority": "high",       # Высокий приоритет
        "content_hash": f"manual_{now.timestamp()}"
    }
    
    # Сохранение + уведомление
    await db.save_message(message_data)
    
    if await bot.test_connection():
        message = f"📰 **Новая новость добавлена**\n\n**{title}**\n\n{text}"
        if url:
            message += f"\n\n🔗 [Читать полностью]({url})"
        message += f"\n\n📍 {source}"
        
        await bot.send_message(message)
        print("✅ Уведомление отправлено в Telegram")
```

#### 🎯 Особенности ручных новостей

- **Автоматический отбор**: `selected_for_output = True` 
- **Максимальный рейтинг**: `ai_score = 10`
- **Высокий приоритет**: `ai_priority = "high"`
- **Уникальная идентификация**: префикс `manual_` в ID
- **Мгновенное уведомление**: отправка в Telegram после добавления

---

## 📦 Резервное копирование

### backup_channels_config.py - Бэкап конфигурации

**Назначение**: Автоматическое резервное копирование настроек каналов  
**Файл**: `tools/backup_channels_config.py` (65 строк)

#### 💾 Использование

```bash
# Создание бэкапа
python tools/backup_channels_config.py
```

#### 🔄 Процесс резервного копирования

```python
def backup_channels_config():
    """Создание резервной копии с управлением версиями"""
    
    # Исходный файл и папка бэкапов
    source = Path('config/channels_config.yaml')
    backup_dir = Path('backups/channels_config')
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Имя с timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    backup_name = f'channels_config_{timestamp}.yaml'
    backup_path = backup_dir / backup_name
    
    # Копирование с метаданными
    shutil.copy2(source, backup_path)
    
    # Создание ссылки на последний бэкап (latest.yaml)
    latest_link = backup_dir / 'latest.yaml'
    if latest_link.exists():
        latest_link.unlink()
    shutil.copy2(backup_path, latest_link)  # Windows совместимость
    
    print(f'✅ Бэкап создан: {backup_name}')
    print(f'📁 Путь: {backup_path}')
    
    # Автоочистка старых бэкапов
    cleanup_old_backups(backup_dir)
```

#### 🧹 Управление версиями

```python
def cleanup_old_backups(backup_dir, keep_count=10):
    """Автоматическое удаление старых бэкапов"""
    
    backup_files = list(backup_dir.glob('channels_config_*.yaml'))
    
    # Сортировка по времени создания (новые первыми)
    backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    # Удаление лишних файлов (сохраняем 10 последних)
    for file in backup_files[keep_count:]:
        file.unlink()
        print(f'🗑️ Удален старый бэкап: {file.name}')
```

#### 📂 Структура бэкапов

```
backups/channels_config/
├── channels_config_2025-01-20_14-30-15.yaml
├── channels_config_2025-01-20_10-15-22.yaml
├── channels_config_2025-01-19_18-45-33.yaml
├── ...
└── latest.yaml → последний бэкап
```

#### 🔧 Рекомендации использования

- **Автоматизация**: добавить в cron для регулярного выполнения
- **Перед изменениями**: создание бэкапа перед редактированием конфигурации
- **Контроль версий**: сохранение истории изменений настроек каналов
- **Быстрое восстановление**: использование latest.yaml для отката

---

## 🛡️ Kill Switch система

### Экстренная остановка

**Назначение**: Полная блокировка системы с предотвращением автоперезапусков  
**Файлы**: `src/handlers/commands/basic.py`, `main.py`

#### 🚨 Активация через бота

```bash
# В Telegram боте
/kill_switch
# ↓ Подтверждение через кнопку
"✅ ДА, ЗАБЛОКИРОВАТЬ"
```

#### 🔧 Механизм работы

```python
# 1. В main.py - проверка при запуске
if __name__ == "__main__":
    # Kill Switch проверка ПЕРЕД любой инициализацией
    if os.path.exists("STOP_BOT"):
        print("🛑 НАЙДЕН ФАЙЛ БЛОКИРОВКИ: STOP_BOT")
        print("🚫 БОТ ЗАБЛОКИРОВАН ОТ ЗАПУСКА")  
        print("💡 Удалите файл STOP_BOT для разблокировки")
        exit(0)
    
    asyncio.run(NewsMonitorWithBot().run())

# 2. Создание файла блокировки
async def confirm_kill_switch(self, message):
    """Выполнение kill switch"""
    
    # Создание файла блокировки
    with open("STOP_BOT", "w") as f:
        f.write(f"Kill Switch activated at {datetime.now()}\n")
        f.write("Bot permanently blocked from starting\n")
    
    # Уведомление пользователя
    await self.send_message_with_keyboard(
        "🛑 <b>KILL SWITCH АКТИВИРОВАН!</b>\n\n"
        "🔒 Файл блокировки создан\n"
        "🚫 Бот заблокирован от запуска\n\n"
        "💡 Для разблокировки: /unlock",
        keyboard
    )
    
    await asyncio.sleep(3)
    
    # Корректное завершение
    if self.monitor_bot:
        self.monitor_bot.running = False
    sys.exit(0)
```

#### 🔓 Разблокировка

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

#### ⚠️ Принципы безопасности

- **Приоритет проверки**: Kill Switch проверяется ПЕРЕД инициализацией системы
- **Предотвращение автозапуска**: блокирует systemd и cron перезапуски
- **Подтверждение действия**: требует явного подтверждения пользователя
- **Корректное завершение**: graceful shutdown с уведомлением

---

## 🌐 Веб-интерфейс

### WebInterface - Мониторинг через браузер

**Назначение**: Веб-панель для мониторинга системы и базы данных  
**Файл**: `src/web_interface.py` (350+ строк)

#### 🖥️ Запуск веб-интерфейса

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

#### 🔗 Доступные endpoints

```python
# Главная страница
@app.route('/')
def index():
    return render_template_string(self.get_main_template())

# API статистики
@app.route('/api/stats')  
def get_stats():
    # Получение статистики из базы + системная информация
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

# API новостей
@app.route('/api/news')
def get_news():
    # Получение последних новостей из базы
    # Поддержка пагинации и фильтрации
```

#### 📊 Отображаемая информация

- **Статистика базы данных**: количество сообщений, дайджестов, активных каналов
- **Системные метрики**: использование CPU, памяти, дискового пространства  
- **Последние новости**: список с возможностью фильтрации по региону
- **Состояние компонентов**: статус Telegram подключений, мониторинга
- **Live обновления**: автоматическое обновление данных через AJAX

#### ⚙️ Установка зависимостей

```bash
# Установка Flask для веб-интерфейса
pip install flask

# Проверка доступности
curl http://localhost:8080
```

---

## 🚀 Деплой и системные команды

### systemd сервис

**Назначение**: Автоматический запуск и управление системой через systemd  
**Конфигурация**: создается при деплое на сервер

#### 📋 Команды управления сервисом

```bash
# Основные команды
systemctl start news-monitor.service      # Запуск
systemctl stop news-monitor.service       # Остановка  
systemctl restart news-monitor.service    # Перезапуск
systemctl status news-monitor.service     # Статус

# Автозапуск
systemctl enable news-monitor.service     # Включить
systemctl disable news-monitor.service    # Отключить

# Логи
journalctl -u news-monitor.service -f     # Реальное время
journalctl -u news-monitor.service --since "1 hour ago"  # За час
```

#### 📝 Структура сервиса

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

### server_commands.txt - Справочник администратора

**Назначение**: Полный справочник команд для управления сервером  
**Файл**: `server_commands.txt` (255 строк)

#### 🗂️ Категории команд

```bash
# 📍 ОСНОВНЫЕ ПУТИ
/opt/news-monitor/SMI_tg_bot                    # Проект
/opt/news-monitor/SMI_tg_bot/logs/              # Логи  
/opt/news-monitor/SMI_tg_bot/config/            # Конфигурация
/opt/news-monitor/SMI_tg_bot/sessions/          # Telegram сессии

# 🔧 УПРАВЛЕНИЕ СЕРВИСОМ
systemctl restart news-monitor.service         # Перезапуск
systemctl status news-monitor.service          # Статус

# 📋 ЛОГИ И МОНИТОРИНГ
tail -f logs/news_monitor.log                  # Логи в реальном времени
grep -i "error" logs/news_monitor.log          # Поиск ошибок
grep "$(date +%Y-%m-%d)" logs/news_monitor.log # Логи за сегодня

# 🔄 GIT ОБНОВЛЕНИЯ  
git pull                                       # Обновление кода
git status                                     # Статус репозитория

# 🔍 ДИАГНОСТИКА
free -h                                        # Память
df -h                                          # Диск  
ps aux | grep python                          # Python процессы

# ⚠️ ЭКСТРЕННЫЕ КОМАНДЫ
rm -f config/subscriptions_cache.json         # Очистка кэша
rm -f sessions/news_monitor_session.session   # Сброс сессии
```

#### 🚨 Быстрые команды для решения проблем

```bash
# Полный перезапуск
systemctl restart news-monitor.service && tail -f logs/news_monitor.log

# Обновление и перезапуск
git pull && systemctl restart news-monitor.service

# Очистка кэша и перезапуск  
rm -f config/subscriptions_cache.json && systemctl restart news-monitor.service

# Полная диагностика
systemctl status news-monitor.service && free -h && df -h && ps aux | grep python
```

### Логирование и мониторинг

#### 📊 Структура логов

```python
# В src/core/config_loader.py
logging:
  file: logs/news_monitor.log    # Основной файл логов
  level: INFO                    # Уровень детализации

# Ротация логов (настраивается в loguru)
logger.add(
    "logs/news_monitor.log",
    rotation="10 MB",              # Новый файл каждые 10MB
    retention="30 days",           # Хранить 30 дней
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)
```

#### 🔍 Ключевые события в логах

```bash
# Успешные операции
grep "✅" logs/news_monitor.log

# Ошибки и предупреждения  
grep -E "(❌|⚠️)" logs/news_monitor.log

# Статистика работы
grep "📊 Статистика" logs/news_monitor.log

# Подключения к Telegram
grep "Telegram клиент" logs/news_monitor.log

# Мониторинг каналов
grep "📡.*мониторинг" logs/news_monitor.log
```

#### 📈 Системный мониторинг

```python
# В src/system_monitor.py (если используется)
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

## 🔧 Диагностика и отладка

### Типичные проблемы и решения

#### 🚫 "Bot blocked from starting" 

```bash
# Проверить Kill Switch
ls -la STOP_BOT

# Разблокировать через бота
/unlock

# Или удалить файл вручную
rm STOP_BOT
```

#### 📡 "Telegram авторизация не работает"

```bash
# Сброс сессии
RESET_TELETHON_SESSION=1 python tools/setup_user_auth.py

# Или удалить сессию вручную
rm sessions/news_monitor_session.session
python tools/setup_user_auth.py
```

#### 💾 "База данных переполнена"

```bash
# Проверить размер
ls -lah news_monitor.db

# Интерактивная очистка
python tools/cleanup_database.py

# Удалить старые данные (7 дней)
python tools/cleanup_database.py 7
```

#### 🔄 "Система не отвечает"

```bash
# Проверить статус сервиса
systemctl status news-monitor.service

# Проверить логи
tail -50 logs/news_monitor.log

# Жесткий перезапуск
systemctl restart news-monitor.service
```

#### ⚠️ "Rate limit от Telegram"

```bash
# Найти в логах время блокировки
grep "wait of.*seconds" logs/news_monitor.log

# Очистить кэш подписок
rm config/subscriptions_cache.json

# Увеличить таймауты в config.yaml
nano config/config.yaml  # Секция monitoring.timeouts
```

### Профилактическое обслуживание

#### 📅 Еженедельные задачи

```bash
# Очистка логов (сохранить 30 дней)
find logs/ -name "*.log.*" -mtime +30 -delete

# Очистка базы данных (сохранить 14 дней)  
python tools/cleanup_database.py 14

# Бэкап конфигурации каналов
python tools/backup_channels_config.py

# Обновление кода
git pull
systemctl restart news-monitor.service
```

#### 📊 Ежемесячные проверки

```bash
# Проверка размера базы
du -sh news_monitor.db

# Анализ логов на ошибки
grep -c "❌" logs/news_monitor.log

# Статистика активности каналов
grep "📊 Найдено.*сообщений" logs/news_monitor.log | tail -20

# Проверка системных ресурсов
free -h && df -h
```

---

## 📋 Чек-лист развертывания

### 🚀 Первоначальная настройка

- [ ] **Клонирование репозитория**
  ```bash
  git clone <repository_url>
  cd news-monitor-bot
  ```

- [ ] **Установка зависимостей**
  ```bash
  pip install -r requirements.txt
  pip install flask  # Для веб-интерфейса
  ```

- [ ] **Создание .env файла**
  ```bash
  cp env_template.txt .env
  # Заполнить реальными данными
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

### 🔧 Послеустановочная проверка

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
  # В Telegram: /start, /status
  ```

- [ ] **Создать первый бэкап**
  ```bash
  python tools/backup_channels_config.py
  ```

### 🛡️ Настройка мониторинга

- [ ] **Настроить ротацию логов**
- [ ] **Добавить cron задачи для бэкапов**
- [ ] **Настроить уведомления о проблемах**  
- [ ] **Проверить автозапуск после перезагрузки**
- [ ] **Задокументировать пути и пароли**

---

*Документация Utilities актуальна на: январь 2025*  
*Покрывает полный цикл администрирования системы*
