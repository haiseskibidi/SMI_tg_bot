# ⚙️ CONFIGURATION - Настройки системы

## 🎯 Обзор

Система конфигурации обеспечивает гибкую настройку всех компонентов News Monitor Bot через YAML файлы и переменные окружения. Поддерживает иерархическую структуру настроек с переопределением чувствительных данных.

**Файлы конфигурации**:
- `config/config.yaml` - основные настройки системы
- `config/channels_config.yaml` - каналы по регионам  
- `.env` - чувствительные данные (токены, API ключи)
- `config_example_timeouts.yaml` - шаблон настроек таймаутов

**Загрузчик**: `src/core/config_loader.py`

---

## 🏗️ Архитектура конфигурационной системы

### Иерархия приоритетов

```
1. Переменные окружения (.env файл)      ← ВЫСШИЙ ПРИОРИТЕТ
2. config.yaml (основные настройки)      ← СРЕДНИЙ ПРИОРИТЕТ  
3. Значения по умолчанию в коде          ← НИЗШИЙ ПРИОРИТЕТ
```

### Компоненты системы

```
ConfigLoader
├── load_config()           # Загрузка config.yaml + .env
├── load_alert_keywords()   # Система алертов  
├── load_regions_config()   # Региональные настройки
└── get_monitoring_timeouts() # Защита от rate limits

Файлы конфигурации:
├── config/config.yaml      # Основные настройки
├── config/channels_config.yaml # Каналы по регионам
├── .env                   # Чувствительные данные
└── config_example_timeouts.yaml # Шаблон таймаутов
```

### Принцип работы

```python
class ConfigLoader:
    def load_config(self) -> bool:
        # 1. Загрузка переменных окружения
        load_dotenv()
        
        # 2. Чтение YAML конфигурации
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 3. Переопределение из environment variables
        self._override_from_env()
        
        # 4. Загрузка специализированных настроек
        self.load_alert_keywords()
        self.load_regions_config()
```

---

## 📄 config.yaml - Основные настройки

### Структура конфигурации

#### 🚨 Система алертов
```yaml
alerts:
  enabled: true
  keywords:
    accident:                    # Категория: ДТП
      emoji: 🚗💥🚑
      priority: true            # Высокий приоритет
      words:
        - дтп
        - авария
        - столкновение
        - пострадавший
        - скорая
    
    crime:                      # Категория: Преступления  
      emoji: 🚔⚠️🚨
      priority: true
      words:
        - убийство
        - взрыв
        - стрельба
        - ограбление
        - задержан
    
    emergency:                  # Категория: ЧС
      emoji: 🔥🚨🔥
      priority: true
      words:
        - пожар
        - горит  
        - чс
        - эвакуация
        
    weather:                    # Категория: Погода
      emoji: 🌨️❄️⛈️
      priority: false           # Низкий приоритет
      words:
        - метель
        - снегопад
        - мороз
        - ливень
```

#### 🤖 Настройки бота
```yaml
bot:
  token: YOUR_BOT_TOKEN_FROM_ENV      # Переопределяется из .env
  chat_id: YOUR_CHAT_ID_FROM_ENV      # ID админа для команд
```

#### 🗄️ База данных
```yaml
database:
  path: news_monitor.db               # Путь к SQLite файлу
```

#### 📝 Логирование
```yaml
logging:
  file: logs/news_monitor.log         # Файл логов
  level: INFO                         # Уровень детализации
```

#### 📤 Настройки вывода
```yaml
output:
  target_group: YOUR_TARGET_GROUP_FROM_ENV  # ID группы для новостей
  topics:                             # Привязка регионов к темам
    kamchatka: 5                      # Камчатка → тема #5
    sakhalin: 2                       # Сахалин → тема #2  
    chita: 32                         # Чита → тема #32
    yakutsk: 890                      # Якутск → тема #890
    general: null                     # Общие без темы
```

