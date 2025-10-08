import os
import yaml
from typing import Dict, Any
from dotenv import load_dotenv
from loguru import logger


class ConfigLoader:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = {}
        self.regions_config = {}
        self.alert_keywords = {}

    def load_config(self) -> bool:
        try:
            load_dotenv()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            logger.info(f"✅ Конфигурация загружена из {self.config_path}")
            
            self._override_from_env()
            
            return True
            
        except FileNotFoundError:
            logger.error(f"❌ Файл конфигурации не найден: {self.config_path}")
            return False
        except yaml.YAMLError as e:
            logger.error(f"❌ Ошибка YAML в конфигурации: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки конфигурации: {e}")
            return False

    def _override_from_env(self):
        bot_token = os.getenv('BOT_TOKEN')
        bot_chat_id = os.getenv('BOT_CHAT_ID')
        bot_group_chat_id = os.getenv('BOT_GROUP_CHAT_ID')
        api_id = os.getenv('TELEGRAM_API_ID')
        api_hash = os.getenv('TELEGRAM_API_HASH')
        
        
        target_group = (os.getenv('TARGET_GROUP_ID') or 
                       os.getenv('YOUR_TARGET_GROUP_FROM_ENV') or
                       os.getenv('BOT_TARGET_GROUP'))
        
        bot_allowed_users = os.getenv('BOT_ALLOWED_USERS')
        
        if bot_token:
            self.config.setdefault('bot', {})['token'] = bot_token
        if bot_chat_id:
            self.config.setdefault('bot', {})['chat_id'] = int(bot_chat_id)
        if bot_group_chat_id:
            self.config.setdefault('bot', {})['group_chat_id'] = int(bot_group_chat_id)
            logger.info(f"👥 Настроена групповая отправка: {bot_group_chat_id}")
        if api_id:
            self.config.setdefault('telegram', {})['api_id'] = int(api_id)
        if api_hash:
            self.config.setdefault('telegram', {})['api_hash'] = api_hash
        if target_group:
            
            self.config.setdefault('output', {})['target_group'] = int(target_group)
            logger.info(f"🎯 Настроена целевая группа: {target_group}")
        if bot_allowed_users:
            self.config.setdefault('bot', {})['allowed_users'] = [int(x.strip()) for x in bot_allowed_users.split(',')]

    def load_alert_keywords(self):
        try:
            alerts_config = self.config.get('alerts', {})
            if not alerts_config.get('enabled', False):
                logger.info("📢 Алерты по ключевым словам отключены")
                return
            
            keywords_config = alerts_config.get('keywords', {})
            for category, data in keywords_config.items():
                words = data.get('words', [])
                emoji = data.get('emoji', '🚨')
                priority = data.get('priority', False)
                
                self.alert_keywords[category] = {
                    'words': [word.lower() for word in words],
                    'emoji': emoji,
                    'priority': priority
                }
            
            total_words = sum(len(cat['words']) for cat in self.alert_keywords.values())
            logger.info(f"📢 Загружено {len(self.alert_keywords)} категорий алертов, {total_words} ключевых слов")
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки алертов: {e}")
            self.alert_keywords = {}

    def load_regions_config(self):
        try:
            regions_config = self.config.get('regions', {})
            if not regions_config:
                logger.warning("📍 Секция regions не найдена в конфигурации, используем стандартные регионы")
                self.regions_config = {
                    'general': {
                        'name': '📰 Общие',
                        'emoji': '📰',
                        'description': 'Общие новости',
                        'keywords': [],
                        'topic_id': None
                    }
                }
                return
            
            self.regions_config = {}
            for region_key, region_data in regions_config.items():
                self.regions_config[region_key] = {
                    'name': region_data.get('name', region_key),
                    'emoji': region_data.get('emoji', '📍'),
                    'description': region_data.get('description', ''),
                    'keywords': region_data.get('keywords', []),
                    'topic_id': region_data.get('topic_id'),
                    'created_at': region_data.get('created_at', '2025-08-26')
                }
            
            logger.info(f"📍 Загружено {len(self.regions_config)} регионов: {list(self.regions_config.keys())}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки регионов: {e}")
            self.regions_config = {}

    def get_regions_list(self) -> list:
        return [
            {
                'key': key,
                'name': data['name'],
                'emoji': data['emoji'],
                'description': data.get('description', ''),
                'topic_id': data.get('topic_id'),
                'created_at': data.get('created_at', '2025-08-26')
            }
            for key, data in self.regions_config.items()
        ]

    def get_config(self) -> Dict[str, Any]:
        return self.config

    def get_regions_config(self) -> Dict[str, Any]:
        return self.regions_config

    def get_alert_keywords(self) -> Dict[str, Any]:
        return self.alert_keywords

    def get_monitoring_timeouts(self) -> Dict[str, Any]:
        """Получить настройки таймаутов для мониторинга каналов"""
        if not self.config or not isinstance(self.config, dict):
            logger.warning("⚠️ Конфигурация не загружена, используем только значения по умолчанию")
            monitoring_config = {}
            timeouts = {}
        else:
            monitoring_config = self.config.get('monitoring', {})
            timeouts = monitoring_config.get('timeouts', {}) if monitoring_config else {}
        
        
        default_timeouts = {
            'batch_size': 6,                    
            'delay_cached_channel': 1,          
            'delay_already_joined': 2,          
            'delay_verification': 3,            
            'delay_after_subscribe': 5,         
            'delay_between_batches': 8,         
            'delay_retry_wait': 300,            
            'delay_retry_subscribe': 5,         
            'delay_between_retries': 8,         
            'fast_start_mode': True,            
            'skip_new_on_startup': False,       
        }
        
        
        for key, default_value in default_timeouts.items():
            if key not in timeouts:
                timeouts[key] = default_value
        
        return timeouts
