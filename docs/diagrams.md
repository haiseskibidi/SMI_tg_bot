

Все диаграммы в формате Mermaid. Их можно:
- Просмотреть прямо в GitHub/GitLab
- Экспортировать в PNG через https://mermaid.live/
- Открыть в VSCode с расширением Mermaid Preview

---



```mermaid
graph TB
    subgraph "Telegram Interface"
        A[Telegram Bot API<br/>Команды и управление]
        B[Telethon UserBot<br/>Мониторинг каналов]
    end
    
    subgraph "Core Application"
        C[Bot Client<br/>bot_client.py]
        D[Update Processor<br/>update_processor.py]
        E[Channel Monitor<br/>channel_monitor.py]
        F[Message Processor<br/>message_processor.py]
    end
    
    subgraph "Handlers Layer"
        G[Basic Commands<br/>start, help, status]
        H[Channel Commands<br/>add, remove, list]
        I[Region Commands<br/>regions management]
        J[AI Chat Handler<br/>ask, ai_info]
    end
    
    subgraph "AI Layer"
        K[Urgency Detector<br/>Анализ срочности]
        L[AI Chat<br/>Диалоги с нейросетью]
        M[Ollama Server<br/>qwen2.5:7b]
    end
    
    subgraph "Data Layer"
        N[(SQLite Database<br/>news_monitor.db)]
        O[YAML Configs<br/>channels, regions]
        P[Subscription Cache<br/>subscriptions_cache.json]
    end
    
    A --> C
    B --> E
    C --> D
    C --> G
    C --> H
    C --> I
    C --> J
    D --> F
    E --> F
    F --> K
    F --> N
    J --> L
    K --> M
    L --> M
    E --> P
    G --> N
    H --> O
    I --> O
    
    style M fill:
    style N fill:
    style K fill:
    style L fill:
```

---



```mermaid
erDiagram
    CHANNELS ||--o{ MESSAGES : contains
    REGIONS ||--o{ CHANNELS : "belongs to"
    MESSAGES ||--o{ DIGEST_MESSAGES : included_in
    
    CHANNELS {
        int id PK
        string channel_username UK
        string channel_name
        string region
        int topic_id
        boolean is_active
        datetime created_at
        datetime updated_at
    }
    
    MESSAGES {
        int id PK
        string channel_username FK
        string text
        datetime message_date
        string message_link
        string media_type
        int media_count
        string urgency_level
        float urgency_score
        string urgency_emoji
        text urgency_keywords
        boolean ai_analyzed
        datetime created_at
    }
    
    REGIONS {
        string region_name PK
        int topic_id UK
        int channel_count
        datetime created_at
        datetime updated_at
    }
    
    DIGEST_MESSAGES {
        int id PK
        int message_id FK
        date digest_date
        string region
        int position
        datetime created_at
    }
```

---



```mermaid
sequenceDiagram
    participant TC as Telegram Channel
    participant TM as Telethon Monitor
    participant MP as Message Processor
    participant UD as Urgency Detector
    participant AI as Ollama AI
    participant DB as Database
    participant Bot as Telegram Bot
    participant Group as Telegram Group
    
    TC->>TM: Новое сообщение
    TM->>TM: Проверка времени запуска
    TM->>TM: Обработка медиа-группы
    TM->>MP: Передача сообщения
    
    MP->>MP: Фильтр спама (keywords)
    alt Спам обнаружен
        MP-->>TM: Отклонить сообщение
    end
    
    MP->>MP: Извлечение текста
    MP->>UD: Анализ срочности
    
    UD->>UD: Поиск ключевых слов
    UD->>AI: AI классификация
    AI-->>UD: urgent/important/normal/ignore
    
    alt Реклама (ignore)
        UD-->>MP: 🚫 + text
    else Срочно (urgent)
        UD-->>MP: 🔴 СРОЧНО + text
    else Важно (important)
        UD-->>MP: 🟡 ВАЖНО + text
    else Обычно (normal)
        UD-->>MP: ⚪ + text
    end
    
    MP->>DB: Сохранение в БД
    MP->>Bot: Отправка в группу
    Bot->>Group: Публикация по топику
    Group-->>Bot: Успешно
    Bot-->>MP: Подтверждение
```

