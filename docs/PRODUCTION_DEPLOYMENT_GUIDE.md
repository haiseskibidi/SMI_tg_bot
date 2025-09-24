# 🏢 Полное руководство по production деплою для медиахолдинга

**Пошаговая инструкция развертывания системы мониторинга новостей на новом сервере для 7 отделов**

---

## 📋 **Предварительные требования**

### 🖥️ **Сервер**
- **ОС**: Ubuntu 20.04+ / Debian 11+
- **RAM**: 8GB+ (рекомендуется 16GB)  
- **CPU**: 4+ ядра
- **Диск**: 100GB+ SSD
- **Сеть**: Стабильное подключение к интернету

### 🔑 **Telegram ресурсы (получите заранее)**
- **7 Telegram аккаунтов** с номерами телефонов
- **Доступ к my.telegram.org** для каждого аккаунта
- **7 групп** для публикации новостей (по одной на отдел)
- **Списки каналов** для каждого отдела (9-11 каналов)

---

## 🚀 **ЭТАП 1: Подготовка сервера**

### 1.1. Обновление системы
```bash
# Подключаемся к серверу
ssh root@your-server-ip

# Обновляем систему
apt update && apt upgrade -y

# Устанавливаем необходимые пакеты
apt install -y python3 python3-pip python3-venv git curl wget htop nano systemd
```

### 1.2. Создание пользователя для приложения
```bash
# Создаем пользователя
useradd -m -s /bin/bash newsmonitor
usermod -aG sudo newsmonitor

# Настраиваем sudo без пароля (опционально)
echo "newsmonitor ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
```

### 1.3. Настройка firewall (если нужно)
```bash
# Установка ufw
apt install -y ufw

# Разрешаем SSH
ufw allow 22

# Разрешаем HTTP/HTTPS (если планируется веб-панель в будущем)
ufw allow 80
ufw allow 443

# Включаем firewall
ufw --force enable
```

### 1.4. Настройка часового пояса
```bash
# Устанавливаем московский часовой пояс
timedatectl set-timezone Europe/Moscow
timedatectl status
```

---

## 📦 **ЭТАП 2: Развертывание кода**

### 2.1. Клонирование репозитория
```bash
# Переходим в /opt
cd /opt

# Клонируем репозиторий (замените на ваш)
git clone https://github.com/your-username/your-repo news-monitor/smi-bot

# Переходим в папку проекта
cd news-monitor/smi-bot

# Переключаемся на ветку deploy
git checkout deploy

# Проверяем что файлы на месте
ls -la deploy/setup_corporate.sh
```

### 2.2. Запуск скрипта развертывания
```bash
# Делаем скрипт исполняемым
chmod +x deploy/setup_corporate.sh

# Запускаем автоматическое развертывание
./deploy/setup_corporate.sh
```

### 2.3. Создание виртуального окружения
```bash
# Переходим в папку проекта
cd /opt/news-monitor/smi-bot

# Создаем виртуальное окружение
python3 -m venv venv

# Активируем
source venv/bin/activate

# Обновляем pip
pip install --upgrade pip

# Устанавливаем зависимости
pip install -r requirements.txt

# Проверяем установку
pip list | grep -E "(telethon|aiosqlite|httpx)"
```

---

## 🔑 **ЭТАП 3: Получение Telegram ключей**

### 3.1. Получение API ключей (для каждого аккаунта)

**Повторить для всех 7 аккаунтов:**

1. **Идем на https://my.telegram.org**
2. **Авторизуемся** под аккаунтом отдела
3. **API development tools** → **Create application**
4. **Заполняем форму:**
   - App title: `News Monitor - Отдел X`  
   - Short name: `newsmonitor_dept_x`
   - URL: (оставляем пустым)
   - Platform: **Other**
   - Description: `Система мониторинга новостей для отдела`
5. **Сохраняем данные:**

```
=== ОТДЕЛ 1: Холодное пламя ===
Телефон: +7XXXXXXXXXX
api_id: 12345678
api_hash: abcdef1234567890abcdef1234567890

=== ОТДЕЛ 2: ===
Телефон: +7XXXXXXXXXX  
api_id: 87654321
api_hash: 0987654321fedcba1234567890

... (и так для всех 7)
```

### 3.2. Создание ботов у @BotFather

**Для каждого отдела:**

