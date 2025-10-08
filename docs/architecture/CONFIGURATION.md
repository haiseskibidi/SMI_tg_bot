



Система конфигурации обеспечивает гибкую настройку всех компонентов News Monitor Bot через YAML файлы и переменные окружения. Поддерживает иерархическую структуру настроек с переопределением чувствительных данных.

**Файлы конфигурации**:
- `config/config.yaml` - основные настройки системы
- `config/channels_config.yaml` - каналы по регионам  
- `.env` - чувствительные данные (токены, API ключи)
- `config_example_timeouts.yaml` - шаблон настроек таймаутов

**Загрузчик**: `src/core/config_loader.py`

---





```
1. Переменные окружения (.env файл)      ← ВЫСШИЙ ПРИОРИТЕТ
2. config.yaml (основные настройки)      ← СРЕДНИЙ ПРИОРИТЕТ  
3. Значения по умолчанию в коде          ← НИЗШИЙ ПРИОРИТЕТ
```



```
ConfigLoader
├── load_config()           
├── load_alert_keywords()   
├── load_regions_config()   
└── get_monitoring_timeouts() 

Файлы конфигурации:
├── config/config.yaml      
├── config/channels_config.yaml 
├── .env                   
└── config_example_timeouts.yaml 
```



```python
class ConfigLoader:
    def load_config(self) -> bool:
        
        load_dotenv()
        
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        
        self._override_from_env()
        
        
        self.load_alert_keywords()
        self.load_regions_config()
```

---






```yaml
alerts:
  enabled: true
  keywords:
    accident:                    
      emoji: 🚗💥🚑
      priority: true            
      words:
        - дтп
        - авария
        - столкновение
        - пострадавший
        - скорая
    
    crime:                      
      emoji: 🚔⚠️🚨
      priority: true
      words:
        - убийство
        - взрыв
        - стрельба
        - ограбление
        - задержан
    
    emergency:                  
      emoji: 🔥🚨🔥
      priority: true
      words:
        - пожар
        - горит  
        - чс
        - эвакуация
        
    weather:                    
      emoji: 🌨️❄️⛈️
      priority: false           
      words:
        - метель
        - снегопад
        - мороз
        - ливень
```


```yaml
bot:
  token: YOUR_BOT_TOKEN_FROM_ENV      
  chat_id: YOUR_CHAT_ID_FROM_ENV      
```


```yaml
database:
  path: news_monitor.db               
```


```yaml
logging:
  file: logs/news_monitor.log         
  level: INFO                         
```


```yaml
output:
  target_group: YOUR_TARGET_GROUP_FROM_ENV  
  topics:                             
    kamchatka: 5                      
    sakhalin: 2                       
    chita: 32                         
    yakutsk: 890                      
    general: null                     
```


```yaml
regions:
  kamchatka:
    name: 🌋 Камчатка
    emoji: 🌋
    description: Камчатский край
    topic_id: 5
    created_at: '2025-08-26'
    keywords:                         
      - камчатка
      - kamchatka
      - петропавловск
      - елизово  
      - вилючинск
      - '41'                          
      
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


```yaml
system:
  cache_size_mb: 100                  
  max_concurrent_channels: 27         
  memory_limit_mb: 800               
```


```yaml
telegram:
  api_id: YOUR_API_ID_FROM_ENV       
  api_hash: YOUR_API_HASH_FROM_ENV   
```


```yaml
web:
  port: 8080                         
```

---





```yaml
regions:
  kamchatka:
    name: 🌋 Камчатка
    channels:
      - title: ИА Кам24               
        username: IA_Kam24            
      - title: Регион ТВ
        username: regiontv41
      - title: ГИБДД по Камчатскому краю
        username: kamchatkadps
      
  
  sakhalin:
    name: 🏝️ Сахалин  
    channels:
      - title: АСТВ
        username: astv_ru
      - title: Точка 65
        username: tochka_65
      - title: Правительство Сахалинской области
        username: sakhgov
      
      
  chita:
    name: 🏔️ Чита
    channels:
      - title: Канал @chp_chita
        username: chp_chita
      - title: Канал @dtp_chita  
        username: dtp_chita
      
      
  general:
    name: 📰 Общие
    channels:
      - title: Канал @amur_mash
        username: amur_mash
      - title: Канал @maximum_news
        username: maximum_news
