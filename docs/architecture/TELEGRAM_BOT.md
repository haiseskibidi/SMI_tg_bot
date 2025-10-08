



Telegram бот предоставляет полнофункциональный интерфейс управления системой мониторинга новостей. Работает как в личных чатах админа, так и в группах. Поддерживает команды, inline кнопки и интерактивные диалоги.

**Файлы**: `src/bot/` + `src/handlers/` (модульная архитектура)  
**API**: Telegram Bot API через HTTP запросы  
**Режимы**: Админ (личный чат) + Группа (командный чат)

---





```
src/bot/ (Модульная архитектура)
├── core/
│   ├── bot_client.py      
│   └── update_processor.py 
├── ui/
│   └── keyboard_builder.py 
├── channels/
│   ├── channel_manager.py  
│   ├── channel_parser.py   
│   └── channel_ui.py       
├── regions/
│   ├── region_manager.py   
│   └── region_ui.py        
├── handlers/
│   └── callback_processor.py 
├── digest/
│   └── digest_interface.py 
└── utils/
    ├── config_operations.py 
    └── text_helpers.py     

src/handlers/ (Интерфейсный слой)
├── commands/
│   ├── basic.py           
│   ├── channels.py        
│   ├── regions.py         
│   └── management.py      
└── callbacks/
    ├── channels.py        
    └── regions.py         
```



```
Telegram API → UpdateProcessor.process_update()
                     ↓
              ┌── Commands → src/handlers/commands/*
              ├── Callbacks → src/handlers/callbacks/*  
              ├── Text Messages → Bot logic (src/bot/*)
              └── Unknown → Help message
```

---





**Файл**: `src/handlers/commands/basic.py` (370+ строк)  
**Функция**: Главное меню, статус системы, управление мониторингом


```python
class BasicCommands:
    async def start(self, message: Optional[Dict[str, Any]]) -> None:
        keyboard = [
            [{"text": "📊 Статус", "callback_data": "status"}, 
             {"text": "🗂️ Управление каналами", "callback_data": "manage_channels"}],
            [{"text": "➕ Добавить канал", "callback_data": "add_channel"}, 
             {"text": "📡 Принудительная подписка", "callback_data": "force_subscribe"}],
            [{"text": "🚀 Запуск", "callback_data": "start_monitoring"}, 
             {"text": "🛑 Стоп", "callback_data": "stop_monitoring"}],
            [{"text": "🔄 Рестарт", "callback_data": "restart"}, 
             {"text": "⚙️ Настройки", "callback_data": "settings"}],
            [{"text": "📰 Дайджест", "callback_data": "digest"}, 
             {"text": "🆘 Справка", "callback_data": "help"}]
        ]
```


```python
async def status(self, message: Optional[Dict[str, Any]]) -> None:
    
    monitoring_status = "🟢 Запущен" if self.bot.main_instance.monitoring_active else "🔴 Остановлен"
    
    
    db_stats = await self.bot.main_instance.database.get_today_stats()
    active_channels = await self.bot.main_instance.database.get_active_channels_count()
    
    
    last_message = await self.bot.main_instance.database.get_latest_message_info()
    
    status_text = f"""
    📊 <b>Статус системы мониторинга</b>
    
    🔄 <b>Мониторинг:</b> {monitoring_status}
    📡 <b>Активных каналов:</b> {active_channels}/80+
    📥 <b>Сообщений за сегодня:</b> {db_stats.get('total_messages', 0)}
    """
```


```python
async def kill_switch(self, message: Optional[Dict[str, Any]]) -> None:
    """Экстренная остановка системы с созданием файла блокировки"""
    try:
        
        with open("STOP_BOT", "w") as f:
            f.write(f"Система остановлена: {datetime.now()}")
        
        
        if self.bot.main_instance:
            self.bot.main_instance.monitoring_active = False
        
        await self.bot.send_message("🛑 <b>ЭКСТРЕННАЯ ОСТАНОВКА АКТИВИРОВАНА</b>\n\n"
                                   "⚠️ Система заблокирована до ручного запуска\n"
                                   "💡 Используйте /unlock для разблокировки")
```



**Файл**: `src/handlers/commands/channels.py`  
**Функция**: Добавление каналов, принудительная подписка

