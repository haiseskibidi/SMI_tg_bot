

**Telegram News Monitor** - корпоративное решение для автоматизации мониторинга Telegram-каналов. 


- **Автоматизация рутины** - исключение ручного мониторинга каналов
- **Региональная аналитика** - систематизация новостей по субъектам ДФО
- **Операционная эффективность** - сокращение времени обработки новостей
- **Централизованное управление** - единая точка контроля всех источников




- **Непрерывное отслеживание** - 24/7 мониторинг 80+ каналов
- **Instant обработка** - обработка новостей в момент публикации
- **Защита от блокировок** - умные таймауты и rate limiting
- **Кэширование подписок** - быстрый запуск (30 сек вместо 30 мин)


- **Автоматическая сортировка** - распределение по 6 регионам ДФО
- **Ключевые слова** - определение региона по контенту
- **Тематическая маршрутизация** - отправка в соответствующие топики
- **Исключение служебных тем** - фильтрация флуда и оффтопа


- **Команды управления** - полный контроль через бота
- **Inline кнопки** - интуитивная навигация
- **Пагинация** - удобный просмотр больших списков
- **Автоматическое редактирование** - чистый интерфейс


- **Live чтение каналов** - прямой доступ к Telegram API
- **Умная фильтрация** - исключение нерелевантного контента
- **Рейтинг популярности** - сортировка по активности
- **Экспорт результатов** - готовые сводки для публикации


- **Kill Switch** - экстренная остановка системы
- **Graceful shutdown** - корректное завершение работы
- **Резервное копирование** - автоматические бэкапы
- **Мониторинг состояния** - веб-интерфейс и уведомления





```
telegram-news-monitor/
├── main.py                  
├── src/                     
│   ├── core/               
│   │   ├── app.py         
│   │   ├── config_loader.py 
│   │   └── lifecycle.py    
│   ├── bot/               
│   │   ├── core/          
│   │   ├── ui/            
│   │   ├── channels/      
│   │   ├── regions/       
│   │   ├── handlers/      
│   │   ├── digest/        
│   │   └── utils/         
│   ├── handlers/          
│   │   ├── commands/      
│   │   └── callbacks/     
│   ├── monitoring/        
│   │   ├── channel_monitor.py 
│   │   ├── message_processor.py 
│   │   └── subscription_cache.py 
│   ├── database.py       
│   ├── digest_generator.py 
│   ├── telegram_client.py 
│   └── web_interface.py  
├── config/               
│   ├── config.yaml      
│   └── channels_config.yaml 
├── logs/                
├── sessions/            
├── tools/               
└── docs/                
```



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




- **ОС**: Ubuntu 20.04+ / Debian 11+ (рекомендуется)
- **RAM**: 1GB+ (минимум 512MB)
- **CPU**: 2 cores (минимум 1 core)
- **Диск**: 5GB+ свободного места
- **Сеть**: стабильное соединение с Telegram API


