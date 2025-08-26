# 🤖 Создание Telegram бота для уведомлений

## Шаг 1: Создайте бота через @BotFather

1. Откройте Telegram
2. Найдите **@BotFather** 
3. Отправьте команду: `/newbot`
4. Введите название бота: **Сахалин Камчатка Новости**
5. Введите username: **sakhalin_kamchatka_news_bot** (или любой доступный)
6. Скопируйте **токен бота** (например: `123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw`)

## Шаг 2: Получите свой chat_id

1. Напишите вашему боту любое сообщение
2. Откройте ссылку: `https://api.telegram.org/bot<ВАШ_ТОКЕН>/getUpdates`
3. Найдите "chat":{"id": **YOUR_CHAT_ID**}
4. Скопируйте этот ID

## Шаг 3: Добавьте в конфигурацию

Добавьте в `config.yaml`:
```yaml
bot:
  token: "ВАШ_ТОКЕН_БОТА"
  chat_id: ВАШ_CHAT_ID
```

## Пример:
```yaml
bot:
  token: "123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
  chat_id: 123456789
```