```python
async def add_channel(self, message: Optional[Dict[str, Any]]) -> None:
    """Добавление канала по ссылке"""
    text = message.get("text", "")
    parts = text.split(maxsplit=1)
    
    if len(parts) < 2:
        await self.bot.send_message(
            "❌ <b>Неверный формат команды</b>\n\n"
            "Используйте:\n"
            "• <code>/add_channel https://t.me/news_channel</code>\n"
            "• <code>/add_channel @news_channel</code>"
        )
        return
    
    channel_link = parts[1].strip()
    await self.bot.add_channel_handler(channel_link)
```



**Файл**: `src/handlers/commands/management.py`  
**Функция**: Статистика

```python
async def stats(self, message: Optional[Dict[str, Any]]) -> None:
    """Детальная статистика работы системы"""
    
    stats = await self.bot.main_instance.database.get_today_stats()
    
    stats_text = f"""
    📊 <b>Статистика за сегодня</b>
    
    📥 Получено сообщений: {stats['total_messages']}
    ✅ Обработано: {stats['processed_messages']}  
    📤 Отправлено в группу: {stats['selected_messages']}
    🤖 AI запросов: {stats['ai_requests']}
    """
```

---





**Файл**: `src/handlers/callbacks/channels.py`  
**Функция**: Визуальное управление каналами через inline кнопки

```python
class ChannelCallbacks:
    async def show_channels_management(self, channels_data: Dict[str, Any]) -> None:
        """Показать список каналов по регионам с кнопками управления"""
        
        
        for region_key, region_info in channels_data.items():
            channels_count = len(region_info.get('channels', []))
            keyboard.append([{
                "text": f"{region_info['emoji']} {region_info['name']} ({channels_count})",
                "callback_data": f"show_region_channels_{region_key}"
            }])
    
    async def show_delete_confirmation(self, region_key: str, username: str) -> None:
        """Подтверждение удаления канала"""
        keyboard = [
            [{"text": "❌ Да, удалить", "callback_data": f"delete_channel_confirmed_{region_key}_{username}"}],
            [{"text": "↩️ Отмена", "callback_data": f"show_region_channels_{region_key}"}]
        ]
```



**Файл**: `src/handlers/callbacks/regions.py`  
**Функция**: Выбор регионов, создание новых регионов

```python
class RegionCallbacks:
    async def handle_region_selection(self, region: str) -> None:
        """Обработка выбора региона для канала"""
        if self.bot.pending_channel_url:
            
            await self.bot.add_channel_to_region(self.bot.pending_channel_url, region)
    
    async def start_create_region_flow(self) -> None:
        """Запуск процесса создания нового региона"""
        self.bot.waiting_for_region_name = True
        await self.bot.send_message(
            "🌏 <b>Создание нового региона</b>\n\n"
            "📝 Введите название региона (например: Приморье, Алтай):"
        )
```

---





```python
class TelegramBot:
    async def send_message(self, text: str, to_group: bool = True, to_user: int = None) -> bool:
        """Универсальная отправка с автоматическим выбором получателя"""
        try:
            if to_user:
                
                target_chat_id = to_user
            elif to_group and self.group_chat_id:
                
                target_chat_id = self.group_chat_id
            else:
                
                target_chat_id = self.admin_chat_id
            
            return await self._send_to_single_user(text, target_chat_id)
```



```python

self.edit_messages = True      
self.delete_commands = True    

async def send_message_with_keyboard(self, text: str, keyboard: List, use_reply_keyboard: bool = False):
    """Отправка с клавиатурой"""
    if self.edit_messages and self.last_message_id:
        
        success = await self.edit_message(text, self.last_message_id, keyboard)
        if success:
            return success
    
    
    response = await self.send_new_message_with_keyboard(text, keyboard)
```

---





```python
async def start_listening(self):
    """Главный цикл обработки команд и callback-ов"""
    self.is_listening = True
    logger.info("👂 Бот начал прослушивание команд")
    
    while self.is_listening:
        try:
            
            updates = await self.get_updates()
            
            if updates:
                for update in updates:
                    await self.process_update(update)
                    
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле прослушивания: {e}")
            await asyncio.sleep(5)
```



