import yaml
import os
import subprocess
from typing import Dict, List, Any
from loguru import logger
from datetime import datetime


class ConfigOperations:
    
    def __init__(self, bot: "TelegramBot"):
        self.bot = bot
    
    async def auto_commit_config(self, action_description: str, files_changed: List[str] = None):
        try:
            if not files_changed:
                files_changed = ["config/channels_config.yaml"]
            
            try:
                subprocess.run(["git", "--version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.debug("📝 Git не найден, пропускаем автокоммит")
                return True
            
            for file_path in files_changed:
                result = subprocess.run(
                    ["git", "add", file_path], 
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    logger.warning(f"⚠️ Не удалось добавить {file_path} в git")
            
            commit_message = f"Update configuration: {action_description}"
            result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                logger.info(f"📝 Автокоммит: {action_description}")
                return True
            else:
                logger.debug(f"📝 Нет изменений для коммита: {action_description}")
                return True
                
        except Exception as e:
            logger.warning(f"⚠️ Ошибка автокоммита: {e}")
            return False
    
    async def load_config_file(self, config_path: str) -> Dict:
        try:
            if not os.path.exists(config_path):
                return {}
            
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
                
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки {config_path}: {e}")
            return {}
    
    async def save_config_file(self, config_path: str, config_data: Dict) -> bool:
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, allow_unicode=True, indent=2, default_flow_style=False)
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения {config_path}: {e}")
            return False
