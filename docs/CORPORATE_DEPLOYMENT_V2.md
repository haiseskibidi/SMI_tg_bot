# 🏢 Корпоративное развертывание v2.0 (Общий код)

**Оптимизированная архитектура для медиахолдинга: 1 исходный код + 7 процессов**

> 📚 **Для полного production развертывания с нуля смотрите:** [`PRODUCTION_DEPLOYMENT_GUIDE.md`](PRODUCTION_DEPLOYMENT_GUIDE.md)

---

### 📊 **Структура на сервере:**
```
/opt/news-monitor/
├── smi-bot/                  # ← Общий исходный код
│   ├── main.py
│   ├── src/
│   └── requirements.txt
├── configs/                  # ← Конфиги отделов
│   ├── holodnoe_plamya/
│   │   ├── config.yaml
│   │   ├── channels_config.yaml
│   │   └── .env
│   ├── department_2/
│   └── department_7/
├── data/                     # ← Базы данных
│   ├── holodnoe_plamya/
│   └── department_2/
├── logs/                     # ← Логи отделов
└── sessions/                 # ← Telegram сессии
```

### 🔄 **Как работают процессы:**
```bash
# 7 systemd сервисов запускают ОДНИ И ТОТ ЖЕ main.py:
systemctl start news-monitor-holodnoe_plamya  # процесс 1
systemctl start news-monitor-department_2     # процесс 2  
systemctl start news-monitor-department_7     # процесс 7

# Каждый процесс получает свои переменные окружения:
CONFIG_PATH=/opt/news-monitor/configs/holodnoe_plamya/config.yaml
DATA_PATH=/opt/news-monitor/data/holodnoe_plamya
DEPARTMENT_KEY=holodnoe_plamya
```

## 🚀 Быстрое развертывание

### 1. Загрузка проекта на сервер
```bash
cd /opt
git clone <your-repo> news-monitor/smi-bot
cd news-monitor/smi-bot
```

### 2. Создание виртуального окружения и установка зависимостей
```bash
# Создаем виртуальное окружение
python3 -m venv venv

# Активируем виртуальное окружение
source venv/bin/activate

# Обновляем pip
pip install --upgrade pip

# Устанавливаем зависимости
pip install -r requirements.txt

# Проверяем установку
pip list | head -10
```

**💡 Важно:** Виртуальное окружение изолирует зависимости проекта от системных Python пакетов.

### 3. Запуск автоматического развертывания
```bash
chmod +x deploy/setup_corporate.sh
./deploy/setup_corporate.sh
```

### 4. Настройка каждого отдела

#### 4.1. Заполните .env файлы
```bash
# Для каждого отдела:
nano /opt/news-monitor/configs/holodnoe_plamya/.env
nano /opt/news-monitor/configs/department_2/.env
# ... и так далее
```

**Пример .env файла:**
```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890  
BOT_TOKEN=1234567890:AAGhT-ZZZ_abc123def456ghi789jkl
BOT_CHAT_ID=123456789
TARGET_GROUP_ID=-1001234567890
DEPARTMENT_NAME=Холодное пламя
DEPARTMENT_EMOJI=🔥
DEPARTMENT_KEY=holodnoe_plamya
```

#### 4.2. Настройте каналы отделов
```bash
nano /opt/news-monitor/configs/holodnoe_plamya/channels_config.yaml
```

**Замените примеры на реальные каналы:**
```yaml
departments:
  main_department:
    name: "🔥 Холодное пламя"
    channels:
      - username: "real_channel_1"    # ← Замените на реальные
        title: "Реальный канал 1"
      - username: "real_channel_2"
        title: "Реальный канал 2"
      # ... добавьте 9-11 каналов отдела
```

