#!/bin/bash
#
# 🎯 Настройка systemd сервисов для 7 ботов (БЕЗ Docker)
# Каждый бот будет работать как отдельный systemd сервис
#

DEPARTMENTS=("sakhalin" "kamchatka" "primorye" "khabarovsk" "magadan" "chukotka" "yakutia")
BASE_DIR="/opt/smi-monitoring"

echo "📦 Создание systemd сервисов для SMI#1..."

for dept in "${DEPARTMENTS[@]}"; do
    echo "Creating service for $dept..."
    
    # Создаем systemd unit файл
    cat > /etc/systemd/system/smi-bot-$dept.service << EOF
[Unit]
Description=SMI#1 News Monitor Bot - $dept
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=10
User=smi-bot
WorkingDirectory=$BASE_DIR/$dept
Environment="DEPARTMENT=$dept"
Environment="PYTHONPATH=$BASE_DIR/$dept"
ExecStart=/usr/bin/python3 $BASE_DIR/$dept/main.py
StandardOutput=append:$BASE_DIR/$dept/logs/systemd.log
StandardError=append:$BASE_DIR/$dept/logs/systemd-error.log

# Ограничения ресурсов
CPUQuota=150%
MemoryLimit=2G
TasksMax=100

[Install]
WantedBy=multi-user.target
EOF

done

# Создаем master сервис для управления всеми ботами
cat > /etc/systemd/system/smi-bots.target << EOF
[Unit]
Description=SMI#1 All Bots
Wants=$(for d in "${DEPARTMENTS[@]}"; do echo -n "smi-bot-$d.service "; done)

[Install]
WantedBy=multi-user.target
EOF

# Перезагружаем systemd
systemctl daemon-reload

echo "✅ Сервисы созданы!"
echo ""
echo "📝 Команды управления:"
echo "  systemctl start smi-bots.target    # Запустить все боты"
echo "  systemctl stop smi-bots.target     # Остановить все боты"
echo "  systemctl status smi-bots.target   # Статус всех ботов"
echo ""
echo "  systemctl start smi-bot-sakhalin   # Запустить конкретного бота"
echo "  systemctl status smi-bot-sakhalin  # Статус конкретного бота"
echo "  journalctl -u smi-bot-sakhalin -f  # Логи конкретного бота"
echo ""
echo "🚀 Для автозапуска при старте системы:"
echo "  systemctl enable smi-bots.target"