```




- Правительство региона
- МЧС, ГИБДД, МВД  
- Министерства и ведомства
- Администрации городов


- Местные информационные агентства
- Телеканалы и радио
- Интернет-издания
- Блогеры и журналисты


- Каналы ЧП и происшествий
- Дорожные сводки
- Погодные предупреждения

---





```env

BOT_TOKEN=1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA


BOT_CHAT_ID=123456789


BOT_GROUP_CHAT_ID=group_chat_id_here


TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890


TARGET_GROUP_ID=-1001234567890
```



```python
def _override_from_env(self):
    """Переопределение настроек из переменных окружения"""
    
    
    if bot_token := os.getenv('BOT_TOKEN'):
        self.config.setdefault('bot', {})['token'] = bot_token
    
    
    if chat_id := os.getenv('BOT_CHAT_ID'):
        self.config.setdefault('bot', {})['chat_id'] = int(chat_id)
    
    
    if api_id := os.getenv('TELEGRAM_API_ID'):
        self.config.setdefault('telegram', {})['api_id'] = int(api_id)
        
    if api_hash := os.getenv('TELEGRAM_API_HASH'):
        self.config.setdefault('telegram', {})['api_hash'] = api_hash
    
    
    target_group = (
        os.getenv('TARGET_GROUP_ID') or 
        os.getenv('YOUR_TARGET_GROUP_FROM_ENV') or
        os.getenv('BOT_TARGET_GROUP')
    )
    if target_group:
        self.config.setdefault('output', {})['target_group'] = int(target_group)
```

---





```yaml
monitoring:
  timeouts:
    
    batch_size: 6                    
    
    
    delay_cached_channel: 1          
    delay_already_joined: 2          
    delay_verification: 3            
    delay_after_subscribe: 5         
    delay_between_batches: 8         
    delay_retry_wait: 300            
    
    
    fast_start_mode: true            
    skip_new_on_startup: false       
```




```yaml
batch_size: 4
delay_cached_channel: 2
delay_already_joined: 3
delay_between_batches: 12
fast_start_mode: false
```


```yaml
batch_size: 6  
delay_between_batches: 8
delay_after_subscribe: 5
fast_start_mode: true
skip_new_on_startup: false
```


```yaml
batch_size: 8
delay_between_batches: 5
delay_after_subscribe: 3
fast_start_mode: true
skip_new_on_startup: true
```



```python
def get_monitoring_timeouts(self) -> Dict[str, Any]:
    """Получение настроек таймаутов с безопасными значениями по умолчанию"""
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

---





```python
def check_alert_keywords(self, text: str) -> tuple:
    """Проверка текста на алерт-ключевые слова"""
    if not text or not self.config_loader.alert_keywords:
        return False, None, None, False, []
    
    text_lower = text.lower()
    
    
    for category, data in self.config_loader.alert_keywords.items():
        words = data['words']
        emoji = data['emoji']
        priority = data['priority']
        
        
        matched_words = []
        for word in words:
            if word in text_lower:
                matched_words.append(word)
        
        if matched_words:
            return True, category, emoji, priority, matched_words
    
    return False, None, None, False, []
```



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





```python
def get_channel_regions(self, channel_username: str) -> list:
    """Определение региона канала по приоритетной системе"""
    found_regions = []
    
    
    try:
        with open('config/channels_config.yaml', 'r', encoding='utf-8') as f:
            channels_config = yaml.safe_load(f)
            
        for region_key, region_data in channels_config['regions'].items():
            channels = region_data.get('channels', [])
            for channel in channels:
                if channel.get('username') == channel_username:
                    found_regions.append(region_key)
                    return found_regions  
                    
    except Exception as e:
        logger.warning(f"⚠️ Ошибка чтения channels_config.yaml: {e}")
    
    
    regions_config = self.config_loader.get_regions_config()
    for region_key, region_data in regions_config.items():
        keywords = region_data.get('keywords', [])
        
        
        channel_lower = channel_username.lower()
        for keyword in keywords:
            if keyword.lower() in channel_lower:
                found_regions.append(region_key)
                break
    
    return found_regions if found_regions else ['general']
```