#### 4.3. Авторизация Telegram для каждого отдела
```bash
# Для каждого отдела запустите main.py в режиме авторизации:
cd /opt/news-monitor/smi-bot

# Отдел 1:
CONFIG_PATH=/opt/news-monitor/configs/holodnoe_plamya/config.yaml \
DATA_PATH=/opt/news-monitor/data/holodnoe_plamya \
SESSION_PATH=/opt/news-monitor/sessions/holodnoe_plamya \
DEPARTMENT_KEY=holodnoe_plamya \
/opt/news-monitor/smi-bot/venv/bin/python main.py

# После авторизации нажмите Ctrl+C и запустите следующий отдел:
CONFIG_PATH=/opt/news-monitor/configs/department_2/config.yaml \
DATA_PATH=/opt/news-monitor/data/department_2 \
SESSION_PATH=/opt/news-monitor/sessions/department_2 \
DEPARTMENT_KEY=department_2 \
/opt/news-monitor/smi-bot/venv/bin/python main.py

# ... и так далее для всех 7 отделов
```

### 5. Запуск всех ботов
```bash
systemctl enable news-monitor-*
systemctl start news-monitor-*
```

### 6. Проверка работы
```bash
systemctl status news-monitor-*
journalctl -u news-monitor-holodnoe_plamya -f
```

## ⚡ Преимущества архитектуры v2.0

### 🔄 **Быстрые обновления**
```bash
# Обновить ВСЕ отделы одной командой:
cd /opt/news-monitor/smi-bot  
git pull origin main
systemctl restart news-monitor-*
# Готово! Все 7 ботов обновлены!
```

### 💾 **Экономия ресурсов**
- **Место на диске:** 50MB vs 350MB (7×50MB)
- **Память:** Общие библиотеки Python
- **Обслуживание:** Один git репозиторий

### 🔒 **Сохраненная безопасность**
- 7 независимых Telegram аккаунтов
- 7 раздельных баз данных
- 7 раздельных конфигураций
- Падение одного процесса не влияет на другие

## 🔧 Управление системой

### Мониторинг всех отделов
```bash
# Статус всех ботов
systemctl list-units "news-monitor-*" --state=active

# Логи всех ботов в реальном времени  
journalctl -u "news-monitor-*" -f

# Использование ресурсов
ps aux --sort=-%mem | grep "python3.*main.py"
```

### Управление отделами
```bash
# Перезапуск всех ботов
systemctl restart news-monitor-*

# Перезапуск конкретного отдела
systemctl restart news-monitor-holodnoe_plamya  

# Остановка всех ботов
systemctl stop news-monitor-*
```

### Обслуживание
```bash
# Очистка старых логов
find /opt/news-monitor/logs -name "*.log" -mtime +30 -delete

# Бэкап конфигураций
tar -czf backup_configs_$(date +%Y%m%d).tar.gz /opt/news-monitor/configs/

# Проверка размеров баз данных
du -sh /opt/news-monitor/data/*/
```

## 🚨 Устранение неполадок

### Проблемы с конкретным отделом
```bash
# Проверка конфигурации отдела
cat /opt/news-monitor/configs/holodnoe_plamya/.env
journalctl -u news-monitor-holodnoe_plamya --since "1 hour ago"
```

### Проблемы с общим кодом
```bash
# Проверка исходного кода
ls -la /opt/news-monitor/smi-bot/
cd /opt/news-monitor/smi-bot && python3 -c "import src; print('OK')"
```

### Rate limiting
```bash
# Если слишком много каналов у одного отдела - увеличить таймауты
nano /opt/news-monitor/configs/отдел/config.yaml
# monitoring.timeouts.delay_between_batches: 15
```

## 📈 Масштабирование

### Добавление нового отдела
1. **Добавьте отдел в скрипт** `deploy/setup_corporate.sh`
2. **Перезапустите развертывание** `./deploy/setup_corporate.sh`
3. **Настройте .env и каналы** нового отдела
4. **Запустите новый сервис** `systemctl start news-monitor-новый_отдел`