#### 🌍 Региональная конфигурация  
```yaml
regions:
  kamchatka:
    name: 🌋 Камчатка
    emoji: 🌋
    description: Камчатский край
    topic_id: 5
    created_at: '2025-08-26'
    keywords:                         # Ключевые слова для автоопределения
      - камчатка
      - kamchatka
      - петропавловск
      - елизово  
      - вилючинск
      - '41'                          # Региональный код
      
  sakhalin:
    name: 🏝️ Сахалин
    emoji: 🏝️ 
    description: Сахалинская область и Курильские острова
    topic_id: 2
    keywords:
      - сахалин
      - sakhalin
      - южно-сахалинск
      - корсаков
      - курилы
      - '65'
```

#### 🔧 Системные настройки
```yaml
system:
  cache_size_mb: 100                  # Размер кэша (MB)
  max_concurrent_channels: 27         # Макс. каналов одновременно
  memory_limit_mb: 800               # Лимит памяти (MB)
```

#### 📡 Telegram API
```yaml
telegram:
  api_id: YOUR_API_ID_FROM_ENV       # Переопределяется из .env
  api_hash: YOUR_API_HASH_FROM_ENV   # Переопределяется из .env
```

#### 🌐 Веб-интерфейс
```yaml
web:
  port: 8080                         # Порт для веб-панели
```

---

## 🗂️ channels_config.yaml - Каналы по регионам

### Структура конфигурации каналов

```yaml
regions:
  kamchatka:
    name: 🌋 Камчатка
    channels:
      - title: ИА Кам24               # Человекочитаемое название
        username: IA_Kam24            # @username канала
      - title: Регион ТВ
        username: regiontv41
      - title: ГИБДД по Камчатскому краю
        username: kamchatkadps
      # ... до 25 каналов по региону
  
  sakhalin:
    name: 🏝️ Сахалин  
    channels:
      - title: АСТВ
        username: astv_ru
      - title: Точка 65
        username: tochka_65
      - title: Правительство Сахалинской области
        username: sakhgov
      # ... до 25 каналов по региону
      
  chita:
    name: 🏔️ Чита
    channels:
      - title: Канал @chp_chita
        username: chp_chita
      - title: Канал @dtp_chita  
        username: dtp_chita
      # ... региональные каналы
      
  general:
    name: 📰 Общие
    channels:
      - title: Канал @amur_mash
        username: amur_mash
      - title: Канал @maximum_news
        username: maximum_news
```

### Принципы организации каналов

#### 🏛️ Официальные каналы
- Правительство региона
- МЧС, ГИБДД, МВД  
- Министерства и ведомства
- Администрации городов

#### 📺 СМИ
- Местные информационные агентства
- Телеканалы и радио
- Интернет-издания
- Блогеры и журналисты

#### 🚨 Экстренные службы
- Каналы ЧП и происшествий
- Дорожные сводки
- Погодные предупреждения

---

## 🔐 Переменные окружения (.env файл)

### Шаблон .env файла

```env
# Токен Telegram бота (получить у @BotFather)
BOT_TOKEN=1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA

# ID админа для управления ботом (ваш Telegram ID)
BOT_CHAT_ID=123456789

# ID группы для всей команды (опционально)
BOT_GROUP_CHAT_ID=group_chat_id_here

# API данные из https://my.telegram.org
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890

# ID целевой группы для постинга новостей  
TARGET_GROUP_ID=-1001234567890
```

### Логика переопределения

