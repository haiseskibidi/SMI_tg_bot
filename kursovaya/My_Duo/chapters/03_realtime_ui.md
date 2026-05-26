# ГЛАВА 2. РЕАЛИЗАЦИЯ ПРОЕКТА

## 2.1 Реализация асинхронного ядра бота

Для создания быстродействующего и отзывчивого пользовательского интерфейса было реализовано полностью асинхронное ядро Telegram-бота. Поскольку стандартные библиотеки (например, aiogram) накладывают много ограничений на архитектуру и требуют большого количества системных ресурсов, ядро бота было спроектировано с нуля на базе встроенной библиотеки асинхронного ввода-вывода `asyncio` и библиотеки HTTP-клиента `httpx`.

Основой архитектуры является класс `TelegramBot` (модуль `src/bot/core/bot_client.py`), который управляет токеном авторизации, инициализирует служебные менеджеры и координирует жизненный цикл приложения. Прослушивание входящих событий от серверов Telegram реализовано по технологии **длинных опросов (Long Polling)** внутри вспомогательного класса `UpdateProcessor` (модуль `src/bot/core/update_processor.py`).

Асинхронный цикл опроса запускается методом `start_listening()`. Он непрерывно отправляет POST-запросы к методу `/getUpdates` API Telegram. Для исключения холостой нагрузки на процессор и сеть используется механизм Long Polling: сервер Telegram удерживает соединение открытым до тех пор, пока не появится новое событие для бота, или пока не истечёт время таймаута (в коде задан таймаут 10 секунд).

В листинге 2.1 представлена реализация основного цикла прослушивания событий и получения обновлений.

Листинг 2.1 — Асинхронный цикл прослушивания обновлений в `UpdateProcessor`

```python
async def start_listening(self):
    self.is_listening = True
    self.bot.is_listening = True
    logger.info("👂 Бот начал прослушивание команд")
    
    while self.is_listening:
        try:
            updates = await self.get_updates()
            
            if updates:
                for update in updates:
                    await self.process_update(update)
                    
            await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле прослушивания: {e}")
            await asyncio.sleep(5)
```

Для предотвращения дублирования обработки событий бот отслеживает параметр `update_offset`. При успешном получении обновлений смещение сдвигается на единицу больше, чем `update_id` последнего обработанного события:
```python
if updates:
    self.bot.update_offset = updates[-1]["update_id"] + 1
```

Метод `get_updates` содержит встроенную логику защиты от сбоев сети. В случае возникновения исключений при HTTP-запросе (например, временный сбой DNS или таймаут прокси-сервера), бот не завершает работу аварийно. Он логирует ошибку через `loguru` и применяет механизм экспоненциальной задержки (backoff) перед повторной попыткой:
```python
except Exception as e:
    logger.error(f"❌ Попытка {attempt + 1}/{max_retries} получения обновлений: {e}")
    if attempt < max_retries - 1:
        await asyncio.sleep(2 ** attempt)
```

Это гарантирует абсолютную стабильность работы бота в качестве фонового демона Linux-системы без риска утечки памяти или падения процесса.

## 2.2 Разработка модуля клавиатур и интерактивной навигации

Для построения интуитивно понятного интерфейса все интерактивные элементы и клавиатуры сгруппированы в отдельном модуле — классе `KeyboardBuilder` (модуль `src/bot/ui/keyboard_builder.py`).

Класс `KeyboardBuilder` предоставляет методы для отправки новых сообщений с клавиатурами и редактирования существующих. Ключевой особенностью является динамическая сборка inline-кнопок, привязанных к сообщениям.

Раскладка главного меню задаётся в коде статическим массивом кнопок, отправляемых в формате JSON структуры `inline_keyboard` (листинг 2.2).

Листинг 2.2 — Метод генерации клавиатуры главного меню

```python
def build_main_menu_keyboard(self) -> List[List[Dict]]:
    return [
        [{"text": "🗂️ Управление каналами", "callback_data": "manage_channels"}],
        [{"text": "➕ Добавить канал", "callback_data": "add_channel"}],
        [{"text": "🚀 Запуск", "callback_data": "start_monitoring"}, 
         {"text": "🛑 Стоп", "callback_data": "stop_monitoring"}],
        [{"text": "📰 Дайджест", "callback_data": "digest"}, 
         {"text": "🆘 Справка", "callback_data": "help"}]
    ]
```

При запуске бота в чате администратора отображается приветственное интерактивное сообщение и клавиатура главного меню.

