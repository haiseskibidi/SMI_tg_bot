



**1. Создайте файл `.env` в корне проекта:**

```bash

notepad .env


nano .env
```

**2. Скопируйте и заполните своими данными:**

```env

BOT_TOKEN=1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA


BOT_CHAT_ID=123456789


TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890


TARGET_GROUP_ID=-1001234567890
```

**3. Сохраните файл**



- **.env файл НИКОГДА не загружайте в Git!**
- **Проверьте что .env добавлен в .gitignore**
- **На сервере создавайте .env файл заново**




```bash
cd /opt/news-monitor
nano .env

```


```bash

export BOT_TOKEN="1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
export BOT_CHAT_ID="123456789"
export TELEGRAM_API_ID="12345678"
export TELEGRAM_API_HASH="abcdef1234567890abcdef1234567890"
export TARGET_GROUP_ID="-1001234567890"
```



Запустите бота - в логах должно быть:
```
✅ Конфигурация загружена из config/config.yaml
```

Если ошибка - проверьте:
1. Существует ли .env файл
2. Правильно ли указаны переменные
3. Нет ли лишних пробелов в .env
