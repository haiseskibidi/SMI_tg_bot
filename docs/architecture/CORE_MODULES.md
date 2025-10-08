



Ядро системы состоит из 4 ключевых модулей, которые управляют жизненным циклом, конфигурацией и координацией всех компонентов системы.

```
CORE SYSTEM
├── main.py              
├── src/core/app.py      
├── src/core/config_loader.py  
└── src/core/lifecycle.py      
```

---



**Размер**: 23 строки  
**Функция**: Запуск системы с Kill Switch защитой


```python

"""
🤖 Telegram News Monitor Bot (Рефакторированная версия)
"""

import asyncio
from src.core import NewsMonitorWithBot

if __name__ == "__main__":
    
    import os
    if os.path.exists("STOP_BOT"):
        print("🛑 НАЙДЕН ФАЙЛ БЛОКИРОВКИ: STOP_BOT")
        print("🚫 БОТ ЗАБЛОКИРОВАН ОТ ЗАПУСКА")  
        print("💡 Удалите файл STOP_BOT для разблокировки")
        exit(0)
    
    asyncio.run(NewsMonitorWithBot().run())
```




- **Файл блокировки**: `STOP_BOT` в корне проекта
- **Приоритет**: Проверяется ДО любой инициализации
- **Безопасность**: Предотвращает автоперезапуски systemd
- **Управление**: Команды `/kill_switch` и `/unlock` в боте


- **Минимальный код**: только критически важная логика
- **Асинхронность**: `asyncio.run()` для основного цикла
- **Импорты**: отложенные импорты для быстроты


- **→ NewsMonitorWithBot**: передача управления главному классу
- **← systemd**: запуск через service файл
- **← Kill Switch**: команды из Telegram бота

---



**Размер**: 784 строки  
**Функция**: Оркестратор всех компонентов системы



```python
class NewsMonitorWithBot:
    def __init__(self, config_path: str = "config/config.yaml"):
        
        self.config_loader = ConfigLoader(config_path)
        self.lifecycle_manager = LifecycleManager(self.config_loader)
        self.subscription_cache = SubscriptionCacheManager()
        
        
        self.database = None
        self.telegram_monitor = None  
        self.telegram_bot = None      
        self.news_processor = None
        self.channel_monitor = None
```




```python
async def run(self):
    """Главный метод запуска системы"""
    
    if not self.config_loader.load_config():
        return False
    
    
    if not await self.initialize_components():
        return False
    
    
    self.running = True
    await self.monitoring_cycle()
```


```python
async def monitoring_cycle(self):
    """Основной цикл обработки событий"""
    
    await self.channel_monitor.setup_realtime_handlers()
    
    
    bot_listener_task = asyncio.create_task(
        self.telegram_bot.start_listening()
    )
    
    
    while self.running:
        await self.send_status_update()  
        await asyncio.sleep(30)
```


```python
async def send_message_to_target(self, news: Dict, is_media: bool = False):
    """Универсальная отправка в каналы с сортировкой по темам"""
    
    regions = self.get_channel_regions(channel_username)
    
    
    topics = output_config.get('topics', {})
    
    
    for region in regions:
        thread_id = topics.get(region)
        await self.telegram_bot.send_message_to_channel(
            message, target, None, thread_id
        )
```




- **Единая точка управления**: все компоненты инициализируются здесь
- **Dependency Injection**: передача зависимостей между модулями
- **Lifecycle Management**: контроль запуска и остановки


```
NewsMonitorWithBot
├── ConfigLoader (конфигурация)
├── LifecycleManager (запуск/остановка)  
├── DatabaseManager (хранение)
├── TelegramMonitor (Telethon чтение)
├── TelegramBot (Bot API команды)
├── ChannelMonitor (подписки)
├── MessageProcessor (обработка)
└── SubscriptionCache (кэш)
```


1. **Приоритет явных настроек**: `channels_config.yaml`
2. **Fallback ключевые слова**: автоопределение региона
3. **Отправка в темы**: соответствие регион → topic_id


- **← main.py**: точка входа через `NewsMonitorWithBot().run()`
- **→ ConfigLoader**: загрузка настроек
- **→ LifecycleManager**: управление компонентами  
- **→ All components**: координация работы всей системы

---



**Размер**: 182 строки  
**Функция**: Загрузка и валидация настроек системы



```python
class ConfigLoader:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = {}           
        self.regions_config = {}   
        self.alert_keywords = {}   
```




```python
def load_config(self) -> bool:
    """Загрузка основного config.yaml"""
    try:
        
        load_dotenv()
        
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        
        self._override_from_env()
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки конфигурации: {e}")
        return False
```


```python
def _override_from_env(self):
    """Переопределение настроек из переменных окружения"""
    
    if api_id := os.getenv('TELEGRAM_API_ID'):
        self.config.setdefault('telegram', {})['api_id'] = int(api_id)
    
    
    if bot_token := os.getenv('BOT_TOKEN'):
        self.config.setdefault('bot', {})['token'] = bot_token
    
    
    target_group = (os.getenv('TARGET_GROUP_ID') or 
                   os.getenv('YOUR_TARGET_GROUP_FROM_ENV') or
                   os.getenv('BOT_TARGET_GROUP'))
    if target_group:
        self.config.setdefault('output', {})['target_group'] = int(target_group)
```


```python
def get_monitoring_timeouts(self) -> Dict[str, Any]:
    """Получить настройки таймаутов для мониторинга каналов"""
    timeouts = self.config.get('monitoring', {}).get('timeouts', {})
    
    
    default_timeouts = {
        'batch_size': 6,                    
        'delay_cached_channel': 1,          
        'delay_between_batches': 8,         
        'delay_retry_wait': 300,            
        'fast_start_mode': True,            
    }
    
    
    for key, default_value in default_timeouts.items():
        if key not in timeouts:
            timeouts[key] = default_value
    
    return timeouts
```