```python
def _override_from_env(self):
    """Переопределение настроек из переменных окружения"""
    
    # Bot токен (обязательный)
    if bot_token := os.getenv('BOT_TOKEN'):
        self.config.setdefault('bot', {})['token'] = bot_token
    
    # ID админа (обязательный)
    if chat_id := os.getenv('BOT_CHAT_ID'):
        self.config.setdefault('bot', {})['chat_id'] = int(chat_id)
    
    # Telegram API (обязательные для мониторинга)
    if api_id := os.getenv('TELEGRAM_API_ID'):
        self.config.setdefault('telegram', {})['api_id'] = int(api_id)
        
    if api_hash := os.getenv('TELEGRAM_API_HASH'):
        self.config.setdefault('telegram', {})['api_hash'] = api_hash
    
    # Целевая группа (поддержка разных названий переменных)
    target_group = (
        os.getenv('TARGET_GROUP_ID') or 
        os.getenv('YOUR_TARGET_GROUP_FROM_ENV') or
        os.getenv('BOT_TARGET_GROUP')
    )
    if target_group:
        self.config.setdefault('output', {})['target_group'] = int(target_group)
```

---

## ⏱️ Настройки таймаутов Telegram API

### Защита от блокировок

```yaml
monitoring:
  timeouts:
    # 📦 ПАКЕТНАЯ ОБРАБОТКА
    batch_size: 6                    # Каналов в одном пакете (4-8)
    
    # ⏱️ БАЗОВЫЕ ЗАДЕРЖКИ  
    delay_cached_channel: 1          # Кешированные каналы (сек)
    delay_already_joined: 2          # Уже подписанные (сек) 
    delay_verification: 3            # Проверка подписки (сек)
    delay_after_subscribe: 5         # После подписки (сек)
    delay_between_batches: 8         # Между пакетами (сек)
    delay_retry_wait: 300            # Rate limit ожидание (5 мин)
    
    # 🚀 ОПТИМИЗАЦИЯ СКОРОСТИ
    fast_start_mode: true            # Приоритет кешированным каналам
    skip_new_on_startup: false       # Пропускать новые при запуске
```

### Профили настроек

#### 🛡️ Безопасный (для новых аккаунтов)
```yaml
batch_size: 4
delay_cached_channel: 2
delay_already_joined: 3
delay_between_batches: 12
fast_start_mode: false
```

#### ⚖️ Сбалансированный (рекомендуется)
```yaml
batch_size: 6  
delay_between_batches: 8
delay_after_subscribe: 5
fast_start_mode: true
skip_new_on_startup: false
```

#### 🚀 Быстрый (риск блокировки)
```yaml
batch_size: 8
delay_between_batches: 5
delay_after_subscribe: 3
fast_start_mode: true
skip_new_on_startup: true
```

### Логика применения таймаутов

```python
def get_monitoring_timeouts(self) -> Dict[str, Any]:
    """Получение настроек таймаутов с безопасными значениями по умолчанию"""
    timeouts = self.config.get('monitoring', {}).get('timeouts', {})
    
    # Безопасные значения по умолчанию
    default_timeouts = {
        'batch_size': 6,
        'delay_cached_channel': 1,
        'delay_between_batches': 8,
        'delay_retry_wait': 300,
        'fast_start_mode': True,
    }
    
    # Объединение с пользовательскими настройками
    for key, default_value in default_timeouts.items():
        if key not in timeouts:
            timeouts[key] = default_value
    
    return timeouts
```

---

## 🚨 Система алертов

### Обработка ключевых слов

```python
def check_alert_keywords(self, text: str) -> tuple:
    """Проверка текста на алерт-ключевые слова"""
    if not text or not self.config_loader.alert_keywords:
        return False, None, None, False, []
    
    text_lower = text.lower()
    
    # Проверяем каждую категорию алертов
    for category, data in self.config_loader.alert_keywords.items():
        words = data['words']
        emoji = data['emoji']
        priority = data['priority']
        
        # Ищем совпадения ключевых слов
        matched_words = []
        for word in words:
            if word in text_lower:
                matched_words.append(word)
        
        if matched_words:
            return True, category, emoji, priority, matched_words
    
    return False, None, None, False, []
```

### Форматирование алерт-сообщений