### Оптимизация производительности
```yaml
# config/config_template_corporate.yaml
system:
  max_concurrent_channels: 100    # Больше каналов на мощном сервере
  memory_limit_mb: 2048          # 2GB на отдел
  cache_size_mb: 500             # Больше кеша
```

## 🎯 Сравнение с версией 1.0

| Параметр | v1.0 (Копии кода) | v2.0 (Общий код) |
|----------|------------------|------------------|
| **Место на диске** | 350MB (7×50MB) | 50MB |
| **Обновление кода** | 7 команд git pull | 1 команда git pull |
| **Обслуживание** | 7 репозиториев | 1 репозиторий |
| **Изоляция процессов** | ✅ Полная | ✅ Полная |
| **Независимость данных** | ✅ | ✅ |
| **Скорость развертывания** | Медленно | ⚡ Быстро |

## 💾 **Бэкапы и восстановление**

### Автоматические бэкапы
```bash
# Создание скрипта бэкапа
nano /opt/backups/backup_news_monitor.sh

# Настройка ежедневных бэкапов в crontab
crontab -e
# Добавить: 0 3 * * * /opt/backups/backup_news_monitor.sh
```

**Что бэкапится:**
- 📂 Конфигурации всех отделов (`/opt/news-monitor/configs/`)
- 🗃️ Базы данных (`/opt/news-monitor/data/`)  
- 🔑 Telegram сессии (`/opt/news-monitor/sessions/`)
- 📊 Логи (`/opt/news-monitor/logs/`)

### Восстановление из бэкапа
```bash
# Остановка всех сервисов
systemctl stop news-monitor-*

# Восстановление конфигураций
tar -xzf backup_configs_YYYYMMDD.tar.gz -C /

# Восстановление баз данных
cp backup_databases_YYYYMMDD/*.db /opt/news-monitor/data/*/

# Запуск сервисов
systemctl start news-monitor-*
```

---

## 📊 **Мониторинг и обслуживание**

### Проверка здоровья системы
```bash
# Скрипт полной диагностики
/opt/backups/system_health.sh

# Мониторинг ресурсов
htop
df -h /opt
free -h
```

### Ротация логов
```bash
# Автоматическая ротация логов (настраивается один раз)
nano /etc/logrotate.d/news-monitor

# Ручная очистка старых логов
find /opt/news-monitor/logs -name "*.log" -mtime +30 -delete
```

### Обновление системы
```bash
# Создание бэкапа перед обновлением
/opt/backups/backup_news_monitor.sh

# Скачивание и применение обновлений
cd /opt/news-monitor/smi-bot
git pull origin deploy
systemctl restart news-monitor-*
```

---

## 🔒 **Безопасность production**

### Базовая безопасность сервера
```bash
# Firewall
ufw enable
ufw allow 22    # SSH
ufw allow 80    # HTTP (если нужен)
ufw allow 443   # HTTPS (если нужен)

# Fail2ban против брутфорса
apt install fail2ban
systemctl enable fail2ban
```

### Защита конфигураций
```bash
# Ограничение доступа к .env файлам
chmod 600 /opt/news-monitor/configs/*/.env
chmod 700 /opt/news-monitor/sessions/

# Владелец файлов - root
chown -R root:root /opt/news-monitor/
```

### SSH безопасность
```bash
# Отключение входа root по паролю
nano /etc/ssh/sshd_config
# PermitRootLogin prohibit-password
# MaxAuthTries 3

systemctl restart sshd
```

---

## 📈 **Производительность и оптимизация**

### Мониторинг нагрузки
```bash
# Процессы ботов
ps aux --sort=-%mem | grep "python.*main.py"

# Использование памяти по отделам
for service in news-monitor-*; do
    echo "=== $service ==="
    systemctl show $service --property=MemoryCurrent
done

# Размеры баз данных
du -sh /opt/news-monitor/data/*/
```

### Настройка лимитов ресурсов
```bash
# В systemd сервисах можно ограничить память:
nano /etc/systemd/system/news-monitor-отдел.service

# Добавить в [Service]:
# MemoryLimit=1G
# CPUQuota=50%
```