```python

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






```python

async def manage_channels(self, message: Optional[Dict[str, Any]]) -> None:
    channels_data = await self.bot.get_all_channels_grouped()
    
    
    for region_key, region_info in channels_data.items():
        channels_count = len(region_info.get('channels', []))
        keyboard.append([{
            "text": f"{region_info['emoji']} {region_info['name']} ({channels_count})",
            "callback_data": f"show_region_channels_{region_key}"
        }])
```




```python



async def add_channel_to_config(self, channel_username: str, region: str) -> bool:
    """Добавление канала в конфигурацию"""
    try:
        with open('config/channels_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        
        if 'regions' not in config:
            config['regions'] = {}
        if region not in config['regions']:
            config['regions'][region] = {'channels': []}
        
        config['regions'][region]['channels'].append({
            'title': f'Канал @{channel_username}',
            'username': channel_username
        })
        
        
        with open('config/channels_config.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(config, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка добавления канала в конфиг: {e}")
        return False
```

---






```bash

grep "✅ Конфигурация загружена из" logs/news_monitor.log


grep "📢 Загружено.*категорий алертов" logs/news_monitor.log


grep "🌍 Загружено.*регионов" logs/news_monitor.log


grep "❌ Ошибка.*конфигурации" logs/news_monitor.log
```


```bash
/status              
/manage_channels    
```




```bash

python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"


python -c "import yaml; yaml.safe_load(open('config/channels_config.yaml'))"


python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('BOT_TOKEN:', bool(os.getenv('BOT_TOKEN')))"
```


```python
from src.core.config_loader import ConfigLoader


config_loader = ConfigLoader()
success = config_loader.load_config()
print(f"Конфигурация загружена: {success}")


config_loader.load_alert_keywords()
print(f"Категорий алертов: {len(config_loader.alert_keywords)}")


config_loader.load_regions_config()
print(f"Регионов: {len(config_loader.regions_config)}")


timeouts = config_loader.get_monitoring_timeouts()
print(f"Настройки таймаутов: {timeouts}")
```




```bash

chmod 644 config/*.yaml


file config/config.yaml  


python -m yaml config/config.yaml
```


```bash

ls -la .env


cat .env


cp env_template.txt .env

```


```bash

python -c "
import yaml
with open('config/channels_config.yaml') as f:
    config = yaml.safe_load(f)
    for region, data in config['regions'].items():
        print(f'{region}: {len(data.get("channels", []))} каналов')
"
```


```python

alerts_enabled = config_loader.config.get('alerts', {}).get('enabled', False)
print(f"Алерты включены: {alerts_enabled}")


print(f"Загружено категорий: {len(config_loader.alert_keywords)}")
for category, data in config_loader.alert_keywords.items():
    print(f"{category}: {len(data['words'])} слов")
```

---






- **Переменные окружения**: все чувствительные данные только в `.env`
- **Права доступа**: `chmod 600 .env` (только владелец может читать)
- **Git ignore**: добавить `.env` в `.gitignore`
- **Backup**: регулярные копии конфигурационных файлов


- **Таймауты**: использовать сбалансированные настройки
- **Fast start**: включить для быстрой загрузки
- **Memory limits**: настроить под доступную RAM сервера
- **Cache size**: оптимизировать под нагрузку


- **Логи**: уровень INFO для продакшена
- **Alerts**: настроить все необходимые категории
- **Regions**: актуализировать ключевые слова
- **Channels**: периодически проверять активность каналов




- **Логи**: уровень DEBUG для детального анализа
- **Timeouts**: безопасные настройки для избежания блокировок
- **Test mode**: отдельные переменные окружения
- **Validation**: автоматические проверки конфигурации при запуске

---

*Документация Configuration актуальна на: январь 2025*  
*Поддерживаемые форматы: YAML, ENV переменные*