```python
def format_alert_message(
    self, original_text: str, 
    channel_username: str, 
    emoji: str, 
    category: str, 
    matched_words: list
) -> str:
    """Форматирование сообщения с алерт-заголовком"""
    alert_header = f"{emoji} АЛЕРТ: {category.upper()}\n"
    alert_header += f"📺 Канал: @{channel_username}\n"  
    alert_header += f"🔍 Ключевые слова: {', '.join(matched_words)}\n"
    alert_header += "─" * 30 + "\n\n"
    
    return alert_header + original_text
```

---

## 🌍 Региональная система

### Определение региона канала

```python
def get_channel_regions(self, channel_username: str) -> list:
    """Определение региона канала по приоритетной системе"""
    found_regions = []
    
    # ПРИОРИТЕТ 1: Явные настройки в channels_config.yaml
    try:
        with open('config/channels_config.yaml', 'r', encoding='utf-8') as f:
            channels_config = yaml.safe_load(f)
            
        for region_key, region_data in channels_config['regions'].items():
            channels = region_data.get('channels', [])
            for channel in channels:
                if channel.get('username') == channel_username:
                    found_regions.append(region_key)
                    return found_regions  # Возвращаем сразу
                    
    except Exception as e:
        logger.warning(f"⚠️ Ошибка чтения channels_config.yaml: {e}")
    
    # ПРИОРИТЕТ 2: Автоопределение по ключевым словам
    regions_config = self.config_loader.get_regions_config()
    for region_key, region_data in regions_config.items():
        keywords = region_data.get('keywords', [])
        
        # Проверяем имя канала на наличие ключевых слов региона
        channel_lower = channel_username.lower()
        for keyword in keywords:
            if keyword.lower() in channel_lower:
                found_regions.append(region_key)
                break
    
    return found_regions if found_regions else ['general']
```

### Привязка к темам супергруппы

```python
# Отправка сообщения в соответствующую тему
async def send_message_to_target(self, news: Dict, is_media: bool = False):
    regions = self.get_channel_regions(channel_username)
    output_config = self.config_loader.get_output_config()
    topics = output_config.get('topics', {})
    
    for region in regions:
        thread_id = topics.get(region)
        await self.telegram_bot.send_message_to_channel(
            message, target, None, thread_id
        )
```

---

## 🛠️ Управление конфигурацией через бота

### Команды управления

#### 🔧 /manage_channels - управление каналами
```python
# Отображение каналов по регионам из channels_config.yaml
async def manage_channels(self, message: Optional[Dict[str, Any]]) -> None:
    channels_data = await self.bot.get_all_channels_grouped()
    
    # Группировка по регионам
    for region_key, region_info in channels_data.items():
        channels_count = len(region_info.get('channels', []))
        keyboard.append([{
            "text": f"{region_info['emoji']} {region_info['name']} ({channels_count})",
            "callback_data": f"show_region_channels_{region_key}"
        }])
```

### Динамическое обновление конфигурации

#### ➕ Добавление каналов
```python
# Через интерфейс бота можно добавлять новые каналы
# Автоматически обновляется channels_config.yaml

async def add_channel_to_config(self, channel_username: str, region: str) -> bool:
    """Добавление канала в конфигурацию"""
    try:
        with open('config/channels_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Добавляем канал в соответствующий регион
        if 'regions' not in config:
            config['regions'] = {}
        if region not in config['regions']:
            config['regions'][region] = {'channels': []}
        
        config['regions'][region]['channels'].append({
            'title': f'Канал @{channel_username}',
            'username': channel_username
        })
        
        # Сохраняем обновленную конфигурацию
        with open('config/channels_config.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(config, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка добавления канала в конфиг: {e}")
        return False
```

---

## 🔍 Диагностика конфигурации

### Проверка загрузки конфигурации

#### 📋 Логи загрузки
```bash
# Основная конфигурация  
grep "✅ Конфигурация загружена из" logs/news_monitor.log

# Система алертов
grep "📢 Загружено.*категорий алертов" logs/news_monitor.log

# Региональная конфигурация
grep "🌍 Загружено.*регионов" logs/news_monitor.log

# Ошибки конфигурации
grep "❌ Ошибка.*конфигурации" logs/news_monitor.log
```

