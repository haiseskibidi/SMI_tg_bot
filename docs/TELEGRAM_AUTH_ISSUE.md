# ⚠️ Проблема с setup_user_auth.py

## 🚨 Проблема
Скрипт `tools/setup_user_auth.py` работает некорректно в корпоративном развертывании:
- Авторизация не сохраняется должным образом
- При запуске `main.py` после `setup_user_auth.py` требуется повторная авторизация
- Сессии создаются не в том месте или формате

## ✅ Решение
**Используйте `main.py` для авторизации напрямую** - в нем уже есть встроенная авторизация Telegram.

### Правильный способ авторизации для корпоративного развертывания:

```bash
cd /opt/news-monitor/smi-bot

# Для каждого отдела:
CONFIG_PATH=/opt/news-monitor/configs/holodnoe_plamya/config.yaml \
DATA_PATH=/opt/news-monitor/data/holodnoe_plamya \
SESSION_PATH=/opt/news-monitor/sessions/holodnoe_plamya \
DEPARTMENT_KEY=holodnoe_plamya \
python3 main.py

# После успешной авторизации нажмите Ctrl+C
# Сессия будет сохранена в правильном месте для systemd сервиса
```

## 📝 Обновленная документация
- ✅ `docs/CORPORATE_DEPLOYMENT_V2.md` - обновлена с правильной авторизацией
- ✅ `deploy/setup_corporate.sh` - инструкции исправлены

## 🔧 Техническая причина
`main.py` и `setup_user_auth.py` используют разные пути или настройки для сессий Telethon, что приводит к несовместимости сохраненных авторизаций.
