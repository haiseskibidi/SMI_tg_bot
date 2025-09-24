#!/bin/bash

# 🏢 КОРПОРАТИВНОЕ РАЗВЕРТЫВАНИЕ МЕДИАХОЛДИНГА
# Вариант B: Общий код + 7 процессов

set -e

echo "🏢 Корпоративное развертывание (общий код)"
echo "=========================================="

# Отделы медиахолдинга (замените на реальные)
DEPARTMENTS=(
    "holodnoe_plamya:🔥:Холодное пламя"
    "department_2:📺:Отдел 2"
    "department_3:⚡:Отдел 3" 
    "department_4:🌟:Отдел 4"
    "department_5:🔸:Отдел 5"
    "department_6:💎:Отдел 6"
    "department_7:🎯:Отдел 7"
)

BASE_DIR="/opt/news-monitor"
APP_DIR="$BASE_DIR/smi-bot"

echo "📁 Создание корпоративной структуры..."

# Создаем основные директории
mkdir -p "$BASE_DIR"/{configs,data,logs,sessions}

# Копируем исходный код в smi-bot (если запускается из исходной папки)
if [ -d "src" ] && [ -f "main.py" ]; then
    echo "📦 Копирование исходного кода в smi-bot..."
    cp -r . "$APP_DIR/"
    echo "✅ Исходный код скопирован"
elif [ ! -d "$APP_DIR" ]; then
    echo "❌ Ошибка: Исходный код не найден!"
    echo "💡 Запустите скрипт из папки с main.py или создайте $APP_DIR"
    exit 1
fi

# Устанавливаем права на выполнение
chmod +x "$APP_DIR/deploy/setup_corporate.sh" 2>/dev/null || true

echo ""
echo "🔧 Настройка отделов..."

# Настраиваем каждый отдел
for dept_info in "${DEPARTMENTS[@]}"; do
    IFS=':' read -r dept_key dept_emoji dept_name <<< "$dept_info"
    
    echo "  📁 $dept_name ($dept_key)"
    
    # Создаем структуру для отдела
    mkdir -p "$BASE_DIR/configs/$dept_key"
    mkdir -p "$BASE_DIR/data/$dept_key" 
    mkdir -p "$BASE_DIR/logs/$dept_key"
    mkdir -p "$BASE_DIR/sessions/$dept_key"
    
    # Копируем шаблоны конфигурации
    cp "$APP_DIR/config/config_template_corporate.yaml" "$BASE_DIR/configs/$dept_key/config.yaml"
    cp "$APP_DIR/config/channels_config_template_corporate.yaml" "$BASE_DIR/configs/$dept_key/channels_config.yaml"
    
    # Заменяем плейсхолдеры в конфигурации
    sed -i "s/\${DEPARTMENT_NAME}/$dept_name/g" "$BASE_DIR/configs/$dept_key/config.yaml"
    sed -i "s/\${DEPARTMENT_EMOJI}/$dept_emoji/g" "$BASE_DIR/configs/$dept_key/config.yaml"  
    sed -i "s/\${DEPARTMENT_KEY}/$dept_key/g" "$BASE_DIR/configs/$dept_key/config.yaml"
    
    sed -i "s/\${DEPARTMENT_NAME}/$dept_name/g" "$BASE_DIR/configs/$dept_key/channels_config.yaml"
    
    # Создаем .env для отдела
    cat > "$BASE_DIR/configs/$dept_key/.env" << EOF
# 🏢 ${dept_name} - Переменные окружения
# ВАЖНО: Замените на реальные значения!

# Telegram API (получить на my.telegram.org)
TELEGRAM_API_ID=YOUR_API_ID_HERE
TELEGRAM_API_HASH=YOUR_API_HASH_HERE

# Bot Token (получить у @BotFather)
BOT_TOKEN=YOUR_BOT_TOKEN_HERE

# ID администратора отдела
BOT_CHAT_ID=YOUR_ADMIN_ID_HERE

