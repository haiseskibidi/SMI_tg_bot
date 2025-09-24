import os
import json
from datetime import datetime
from typing import Set, Dict
from loguru import logger


class SubscriptionCacheManager:
    def __init__(self, cache_file: str = "config/subscriptions_cache.json"):
        self.subscription_cache_file = cache_file
        self.subscribed_channels: Set[str] = set()

    def load_subscription_cache(self):
        try:
            if os.path.exists(self.subscription_cache_file):
                with open(self.subscription_cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    self.subscribed_channels = set(cache_data.get('subscribed_channels', []))
                    logger.info(f"📋 Загружен кэш подписок: {len(self.subscribed_channels)} каналов")
            else:
                self.subscribed_channels = set()
                logger.info("📋 Файл кэша подписок не найден, создаем новый")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки кэша подписок: {e}")
            self.subscribed_channels = set()
    
    def sync_cache_with_config(self, current_channels: set):
        before_count = len(self.subscribed_channels)
        
        removed_channels = self.subscribed_channels - current_channels
        if removed_channels:
            logger.info(f"🧹 Удаляем из кэша несуществующие каналы: {list(removed_channels)}")
            self.subscribed_channels = self.subscribed_channels & current_channels
            self.save_subscription_cache()
            logger.info(f"💾 Кэш синхронизирован: {before_count} → {len(self.subscribed_channels)} каналов")

    def save_subscription_cache(self):
        try:
            os.makedirs(os.path.dirname(self.subscription_cache_file), exist_ok=True)
            
            cache_data = {
                'subscribed_channels': list(self.subscribed_channels),
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.subscription_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"💾 Сохранен кэш подписок: {len(self.subscribed_channels)} каналов")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения кэша подписок: {e}")

    def is_channel_cached_as_subscribed(self, channel_username: str) -> bool:
        return channel_username in self.subscribed_channels

    def add_channel_to_cache(self, channel_username: str):
        self.subscribed_channels.add(channel_username)
        self.save_subscription_cache()

    def clear_subscription_cache(self):
        self.subscribed_channels.clear()
        self.save_subscription_cache()

    def get_subscribed_channels(self) -> Set[str]:
        return self.subscribed_channels.copy()

    def remove_from_cache(self, channel_username: str):
        if channel_username in self.subscribed_channels:
            self.subscribed_channels.remove(channel_username)
            self.save_subscription_cache()

    def get_cache_stats(self) -> dict:
        return {
            'total_subscribed': len(self.subscribed_channels),
            'cache_file': self.subscription_cache_file,
            'file_exists': os.path.exists(self.subscription_cache_file)
        }
