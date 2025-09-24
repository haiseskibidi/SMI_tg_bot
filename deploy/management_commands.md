# 🔧 Команды управления корпоративными ботами

## 📊 Мониторинг всех ботов

### Статус всех сервисов
```bash
systemctl list-units "news-monitor-*" --state=active
```

### Подробный статус
```bash
for service in news-monitor-*; do
    echo "=== $service ==="
    systemctl status $service | head -5
    echo ""
done
```

### Использование ресурсов
```bash
# RAM по отделам
ps aux --sort=-%mem | grep "python3.*main.py" | head -10

# CPU нагрузка
htop -p $(pgrep -f "python3.*main.py" | tr '\n' ',')
```

## 🔄 Управление сервисами

### Запуск всех ботов
```bash
systemctl start news-monitor-*
```

### Остановка всех ботов  
```bash
systemctl stop news-monitor-*
```

### Перезапуск всех ботов
```bash
systemctl restart news-monitor-*
```

### Включить автозапуск для всех
```bash
systemctl enable news-monitor-*
```

## 📝 Логи и диагностика

### Логи всех ботов в реальном времени
```bash
journalctl -u "news-monitor-*" -f
```

### Ошибки за последний час
```bash
journalctl -u "news-monitor-*" --since "1 hour ago" | grep -E "(ERROR|CRITICAL|Failed)"
```

### Статистика по отделу
```bash
journalctl -u news-monitor-holodnoe_plamya --since today | grep -E "(📊|сообщений|обработано)"
```

### Проверка подключений к Telegram
```bash
journalctl -u "news-monitor-*" --since "10 minutes ago" | grep -E "(подключен|connected|авторизован)"
```

## 🔧 Обслуживание

### Очистка логов старше 30 дней
```bash
find /opt/news-monitor/*/logs -name "*.log" -mtime +30 -delete
```

### Очистка кеша всех ботов
```bash
find /opt/news-monitor/*/config -name "subscriptions_cache.json" -delete
```

### Бэкап конфигураций
```bash
DATE=$(date +%Y%m%d_%H%M%S)
for dept in /opt/news-monitor/*/; do
    dept_name=$(basename "$dept")
    tar -czf "/backup/${dept_name}_config_${DATE}.tar.gz" -C "$dept" config/ .env
done
```

### Обновление всех ботов
```bash
# Остановка
systemctl stop news-monitor-*

# Бэкап текущих конфигов
./deploy/backup_all_configs.sh

# Обновление кода
cd /opt/news-monitor/SMI_tg_bot
git pull origin main

# Синхронизация изменений
./deploy/sync_code_to_departments.sh

# Запуск
systemctl start news-monitor-*
```

## 📈 Мониторинг производительности

### Дисковое пространство по отделам
```bash
du -sh /opt/news-monitor/*/data /opt/news-monitor/*/logs
```

### Размеры баз данных
```bash
find /opt/news-monitor -name "*.db" -exec ls -lh {} \; | sort -k5 -h
```

### Активность по каналам
```bash
# В каждой базе проверяем статистику
for db in /opt/news-monitor/*/data/*.db; do
    echo "=== $(basename $db) ==="
    sqlite3 "$db" "SELECT COUNT(*) as total_messages FROM messages WHERE date(created_at) = date('now');"
done
```

## 🚨 Экстренные команды

### Экстренная остановка всех ботов
```bash
systemctl stop news-monitor-*
pkill -f "python3.*main.py"
```

### Kill switch для всех ботов
```bash
for dept_dir in /opt/news-monitor/*/; do
    touch "$dept_dir/STOP_BOT"
done
```

### Разблокировка всех ботов
```bash
find /opt/news-monitor -name "STOP_BOT" -delete
```

### Проверка блокировок
```bash
find /opt/news-monitor -name "STOP_BOT" -ls
```

## 📊 Отчеты

### Daily report по всем отделам
```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d)
echo "📈 Отчет за $DATE"
echo "================================="

for dept_dir in /opt/news-monitor/*/; do
    dept_name=$(basename "$dept_dir")
    if [ -f "$dept_dir/data/${dept_name}_monitor.db" ]; then
        db="$dept_dir/data/${dept_name}_monitor.db"
        total=$(sqlite3 "$db" "SELECT COUNT(*) FROM messages WHERE date(created_at) = '$DATE';" 2>/dev/null || echo "0")
        selected=$(sqlite3 "$db" "SELECT COUNT(*) FROM messages WHERE date(created_at) = '$DATE' AND is_selected = 1;" 2>/dev/null || echo "0")
        echo "$dept_name: $total сообщений, $selected отобрано"
    fi
done
```

### Проверка здоровья системы
```bash
#!/bin/bash
echo "🏥 Проверка здоровья системы"
echo "============================"

# Проверка сервисов
failed_services=$(systemctl list-units "news-monitor-*" --state=failed --no-legend | wc -l)
echo "❌ Неработающих сервисов: $failed_services"

# Проверка места на диске
disk_usage=$(df /opt | tail -1 | awk '{print $5}' | sed 's/%//')
echo "💾 Использование диска: ${disk_usage}%"

# Проверка RAM
ram_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
echo "🧠 Использование RAM: ${ram_usage}%"

# Проверка логов на ошибки
recent_errors=$(journalctl -u "news-monitor-*" --since "1 hour ago" | grep -c ERROR || echo "0")
echo "🚨 Ошибок за час: $recent_errors"
```

## 🔄 Автоматизация

### Cron задачи для автоматического обслуживания
```bash
# /etc/crontab
# Ежедневная очистка старых логов в 2:00
0 2 * * * root find /opt/news-monitor/*/logs -name "*.log" -mtime +7 -exec truncate -s 0 {} \;

# Еженедельный перезапуск всех сервисов в воскресенье в 3:00  
0 3 * * 0 root systemctl restart news-monitor-*

# Ежедневный отчет в 23:59
59 23 * * * root /opt/news-monitor/deploy/daily_report.sh | mail -s "News Monitor Daily Report" admin@company.com
```