# ID группы для публикации новостей
TARGET_GROUP_ID=YOUR_GROUP_ID_HERE

# Настройки отдела
DEPARTMENT_NAME=${dept_name}
DEPARTMENT_EMOJI=${dept_emoji}  
DEPARTMENT_KEY=${dept_key}
EOF

    # Создаем systemd сервис с общим кодом
    cat > "/etc/systemd/system/news-monitor-$dept_key.service" << EOF
[Unit]
Description=News Monitor Bot - ${dept_name}
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python main.py
Restart=always
RestartSec=10
EnvironmentFile=$BASE_DIR/configs/$dept_key/.env
Environment=PYTHONPATH=$APP_DIR
Environment=CONFIG_PATH=$BASE_DIR/configs/$dept_key/config.yaml
Environment=CHANNELS_CONFIG_PATH=$BASE_DIR/configs/$dept_key/channels_config.yaml
Environment=DATA_PATH=$BASE_DIR/data/$dept_key
Environment=LOG_PATH=$BASE_DIR/logs/$dept_key
Environment=SESSION_PATH=$BASE_DIR/sessions/$dept_key

[Install]
WantedBy=multi-user.target
EOF
done

# Перезагружаем systemd
systemctl daemon-reload

echo ""
echo "🎉 КОРПОРАТИВНОЕ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО!"
echo ""
echo "📊 Создана структура:"
echo "├── $APP_DIR/         # Общий исходный код"
echo "├── $BASE_DIR/configs/    # Конфигурации отделов"
echo "├── $BASE_DIR/data/       # Базы данных отделов" 
echo "├── $BASE_DIR/logs/       # Логи отделов"
echo "└── $BASE_DIR/sessions/   # Telegram сессии"
echo ""
echo "📋 СЛЕДУЮЩИЕ ШАГИ:"
echo ""
echo "1️⃣  Создайте виртуальное окружение:"
echo "     cd $APP_DIR"
echo "     python3 -m venv venv"
echo "     source venv/bin/activate"
echo "     pip install --upgrade pip"
echo "     pip install -r requirements.txt"
echo ""
echo "2️⃣  Настройте .env файлы для каждого отдела:"
for dept_info in "${DEPARTMENTS[@]}"; do
    IFS=':' read -r dept_key dept_emoji dept_name <<< "$dept_info"
    echo "     nano $BASE_DIR/configs/$dept_key/.env"
done
echo ""
echo "3️⃣  Настройте каналы в channels_config.yaml для каждого отдела"
echo ""
echo "4️⃣  Проведите авторизацию Telegram для каждого отдела:"
echo "     cd $APP_DIR"
for dept_info in "${DEPARTMENTS[@]}"; do
    IFS=':' read -r dept_key dept_emoji dept_name <<< "$dept_info"
    echo "     CONFIG_PATH=$BASE_DIR/configs/$dept_key/config.yaml \\"
    echo "     DATA_PATH=$BASE_DIR/data/$dept_key \\"  
    echo "     SESSION_PATH=$BASE_DIR/sessions/$dept_key \\"
    echo "     DEPARTMENT_KEY=$dept_key \\"
    echo "     $APP_DIR/venv/bin/python main.py  # $dept_name - после авторизации нажмите Ctrl+C"
    echo ""
done
echo ""
echo "5️⃣  Запустите все сервисы:"
echo "     systemctl enable news-monitor-*"
echo "     systemctl start news-monitor-*"
echo ""
echo "📊 Мониторинг:"
echo "     systemctl status news-monitor-*"
echo "     journalctl -u news-monitor-holodnoe_plamya -f"
echo ""
echo "🔄 Обновление кода (для всех отделов сразу):"
echo "     cd $APP_DIR && git pull origin main"
echo "     systemctl restart news-monitor-*"
echo ""
echo "💡 Документация: $APP_DIR/docs/CORPORATE_DEPLOYMENT_V2.md"