- **Python**: 3.8+
- **Telegram API**: api_id и api_hash с [my.telegram.org](https://my.telegram.org)
- **Telegram Bot**: токен от [@BotFather](https://t.me/BotFather)
- **Системный сервис**: systemd для автозапуска





```bash

sudo apt update && sudo apt upgrade -y


sudo apt install python3 python3-pip git systemd -y


sudo useradd -m -s /bin/bash news-monitor
sudo usermod -aG sudo news-monitor
```



```bash

sudo git clone <repository-url> /opt/telegram-news-monitor
cd /opt/telegram-news-monitor


sudo pip3 install -r requirements.txt


sudo chown -R news-monitor:news-monitor /opt/telegram-news-monitor
```



```bash

sudo cp env_template.txt .env
sudo nano .env
```

**Заполните .env файл:**
```env

BOT_TOKEN=1234567890:AAAA...


BOT_CHAT_ID=123456789


TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef...


TARGET_GROUP_ID=-1001234567890
```



```bash

python3 tools/setup_user_auth.py


python3 tools/safe_mode.py
```



```bash

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


sudo systemctl daemon-reload
sudo systemctl enable news-monitor.service
sudo systemctl start news-monitor.service
```





**Основная конфигурация системы:**

```yaml

telegram:
  api_id: "${TELEGRAM_API_ID}"        
  api_hash: "${TELEGRAM_API_HASH}"    


bot:
  token: "${BOT_TOKEN}"               
  chat_id: "${BOT_CHAT_ID}"          


output:
  target_group: "${TARGET_GROUP_ID}"  
  excluded_topics: [26, 27]          
  topics:                            
    sakhalin: 2
    kamchatka: 5  
    chita: 32
    yakutsk: 890
    vladivostok: 1020
    general: null                     


alerts:
  enabled: true
  keywords:
    emergency:                        
      emoji: "🔴🚨"
      priority: true
      words: ["пожар", "дтп", "чс", "авария", "взрыв"]
    important:                        
      emoji: "🟡⚠️"  
      priority: false
      words: ["власть", "транспорт", "погода", "шторм"]


regions:
  sakhalin:
    name: "🏝️ Сахалин"
    emoji: "🏝️"
    description: "Сахалинская область и Курильские острова"
    keywords: ["сахалин", "южно", "корсаков", "курилы"]
    topic_id: 2
    created_at: "2025-08-26"


monitoring:
  timeouts:
    batch_size: 6                     
    delay_cached_channel: 1           
    delay_between_batches: 8          
    delay_retry_wait: 300             
    fast_start_mode: true             


database:
  path: news_monitor.db


logging:
  file: logs/news_monitor.log
  level: INFO


web:
  port: 8080
```



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





**Утилиты для обслуживания (`tools/`):**

```bash

python3 tools/safe_mode.py


python3 tools/cleanup_database.py 7    
python3 tools/cleanup_database.py all  


python3 tools/backup_channels_config.py


python3 tools/add_news_manual.py


RESET_TELETHON_SESSION=1 python3 tools/setup_user_auth.py
```



```bash

sudo systemctl start news-monitor.service    
sudo systemctl stop news-monitor.service     
sudo systemctl restart news-monitor.service  
sudo systemctl status news-monitor.service   


sudo systemctl enable news-monitor.service   
sudo systemctl disable news-monitor.service  


sudo journalctl -u news-monitor.service -f           
sudo journalctl -u news-monitor.service --since "1 hour ago"  
```



**Доступ**: `http://localhost:8080` (или IP сервера)

**Возможности:**
- **Статистика в реальном времени** - сообщения, каналы, ошибки
- **Состояние компонентов** - Telegram, база данных, мониторинг
- **Системные ресурсы** - CPU, RAM, диск
- **Последние новости** - просмотр недавних сообщений
- **API endpoints** - `/api/stats`, `/api/news` для интеграций





```bash

sudo systemctl status news-monitor.service


tail -f /opt/telegram-news-monitor/logs/news_monitor.log


grep -E "(❌|ERROR)" /opt/telegram-news-monitor/logs/news_monitor.log | tail -20


ps aux | grep python3 | grep main.py


free -h && df -h && top -p $(pgrep -f "python3 main.py")
```



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



**1. "Rate limit" от Telegram API:**
```bash

grep "wait of.*seconds" logs/news_monitor.log


nano config/config.yaml



rm config/subscriptions_cache.json
sudo systemctl restart news-monitor.service
```

**2. "Бот заблокирован" (Kill Switch):**
```bash

ls -la /opt/telegram-news-monitor/STOP_BOT


/unlock


sudo rm /opt/telegram-news-monitor/STOP_BOT
sudo systemctl restart news-monitor.service
```

**3. "Проблемы с авторизацией Telethon":**
```bash

sudo rm /opt/telegram-news-monitor/sessions/news_monitor_session.session
cd /opt/telegram-news-monitor
sudo -u news-monitor python3 tools/setup_user_auth.py
```

**4. "База данных переполнена":**
```bash

ls -lah /opt/telegram-news-monitor/news_monitor.db


cd /opt/telegram-news-monitor
sudo -u news-monitor python3 tools/cleanup_database.py 14
```



**Уровни логирования в config.yaml:**
```yaml
logging:
  file: logs/news_monitor.log
  level: INFO    
```

**Ротация логов (настройка loguru):**
```python

logger.add("logs/news_monitor.log", 
          rotation="10 MB", retention="30 days")
```





**Безопасные настройки (config.yaml):**
```yaml
monitoring:
  timeouts:
    batch_size: 6              
    delay_cached_channel: 1    
    delay_between_batches: 8   
    delay_retry_wait: 300      
    fast_start_mode: true      
```

**Агрессивные настройки (риск блокировок):**
```yaml
monitoring:
  timeouts:
    batch_size: 10
    delay_between_batches: 5
    fast_start_mode: true
```



**Целевые показатели:**
- **RAM**: < 200MB в нормальном режиме
- **CPU**: < 10% при стабильной работе  
- **База данных**: < 500MB для 30 дней данных
- **Время запуска**: 30-60 секунд с кешем подписок

**Оптимизация SQLite:**
```yaml
database:
  path: news_monitor.db
  
```





Полная техническая документация по компонентам системы:

- **[Core Modules](architecture/CORE_MODULES.md)** - ядро системы (app.py, config_loader.py, lifecycle.py)
- **[Telegram Bot](architecture/TELEGRAM_BOT.md)** - модульная архитектура бота
- **[Monitoring](architecture/MONITORING.md)** - система мониторинга каналов  
- **[Database](architecture/DATABASE.md)** - SQLite база данных и операции
- **[Configuration](architecture/CONFIGURATION.md)** - настройки и переменные окружения
- **[Digest System](architecture/DIGEST_SYSTEM.md)** - генерация дайджестов
- **[Utilities](architecture/UTILITIES.md)** - административные утилиты
- **[Security](architecture/SECURITY.md)** - настройка безопасности



**Веб API endpoints:**
```
GET /api/stats    
GET /api/news     
GET /           
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



**Защита данных:**
- Все токены и API ключи только в `.env` файле
- Файл `.env` с правами 600 (только владелец может читать)
- Kill Switch для экстренной остановки системы
- Graceful shutdown при получении сигналов системы

**Сетевая безопасность:**
- Веб-интерфейс по умолчанию доступен только локально
- Можно настроить firewall для ограничения доступа
- HTTPS рекомендуется для продакшена (через nginx)





```bash

cd /opt/telegram-news-monitor


sudo -u news-monitor python3 tools/backup_channels_config.py


sudo git pull


sudo systemctl restart news-monitor.service


sudo journalctl -u news-monitor.service -f
```



**При переносе на новый сервер:**

1. **Сохранить конфигурацию:**
   ```bash
   
   tar -czf backup.tar.gz config/ sessions/ news_monitor.db
   ```

2. **Установить на новом сервере** (следовать инструкциям выше)

3. **Восстановить данные:**
   ```bash
   
   sudo systemctl stop news-monitor.service
   tar -xzf backup.tar.gz -C /opt/telegram-news-monitor/
   sudo chown -R news-monitor:news-monitor /opt/telegram-news-monitor/
   sudo systemctl start news-monitor.service
   ```





**Основные источники информации:**
```bash

tail -f /opt/telegram-news-monitor/logs/news_monitor.log


sudo journalctl -u news-monitor.service --since "1 hour ago"


sudo dmesg | grep -i error


ping telegram.org
curl -I https://api.telegram.org
```



При возникновении проблем:

1. **Проверьте логи** - большинство проблем видны в логах
2. **Проверьте статус** - команда `/status` в боте  
3. **Используйте безопасный режим** - `python3 tools/safe_mode.py`
4. **Консультируйтесь с документацией** - `docs/architecture/`

---

**Система Telegram News Monitor готова к круглосуточной работе в производственной среде для автоматизации мониторинга региональных новостей Дальнего Востока России.**



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




```
📈 Статистика за сегодня

📊 Всего сообщений: 1,247
📤 Отобрано: 89 (7.1%)
🎯 Процент отбора: ↗️ +2.3%

⏰ Последнее обновление: 14:25:17

📊 Статус    🗑️ Очистить статистику
🏠 Главное меню
```


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



```
🔴 КРИТИЧЕСКИЙ АЛЕРТ

🔥 Пожар на складе в Южно-Сахалинске
📍 Источник: @sakhalin_news
⏰ 14:25

[Текст сообщения...]


```




- **Быстрый старт** - не проверяет подписки на уже известные каналы
- **Автоматическое обновление** - добавляет новые каналы в кэш
- **Файл кэша** - `config/subscriptions_cache.json`


- **Inline кнопки** - редактируют то же сообщение
- **Reply кнопки** - создают новые сообщения (стандартное поведение)
- **Чистый интерфейс** - без спама сообщениями


- **8 каналов на страницу** - оптимально для мобильных экранов
- **Навигация** - ◀️ Назад / ▶️ Далее
- **Индикатор** - 📄 2/5 (текущая страница из общего количества)





```yaml
telegram:
  api_id: int                    
  api_hash: str                  
  bot_token: str                 
  phone: str                     

output:
  target_group: int              
  topics:                        
    region_key: topic_id         

alerts:
  category_name:                 
    keywords: [str]              
    emoji: str                   
    priority: str                

regions:                         
  region_key:
    name: str                    
    emoji: str                   
    description: str             
    keywords: [str]              
    topic_id: int                
    created_at: str              

database:
  path: str                      
  backup_interval: int           
```



```yaml
regions:
  region_key:                    
    name: str                    
    channels:                    
      - username: str            
        title: str               
```



```
telegram-news-monitor/
├── main_bot.py                
├── requirements.txt           
├── README.md                  
├── config/
│   ├── config.yaml           
│   ├── channels_config.yaml  
│   └── subscriptions_cache.json  
├── src/
│   ├── telegram_bot.py       
│   ├── database.py           
│   └── news_processor.py     
├── logs/
│   └── news_monitor.log      
└── docs/
    ├── README.md             
    └── CREATE_BOT.md         
```




```bash

python main_bot.py


nohup python main_bot.py &



```


```bash

tail -f logs/news_monitor.log


grep ERROR logs/news_monitor.log


grep "📊" logs/news_monitor.log | tail -20
```


```bash

sqlite3 news_monitor.db


.tables                        
SELECT COUNT(*) FROM messages; 
.quit                          
```




- 🔒 **Не публикуйте** API ключи и токены
- 🛡️ **Ограничьте доступ** к файлам конфигурации  
- 💾 **Делайте бэкапы** базы данных регулярно
- 🔄 **Обновляйте** зависимости периодически


```bash

chmod 600 config/config.yaml
chmod 600 config/channels_config.yaml


chmod 755 logs/
chmod 755 config/
```




- 📖 **Telegram Bot API**: https://core.telegram.org/bots/api
- 🔧 **Python Telegram Bot**: https://python-telegram-bot.org/
- 💾 **SQLite документация**: https://sqlite.org/docs.html


```bash

pip install -r requirements.txt


python main_bot.py --debug


python -m pytest tests/
```



MIT License - свободное использование и модификация.

---