1. **YAML файлы** - основные настройки
2. **Переменные окружения** - переопределения для деплоя
3. **Значения по умолчанию** - безопасные fallback значения


- **telegram**: API ключи, токены ботов
- **output**: целевые группы, темы
- **alerts**: ключевые слова, приоритеты
- **regions**: регионы, эмодзи, keywords
- **monitoring**: таймауты, защита от блокировок


- **Чувствительные данные**: только в переменных окружения
- **Валидация**: проверка типов и обязательных полей
- **Fallback значения**: система работает даже с минимальной конфигурацией


- **← NewsMonitorWithBot**: основной потребитель конфигурации
- **→ ChannelMonitor**: настройки таймаутов
- **→ TelegramBot**: токены и API ключи
- **→ All modules**: получение специфичных настроек

---



**Размер**: ~150 строк  
**Функция**: Инициализация, остановка и безопасность перезапусков



```python
class LifecycleManager:
    def __init__(self, config_loader):
        self.config_loader = config_loader
        
        
        self.database = None
        self.telegram_monitor = None
        self.telegram_bot = None
        self.news_processor = None
        self.system_monitor = None
        self.web_interface = None
```




```python
async def initialize_components(self) -> bool:
    """Последовательная инициализация всех компонентов"""
    try:
        
        self.database = DatabaseManager(db_path)
        await self.database.initialize()
        
        
        self.telegram_monitor = TelegramMonitor(api_id, api_hash, self.database)
        await self.telegram_monitor.initialize()
        
        self.telegram_bot = TelegramBot(config, self.database)
        await self.telegram_bot.initialize()
        
        
        self.news_processor = NewsProcessor(self.database)
        self.system_monitor = SystemMonitor()
        self.web_interface = WebInterface(self.database)
        
        logger.info("✅ Все компоненты инициализированы успешно")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации: {e}")
        return False
```


```python
async def _check_restart_safety(self) -> bool:
    """Проверка безопасности перезапуска (мин. 30 мин между перезапусками)"""
    restart_file = "config/.last_restart"
    
    try:
        if os.path.exists(restart_file):
            with open(restart_file, 'r') as f:
                last_restart = float(f.read().strip())
            
            time_since_restart = time.time() - last_restart
            min_interval = 30 * 60  
            
            if time_since_restart < min_interval:
                remaining = min_interval - time_since_restart
                logger.warning(f"⚠️ Слишком частый перезапуск. Ждём {remaining:.0f} сек")
                return False
        
        
        with open(restart_file, 'w') as f:
            f.write(str(time.time()))
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки безопасности: {e}")
        return True  
```


```python
async def shutdown(self):
    """Корректное завершение работы всех компонентов"""
    logger.info("🛑 Начинаем остановку системы...")
    
    try:
        
        if self.telegram_monitor:
            await self.telegram_monitor.disconnect()
        
        
        if self.telegram_bot:
            await self.telegram_bot.stop()
        
        
        if self.database:
            await self.database.close()
        
        
        if self.web_interface:
            await self.web_interface.stop()
        
        logger.info("✅ Система корректно остановлена")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при остановке: {e}")
```




**Правильный порядок инициализации:**
1. **Database** - основа для всех остальных
2. **TelegramMonitor** - чтение каналов
3. **TelegramBot** - интерфейс пользователя
4. **Processors** - обработка данных
5. **Auxiliary** - дополнительные сервисы


- **Минимальный интервал**: 30 минут между перезапусками
- **Файл состояния**: `.last_restart` с timestamp
- **Защита от флуда**: предотвращение блокировок Telegram


- **Порядок остановки**: обратный порядку запуска
- **Завершение задач**: ожидание текущих операций
- **Освобождение ресурсов**: корректное закрытие соединений


- **← NewsMonitorWithBot**: управление через `lifecycle_manager`
- **→ All components**: создание и управление жизненным циклом
- **↔ ConfigLoader**: получение настроек для инициализации

---




```
main.py
    ↓
NewsMonitorWithBot
    ↓
├── ConfigLoader ←→ LifecycleManager
    ↓                    ↓
└── All Components ←── Components Init
```


1. **main.py**: Kill Switch → запуск NewsMonitorWithBot
2. **NewsMonitorWithBot**: создание ConfigLoader и LifecycleManager
3. **ConfigLoader**: загрузка всех настроек
4. **LifecycleManager**: поэтапная инициализация компонентов
5. **NewsMonitorWithBot**: запуск основного цикла мониторинга


1. **Signal handling**: перехват Ctrl+C или системных сигналов
2. **NewsMonitorWithBot**: установка флага остановки
3. **LifecycleManager**: корректное завершение компонентов
4. **Exit**: освобождение ресурсов и выход

---




```bash

ls -la STOP_BOT


chmod 644 STOP_BOT


touch STOP_BOT
```


```bash

python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"


env | grep -E "(BOT_TOKEN|API_ID|TARGET_GROUP)"


python -c "from src.core import ConfigLoader; cl = ConfigLoader(); print(cl.load_config())"
```


```bash

grep -A 10 -B 5 "инициализация" logs/news_monitor.log


grep "✅.*инициализирован" logs/news_monitor.log


grep -E "(Database|Telegram).*ERROR" logs/news_monitor.log
```

---

*Документация модулей Core актуальна на: январь 2025*
