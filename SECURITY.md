# 🔒 НАСТРОЙКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ

## 📋 Создание .env файла

**1. Создайте файл `.env` в корне проекта:**

```bash
# На своем компьютере
notepad .env

# На сервере
nano .env
```

**2. Скопируйте и заполните своими данными:**

```env
# Токен Telegram бота (получить у @BotFather)
BOT_TOKEN=1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA

# ID чата для уведомлений (ваш Telegram ID)
BOT_CHAT_ID=123456789

# API данные из https://my.telegram.org
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890

# ID целевой группы для постинга новостей
TARGET_GROUP_ID=-1001234567890
```

**3. Сохраните файл**

## ⚠️ ВАЖНО!

- **.env файл НИКОГДА не загружайте в Git!**
- **Проверьте что .env добавлен в .gitignore**
- **На сервере создавайте .env файл заново**

## 🚀 Перенос на сервер

### Способ 1: Создать .env на сервере вручную
```bash
cd /opt/news-monitor
nano .env
# Вставить содержимое и сохранить
```

### Способ 2: Через переменные окружения системы
```bash
# Добавить в ~/.bashrc или /etc/environment
export BOT_TOKEN="1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
export BOT_CHAT_ID="123456789"
export TELEGRAM_API_ID="12345678"
export TELEGRAM_API_HASH="abcdef1234567890abcdef1234567890"
export TARGET_GROUP_ID="-1001234567890"
```

## ✅ Проверка

Запустите бота - в логах должно быть:
```
✅ Конфигурация загружена из config/config.yaml
```

Если ошибка - проверьте:
1. Существует ли .env файл
2. Правильно ли указаны переменные
3. Нет ли лишних пробелов в .env
