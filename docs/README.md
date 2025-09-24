## 🎯 Назначение системы

**Telegram News Monitor** - корпоративное решение для автоматизации мониторинга Telegram-каналов. 

### Бизнес-задачи
- **Автоматизация рутины** - исключение ручного мониторинга каналов
- **Региональная аналитика** - систематизация новостей по субъектам ДФО
- **Операционная эффективность** - сокращение времени обработки новостей
- **Централизованное управление** - единая точка контроля всех источников

## 🚀 Ключевые возможности

### 📡 **Real-time мониторинг**
- **Непрерывное отслеживание** - 24/7 мониторинг 80+ каналов
- **Instant обработка** - обработка новостей в момент публикации
- **Защита от блокировок** - умные таймауты и rate limiting
- **Кэширование подписок** - быстрый запуск (30 сек вместо 30 мин)

### 🌍 **Региональная аналитика**
- **Автоматическая сортировка** - распределение по 6 регионам ДФО
- **Ключевые слова** - определение региона по контенту
- **Тематическая маршрутизация** - отправка в соответствующие топики
- **Исключение служебных тем** - фильтрация флуда и оффтопа

### 🎮 **Telegram интерфейс**
- **Команды управления** - полный контроль через бота
- **Inline кнопки** - интуитивная навигация
- **Пагинация** - удобный просмотр больших списков
- **Автоматическое редактирование** - чистый интерфейс

### 📊 **Система дайджестов**
- **Live чтение каналов** - прямой доступ к Telegram API
- **Умная фильтрация** - исключение нерелевантного контента
- **Рейтинг популярности** - сортировка по активности
- **Экспорт результатов** - готовые сводки для публикации

### 🛡️ **Безопасность и надежность**
- **Kill Switch** - экстренная остановка системы
- **Graceful shutdown** - корректное завершение работы
- **Резервное копирование** - автоматические бэкапы
- **Мониторинг состояния** - веб-интерфейс и уведомления

## 🏗️ Архитектура системы

### Модульная структура

```
telegram-news-monitor/
├── main.py                  # Точка входа с Kill Switch
├── src/                     # Исходный код
│   ├── core/               # Ядро системы
│   │   ├── app.py         # Главный оркестратор
│   │   ├── config_loader.py # Управление конфигурацией
│   │   └── lifecycle.py    # Жизненный цикл компонентов
│   ├── bot/               # Telegram Bot (модульная архитектура)
│   │   ├── core/          # Основные компоненты
│   │   ├── ui/            # Пользовательский интерфейс
│   │   ├── channels/      # Управление каналами
│   │   ├── regions/       # Управление регионами
│   │   ├── handlers/      # Обработчики событий
│   │   ├── digest/        # Система дайджестов
│   │   └── utils/         # Вспомогательные функции
│   ├── handlers/          # Интерфейс команд и callbacks
│   │   ├── commands/      # Команды бота
│   │   └── callbacks/     # Обработчики кнопок
│   ├── monitoring/        # Система мониторинга
│   │   ├── channel_monitor.py # Подписки на каналы
│   │   ├── message_processor.py # Обработка сообщений
│   │   └── subscription_cache.py # Кэш подписок
│   ├── database.py       # SQLite база данных
│   ├── digest_generator.py # Генерация дайджестов
│   ├── telegram_client.py # Telethon клиент
│   └── web_interface.py  # Веб-панель администратора
├── config/               # Конфигурация
│   ├── config.yaml      # Основные настройки
│   └── channels_config.yaml # Конфигурация каналов
├── logs/                # Логи системы
├── sessions/            # Telegram сессии
├── tools/               # Утилиты администрирования
└── docs/                # Документация
```

### Компоненты системы

**Ядро (Core)**
- `app.py` - главный оркестратор, координирует все компоненты
- `config_loader.py` - загрузка YAML + переменные окружения
- `lifecycle.py` - управление запуском и остановкой компонентов

