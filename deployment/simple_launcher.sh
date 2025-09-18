#!/bin/bash
#
# 🚀 Простой launcher для 7 ботов SMI#1 БЕЗ Docker
# Запускает каждого бота в отдельном screen/tmux сессии
#

# Цвета для красивого вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Базовая директория
BASE_DIR="/opt/smi-monitoring"

# Список отделов
DEPARTMENTS=("sakhalin" "kamchatka" "primorye" "khabarovsk" "magadan" "chukotka" "yakutia")

# Функция для запуска одного бота
start_bot() {
    local dept=$1
    echo -e "${YELLOW}🚀 Запуск бота для отдела: $dept${NC}"
    
    # Создаем директорию если нет
    mkdir -p "$BASE_DIR/$dept"
    mkdir -p "$BASE_DIR/$dept/logs"
    mkdir -p "$BASE_DIR/$dept/data"
    mkdir -p "$BASE_DIR/$dept/config"
    
    # Копируем код (если еще не скопирован)
    if [ ! -f "$BASE_DIR/$dept/main.py" ]; then
        cp -r "$BASE_DIR/src" "$BASE_DIR/$dept/"
        cp "$BASE_DIR/main.py" "$BASE_DIR/$dept/"
        cp "$BASE_DIR/requirements.txt" "$BASE_DIR/$dept/"
    fi
    
    # Запускаем в screen сессии
    screen -dmS "bot_$dept" bash -c "
        cd $BASE_DIR/$dept
        source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
        pip install -q -r requirements.txt
        export DEPARTMENT=$dept
        python3 main.py 2>&1 | tee -a logs/bot.log
    "
    
    sleep 2
    
    # Проверяем запустился ли
    if screen -list | grep -q "bot_$dept"; then
        echo -e "${GREEN}✅ Бот $dept успешно запущен${NC}"
    else
        echo -e "${RED}❌ Ошибка запуска бота $dept${NC}"
    fi
}

# Функция для остановки одного бота
stop_bot() {
    local dept=$1
    echo -e "${YELLOW}🛑 Остановка бота: $dept${NC}"
    
    screen -S "bot_$dept" -X quit 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Бот $dept остановлен${NC}"
    else
        echo -e "${YELLOW}⚠️ Бот $dept уже был остановлен${NC}"
    fi
}

# Функция для проверки статуса
check_status() {
    echo -e "${YELLOW}📊 СТАТУС СИСТЕМЫ:${NC}"
    echo "========================"
    
    for dept in "${DEPARTMENTS[@]}"; do
        if screen -list | grep -q "bot_$dept"; then
            # Получаем PID процесса
            pid=$(screen -list | grep "bot_$dept" | awk -F'.' '{print $1}' | awk '{print $1}')
            # Получаем использование памяти
            if [ ! -z "$pid" ]; then
                mem=$(ps -o rss= -p $pid 2>/dev/null | awk '{print int($1/1024)"MB"}')
                echo -e "✅ $dept: ${GREEN}Работает${NC} (PID: $pid, RAM: $mem)"
            else
                echo -e "✅ $dept: ${GREEN}Работает${NC}"
            fi
        else
            echo -e "🔴 $dept: ${RED}Остановлен${NC}"
        fi
    done
    
    echo "========================"
    
    # Общая статистика
    running=$(screen -list | grep -c "bot_")
    echo -e "Работает ботов: ${GREEN}$running${NC} из ${#DEPARTMENTS[@]}"
    
    # Использование ресурсов
    echo -e "\n${YELLOW}📊 РЕСУРСЫ СЕРВЕРА:${NC}"
    echo "CPU: $(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1"%"}')"
    echo "RAM: $(free -h | awk 'NR==2{printf "%s/%s (%.1f%%)\n", $3,$2,$3*100/$2}')"
    echo "Disk: $(df -h / | awk 'NR==2{printf "%s/%s (%s)\n", $3,$2,$5}')"
}

# Главное меню
case "$1" in
    start)
        if [ -z "$2" ]; then
            # Запускаем все боты
            echo -e "${GREEN}🚀 Запуск всех ботов...${NC}"
            for dept in "${DEPARTMENTS[@]}"; do
                start_bot "$dept"
                sleep 5  # Задержка между запусками
            done
        else
            # Запускаем конкретного бота
            start_bot "$2"
        fi
        ;;
        
    stop)
        if [ -z "$2" ]; then
            # Останавливаем все боты
            echo -e "${RED}🛑 Остановка всех ботов...${NC}"
            for dept in "${DEPARTMENTS[@]}"; do
                stop_bot "$dept"
            done
        else
            # Останавливаем конкретного бота
            stop_bot "$2"
        fi
        ;;
        
    restart)
        if [ -z "$2" ]; then
            # Перезапускаем все
            $0 stop
            sleep 3
            $0 start
        else
            # Перезапускаем конкретного бота
            stop_bot "$2"
            sleep 2
            start_bot "$2"
        fi
        ;;
        
    status)
        check_status
        ;;
        
    logs)
        if [ -z "$2" ]; then
            echo "Использование: $0 logs <department>"
            echo "Доступные отделы: ${DEPARTMENTS[@]}"
        else
            echo -e "${YELLOW}📜 Логи бота $2:${NC}"
            tail -f "$BASE_DIR/$2/logs/bot.log"
        fi
        ;;
        
    attach)
        if [ -z "$2" ]; then
            echo "Использование: $0 attach <department>"
            echo "Доступные отделы: ${DEPARTMENTS[@]}"
        else
            echo -e "${YELLOW}📺 Подключение к боту $2...${NC}"
            echo -e "${RED}Для выхода используйте: Ctrl+A, затем D${NC}"
            sleep 2
            screen -r "bot_$2"
        fi
        ;;
        
    *)
        echo "🤖 SMI#1 Bot Manager (БЕЗ Docker)"
        echo "=================================="
        echo "Использование: $0 {start|stop|restart|status|logs|attach} [department]"
        echo ""
        echo "Команды:"
        echo "  start [dept]   - Запустить все боты или конкретный отдел"
        echo "  stop [dept]    - Остановить все боты или конкретный отдел"
        echo "  restart [dept] - Перезапустить боты"
        echo "  status         - Показать статус всех ботов"
        echo "  logs <dept>    - Показать логи конкретного бота"
        echo "  attach <dept>  - Подключиться к screen сессии бота"
        echo ""
        echo "Отделы: ${DEPARTMENTS[@]}"
        echo ""
        echo "Примеры:"
        echo "  $0 start              # Запустить все боты"
        echo "  $0 start sakhalin     # Запустить только Сахалин"
        echo "  $0 status             # Проверить статус"
        echo "  $0 logs kamchatka     # Смотреть логи Камчатки"
        ;;
esac