```python
async def process_update(self, update: dict):
    """Диспетчер событий"""
    
    
    if "message" in update:
        message = update["message"]
        text = message.get("text", "")
        
        if text.startswith("/"):
            
            await self.handle_command(text, message)
        elif "t.me/" in text or text.startswith("@"):
            
            await self.add_channel_handler(text)
        else:
            
            await self.handle_text_input(text, message)
    
    
    elif "callback_query" in update:
        callback = update["callback_query"]
        callback_data = callback.get("data", "")
        await self.handle_callback(callback_data, callback)
```

---





```python

async def initialize_components(self):
    """Инициализация бота как компонента системы"""
    
    
    self.telegram_bot = TelegramBot(
        bot_token=bot_config.get('token'),
        admin_chat_id=bot_config.get('chat_id'), 
        group_chat_id=output_config.get('target_group'),
        monitor_bot=self  
    )
    
    
    bot_listener_task = asyncio.create_task(
        self.telegram_bot.start_listening()
    )
```



```python
class TelegramBot:
    def __init__(self, monitor_bot=None):
        self.monitor_bot = monitor_bot      
        self.main_instance = monitor_bot    
    
    async def get_system_status(self):
        """Получение статуса через основное приложение"""
        if not self.main_instance:
            return "❌ Нет связи с системой"
        
        
        stats = await self.main_instance.database.get_today_stats()
        
        
        monitoring_active = self.main_instance.monitoring_active
        
        return f"📊 Система: {'🟢 OK' if monitoring_active else '🔴 Остановлена'}"
```

---





```python

"https://t.me/news_channel" → add_channel_handler()


channel_username = extract_channel_username(url)


await show_region_selection_for_channel(channel_username)


"region_selected_kamchatka" → handle_region_selection("kamchatka")


await add_channel_to_config(channel_username, region)
await monitor_bot.subscribe_to_single_channel(channel_username)
```



```python

self.waiting_for_region_name = True
await send_message("Введите название региона:")


user_input → handle_region_creation(region_input)


await show_emoji_selection(region_name)  


await show_region_creation_confirmation(region_data)


await create_region_confirmed(region_key)
```

---






```bash

grep "👂 Бот начал прослушивание" logs/news_monitor.log


grep "🎯 Получен callback\|💬 Команда:" logs/news_monitor.log  


grep "❌ Ошибка отправки сообщения" logs/news_monitor.log
```


```bash
/status          
/start          
/help           
```




```python

if not self.bot_token or self.bot_token == "YOUR_BOT_TOKEN":
    logger.error("❌ Некорректный токен бота")


if not self.is_listening:
    logger.warning("⚠️ Бот не прослушивает команды")
```


```python

if self.admin_chat_id == 123456789:  
    logger.error("❌ Не настроен admin_chat_id")


response = await httpx.get(f"{self.base_url}/getMe")
if response.status_code != 200:
    logger.error("❌ Нет доступа к Telegram API")
```


```bash

grep "Получен callback" logs/news_monitor.log


grep "❓ Неизвестный callback" logs/news_monitor.log
```




- **Время отклика**: < 2 секунды на команду
- **Успешность отправки**: > 95% сообщений доставлено  
- **Доступность**: 24/7 прослушивание команд
- **Обработка ошибок**: graceful degradation при сбоях


```yaml

bot:
  token: "${BOT_TOKEN}"           
  chat_id: "${BOT_CHAT_ID}"       
  
output:
  target_group: "${TARGET_GROUP_ID}"  
```

---




```
📊 Статус              🗂️ Управление каналами
➕ Добавить канал      📡 Принудительная подписка  
🚀 Запуск              🛑 Стоп
🔄 Рестарт             ⚙️ Настройки
📰 Дайджест            🆘 Справка
```


- **Редактирование сообщений**: обновление одного сообщения (по умолчанию)
- **Новые сообщения**: каждый ответ в новом сообщении  
- **Удаление команд**: автоматическая очистка команд пользователя
- **Админ + Группа**: поддержка личных команд и групповых уведомлений

---

*Документация Telegram Bot актуальна на: январь 2025*  
*Telegram Bot API версия: 7.0+, Python 3.8+*