**Telegram интерфейс**
- `bot/` - модульный Telegram Bot API для управления
- `handlers/` - команды и callbacks интерфейса
- `telegram_client.py` - Telethon клиент для чтения каналов

**Мониторинг**
- `channel_monitor.py` - подписки на каналы с защитой от rate limits
- `message_processor.py` - обработка сообщений в реальном времени
- `subscription_cache.py` - кэш для быстрого запуска

**Хранение данных**
- `database.py` - SQLite с оптимизацией для VPS
- `digest_generator.py` - генерация дайджестов
- `web_interface.py` - веб-панель мониторинга

## 📋 Системные требования

### Производственная среда
- **ОС**: Ubuntu 20.04+ / Debian 11+ (рекомендуется)
- **RAM**: 1GB+ (минимум 512MB)
- **CPU**: 2 cores (минимум 1 core)
- **Диск**: 5GB+ свободного места
- **Сеть**: стабильное соединение с Telegram API

### Зависимости
- **Python**: 3.8+
- **Telegram API**: api_id и api_hash с [my.telegram.org](https://my.telegram.org)
- **Telegram Bot**: токен от [@BotFather](https://t.me/BotFather)
- **Системный сервис**: systemd для автозапуска

## 🚀 Установка и настройка

### 1. Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка зависимостей
sudo apt install python3 python3-pip git systemd -y

# Создание пользователя (опционально)
sudo useradd -m -s /bin/bash news-monitor
sudo usermod -aG sudo news-monitor
```

### 2. Клонирование проекта

```bash
# Клонирование в /opt (рекомендуется для продакшена)
sudo git clone <repository-url> /opt/telegram-news-monitor
cd /opt/telegram-news-monitor

# Установка Python зависимостей
sudo pip3 install -r requirements.txt

# Права доступа
sudo chown -R news-monitor:news-monitor /opt/telegram-news-monitor
```

### 3. Конфигурация окружения

```bash
# Создание .env файла
sudo cp env_template.txt .env
sudo nano .env
```

**Заполните .env файл:**
```env
# Токен бота от @BotFather
BOT_TOKEN=1234567890:AAAA...

# Ваш Telegram ID для управления
BOT_CHAT_ID=123456789

# API данные с my.telegram.org  
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef...

# ID группы для публикации новостей
TARGET_GROUP_ID=-1001234567890
```

### 4. Telegram авторизация

```bash
# Настройка Telethon сессии
python3 tools/setup_user_auth.py

# Проверка в безопасном режиме
python3 tools/safe_mode.py
```

### 5. Настройка systemd сервиса

```bash
# Создание сервис файла
sudo tee /etc/systemd/system/news-monitor.service > /dev/null <<EOF
[Unit]
Description=Telegram News Monitor Bot
After=network.target

[Service]
Type=simple
User=news-monitor
WorkingDirectory=/opt/telegram-news-monitor
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=/opt/telegram-news-monitor

[Install]
WantedBy=multi-user.target
EOF

# Активация сервиса
sudo systemctl daemon-reload
sudo systemctl enable news-monitor.service
sudo systemctl start news-monitor.service
```

## ⚙️ Конфигурация системы

### config/config.yaml

**Основная конфигурация системы:**

```yaml
# Telegram API подключение
telegram:
  api_id: "${TELEGRAM_API_ID}"        # Из переменных окружения
  api_hash: "${TELEGRAM_API_HASH}"    

# Настройки бота
bot:
  token: "${BOT_TOKEN}"               # Токен от @BotFather
  chat_id: "${BOT_CHAT_ID}"          # ID админа

# Вывод новостей  
output:
  target_group: "${TARGET_GROUP_ID}"  # ID группы для публикации
  excluded_topics: [26, 27]          # ID тем для исключения (флуд, оффтоп)
  topics:                            # Привязка регионов к темам
    sakhalin: 2
    kamchatka: 5  
    chita: 32
    yakutsk: 890
    vladivostok: 1020
    general: null                     # Общие новости без темы

# Система алертов
alerts:
  enabled: true
  keywords:
    emergency:                        # Критические
      emoji: "🔴🚨"
      priority: true
      words: ["пожар", "дтп", "чс", "авария", "взрыв"]
    important:                        # Важные
      emoji: "🟡⚠️"  
      priority: false
      words: ["власть", "транспорт", "погода", "шторм"]

# Региональные настройки
regions:
  sakhalin:
    name: "🏝️ Сахалин"
    emoji: "🏝️"
    description: "Сахалинская область и Курильские острова"
    keywords: ["сахалин", "южно", "корсаков", "курилы"]
    topic_id: 2
    created_at: "2025-08-26"

# Настройки мониторинга (защита от блокировок)
monitoring:
  timeouts:
    batch_size: 6                     # Каналов в одном пакете
    delay_cached_channel: 1           # Задержка для кешированных (сек)
    delay_between_batches: 8          # Между пакетами (сек)
    delay_retry_wait: 300             # Rate limit ожидание (5 мин)
    fast_start_mode: true             # Быстрый старт

# База данных
database:
  path: news_monitor.db

# Логирование
logging:
  file: logs/news_monitor.log
  level: INFO

# Веб-интерфейс  
web:
  port: 8080
```

### config/channels_config.yaml

**Конфигурация каналов по регионам:**

```yaml
regions:
  sakhalin:
    name: "🏝️ Сахалин"
    channels:
      - username: "astv_ru"
        title: "АСТВ"
      - username: "tochka_65"  
        title: "Точка 65"
      - username: "sakhgov"
        title: "Правительство Сахалинской области"
        
  kamchatka:
    name: "🌋 Камчатка"  
    channels:
      - username: "IA_Kam24"
        title: "ИА Кам24"
      - username: "regiontv41"
        title: "Регион ТВ"
        
  chita:
    name: "🏔️ Чита"  
    channels:
      - username: "chp_chita"
        title: "ЧП Чита"
      - username: "dtp_chita"
        title: "ДТП Чита"
## 🎮 Использование системы

### Команды управления ботом

**Основные команды:**
```
/start        - Главное меню системы
/status       - Статус всех компонентов  
/digest       - Генерация дайджеста новостей
/manage_channels - Управление списком каналов
/topic_id     - Получить ID темы группы для настройки
/restart      - Перезапуск системы
/kill_switch  - Экстренная остановка (блокировка)
/unlock       - Разблокировка после kill_switch
```

**Команды диагностики:**
```
/stats        - Детальная статистика работы
/force_subscribe - Принудительная проверка подписок
/help         - Справка по всем командам
```

### Интерфейс управления каналами

**Добавление каналов (3 способа):**

1. **По ссылке**: `https://t.me/news_channel`
2. **По username**: `@news_channel`  
3. **Forward сообщения**: переслать любое сообщение из канала
4. **Массово**: отправить несколько ссылок одним сообщением

**Пример интерфейса:**
```
🗂️ Управление каналами

📊 Всего каналов: 85
📂 Регионов: 6

🏝️ Сахалин (18 каналов)
🌋 Камчатка (15 каналов)  
🏔️ Чита (12 каналов)
❄️ Якутск (14 каналов)
🌊 Владивосток (16 каналов)
📰 Общие (10 каналов)

[➕ Добавить канал] [🔄 Обновить]
```

### Система регионов

**Динамическое создание регионов:**

1. При добавлении канала система предлагает существующие регионы
2. Возможность создать новый регион с выбором эмодзи
3. Автоматическое определение региона по ключевым словам
4. Настройка topic_id для маршрутизации сообщений

**Настройка тем (topics):**

1. Зайти в нужную тему группы
2. Выполнить `/topic_id` 
3. Скопировать полученный ID
4. Привязать к региону через бота или config.yaml

### Система дайджестов

**Генерация дайджестов:**

- **База данных**: `/digest 7` - за последние 7 дней из сохраненных новостей
- **Live чтение**: отправить ссылку на канал для анализа в реальном времени
- **Пагинация**: навигация по страницам результатов
- **Фильтрация**: исключение флуда, политики, неактивного контента

**Пример дайджеста:**
```
📰 Топ новостей @sakhalin_news
📅 13.09.2025 - 20.09.2025
📄 Страница 1/3 (всего 28 новостей)

1. Открытие нового моста в Южно-Сахалинске...
   🔗 https://t.me/sakhalin_news/1234 [👍15 💬3]

2. Шторм на Курильских островах...
   🔗 https://t.me/sakhalin_news/1235 [👍28 💬7]

[⬅️ Стр. 1] [Стр. 2 ➡️]
[📰 Новый дайджест] [🏠 Главное меню]
```

## 🛠️ Администрирование системы

### Системные утилиты

**Утилиты для обслуживания (`tools/`):**

```bash
# Безопасный режим (тестирование без мониторинга)
python3 tools/safe_mode.py

# Очистка базы данных от старых записей  
python3 tools/cleanup_database.py 7    # Оставить данные за 7 дней
python3 tools/cleanup_database.py all  # Полная очистка (осторожно!)

# Резервное копирование конфигурации
python3 tools/backup_channels_config.py

# Ручное добавление новости
python3 tools/add_news_manual.py

# Сброс Telegram авторизации
RESET_TELETHON_SESSION=1 python3 tools/setup_user_auth.py
```

### Управление systemd сервисом

```bash
# Основные команды
sudo systemctl start news-monitor.service    # Запуск
sudo systemctl stop news-monitor.service     # Остановка
sudo systemctl restart news-monitor.service  # Перезапуск
sudo systemctl status news-monitor.service   # Статус

# Автозапуск
sudo systemctl enable news-monitor.service   # Включить автозапуск
sudo systemctl disable news-monitor.service  # Отключить автозапуск

# Логи
sudo journalctl -u news-monitor.service -f           # Логи в реальном времени
sudo journalctl -u news-monitor.service --since "1 hour ago"  # За час
```

### Веб-интерфейс мониторинга

**Доступ**: `http://localhost:8080` (или IP сервера)

**Возможности:**
- **Статистика в реальном времени** - сообщения, каналы, ошибки
- **Состояние компонентов** - Telegram, база данных, мониторинг
- **Системные ресурсы** - CPU, RAM, диск
- **Последние новости** - просмотр недавних сообщений
- **API endpoints** - `/api/stats`, `/api/news` для интеграций

## 📊 Мониторинг и диагностика

### Проверка состояния системы

```bash
# Статус сервиса
sudo systemctl status news-monitor.service

# Логи системы
tail -f /opt/telegram-news-monitor/logs/news_monitor.log

# Поиск ошибок
grep -E "(❌|ERROR)" /opt/telegram-news-monitor/logs/news_monitor.log | tail -20

# Проверка процессов
ps aux | grep python3 | grep main.py

# Использование ресурсов
free -h && df -h && top -p $(pgrep -f "python3 main.py")
```

### Мониторинг через Telegram

**Команды диагностики в боте:**
```
/status       - Общий статус всех компонентов
/stats        - Детальная статистика работы  
/force_subscribe - Принудительная проверка подписок
```

**Пример вывода `/status`:**
```
📊 Статус системы

📱 Telegram бот: ✅ Активен
🗄️ База данных: ✅ Подключена (245 MB)
📺 Мониторинг: ✅ Активен (82 канала)
💾 Кэш подписок: ✅ Загружен

⚡ Время работы: 2ч 34мин
🔄 Последний перезапуск: 14:25
📥 Сообщений за сегодня: 1,247
📤 Отобрано: 89 (7.2%)
```

### Типичные проблемы и решения

**1. "Rate limit" от Telegram API:**
```bash
# Признаки: "wait of X seconds" в логах
grep "wait of.*seconds" logs/news_monitor.log

# Решение: увеличить таймауты
nano config/config.yaml
# monitoring.timeouts.delay_between_batches: 15

# Или очистить кэш подписок
rm config/subscriptions_cache.json
sudo systemctl restart news-monitor.service
```

**2. "Бот заблокирован" (Kill Switch):**
```bash
# Проверка
ls -la /opt/telegram-news-monitor/STOP_BOT

# Разблокировка через бота
/unlock

# Или вручную
sudo rm /opt/telegram-news-monitor/STOP_BOT
sudo systemctl restart news-monitor.service
```

**3. "Проблемы с авторизацией Telethon":**
```bash
# Сброс сессии
sudo rm /opt/telegram-news-monitor/sessions/news_monitor_session.session
cd /opt/telegram-news-monitor
sudo -u news-monitor python3 tools/setup_user_auth.py
```

**4. "База данных переполнена":**
```bash
# Проверка размера
ls -lah /opt/telegram-news-monitor/news_monitor.db

# Очистка (сохранить данные за 14 дней)
cd /opt/telegram-news-monitor
sudo -u news-monitor python3 tools/cleanup_database.py 14
```

### Настройка логирования

**Уровни логирования в config.yaml:**
```yaml
logging:
  file: logs/news_monitor.log
  level: INFO    # DEBUG для отладки, WARNING для продакшена
```

**Ротация логов (настройка loguru):**
```python
# В коде: автоматическая ротация каждые 10MB, хранение 30 дней
logger.add("logs/news_monitor.log", 
          rotation="10 MB", retention="30 days")
```

## 📈 Производительность и оптимизация

### Настройки мониторинга

**Безопасные настройки (config.yaml):**
```yaml
monitoring:
  timeouts:
    batch_size: 6              # Каналов в пакете (рекомендуется 4-8)
    delay_cached_channel: 1    # Задержка для кешированных (сек)
    delay_between_batches: 8   # Между пакетами (сек, рекомендуется 8-15)
    delay_retry_wait: 300      # Rate limit ожидание (5 мин)
    fast_start_mode: true      # Быстрый старт с кешем
```

**Агрессивные настройки (риск блокировок):**
```yaml
monitoring:
  timeouts:
    batch_size: 10
    delay_between_batches: 5
    fast_start_mode: true
```

### Системные ресурсы

**Целевые показатели:**
- **RAM**: < 200MB в нормальном режиме
- **CPU**: < 10% при стабильной работе  
- **База данных**: < 500MB для 30 дней данных
- **Время запуска**: 30-60 секунд с кешем подписок

**Оптимизация SQLite:**
```yaml
database:
  path: news_monitor.db
  # Автоматически используется WAL режим для производительности
```

## 📚 Техническая документация

### Детальная архитектурная документация

Полная техническая документация по компонентам системы:

- **[Core Modules](architecture/CORE_MODULES.md)** - ядро системы (app.py, config_loader.py, lifecycle.py)
- **[Telegram Bot](architecture/TELEGRAM_BOT.md)** - модульная архитектура бота
- **[Monitoring](architecture/MONITORING.md)** - система мониторинга каналов  
- **[Database](architecture/DATABASE.md)** - SQLite база данных и операции
- **[Configuration](architecture/CONFIGURATION.md)** - настройки и переменные окружения
- **[Digest System](architecture/DIGEST_SYSTEM.md)** - генерация дайджестов
- **[Utilities](architecture/UTILITIES.md)** - административные утилиты
- **[Security](architecture/SECURITY.md)** - настройка безопасности

### API и интеграции

**Веб API endpoints:**
```
GET /api/stats    # Статистика системы (JSON)
GET /api/news     # Последние новости (JSON)  
GET /           # Веб-интерфейс (HTML)
```

**Формат JSON ответа `/api/stats`:**
```json
{
  "database": {
    "total_messages": 15420,
    "selected_messages": 1247,
    "date": "2025-01-20"
  },
  "system": {
    "memory": 185.4,
    "cpu": 8.2,
    "disk": 2.1
  },
  "timestamp": "2025-01-20T15:30:45"
}
```

### Безопасность

**Защита данных:**
- Все токены и API ключи только в `.env` файле
- Файл `.env` с правами 600 (только владелец может читать)
- Kill Switch для экстренной остановки системы
- Graceful shutdown при получении сигналов системы

**Сетевая безопасность:**
- Веб-интерфейс по умолчанию доступен только локально
- Можно настроить firewall для ограничения доступа
- HTTPS рекомендуется для продакшена (через nginx)

## 🔄 Обновление и развертывание

### Обновление системы

```bash
# Переход в директорию проекта
cd /opt/telegram-news-monitor

# Создание бэкапа конфигурации
sudo -u news-monitor python3 tools/backup_channels_config.py

# Обновление кода
sudo git pull

# Перезапуск сервиса
sudo systemctl restart news-monitor.service

# Проверка логов
sudo journalctl -u news-monitor.service -f
```

### Миграция данных

**При переносе на новый сервер:**

1. **Сохранить конфигурацию:**
   ```bash
   # Старый сервер
   tar -czf backup.tar.gz config/ sessions/ news_monitor.db
   ```

2. **Установить на новом сервере** (следовать инструкциям выше)

3. **Восстановить данные:**
   ```bash
   # Новый сервер
   sudo systemctl stop news-monitor.service
   tar -xzf backup.tar.gz -C /opt/telegram-news-monitor/
   sudo chown -R news-monitor:news-monitor /opt/telegram-news-monitor/
   sudo systemctl start news-monitor.service
   ```

## 📞 Поддержка и устранение неполадок

### Логи для диагностики

**Основные источники информации:**
```bash
# Логи приложения
tail -f /opt/telegram-news-monitor/logs/news_monitor.log

# Логи systemd
sudo journalctl -u news-monitor.service --since "1 hour ago"

# Системные логи
sudo dmesg | grep -i error

# Сетевые проблемы  
ping telegram.org
curl -I https://api.telegram.org
```

### Контакты поддержки

При возникновении проблем:

1. **Проверьте логи** - большинство проблем видны в логах
2. **Проверьте статус** - команда `/status` в боте  
3. **Используйте безопасный режим** - `python3 tools/safe_mode.py`
4. **Консультируйтесь с документацией** - `docs/architecture/`

---

**Система Telegram News Monitor готова к круглосуточной работе в производственной среде для автоматизации мониторинга региональных новостей Дальнего Востока России.**

### 🗂️ Управление каналами

**Главный экран:**
```
🗂️ Управление каналами

📊 Всего каналов: 25
📂 Регионов: 4

🏝️ Сахалин (8)
🌋 Камчатка (6)  
🏔️ Чита (7)
📰 Общие (4)

➕ Добавить канал    🔄 Обновить
🏠 Главное меню
```

**Просмотр региона с пагинацией:**
```
📂 🏝️ Сахалин

📊 Каналов в регионе: 25
📄 Страница: 1 из 4

📋 Список каналов:
1. @sakhalin_news
   📄 Сахалин Новости
🗑️ Удалить @sakhalin_news

2. @yuzhno_news
   📄 Южно-Сахалинск  
🗑️ Удалить @yuzhno_news

◀️ Назад    📄 1/4    ▶️ Далее
```

### ➕ Добавление каналов

**3 способа добавления:**

1. **По ссылке** - отправь ссылку: `https://t.me/news_channel`
2. **Forward сообщений** - перешли любое сообщение из канала
3. **Массовое добавление** - отправь несколько ссылок сразу

**Автоматическое определение региона:**
```
📺 Найден новый канал!

📋 Название: Владивосток Новости
🔗 Username: @vladivostok_news

🎯 Предлагаемый регион: 🌊 Приморье (найдено: владивосток)

🏝️ Сахалин        🌋 Камчатка
🏔️ Чита           📰 Общие

➕ Создать новый регион
❌ Отмена
```

### 🌍 Создание новых регионов

**Шаг 1 - Название:**
```
➕ Создание нового региона

📝 Шаг 1 из 2: Название региона

Отправьте название региона:

Примеры:
• Владивосток
• Магадан  
• Иркутск

💡 На следующем шаге выберете эмодзи!
```

**Шаг 2 - Эмодзи:**
```
🎨 Шаг 2 из 2: Выбор эмодзи

📋 Регион: Владивосток

Выберите эмодзи для региона:

🌊 🏔️ 🌲 ❄️
🌋 🏝️ 🏜️ 🌾  
🏞️ 🌸 ⚡ 🚢

✏️ Ввести свой эмодзи
❌ Отмена
```

### 🗑️ Удаление каналов

**Безопасное удаление с подтверждением:**
```
🗑️ Подтверждение удаления

📂 Регион: 🏝️ Сахалин
📺 Канал: @sakhalin_news
📄 Название: Сахалин Новости

⚠️ Вы уверены, что хотите удалить этот канал?

❌ Это действие НЕОБРАТИМО!
🛑 Мониторинг канала будет остановлен
📊 История сообщений сохранится в базе данных

✅ Да, удалить    ❌ Отмена
```

## 📊 Статистика и мониторинг

### Статистика работы
```
📈 Статистика за сегодня

📊 Всего сообщений: 1,247
📤 Отобрано: 89 (7.1%)
🎯 Процент отбора: ↗️ +2.3%

⏰ Последнее обновление: 14:25:17

📊 Статус    🗑️ Очистить статистику
🏠 Главное меню
```

### Системный статус
```
📊 Статус системы

📱 Telegram бот: ✅ Активен
🗄️ База данных: ✅ Подключена  
📺 Мониторинг каналов: ✅ Активен (47 каналов)
💾 Кэш подписок: ✅ Загружен (47 каналов)

🔄 Последний перезапуск: 12:30:45
⚡ Время работы: 2ч 15мин

🗂️ Управление каналами    📈 Статистика
🏠 Главное меню
```

## 🚨 Система алертов

### Категории алертов

**🔴 Критические (высокий приоритет):**
- Пожары, взрывы, ЧС
- ДТП с пострадавшими
- Стихийные бедствия

**🟡 Важные (средний приоритет):**
- Решения властей
- Транспортные происшествия  
- Погодные предупреждения

**📰 Общие (обычный приоритет):**
- Социальные события
- Спортивные новости
- Культурные мероприятия

### Формат алертов

```
🔴 КРИТИЧЕСКИЙ АЛЕРТ

🔥 Пожар на складе в Южно-Сахалинске
📍 Источник: @sakhalin_news
⏰ 14:25

[Текст сообщения...]

#пожар #ЧС #сахалин
```

## ⚡ Технические особенности

### Кэширование подписок
- **Быстрый старт** - не проверяет подписки на уже известные каналы
- **Автоматическое обновление** - добавляет новые каналы в кэш
- **Файл кэша** - `config/subscriptions_cache.json`

### Автоматическое редактирование сообщений
- **Inline кнопки** - редактируют то же сообщение
- **Reply кнопки** - создают новые сообщения (стандартное поведение)
- **Чистый интерфейс** - без спама сообщениями

### Пагинация
- **8 каналов на страницу** - оптимально для мобильных экранов
- **Навигация** - ◀️ Назад / ▶️ Далее
- **Индикатор** - 📄 2/5 (текущая страница из общего количества)

## 🛠️ Конфигурация

### Структура config.yaml

```yaml
telegram:
  api_id: int                    # Telegram API ID  
  api_hash: str                  # Telegram API Hash
  bot_token: str                 # Bot Token от @BotFather
  phone: str                     # Номер телефона (опционально)

output:
  target_group: int              # ID группы для отправки новостей
  topics:                        # Соответствие регион -> topic_id
    region_key: topic_id         # null для общего чата

alerts:
  category_name:                 # Категория алертов
    keywords: [str]              # Ключевые слова для поиска
    emoji: str                   # Эмодзи для категории  
    priority: str                # Приоритет: high/medium/low

regions:                         # Динамические регионы
  region_key:
    name: str                    # Отображаемое название с эмодзи
    emoji: str                   # Эмодзи региона
    description: str             # Описание региона
    keywords: [str]              # Ключевые слова для автоопределения
    topic_id: int                # ID топика в группе (опционально)
    created_at: str              # Дата создания

database:
  path: str                      # Путь к файлу базы данных
  backup_interval: int           # Интервал резервного копирования (часы)
```

### Структура channels_config.yaml

```yaml
regions:
  region_key:                    # Ключ региона из config.yaml
    name: str                    # Название региона
    channels:                    # Список каналов региона
      - username: str            # Username канала (без @)
        title: str               # Название канала
```

## 📁 Структура проекта

```
telegram-news-monitor/
├── main_bot.py                # 🚀 Главный файл запуска
├── requirements.txt           # 📦 Python зависимости
├── README.md                  # 📖 Документация
├── config/
│   ├── config.yaml           # ⚙️ Основная конфигурация
│   ├── channels_config.yaml  # 📺 Конфигурация каналов
│   └── subscriptions_cache.json  # 💾 Кэш подписок
├── src/
│   ├── telegram_bot.py       # 🤖 Telegram Bot API
│   ├── database.py           # 💾 SQLite база данных  
│   └── news_processor.py     # 📰 Обработка новостей
├── logs/
│   └── news_monitor.log      # 📝 Логи приложения
└── docs/
    ├── README.md             # 📚 Документация
    └── CREATE_BOT.md         # 🆕 Создание бота
```

## 🔧 Команды для управления

### Запуск и остановка
```bash
# Запуск
python main_bot.py

# Запуск в фоне  
nohup python main_bot.py &

# Остановка
# Ctrl+C или команда /restart в боте
```

### Просмотр логов
```bash
# Все логи
tail -f logs/news_monitor.log

# Только ошибки
grep ERROR logs/news_monitor.log

# Статистика работы
grep "📊" logs/news_monitor.log | tail -20
```

### Обслуживание базы данных
```bash
# Подключение к базе
sqlite3 news_monitor.db

# Основные запросы
.tables                        # Список таблиц
SELECT COUNT(*) FROM messages; # Количество сообщений
.quit                          # Выход
```

## 🔐 Безопасность

### Рекомендации по безопасности
- 🔒 **Не публикуйте** API ключи и токены
- 🛡️ **Ограничьте доступ** к файлам конфигурации  
- 💾 **Делайте бэкапы** базы данных регулярно
- 🔄 **Обновляйте** зависимости периодически

### Настройка прав доступа
```bash
# Ограничение доступа к конфигурации
chmod 600 config/config.yaml
chmod 600 config/channels_config.yaml

# Права на директории
chmod 755 logs/
chmod 755 config/
```

## 📞 Поддержка и разработка

### Полезные ссылки
- 📖 **Telegram Bot API**: https://core.telegram.org/bots/api
- 🔧 **Python Telegram Bot**: https://python-telegram-bot.org/
- 💾 **SQLite документация**: https://sqlite.org/docs.html

### Разработка
```bash
# Установка зависимостей для разработки
pip install -r requirements.txt

# Запуск в режиме отладки
python main_bot.py --debug

# Тестирование
python -m pytest tests/
```

## 📄 Лицензия

MIT License - свободное использование и модификация.

---