1. **Пишем @BotFather**: `/newbot`
2. **Вводим название**: `News Monitor - Холодное пламя`
3. **Вводим username**: `news_holodnoe_plamya_bot`
4. **Копируем токен**: `1234567890:AAGhT-ZZZ_abc123def456ghi789jkl`
5. **Настраиваем бота**:
   - `/setdescription` - описание бота
   - `/setcommands` - команды бота
   - `/setprivacy` - отключаем privacy mode

**Список команд для @BotFather:**
```
start - Главное меню системы
status - Статус всех компонентов
digest - Генерация дайджеста новостей
help - Справка по командам
manage_channels - Управление каналами
restart - Перезапуск системы
```

### 3.3. Получение ID пользователей и групп

**Для каждого отдела:**

1. **ID админа отдела**: 
   - Админ пишет @userinfobot
   - Копирует "Your ID"

2. **ID группы отдела**:
   - Создаем группу отдела (если еще нет)
   - Добавляем @userinfobot в группу
   - Копируем "Chat ID" (отрицательное число)

3. **Настройка топиков в группе** (если нужно):
   - Включаем темы в группе
   - Создаем темы: "Срочные новости", "Общие новости", "Аналитика"
   - Команда `/topic_id` в каждой теме для получения ID

---

## ⚙️ **ЭТАП 4: Настройка конфигураций**

### 4.1. Заполнение .env файлов

**Для КАЖДОГО отдела** (пример для "Холодное пламя"):

```bash
nano /opt/news-monitor/configs/holodnoe_plamya/.env
```

```env
# Telegram API (с my.telegram.org)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890

# Bot Token (от @BotFather)
BOT_TOKEN=1234567890:AAGhT-ZZZ_abc123def456ghi789jkl

# ID администратора отдела (от @userinfobot)
BOT_CHAT_ID=123456789

# ID группы для публикации новостей (от @userinfobot)
TARGET_GROUP_ID=-1001234567890

# Настройки отдела
DEPARTMENT_NAME=Холодное пламя
DEPARTMENT_EMOJI=🔥
DEPARTMENT_KEY=holodnoe_plamya
```

**Повторить для всех 7 отделов!**

### 4.2. Настройка каналов отделов

**Для каждого отдела** заменить примеры на реальные каналы:

```bash
nano /opt/news-monitor/configs/holodnoe_plamya/channels_config.yaml
```

```yaml
departments:
  main_department:
    name: "🔥 Холодное пламя"
    channels:
      # Замените на РЕАЛЬНЫЕ каналы отдела!
      - username: "real_department_channel_1"
        title: "Главные новости отдела"
      - username: "real_department_channel_2"  
        title: "Региональные новости"
      - username: "real_department_channel_3"
        title: "Срочные новости"
      - username: "real_department_channel_4"
        title: "Политика"
      - username: "real_department_channel_5"
        title: "Экономика"
      - username: "real_department_channel_6"
        title: "Общество"
      - username: "real_department_channel_7"
        title: "Криминал"
      - username: "real_department_channel_8"
        title: "ЧП и происшествия"
      - username: "real_department_channel_9"
        title: "Спорт"
      # Добавьте еще 1-2 канала по необходимости
```

### 4.3. Настройка прав доступа
```bash
# Устанавливаем права
chown -R root:root /opt/news-monitor/
chmod 600 /opt/news-monitor/configs/*/.env
chmod +x /opt/news-monitor/smi-bot/venv/bin/python
```

---

## 🔐 **ЭТАП 5: Авторизация Telegram**

### 5.1. Авторизация каждого отдела

**Для КАЖДОГО отдела** (используйте номера телефонов аккаунтов):

```bash
cd /opt/news-monitor/smi-bot

# Отдел 1: Холодное пламя
CONFIG_PATH=/opt/news-monitor/configs/holodnoe_plamya/config.yaml \
DATA_PATH=/opt/news-monitor/data/holodnoe_plamya \
SESSION_PATH=/opt/news-monitor/sessions/holodnoe_plamya \
DEPARTMENT_KEY=holodnoe_plamya \
/opt/news-monitor/smi-bot/venv/bin/python main.py
```

**При запуске каждого:**
1. Введите номер телефона аккаунта: `+7XXXXXXXXXX`
2. Введите код из SMS
3. После сообщения "✅ Telegram мониторинг готов" нажмите **Ctrl+C**
4. Переходите к следующему отделу

**Повторите для всех 7 отделов!**

---

## 🚀 **ЭТАП 6: Запуск системы**

### 6.1. Запуск всех сервисов
```bash
# Перезагружаем systemd
systemctl daemon-reload

# Включаем автозапуск всех сервисов
systemctl enable news-monitor-*

# Запускаем все боты
systemctl start news-monitor-*

# Проверяем статус
systemctl status news-monitor-*
```

