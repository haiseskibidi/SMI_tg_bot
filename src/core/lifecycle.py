import sys
import os
import asyncio
import pytz
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from ..database import DatabaseManager
    from ..telegram_client import TelegramMonitor
    from ..bot import TelegramBot
    from ..news_processor import NewsProcessor
    from ..system_monitor import SystemMonitor
    from .config_loader import ConfigLoader


class LifecycleManager:
    def __init__(self, config_loader: "ConfigLoader"):
        self.config_loader = config_loader
        self.running = False
        self.restart_check_file = "config/.last_restart"
        
        # Компоненты системы
        self.database: Optional["DatabaseManager"] = None
        self.telegram_monitor: Optional["TelegramMonitor"] = None
        self.telegram_bot: Optional["TelegramBot"] = None
        self.news_processor: Optional["NewsProcessor"] = None
        self.system_monitor: Optional["SystemMonitor"] = None

    def setup_logging(self):
        try:
            log_config = self.config_loader.get_config().get('logging', {})
            
            # Поддержка корпоративного развертывания 
            default_log_file = 'logs/news_monitor.log'
            if os.getenv('LOG_PATH') and os.getenv('DEPARTMENT_KEY'):
                log_path = os.getenv('LOG_PATH')
                dept_key = os.getenv('DEPARTMENT_KEY')
                default_log_file = os.path.join(log_path, f'{dept_key}_monitor.log')
            
            log_file = Path(log_config.get('file') or default_log_file)
            log_file.parent.mkdir(exist_ok=True)
            
            logger.remove()
            
            logger.add(
                sys.stdout, 
                level="INFO",
                format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
                colorize=True
            )
            
            logger.add(
                log_file,
                level=log_config.get('level', 'INFO'),
                rotation=f"{log_config.get('max_size_mb', 10)} MB",
                retention=log_config.get('backup_count', 5),
                encoding='utf-8',
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
            )
            
            logger.info("📝 Система логирования настроена")
            
        except Exception as e:
            print(f"❌ Ошибка настройки логирования: {e}")

    async def initialize_components(self) -> bool:
        try:
            from ..database import DatabaseManager
            from ..telegram_client import TelegramMonitor
            from ..bot import create_bot_from_config
            from ..news_processor import NewsProcessor
            from ..system_monitor import SystemMonitor

            config = self.config_loader.get_config()
            
            # 1. База данных
            db_config = config.get('database', {})
            self.database = DatabaseManager(db_config.get('path', 'news_monitor.db'))
            await self.database.initialize()
            
            # 2. Системный монитор
            system_config = config.get('system', {})
            self.system_monitor = SystemMonitor(
                memory_limit_mb=system_config.get('memory_limit_mb', 800)
            )
            
            # 3. Telegram бот (ОСНОВНОЙ КАНАЛ СВЯЗИ) - временно без monitor_bot
            self.telegram_bot = await create_bot_from_config(config, None)
            if not self.telegram_bot:
                logger.error("❌ Не удалось создать Telegram бота")
                return False
            
            # 4. Telegram монитор (ОПЦИОНАЛЬНО)
            try:
                telegram_config = config['telegram']
                self.telegram_monitor = TelegramMonitor(
                    api_id=telegram_config['api_id'],
                    api_hash=telegram_config['api_hash'],
                    database=self.database
                )
                
                if await self.telegram_monitor.initialize():
                    logger.success("✅ Telegram мониторинг активен")
                else:
                    logger.warning("⚠️ Telegram мониторинг отключен (требуется авторизация)")
                    self.telegram_monitor = None
                    
            except Exception as e:
                logger.warning(f"⚠️ Telegram мониторинг недоступен: {e}")
                self.telegram_monitor = None
            
            # 5. Процессор новостей
            monitoring_config = config.get('monitoring', {})
            self.news_processor = NewsProcessor(
                database=self.database,
                telegram_bot=self.telegram_bot,
                telegram_monitor=self.telegram_monitor,
                config=monitoring_config
            )
            
            logger.success("✅ Все компоненты инициализированы")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            return False

    async def shutdown(self):
        logger.info("🛑 Завершение работы системы...")
        self.running = False
        
        try:
            if self.telegram_bot:
                self.telegram_bot.stop_listening()
                
                await self.telegram_bot.send_system_notification(
                    "🛑 <b>Система мониторинга остановлена</b>\n\n"
                    f"🕐 {datetime.now(pytz.timezone('Europe/Moscow')).strftime('%d.%m.%Y %H:%M:%S')} (Москва)"
                )
            
            if self.database:
                await self.database.close()
            
            if self.telegram_monitor:
                await self.telegram_monitor.disconnect()
            
            
        except Exception as e:
            logger.error(f"❌ Ошибка при завершении: {e}")
        
        logger.info("👋 Система завершена")

    def _check_restart_safety(self) -> bool:
        """Проверяет безопасность перезапуска (предотвращает блокировки Telegram)"""
        try:
            if not os.path.exists(self.restart_check_file):
                # Первый запуск - создаем файл
                self._update_restart_time()
                return True
            
            with open(self.restart_check_file, 'r') as f:
                last_restart_str = f.read().strip()
            
            last_restart = datetime.fromisoformat(last_restart_str)
            now = datetime.now()
            time_diff = now - last_restart
            
            # Проверяем, прошло ли достаточно времени с последнего перезапуска
            min_restart_interval = timedelta(minutes=30)  # Минимум 30 минут между перезапусками
            
            if time_diff < min_restart_interval:
                remaining = min_restart_interval - time_diff
                logger.error(f"🚫 ОПАСНОСТЬ БЛОКИРОВКИ! Слишком частый перезапуск!")
                logger.error(f"⏰ Последний запуск: {last_restart.strftime('%H:%M:%S')}")
                logger.error(f"⏳ Подождите еще: {remaining.total_seconds()//60:.0f} минут")
                logger.error(f"💡 Причина: частые перезапуски могут привести к блокировке аккаунта на 24 часа")
                logger.error(f"🔧 Решение: подождите или используйте другой аккаунт")
                return False
            
            # Обновляем время последнего запуска
            self._update_restart_time()
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка проверки безопасности перезапуска: {e}")
            self._update_restart_time()
            return True

    def _update_restart_time(self):
        """Обновляет время последнего перезапуска"""
        try:
            os.makedirs(os.path.dirname(self.restart_check_file), exist_ok=True)
            with open(self.restart_check_file, 'w') as f:
                f.write(datetime.now().isoformat())
        except Exception as e:
            logger.warning(f"⚠️ Не удалось обновить время перезапуска: {e}")

    async def run(self):
        try:
            # Проверяем безопасность перезапуска
            if not self._check_restart_safety():
                return False
            
            if not self.config_loader.load_config():
                return False
            
            self.config_loader.load_alert_keywords()
            self.config_loader.load_regions_config()
            
            self.setup_logging()
            
            if not await self.initialize_components():
                return False
            
            self.running = True
            logger.info("🚀 Система запущена")
            
            return True
            
        except KeyboardInterrupt:
            logger.info("👋 Получен сигнал завершения (Ctrl+C)")
        except Exception as e:
            logger.error(f"💥 Критическая ошибка: {e}")
            if self.telegram_bot:
                await self.telegram_bot.send_error_alert(f"Критическая ошибка: {e}")
            return False
        finally:
            await self.shutdown()
        
        return True