---



```mermaid
flowchart TD
    Start([Получена новость]) --> CheckText{Есть текст?}
    CheckText -->|Нет| SetWhite[⚪ Белый круг]
    CheckText -->|Да| CheckAI{AI доступен?}
    
    CheckAI -->|Нет| KeywordAnalysis[Анализ по ключевым словам]
    KeywordAnalysis --> SetBasicLevel[Базовый уровень срочности]
    SetBasicLevel --> SaveDB
    
    CheckAI -->|Да| PreparePrompt[Формирование промпта для AI]
    PreparePrompt --> SendToOllama[Отправка в Ollama]
    SendToOllama --> ParseResponse{Парсинг ответа}
    
    ParseResponse -->|ИГНОРИРОВАТЬ| SetIgnore[🚫 Спам/Реклама<br/>score = 0.0]
    ParseResponse -->|СРОЧНО| SetUrgent[🔴 СРОЧНО<br/>score = 0.9]
    ParseResponse -->|ВАЖНО| SetImportant[🟡 ВАЖНО<br/>score = 0.6]
    ParseResponse -->|ОБЫЧНО| SetNormal[⚪ Обычно<br/>score = 0.2]
    
    SetIgnore --> AddEmoji[Добавить эмодзи к тексту]
    SetUrgent --> AddPrefix[Добавить префикс **СРОЧНО**]
    SetImportant --> AddPrefixImp[Добавить префикс **ВАЖНО**]
    SetNormal --> AddEmoji
    
    AddEmoji --> SaveDB[(Сохранить в БД)]
    AddPrefix --> SaveDB
    AddPrefixImp --> SaveDB
    SetWhite --> SaveDB
    
    SaveDB --> SendToGroup[Отправить в Telegram группу]
    SendToGroup --> End([Конец])
    
    style SetUrgent fill:
    style SetImportant fill:
    style SetNormal fill:
    style SetIgnore fill:
    style SendToOllama fill:
    style SaveDB fill:
```

---



```mermaid
classDiagram
    class NewsMonitorWithBot {
        +ConfigLoader config_loader
        +DatabaseManager database
        +TelegramBot bot
        +ChannelMonitor telegram_monitor
        +initialize() bool
        +start() void
        +stop() void
    }
    
    class TelegramBot {
        -str bot_token
        -int group_chat_id
        -BasicCommands basic_commands
        -ChannelCommands channel_commands
        -AIChatHandler ai_chat
        +send_message(text, chat_id) bool
        +send_chat_action(action) bool
        +register_handlers() void
    }
    
    class ChannelMonitor {
        -TelegramClient client
        -dict monitored_channels
        +start_monitoring() void
        +add_channel(username) bool
        +remove_channel(username) bool
        +get_channel_entity(username) Entity
    }
    
    class MessageProcessor {
        -DatabaseManager database
        -NewsMonitorWithBot app_instance
        +process_new_message(message) void
        -_analyze_urgency(text) Dict
        -_save_to_database(data) void
    }
    
    class UrgencyDetector {
        -AsyncClient ollama_client
        -str model_name
        -dict urgent_keywords
        +analyze_news_urgency(text, source) Dict
        -_ai_classify_urgency(text) Dict
        -_keyword_based_urgency(text) float
    }
    
    class AIChatHandler {
        -AsyncClient ollama_client
        -dict chat_history
        -int max_history
        +handle_ai_question(message) void
        -_ask_ai(question, chat_id) str
        +clear_chat_history(chat_id) void
    }
    
    class DatabaseManager {
        -str db_path
        -Connection connection
        +save_message(data) void
        +get_messages(filters) List
        +update_channel(username, data) bool
    }
    
    NewsMonitorWithBot *-- TelegramBot
    NewsMonitorWithBot *-- ChannelMonitor
    NewsMonitorWithBot *-- DatabaseManager
    TelegramBot *-- AIChatHandler
    ChannelMonitor --> MessageProcessor
    MessageProcessor --> UrgencyDetector
    MessageProcessor --> DatabaseManager
    AIChatHandler --> "Ollama API" : uses
    UrgencyDetector --> "Ollama API" : uses
```