![2.2.png](file:///C:/Users/Q1/Documents/SMI_tg_bot/kursovaya/2.2.png)

Рисунок 2.2 — Интерфейс главного меню Telegram-бота в чате администратора

Особую сложность в UX/UI проектировании мессенджеров представляет вывод больших объёмов данных. Если у администратора подключено несколько десятков каналов мониторинга, попытка вывести их все в одной клавиатуре приведёт к превышению лимитов Telegram API на размер сообщения и сделает интерфейс нечитаемым.

Для решения этой проблемы в `KeyboardBuilder` был спроектирован алгоритм интерактивной пагинации (постраничного вывода). Метод `build_pagination_keyboard` принимает текущую страницу, общее количество страниц и префикс для формирования callback-команды.

Алгоритм динамически рассчитывает количество элементов и дописывает внизу клавиатуры навигационные стрелки `⬅️ Стр. X-1` и `Стр. X+1 ➡️` только тогда, когда это логически необходимо (листинг 2.3).

Листинг 2.3 — Алгоритм постраничной пагинации клавиатуры

```python
def build_pagination_keyboard(self, current_page: int, total_pages: int, callback_prefix: str) -> List[List[Dict]]:
    keyboard = []
    nav_buttons = []
    
    if current_page > 1:
        nav_buttons.append({
            "text": f"⬅️ Стр. {current_page-1}",
            "callback_data": f"{callback_prefix}_{current_page-1}"
        })
    
    if current_page < total_pages:
        nav_buttons.append({
            "text": f"Стр. {current_page+1} ➡️",
            "callback_data": f"{callback_prefix}_{current_page+1}"
        })
        
    if nav_buttons:
        keyboard.append(nav_buttons)
        
    # Всегда добавляем кнопку возврата в главное меню
    keyboard.append([{"text": "🏠 Главное меню", "callback_data": "main_menu"}])
    return keyboard
```

Этот подход обеспечивает идеальный пользовательский опыт: интерфейс выглядит компактно, загружается мгновенно и адаптируется под любой размер экрана смартфона.

![2.3.png](file:///C:/Users/Q1/Documents/SMI_tg_bot/kursovaya/2.3.png)

Рисунок 2.3 — Экран управления подключенными каналами и пагинация

## 2.3 Обработка Callback-запросов и динамическое обновление интерфейса

При нажатии пользователем на любую inline-кнопку, клиент Telegram отправляет на сервер бота специальное событие — `CallbackQuery`. Это событие содержит поле `data` (уникальную строку, привязанную к кнопке при её создании) и идентификатор сообщения `message_id`, на котором был совершён клик.

Маршрутизация этих событий реализована в модуле `src/handlers/callback_processor.py`. Класс `CallbackProcessor` считывает строковое значение `callback_data` и распределяет выполнение по специализированным обработчикам.

Для реализации концепции SPA (Single Page Application) внутри чата, бот использует метод Telegram API `editMessageText` вместо отправки новых сообщений. Это реализовано через метод `edit_message_with_keyboard` класса `KeyboardBuilder`, который отправляет асинхронный POST-запрос к API (листинг 2.4).

Листинг 2.4 — Метод динамического редактирования экрана `edit_message_with_keyboard`

```python
async def edit_message_with_keyboard(
    self, 
    text: str, 
    keyboard: List = None, 
    message_id: int = None, 
    parse_mode: str = "HTML", 
    chat_id: int = None
) -> bool:
    try:
        target_message_id = message_id or self.bot.last_message_id
        target_chat_id = chat_id or self.bot.admin_chat_id
        
        if not target_message_id:
            return False
        
        data = {
            "chat_id": target_chat_id,
            "message_id": target_message_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        
        if keyboard:
            data["reply_markup"] = {"inline_keyboard": keyboard}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.bot.base_url}/editMessageText", json=data)
            
            if response.status_code == 200:
                logger.debug(f"✏️ Сообщение {target_message_id} отредактировано")
                return True
            else:
                logger.warning(f"⚠️ Ошибка редактирования сообщения: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Ошибка редактирования сообщения: {e}")
        return False
```

Благодаря такому подходу, пользователь видит мгновенную смену интерфейса прямо в одном сообщении. Например, при клике на кнопку «Управление каналами» текст сообщения меняется на «Список каналов», а кнопки под ним перестраиваются в список каналов с пагинацией. Это создаёт ощущение работы с полноценным мобильным приложением и полностью избавляет пользователя от необходимости прокручивать историю чата вверх-вниз.