#### 🔧 Команды для диагностики
```bash
/status              # Общий статус системы 
/manage_channels    # Проверка конфигурации каналов
```

### Валидация файлов

#### 🔍 YAML валидация
```bash
# Проверка синтаксиса config.yaml
python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"

# Проверка channels_config.yaml
python -c "import yaml; yaml.safe_load(open('config/channels_config.yaml'))"

# Проверка переменных окружения
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('BOT_TOKEN:', bool(os.getenv('BOT_TOKEN')))"
```

#### 📊 Проверка настроек через код
```python
from src.core.config_loader import ConfigLoader

# Загрузка и проверка конфигурации
config_loader = ConfigLoader()
success = config_loader.load_config()
print(f"Конфигурация загружена: {success}")

# Проверка алертов
config_loader.load_alert_keywords()
print(f"Категорий алертов: {len(config_loader.alert_keywords)}")

# Проверка регионов  
config_loader.load_regions_config()
print(f"Регионов: {len(config_loader.regions_config)}")

# Проверка таймаутов
timeouts = config_loader.get_monitoring_timeouts()
print(f"Настройки таймаутов: {timeouts}")
```

### Типичные проблемы конфигурации

#### ❌ "Ошибка загрузки конфигурации"
```bash
# Проблемы с правами доступа
chmod 644 config/*.yaml

# Проблемы с кодировкой
file config/config.yaml  # Должен быть UTF-8

# Проблемы с синтаксисом YAML
python -m yaml config/config.yaml
```

#### ❌ "Переменные окружения не найдены"  
```bash
# Проверить существование .env
ls -la .env

# Проверить содержимое
cat .env

# Создать из шаблона
cp env_template.txt .env
# Заполнить своими данными
```

#### ❌ "Каналы не загружаются"
```bash
# Проверить channels_config.yaml
python -c "
import yaml
with open('config/channels_config.yaml') as f:
    config = yaml.safe_load(f)
    for region, data in config['regions'].items():
        print(f'{region}: {len(data.get("channels", []))} каналов')
"
```

#### ❌ "Алерты не работают"
```python
# Проверить настройки алертов в config.yaml
alerts_enabled = config_loader.config.get('alerts', {}).get('enabled', False)
print(f"Алерты включены: {alerts_enabled}")

# Проверить загрузку ключевых слов
print(f"Загружено категорий: {len(config_loader.alert_keywords)}")
for category, data in config_loader.alert_keywords.items():
    print(f"{category}: {len(data['words'])} слов")
```

---

## 🚀 Рекомендации по настройке

### Для продакшена

#### 🛡️ Безопасность
- **Переменные окружения**: все чувствительные данные только в `.env`
- **Права доступа**: `chmod 600 .env` (только владелец может читать)
- **Git ignore**: добавить `.env` в `.gitignore`
- **Backup**: регулярные копии конфигурационных файлов

#### ⚡ Производительность  
- **Таймауты**: использовать сбалансированные настройки
- **Fast start**: включить для быстрой загрузки
- **Memory limits**: настроить под доступную RAM сервера
- **Cache size**: оптимизировать под нагрузку

#### 📊 Мониторинг
- **Логи**: уровень INFO для продакшена
- **Alerts**: настроить все необходимые категории
- **Regions**: актуализировать ключевые слова
- **Channels**: периодически проверять активность каналов

### Для разработки

#### 🔧 Отладка
- **Логи**: уровень DEBUG для детального анализа
- **Timeouts**: безопасные настройки для избежания блокировок
- **Test mode**: отдельные переменные окружения
- **Validation**: автоматические проверки конфигурации при запуске

---

*Документация Configuration актуальна на: январь 2025*  
*Поддерживаемые форматы: YAML, ENV переменные*