### 6.2. Проверка работы
```bash
# Статус всех сервисов
systemctl list-units "news-monitor-*" --state=active

# Логи конкретного отдела
journalctl -u news-monitor-holodnoe_plamya -f

# Проверка процессов
ps aux | grep python | grep main.py
```

---

## 💾 **ЭТАП 7: Настройка бэкапов**

### 7.1. Создание скрипта бэкапа
```bash
mkdir -p /opt/backups
nano /opt/backups/backup_news_monitor.sh
```

```bash
#!/bin/bash

# Скрипт бэкапа системы мониторинга новостей
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"
SOURCE_DIR="/opt/news-monitor"

echo "🔄 Начинаем бэкап системы мониторинга..."

# Создаем папку для бэкапа
mkdir -p "$BACKUP_DIR/daily"
mkdir -p "$BACKUP_DIR/weekly"

# Останавливаем сервисы для консистентности данных
echo "⏸️ Останавливаем сервисы..."
systemctl stop news-monitor-*

# Создаем архив
echo "📦 Создаем архив..."
tar -czf "$BACKUP_DIR/daily/news_monitor_backup_$DATE.tar.gz" \
    -C /opt news-monitor/configs \
    -C /opt news-monitor/data \
    -C /opt news-monitor/sessions \
    -C /opt news-monitor/logs

# Бэкап базы данных отдельно
echo "💾 Бэкап баз данных..."
mkdir -p "$BACKUP_DIR/daily/databases_$DATE"
for db in /opt/news-monitor/data/*/*.db; do
    if [ -f "$db" ]; then
        dept_name=$(basename $(dirname "$db"))
        cp "$db" "$BACKUP_DIR/daily/databases_$DATE/${dept_name}_monitor.db"
    fi
done

# Запускаем сервисы обратно
echo "▶️ Запускаем сервисы..."
systemctl start news-monitor-*

# Удаляем старые бэкапы (старше 7 дней)
find "$BACKUP_DIR/daily" -name "*.tar.gz" -mtime +7 -delete
find "$BACKUP_DIR/daily" -name "databases_*" -mtime +7 -exec rm -rf {} \;

# Еженедельный бэкап (по воскресеньям)
if [ $(date +%u) -eq 7 ]; then
    cp "$BACKUP_DIR/daily/news_monitor_backup_$DATE.tar.gz" "$BACKUP_DIR/weekly/"
    cp -r "$BACKUP_DIR/daily/databases_$DATE" "$BACKUP_DIR/weekly/"
    
    # Удаляем старые еженедельные бэкапы (старше 30 дней)
    find "$BACKUP_DIR/weekly" -name "*.tar.gz" -mtime +30 -delete
    find "$BACKUP_DIR/weekly" -name "databases_*" -mtime +30 -exec rm -rf {} \;
fi

echo "✅ Бэкап завершен: $BACKUP_DIR/daily/news_monitor_backup_$DATE.tar.gz"
```

```bash
# Делаем скрипт исполняемым
chmod +x /opt/backups/backup_news_monitor.sh
```

### 7.2. Настройка автоматических бэкапов через cron
```bash
# Открываем crontab
crontab -e

# Добавляем задачи
# Ежедневный бэкап в 3:00
0 3 * * * /opt/backups/backup_news_monitor.sh

# Проверка состояния системы каждый час
0 * * * * systemctl is-active --quiet news-monitor-* || /opt/backups/check_services.sh
```

### 7.3. Скрипт проверки сервисов
```bash
nano /opt/backups/check_services.sh
```

```bash
#!/bin/bash

# Проверка состояния сервисов
echo "🔍 Проверка сервисов мониторинга..."

failed_services=()

for service in news-monitor-*; do
    if ! systemctl is-active --quiet "$service"; then
        failed_services+=("$service")
        echo "❌ Сервис $service не активен"
        
        # Пытаемся перезапустить
        systemctl restart "$service"
        sleep 5
        
        if systemctl is-active --quiet "$service"; then
            echo "✅ Сервис $service перезапущен успешно"
        else
            echo "🚨 Сервис $service НЕ УДАЛОСЬ перезапустить!"
        fi
    fi
done

if [ ${#failed_services[@]} -eq 0 ]; then
    echo "✅ Все сервисы работают нормально"
else
    echo "⚠️ Обнаружены проблемы с сервисами: ${failed_services[*]}"
fi
```

```bash
chmod +x /opt/backups/check_services.sh
```

