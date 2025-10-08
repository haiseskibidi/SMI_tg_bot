

Корпоративная система автоматического мониторинга новостных каналов для СМИ с интеллектуальной фильтрацией и региональной сортировкой.



Готовое к продакшену решение для автоматизации мониторинга Telegram каналов. Система обеспечивает круглосуточное отслеживание новостей с автоматической сортировкой по регионам и темам.



```bash

git clone <repository-url> /opt/telegram-news-monitor
cd /opt/telegram-news-monitor
pip3 install -r requirements.txt


cp env_template.txt .env



python3 tools/setup_user_auth.py


python3 main.py
```



- **📡 Real-time мониторинг** - 24/7 отслеживание каналов
- **🌍 Региональная сортировка** - автоматическое распределение по регионам  
- **🎯 Тематическая маршрутизация** - отправка в соответствующие топики
- **📊 Система дайджестов** - генерация сводок популярных новостей
- **🛡️ Защита от блокировок** - умные таймауты и rate limiting
- **⚡ Быстрый запуск** - кэширование подписок (30 сек вместо 30 мин)



```bash

python3 main.py                    
python3 tools/safe_mode.py         
python3 tools/backup_channels_config.py  


/start        
/status       
/digest       
/manage_channels 
/topic_id     
/restart      
```



- **Python 3.8+**
- **Ubuntu 20.04+ / Debian 11+** (рекомендуется)
- **RAM**: 1GB+ (минимум 512MB)
- **CPU**: 2 cores (минимум 1 core)
- **Диск**: 5GB+ свободного места



**Вся детальная информация по установке, настройке, использованию и администрированию находится в:**



Включает:
- **Пошаговую установку** - от нуля до продакшена
- **Конфигурацию системы** - все настройки с примерами
- **Команды управления** - полный справочник
- **Диагностику проблем** - решение типичных ошибок
- **Администрирование** - обслуживание и мониторинг
- **Архитектурную документацию** - техническая информация



Детальная документация по компонентам в `docs/architecture/`:
- [Core Modules](docs/architecture/CORE_MODULES.md) - ядро системы
- [Configuration](docs/architecture/CONFIGURATION.md) - настройки системы
- [Security](docs/architecture/SECURITY.md) - переменные окружения и безопасность
- [Database](docs/architecture/DATABASE.md) - SQLite база данных
- [Monitoring](docs/architecture/MONITORING.md) - система мониторинга каналов
- [Bot System](docs/architecture/TELEGRAM_BOT.md) - модульная архитектура бота
- [Digest System](docs/architecture/DIGEST_SYSTEM.md) - генерация дайджестов
- [Utilities](docs/architecture/UTILITIES.md) - административные инструменты

---