---



```mermaid
graph TD
    subgraph Actors
        J[Журналист]
        R[Редактор]
        A[Администратор]
        S[Система]
    end
    
    subgraph "Управление каналами"
        UC1[Добавить канал]
        UC2[Удалить канал]
        UC3[Просмотреть список каналов]
        UC4[Принудительная подписка]
    end
    
    subgraph "Мониторинг новостей"
        UC5[Мониторить каналы]
        UC6[Обрабатывать сообщения]
        UC7[Анализировать срочность]
        UC8[Фильтровать спам]
    end
    
    subgraph "AI функции"
        UC9[Задать вопрос AI]
        UC10[Получить анализ текста]
        UC11[Генерация заголовков]
        UC12[Создание байтов]
    end
    
    subgraph "Дайджесты"
        UC13[Создать дайджест]
        UC14[Просмотреть дайджест]
    end
    
    subgraph "Администрирование"
        UC15[Просмотр статистики]
        UC16[Управление регионами]
        UC17[Настройка конфигов]
    end
    
    A --> UC1
    A --> UC2
    R --> UC3
    A --> UC4
    
    S --> UC5
    S --> UC6
    S --> UC7
    S --> UC8
    
    J --> UC9
    J --> UC10
    J --> UC11
    J --> UC12
    
    R --> UC13
    J --> UC14
    
    A --> UC15
    A --> UC16
    A --> UC17
    
    UC6 --> UC7
    UC6 --> UC8
    UC7 -.-> UC9
    UC10 -.-> UC11
    UC11 -.-> UC12
```

---



```mermaid
graph TB
    subgraph "VPS Server (IShosting)"
        subgraph "Python Environment"
            Bot[news_monitor.py<br/>Main Application]
            DB[(SQLite Database<br/>news_monitor.db)]
            Logs[/logs/<br/>news_monitor.log]
            Config[/config/<br/>YAML files]
        end
        
        subgraph "Ollama Service"
            Ollama[Ollama Server<br/>:11434]
            Model[qwen2.5:7b Model<br/>~4.7 GB]
        end
    end
    
    subgraph "Telegram Infrastructure"
        TelegramAPI[Telegram Bot API]
        TelegramMTProto[Telegram MTProto API]
        NewsChannels[Новостные каналы<br/>9 регионов]
        WorkGroup[Рабочая группа<br/>с темами]
    end
    
    Bot -->|Bot API| TelegramAPI
    Bot -->|Telethon| TelegramMTProto
    Bot -->|HTTP| Ollama
    Ollama -->|Load| Model
    Bot -->|Write| DB
    Bot -->|Write| Logs
    Bot -->|Read| Config
    
    TelegramMTProto -->|Monitor| NewsChannels
    TelegramAPI -->|Post| WorkGroup
    
    style Bot fill:
    style Ollama fill:
    style Model fill:
    style DB fill:
    style WorkGroup fill:
```

---




1. Откройте https://mermaid.live/
2. Скопируйте код диаграммы
3. Экспортируйте в PNG/SVG/PDF


1. Установите расширение "Markdown Preview Mermaid Support"
2. Откройте этот файл
3. Нажмите Preview (Ctrl+Shift+V)


Диаграммы автоматически рендерятся при просмотре .md файлов

---



Вы можете изменить:
- Цвета: `style NodeName fill:
- Стрелки: `-->` (обычная), `-.->` (пунктир), `==>` (жирная)
- Формы: `[]` (прямоугольник), `()` (овал), `{}` (ромб), `[()]` (стадион)
- Направление: `TB` (сверху вниз), `LR` (слева направо)

