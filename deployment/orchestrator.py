#!/usr/bin/env python3
"""
🎯 SMI#1 Multi-Department Bot Orchestrator
Централизованное управление 7 ботами для медиа-холдинга
"""

import asyncio
import subprocess
import psutil
import yaml
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from loguru import logger


class SMIBotOrchestrator:
    """Оркестратор для управления множественными экземплярами ботов"""
    
    def __init__(self):
        self.departments = [
            "sakhalin",    # Сахалинская область
            "kamchatka",   # Камчатский край
            "primorye",    # Приморский край
            "khabarovsk",  # Хабаровский край
            "magadan",     # Магаданская область
            "chukotka",    # Чукотский АО
            "yakutia"      # Республика Саха (Якутия)
        ]
        
        self.bot_processes: Dict[str, subprocess.Popen] = {}
        self.monitoring_data: Dict[str, Dict] = {}
        
    def get_server_resources(self) -> Dict:
        """Получить информацию о ресурсах сервера"""
        return {
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent
        }
    
    def calculate_resource_allocation(self) -> Dict[str, Dict]:
        """Рассчитать распределение ресурсов для каждого бота"""
        resources = self.get_server_resources()
        
        # Рекомендуемые ресурсы на один бот
        per_bot_cpu = min(2, resources["cpu_count"] // len(self.departments))
        per_bot_memory = min(2, resources["memory_total_gb"] // len(self.departments))
        
        allocation = {}
        for dept in self.departments:
            allocation[dept] = {
                "cpu_cores": per_bot_cpu,
                "memory_gb": per_bot_memory,
                "priority": "high" if dept in ["sakhalin", "kamchatka"] else "normal"
            }
        
        return allocation
    
    async def start_bot(self, department: str) -> bool:
        """Запустить бота для конкретного отдела"""
        try:
            logger.info(f"🚀 Запуск бота для отдела: {department}")
            
            # Путь к директории отдела
            dept_path = Path(f"/opt/smi-monitoring/{department}")
            dept_path.mkdir(parents=True, exist_ok=True)
            
            # Копируем код бота
            subprocess.run([
                "cp", "-r", "/opt/smi-monitoring/src", 
                str(dept_path)
            ], check=True)
            
            # Запускаем процесс бота
            env = {
                "DEPARTMENT": department,
                "CONFIG_PATH": f"{dept_path}/config/config.yaml",
                "DB_PATH": f"{dept_path}/data/news_monitor.db",
                "LOG_PATH": f"{dept_path}/logs"
            }
            
            process = subprocess.Popen(
                ["python3", "main.py"],
                cwd=str(dept_path),
                env={**os.environ, **env},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.bot_processes[department] = process
            
            # Проверяем что процесс запустился
            await asyncio.sleep(3)
            if process.poll() is None:
                logger.success(f"✅ Бот {department} успешно запущен (PID: {process.pid})")
                return True
            else:
                logger.error(f"❌ Бот {department} завершился с ошибкой")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка запуска бота {department}: {e}")
            return False
    
    async def stop_bot(self, department: str) -> bool:
        """Остановить бота для конкретного отдела"""
        try:
            if department in self.bot_processes:
                process = self.bot_processes[department]
                process.terminate()
                
                # Ждем корректного завершения
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                
                del self.bot_processes[department]
                logger.info(f"🛑 Бот {department} остановлен")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка остановки бота {department}: {e}")
            return False
    
    async def restart_bot(self, department: str) -> bool:
        """Перезапустить бота для конкретного отдела"""
        await self.stop_bot(department)
        await asyncio.sleep(2)
        return await self.start_bot(department)
    
    async def monitor_bots(self):
        """Мониторинг состояния всех ботов"""
        while True:
            try:
                for dept, process in self.bot_processes.items():
                    if process.poll() is not None:
                        # Бот упал, перезапускаем
                        logger.warning(f"⚠️ Бот {dept} неожиданно завершился, перезапуск...")
                        await self.start_bot(dept)
                
                # Собираем метрики
                self.monitoring_data = {
                    "timestamp": datetime.now().isoformat(),
                    "server": self.get_server_resources(),
                    "bots": {}
                }
                
                for dept in self.departments:
                    if dept in self.bot_processes:
                        process = self.bot_processes[dept]
                        if process.poll() is None:
                            # Получаем метрики процесса
                            try:
                                p = psutil.Process(process.pid)
                                self.monitoring_data["bots"][dept] = {
                                    "status": "running",
                                    "pid": process.pid,
                                    "cpu_percent": p.cpu_percent(),
                                    "memory_mb": round(p.memory_info().rss / (1024**2), 2),
                                    "threads": p.num_threads()
                                }
                            except:
                                self.monitoring_data["bots"][dept] = {"status": "error"}
                        else:
                            self.monitoring_data["bots"][dept] = {"status": "stopped"}
                    else:
                        self.monitoring_data["bots"][dept] = {"status": "not_started"}
                
                # Логируем статус
                running = sum(1 for b in self.monitoring_data["bots"].values() 
                            if b.get("status") == "running")
                logger.info(f"📊 Статус: {running}/{len(self.departments)} ботов работают")
                
                await asyncio.sleep(60)  # Проверка каждую минуту
                
            except Exception as e:
                logger.error(f"❌ Ошибка мониторинга: {e}")
                await asyncio.sleep(60)
    
    async def start_all(self):
        """Запустить все боты"""
        logger.info("🚀 Запуск всех ботов SMI#1...")
        
        # Проверяем ресурсы
        resources = self.get_server_resources()
        logger.info(f"📊 Ресурсы сервера: CPU: {resources['cpu_count']} ядер, "
                   f"RAM: {resources['memory_total_gb']}GB")
        
        if resources["memory_available_gb"] < 14:  # 7 ботов * 2GB
            logger.warning("⚠️ Недостаточно памяти для запуска всех ботов!")
        
        # Запускаем боты последовательно с задержкой
        for dept in self.departments:
            success = await self.start_bot(dept)
            if success:
                await asyncio.sleep(10)  # Задержка между запусками
            else:
                logger.error(f"❌ Не удалось запустить бот {dept}")
        
        # Запускаем мониторинг
        asyncio.create_task(self.monitor_bots())
        
        logger.success(f"✅ Запущено {len(self.bot_processes)}/{len(self.departments)} ботов")
    
    async def stop_all(self):
        """Остановить все боты"""
        logger.info("🛑 Остановка всех ботов...")
        
        for dept in list(self.bot_processes.keys()):
            await self.stop_bot(dept)
        
        logger.info("✅ Все боты остановлены")
    
    def get_status_report(self) -> str:
        """Получить отчет о состоянии системы"""
        report = "📊 ОТЧЕТ О СОСТОЯНИИ СИСТЕМЫ SMI#1\n"
        report += "=" * 50 + "\n\n"
        
        # Информация о сервере
        resources = self.get_server_resources()
        report += f"🖥️ СЕРВЕР:\n"
        report += f"  CPU: {resources['cpu_percent']}% ({resources['cpu_count']} ядер)\n"
        report += f"  RAM: {resources['memory_percent']}% "
        report += f"({resources['memory_available_gb']}GB свободно из {resources['memory_total_gb']}GB)\n"
        report += f"  Диск: {resources['disk_usage_percent']}%\n\n"
        
        # Статус ботов
        report += "🤖 БОТЫ:\n"
        for dept in self.departments:
            if dept in self.monitoring_data.get("bots", {}):
                bot_data = self.monitoring_data["bots"][dept]
                status = bot_data.get("status", "unknown")
                
                if status == "running":
                    report += f"  ✅ {dept.upper()}: Работает "
                    report += f"(PID: {bot_data.get('pid')}, "
                    report += f"CPU: {bot_data.get('cpu_percent')}%, "
                    report += f"RAM: {bot_data.get('memory_mb')}MB)\n"
                elif status == "stopped":
                    report += f"  🔴 {dept.upper()}: Остановлен\n"
                else:
                    report += f"  ⚠️ {dept.upper()}: {status}\n"
            else:
                report += f"  ⚪ {dept.upper()}: Не запущен\n"
        
        return report


async def main():
    """Главная функция оркестратора"""
    logger.add("orchestrator.log", rotation="100 MB")
    
    orchestrator = SMIBotOrchestrator()
    
    try:
        # Запускаем все боты
        await orchestrator.start_all()
        
        # Держим оркестратор активным
        while True:
            # Выводим статус каждые 5 минут
            print(orchestrator.get_status_report())
            await asyncio.sleep(300)
            
    except KeyboardInterrupt:
        logger.info("👋 Получен сигнал остановки")
        await orchestrator.stop_all()
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        await orchestrator.stop_all()


if __name__ == "__main__":
    import os
    asyncio.run(main())