### Оптимизация для мощного сервера
```yaml
# В config_template_corporate.yaml
system:
  max_concurrent_channels: 100    # Больше каналов одновременно
  memory_limit_mb: 2048          # 2GB на отдел
  cache_size_mb: 500             # Больше кеша для быстродействия
  
monitoring:
  timeouts:
    delay_between_batches: 10    # Меньше задержки на быстром сервере
```

---

## 🚨 **Аварийное восстановление**

### Быстрая диагностика проблем
```bash
# Проверка всех сервисов
systemctl list-units "news-monitor-*" --failed

# Последние ошибки во всех логах
journalctl -u "news-monitor-*" --since "1 hour ago" | grep ERROR

# Проверка дискового пространства
df -h | grep -E "(root|opt)"

# Проверка памяти
free -h | grep Mem
```

### Перезапуск проблемного отдела
```bash
# Полная перезагрузка конкретного отдела
systemctl stop news-monitor-holodnoe_plamya
sleep 5
systemctl start news-monitor-holodnoe_plamya

# Проверка запуска
journalctl -u news-monitor-holodnoe_plamya --since "1 minute ago"
```

### Экстренный откат системы
```bash
# Остановка всех ботов
systemctl stop news-monitor-*

# Откат кода на предыдущую версию
cd /opt/news-monitor/smi-bot
git log --oneline -5               # Смотрим последние коммиты
git checkout <предыдущий-коммит>   # Откатываемся

# Восстановление из бэкапа (если нужно)
tar -xzf /opt/backups/daily/news_monitor_backup_latest.tar.gz -C /

# Запуск системы
systemctl start news-monitor-*
```

---

## 📞 **Поддержка и контакты**

### Полезные команды для отладки
```bash
# Полная информация о системе
/opt/backups/system_health.sh

# Логи конкретного отдела в реальном времени
journalctl -u news-monitor-holodnoe_plamya -f

# Статистика использования ресурсов
systemctl show news-monitor-* --property=MemoryCurrent,CPUUsageNSec

# Проверка активности всех ботов
systemctl is-active news-monitor-*
```

### Структура логов
```
/opt/news-monitor/logs/
├── holodnoe_plamya/
│   ├── holodnoe_plamya_monitor.log      # Основные логи
│   ├── holodnoe_plamya_monitor.log.1.gz # Ротированные логи
│   └── holodnoe_plamya_monitor.log.2.gz
├── department_2/
│   └── department_2_monitor.log
└── ...
```

### Файлы конфигурации
```
/opt/news-monitor/configs/
├── holodnoe_plamya/
│   ├── .env                    # Секретные данные
│   ├── config.yaml            # Основная конфигурация  
│   └── channels_config.yaml   # Списки каналов
├── department_2/
│   └── ...
└── ...
```

---

## 📋 Чек-лист запуска v2.0

**Основное развертывание:**
- [ ] Исходный код скопирован в `/opt/news-monitor/smi-bot/`
- [ ] Виртуальное окружение создано и активно
- [ ] Скрипт развертывания выполнен успешно
- [ ] Все 7 .env файлов заполнены реальными данными
- [ ] Все channels_config.yaml содержат реальные каналы  
- [ ] Авторизация Telegram пройдена для всех 7 аккаунтов
- [ ] Все systemd сервисы запущены и активны
- [ ] Логи показывают успешную инициализацию всех отделов

**Production готовность:**
- [ ] Автоматические бэкапы настроены и работают
- [ ] Мониторинг здоровья системы настроен
- [ ] Firewall и fail2ban настроены
- [ ] Ротация логов настроена
- [ ] SSH безопасность настроена
- [ ] Права доступа к файлам настроены
- [ ] Тестовые сообщения доставляются в группы отделов
- [ ] Команда обновления `git pull + systemctl restart` работает

🎉 **Корпоративная система v2.0 готова к production работе!**