---

## 📊 **ЭТАП 8: Мониторинг и обслуживание**

### 8.1. Создание скрипта мониторинга
```bash
nano /opt/backups/system_health.sh
```

```bash
#!/bin/bash

# Скрипт проверки здоровья системы
echo "🏥 === ПРОВЕРКА ЗДОРОВЬЯ СИСТЕМЫ === $(date)"
echo ""

# Проверка сервисов
echo "📊 СТАТУС СЕРВИСОВ:"
failed_count=0
for service in news-monitor-*; do
    if systemctl is-active --quiet "$service" 2>/dev/null; then
        echo "✅ $service"
    else
        echo "❌ $service"
        ((failed_count++))
    fi
done
echo "Неработающих сервисов: $failed_count"
echo ""

# Проверка ресурсов
echo "💻 СИСТЕМНЫЕ РЕСУРСЫ:"
echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "RAM: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"
echo "Диск: $(df /opt | tail -1 | awk '{print $5}')"
echo ""

# Проверка логов на ошибки
echo "🔍 ПОСЛЕДНИЕ ОШИБКИ:"
error_count=$(journalctl -u "news-monitor-*" --since "1 hour ago" | grep -c "ERROR" || echo "0")
echo "Ошибок за последний час: $error_count"

if [ $error_count -gt 10 ]; then
    echo "⚠️ ВНИМАНИЕ: Много ошибок в логах!"
    journalctl -u "news-monitor-*" --since "1 hour ago" | grep "ERROR" | tail -5
fi
echo ""

# Проверка места на диске
echo "💾 ИСПОЛЬЗОВАНИЕ ДИСКА:"
for path in /opt/news-monitor/data /opt/news-monitor/logs /opt/backups; do
    if [ -d "$path" ]; then
        size=$(du -sh "$path" | cut -f1)
        echo "$path: $size"
    fi
done
echo ""

# Проверка размеров баз данных
echo "🗃️ РАЗМЕРЫ БАЗ ДАННЫХ:"
for db in /opt/news-monitor/data/*/*.db; do
    if [ -f "$db" ]; then
        dept=$(basename $(dirname "$db"))
        size=$(du -sh "$db" | cut -f1)
        echo "$dept: $size"
    fi
done
```

```bash
chmod +x /opt/backups/system_health.sh
```

### 8.2. Настройка логирования
```bash
# Создаем конфиг для logrotate
nano /etc/logrotate.d/news-monitor
```

```
/opt/news-monitor/logs/*/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    maxsize 100M
}
```

### 8.3. Скрипт обновления системы
```bash
nano /opt/backups/update_system.sh
```

```bash
#!/bin/bash

# Скрипт обновления системы мониторинга
echo "🔄 Обновление системы мониторинга новостей..."

# Переходим в директорию
cd /opt/news-monitor/smi-bot

# Создаем бэкап перед обновлением
echo "💾 Создаем бэкап перед обновлением..."
/opt/backups/backup_news_monitor.sh

# Останавливаем сервисы
echo "⏸️ Останавливаем сервисы..."
systemctl stop news-monitor-*

# Обновляем код
echo "⬇️ Скачиваем обновления..."
git fetch origin
git pull origin deploy

# Обновляем зависимости (если нужно)
echo "📦 Проверяем зависимости..."
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Запускаем сервисы
echo "▶️ Запускаем сервисы..."
systemctl start news-monitor-*

# Проверяем статус
sleep 10
echo "📊 Проверяем статус..."
systemctl status news-monitor-* --no-pager

echo "✅ Обновление завершено!"
```

```bash
chmod +x /opt/backups/update_system.sh
```

---

## 🔒 **ЭТАП 9: Безопасность**

### 9.1. Настройка fail2ban (защита от брутфорса)
```bash
# Устанавливаем fail2ban
apt install -y fail2ban

# Создаем конфиг
nano /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
```

```bash
# Запускаем fail2ban
systemctl enable fail2ban
systemctl start fail2ban
```

### 9.2. Настройка SSH безопасности
```bash
# Бэкапим оригинальный конфиг
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak

# Редактируем конфиг
nano /etc/ssh/sshd_config
```

Добавляем/изменяем:
```
# Отключаем вход по паролю для root
PermitRootLogin prohibit-password

# Отключаем аутентификацию по паролю (если настроены SSH ключи)
# PasswordAuthentication no

# Ограничиваем количество попыток
MaxAuthTries 3

# Ограничиваем время сессии
ClientAliveInterval 300
ClientAliveCountMax 2
```

