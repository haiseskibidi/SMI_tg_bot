"""
🖥️ System Monitor Module
Модуль для мониторинга системных ресурсов
Особенно важно для VPS с 1GB RAM
"""

import psutil
import asyncio
from datetime import datetime
from typing import Dict, Optional, List
from loguru import logger


class SystemMonitor:
    """Монитор системных ресурсов"""
    
    def __init__(self, memory_limit_mb: int = 800):
        self.memory_limit_mb = memory_limit_mb
        self.memory_limit_percent = 80  
        
        
        self.memory_warnings = 0
        self.cpu_warnings = 0
        
        logger.info(f"🖥️ SystemMonitor инициализирован (лимит RAM: {memory_limit_mb}MB)")
    
    def get_memory_usage(self) -> Dict:
        """Получение информации об использовании памяти"""
        try:
            memory = psutil.virtual_memory()
            
            return {
                'total_mb': round(memory.total / 1024 / 1024, 1),
                'available_mb': round(memory.available / 1024 / 1024, 1),
                'used_mb': round(memory.used / 1024 / 1024, 1),
                'used_percent': memory.percent,
                'free_mb': round(memory.free / 1024 / 1024, 1)
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о памяти: {e}")
            return {}
    
    def get_cpu_usage(self) -> Dict:
        """Получение информации об использовании CPU"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            return {
                'cpu_percent': cpu_percent,
                'cpu_count': cpu_count,
                'load_1min': load_avg[0],
                'load_5min': load_avg[1],
                'load_15min': load_avg[2]
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о CPU: {e}")
            return {}
    
    def get_disk_usage(self) -> Dict:
        """Получение информации об использовании диска"""
        try:
            disk = psutil.disk_usage('/')
            
            return {
                'total_gb': round(disk.total / 1024 / 1024 / 1024, 1),
                'used_gb': round(disk.used / 1024 / 1024 / 1024, 1),
                'free_gb': round(disk.free / 1024 / 1024 / 1024, 1),
                'used_percent': round(disk.used / disk.total * 100, 1)
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о диске: {e}")
            return {}
    
    def get_process_info(self) -> Dict:
        """Получение информации о текущем процессе"""
        try:
            process = psutil.Process()
            
            return {
                'memory_mb': round(process.memory_info().rss / 1024 / 1024, 1),
                'memory_percent': round(process.memory_percent(), 2),
                'cpu_percent': round(process.cpu_percent(), 2),
                'num_threads': process.num_threads(),
                'create_time': datetime.fromtimestamp(process.create_time()).isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о процессе: {e}")
            return {}
    
    def check_memory_usage(self) -> bool:
        """Проверка превышения лимитов памяти"""
        try:
            memory_info = self.get_memory_usage()
            
            if not memory_info:
                return False
            
            used_percent = memory_info.get('used_percent', 0)
            used_mb = memory_info.get('used_mb', 0)
            
            
            memory_critical = (
                used_percent > self.memory_limit_percent or 
                used_mb > self.memory_limit_mb
            )
            
            if memory_critical:
                self.memory_warnings += 1
                logger.warning(
                    f"⚠️ Критическое использование памяти: "
                    f"{used_percent}% ({used_mb}MB) "
                    f"лимит: {self.memory_limit_percent}% ({self.memory_limit_mb}MB)"
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки памяти: {e}")
            return False
    
    def check_cpu_usage(self) -> bool:
        """Проверка превышения лимитов CPU"""
        try:
            cpu_info = self.get_cpu_usage()
            
            if not cpu_info:
                return False
            
            cpu_percent = cpu_info.get('cpu_percent', 0)
            
            
            if cpu_percent > 90:
                self.cpu_warnings += 1
                logger.warning(f"⚠️ Высокая нагрузка на CPU: {cpu_percent}%")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки CPU: {e}")
            return False
    
    def check_disk_space(self) -> bool:
        """Проверка свободного места на диске"""
        try:
            disk_info = self.get_disk_usage()
            
            if not disk_info:
                return False
            
            used_percent = disk_info.get('used_percent', 0)
            free_gb = disk_info.get('free_gb', 0)
            
            
            if used_percent > 90 or free_gb < 1:
                logger.warning(
                    f"⚠️ Мало места на диске: "
                    f"{used_percent}% использовано, {free_gb}GB свободно"
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки диска: {e}")
            return False
    
    def get_full_system_status(self) -> Dict:
        """Получение полной информации о системе"""
        return {
            'timestamp': datetime.now().isoformat(),
            'memory': self.get_memory_usage(),
            'cpu': self.get_cpu_usage(),
            'disk': self.get_disk_usage(),
            'process': self.get_process_info(),
            'warnings': {
                'memory_warnings': self.memory_warnings,
                'cpu_warnings': self.cpu_warnings
            }
        }
    
    def log_system_status(self):
        """Логирование текущего состояния системы"""
        try:
            status = self.get_full_system_status()
            
            memory = status.get('memory', {})
            cpu = status.get('cpu', {})
            process = status.get('process', {})
            
            logger.info(
                f"🖥️ Система: "
                f"RAM {memory.get('used_percent', 0):.1f}% "
                f"({memory.get('used_mb', 0):.1f}MB), "
                f"CPU {cpu.get('cpu_percent', 0):.1f}%, "
                f"Процесс: {process.get('memory_mb', 0):.1f}MB"
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка логирования статуса: {e}")
    
    async def monitor_loop(self, interval_seconds: int = 300):
        """Цикл мониторинга (каждые 5 минут по умолчанию)"""
        logger.info(f"🖥️ Запуск цикла мониторинга (интервал: {interval_seconds}с)")
        
        while True:
            try:
                
                memory_critical = self.check_memory_usage()
                cpu_critical = self.check_cpu_usage()
                disk_critical = self.check_disk_space()
                
                
                self.log_system_status()
                
                
                if memory_critical or cpu_critical or disk_critical:
                    logger.warning("⚠️ Обнаружены проблемы с ресурсами!")
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"❌ Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(60)  
    
    def check_memory_limit(self) -> bool:
        """Проверить превышение лимита памяти"""
        try:
            memory_info = self.get_memory_usage()
            used_percent = memory_info.get('used_percent', 0)
            
            if used_percent > self.memory_limit_percent:
                logger.warning(f"⚠️ Превышен лимит памяти: {used_percent}% > {self.memory_limit_percent}%")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки лимита памяти: {e}")
            return False
    
    def suggest_optimizations(self) -> List[str]:
        """Предложения по оптимизации на основе текущего состояния"""
        suggestions = []
        
        try:
            memory_info = self.get_memory_usage()
            cpu_info = self.get_cpu_usage()
            disk_info = self.get_disk_usage()
            
            
            if memory_info.get('used_percent', 0) > 70:
                suggestions.append("🧹 Рекомендуется очистка кэша и неиспользуемых данных")
                suggestions.append("📉 Снизить количество одновременно обрабатываемых каналов")
            
            
            if cpu_info.get('cpu_percent', 0) > 80:
                suggestions.append("⏱️ Увеличить интервалы между запросами к API")
                suggestions.append("🔄 Добавить больше пауз между операциями")
            
            
            if disk_info.get('used_percent', 0) > 80:
                suggestions.append("📁 Очистить старые логи и данные")
                suggestions.append("🗃️ Настроить ротацию базы данных")
            
            
            if memory_info.get('total_mb', 0) < 1200:  
                suggestions.extend([
                    "⚡ Использовать файловое кэширование вместо RAM",
                    "📦 Обрабатывать каналы меньшими пакетами",
                    "🔧 Настроить swap файл для дополнительной памяти"
                ])
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа оптимизации: {e}")
            suggestions.append("❌ Не удалось проанализировать систему")
        
        return suggestions
    
    def is_system_healthy(self) -> bool:
        """Проверка общего состояния системы"""
        try:
            memory_ok = not self.check_memory_usage()
            cpu_ok = not self.check_cpu_usage()
            disk_ok = not self.check_disk_space()
            
            return memory_ok and cpu_ok and disk_ok
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки состояния системы: {e}")
            return False