```bash
# Перезапускаем SSH
systemctl restart sshd
```

### 9.3. Настройка прав доступа
```bash
# Устанавливаем строгие права на конфигурационные файлы
chmod 600 /opt/news-monitor/configs/*/.env
chmod 700 /opt/news-monitor/sessions/
chmod 755 /opt/news-monitor/smi-bot/

# Настраиваем владельца
chown -R root:root /opt/news-monitor/
```

---

## 📈 **ЭТАП 10: Финальная проверка**

### 10.1. Чек-лист завершения

**✅ Проверьте все пункты:**

- [ ] **Сервер настроен** (обновлен, firewall, пользователи)
- [ ] **Код развернут** в `/opt/news-monitor/smi-bot/`
- [ ] **Виртуальное окружение** создано и активно
- [ ] **7 Telegram API ключей** получены и записаны
- [ ] **7 ботов** созданы у @BotFather
- [ ] **7 .env файлов** заполнены реальными данными
- [ ] **7 channels_config.yaml** содержат реальные каналы
- [ ] **7 Telegram авторизаций** пройдены успешно
- [ ] **7 systemd сервисов** запущены и активны
- [ ] **Логи** показывают успешную инициализацию
- [ ] **Боты отвечают** на команды в группах
- [ ] **Тестовые сообщения** доставляются
- [ ] **Бэкапы настроены** (ежедневные + еженедельные)
- [ ] **Мониторинг настроен** (проверка сервисов)
- [ ] **Безопасность настроена** (firewall, fail2ban, SSH)
- [ ] **Документация** сохранена и доступна

### 10.2. Команды для финальной проверки

```bash
# Статус всех сервисов
systemctl list-units "news-monitor-*" --state=active

# Проверка ресурсов
/opt/backups/system_health.sh

# Проверка бэкапов
ls -la /opt/backups/daily/

# Тест одного из ботов
echo "Отправьте /start одному из ботов в группе"
```

---

## 🆘 **ЭТАП 11: Поддержка и устранение проблем**

### 11.1. Полезные команды

```bash
# Перезапуск всех сервисов
systemctl restart news-monitor-*

# Перезапуск конкретного отдела
systemctl restart news-monitor-holodnoe_plamya

# Логи конкретного отдела
journalctl -u news-monitor-holodnoe_plamya -f

# Логи всех сервисов за последний час
journalctl -u "news-monitor-*" --since "1 hour ago"

# Проверка места на диске
df -h /opt

# Проверка памяти
free -h

# Процессы ботов
ps aux | grep python | grep main.py
```

### 11.2. Типичные проблемы

**🔴 Проблема**: Сервис не запускается
**🔧 Решение**:
```bash
journalctl -u news-monitor-отдел --since "5 minutes ago"
# Проверьте .env файл и авторизацию
```

**🔴 Проблема**: "Rate limit exceeded"
**🔧 Решение**:
```bash
# Увеличьте таймауты в config.yaml
nano /opt/news-monitor/configs/отдел/config.yaml
# monitoring.timeouts.delay_between_batches: 15
```

**🔴 Проблема**: Нет места на диске
**🔧 Решение**:
```bash
# Очистка старых логов
find /opt/news-monitor/logs -name "*.log" -mtime +7 -delete
# Очистка старых бэкапов
find /opt/backups -name "*.tar.gz" -mtime +14 -delete
```

---

## 📞 **Контакты и документация**

### 📚 **Документация**
- **Основная**: `/opt/news-monitor/smi-bot/docs/CORPORATE_DEPLOYMENT_V2.md`
- **Архитектура**: `/opt/news-monitor/smi-bot/docs/architecture/`
- **Утилиты**: `/opt/news-monitor/smi-bot/tools/README.md`

### 🛠️ **Полезные ссылки**
- **my.telegram.org** - получение API ключей
- **@BotFather** - создание ботов
- **@userinfobot** - получение ID пользователей и групп

### 📊 **Мониторинг**
```bash
# Ежедневная проверка здоровья
/opt/backups/system_health.sh

# Еженедельное обновление (по необходимости)
/opt/backups/update_system.sh
```

---

🎉 **СИСТЕМА ГОТОВА К РАБОТЕ В PRODUCTION!**

**Время развертывания**: 4-6 часов (включая получение всех токенов и настройку 7 отделов)
**Поддерживаемая нагрузка**: 70+ каналов, 7 независимых ботов
**Автоматические бэкапы**: Ежедневные + еженедельные
**Мониторинг**: 24/7 проверка сервисов
