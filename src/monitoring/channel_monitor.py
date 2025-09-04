import asyncio
import re
import yaml
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from ..telegram_client import TelegramMonitor
    from .message_processor import MessageProcessor
    from .subscription_cache import SubscriptionCacheManager


class ChannelMonitor:
    def __init__(self, telegram_monitor: "TelegramMonitor", 
                 subscription_cache: "SubscriptionCacheManager",
                 message_processor: "MessageProcessor",
                 config_loader=None):
        self.telegram_monitor = telegram_monitor
        self.subscription_cache = subscription_cache
        self.message_processor = message_processor
        self.channels_config_path = "config/channels_config.yaml"
        
        # ⏱️ НАСТРОЙКИ ТАЙМАУТОВ (загружаются из конфигурации или используются по умолчанию)
        if config_loader:
            try:
                timeouts = config_loader.get_monitoring_timeouts()
                if timeouts and isinstance(timeouts, dict):
                    self.batch_size = timeouts.get('batch_size', 6)
                    self.delay_cached_channel = timeouts.get('delay_cached_channel', 1)
                    self.delay_already_joined = timeouts.get('delay_already_joined', 2)
                    self.delay_verification = timeouts.get('delay_verification', 3)
                    self.delay_after_subscribe = timeouts.get('delay_after_subscribe', 5)
                    self.delay_between_batches = timeouts.get('delay_between_batches', 8)
                    self.delay_retry_wait = timeouts.get('delay_retry_wait', 300)
                    self.delay_retry_subscribe = timeouts.get('delay_retry_subscribe', 5)
                    self.delay_between_retries = timeouts.get('delay_between_retries', 8)
                    # 🚀 Новые настройки оптимизации
                    self.fast_start_mode = timeouts.get('fast_start_mode', True)
                    self.skip_new_on_startup = timeouts.get('skip_new_on_startup', False)
                else:
                    logger.warning("⚠️ Получены неверные настройки таймаутов, используем значения по умолчанию")
                    self._set_default_timeouts()
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки настроек таймаутов: {e}")
                self._set_default_timeouts()
        else:
            # ⚠️ БЕЗОПАСНЫЕ значения по умолчанию (если конфигурация недоступна)
            self._set_default_timeouts()

    def _set_default_timeouts(self):
        """Установить безопасные значения таймаутов по умолчанию"""
        self.batch_size = 6
        self.delay_cached_channel = 1
        self.delay_already_joined = 2
        self.delay_verification = 3
        self.delay_after_subscribe = 5
        self.delay_between_batches = 8
        self.delay_retry_wait = 300
        self.delay_retry_subscribe = 5
        self.delay_between_retries = 8
        self.fast_start_mode = True
        self.skip_new_on_startup = False

    async def setup_realtime_handlers(self):
        from telethon import events
        
        logger.info("⚡ Настройка обработчиков реального времени...")
        
        if not self.telegram_monitor or not self.telegram_monitor.client:
            logger.error("❌ Telegram клиент недоступен")
            return
        
        all_channels = await self._load_channels_config()
        
        if not all_channels:
            logger.warning("⚠️ Список каналов для мониторинга пуст. Создайте правильный config/channels_config.yaml или добавьте каналы через бота.")
            return
        
        monitored_channels = await self._subscribe_to_channels(all_channels)
        
        if monitored_channels:
            self.telegram_monitor.client.add_event_handler(
                self.message_processor.handle_new_message,
                events.NewMessage(chats=monitored_channels)
            )
            logger.info(f"⚡ Настроен мониторинг {len(monitored_channels)} каналов в реальном времени!")
        
        await self._test_telethon_client()
        
        rate_limited_channels = getattr(self, '_rate_limited_channels', [])
        if rate_limited_channels:
            await self._retry_rate_limited_subscriptions(rate_limited_channels)

    async def _load_channels_config(self) -> List[Dict[str, Any]]:
        try:
            with open(self.channels_config_path, 'r', encoding='utf-8') as f:
                channels_data = yaml.safe_load(f) or {}
        except (FileNotFoundError, yaml.YAMLError) as e:
            logger.warning(f"⚠️ Проблема с файлом каналов {self.channels_config_path}: {e}")
            return []
        
        all_channels = []
        
        if 'regions' in channels_data:
            for region_key, region_data in channels_data['regions'].items():
                if not region_data or not isinstance(region_data, dict):
                    logger.warning(f"⚠️ Неверные данные для региона '{region_key}' - пропускаем")
                    continue
                    
                region_channels = region_data.get('channels', [])
                for channel in region_channels:
                    if not channel or not isinstance(channel, dict):
                        logger.warning(f"⚠️ Неверные данные канала в регионе '{region_key}' - пропускаем")
                        continue
                        
                    channel_with_region = channel.copy()
                    channel_with_region['region'] = region_key
                    all_channels.append(channel_with_region)
        elif channels_data and 'channels' in channels_data and channels_data['channels']:
            channels_list = channels_data['channels']
            if isinstance(channels_list, list):
                all_channels = channels_list
            else:
                logger.warning("⚠️ Секция 'channels' должна быть списком - пропускаем")
        elif channels_data:
            if 'vip_channels' in channels_data and channels_data['vip_channels']:
                vip_channels = channels_data['vip_channels']
                if isinstance(vip_channels, list):
                    all_channels.extend(vip_channels)
                else:
                    logger.warning("⚠️ Секция 'vip_channels' должна быть списком - пропускаем")
                    
            if 'regular_channels' in channels_data and channels_data['regular_channels']:
                regular_channels = channels_data['regular_channels']
                if isinstance(regular_channels, list):
                    all_channels.extend(regular_channels)
                else:
                    logger.warning("⚠️ Секция 'regular_channels' должна быть списком - пропускаем")
        
        return all_channels

    async def _fast_load_cached_channels(self, all_channels: List[Dict[str, Any]]) -> Tuple[List, List[Dict[str, Any]]]:
        """🚀 БЫСТРАЯ загрузка кешированных каналов (без API вызовов)"""
        logger.info("🚀 БЫСТРАЯ ЗАГРУЗКА: обрабатываем кешированные каналы...")
        
        cached_channels = []
        new_channels = []
        failed_entities = []
        
        for channel_config in all_channels:
            username = channel_config['username']
            
            # Проверяем кэш БЕЗ API вызова
            if self.subscription_cache.is_channel_cached_as_subscribed(username):
                cached_channels.append(channel_config)
            else:
                new_channels.append(channel_config)
        
        logger.info(f"💾 Найдено в кэше: {len(cached_channels)} каналов")
        logger.info(f"🆕 Новых каналов: {len(new_channels)} (требуют медленной обработки)")
        
        # Быстро получаем entity для кешированных каналов
        monitored_channels = []
        for i, channel_config in enumerate(cached_channels):
            try:
                username = channel_config['username']
                logger.debug(f"💾 Загрузка кешированного канала {username} ({i+1}/{len(cached_channels)})")
                
                entity = await self.telegram_monitor.get_channel_entity(username)
                if entity:
                    monitored_channels.append(entity)
                    # Минимальная задержка только для кешированных
                    if i % 10 == 0 and i > 0:  # Каждые 10 каналов небольшая пауза
                        await asyncio.sleep(0.5)
                else:
                    failed_entities.append(channel_config)
                    logger.warning(f"⚠️ Не удалось получить entity для кешированного канала {username}")
                    
            except Exception as e:
                failed_entities.append(channel_config)
                logger.warning(f"⚠️ Ошибка загрузки кешированного канала {username}: {e}")
        
        # Добавляем неудачные кешированные каналы к новым для повторной обработки
        new_channels.extend(failed_entities)
        
        logger.info(f"✅ Быстро загружено: {len(monitored_channels)} кешированных каналов")
        if failed_entities:
            logger.info(f"⚠️ Не удалось загрузить: {len(failed_entities)} каналов (будут обработаны медленно)")
        
        return monitored_channels, new_channels

    async def _slow_process_new_channels(self, new_channels: List[Dict[str, Any]]) -> Tuple[List, List[Dict[str, Any]]]:
        """🐌 МЕДЛЕННАЯ обработка новых каналов с безопасными задержками"""
        from telethon.tl.functions.channels import JoinChannelRequest
        
        if not new_channels:
            logger.info("✅ Новых каналов нет - пропускаем медленную обработку")
            return [], []
        
        logger.info(f"🐌 МЕДЛЕННАЯ ОБРАБОТКА: {len(new_channels)} новых каналов...")
        logger.info("⚠️ Это займет время, но предотвратит блокировки")
        
        monitored_channels = []
        subscribed_count = 0
        failed_count = 0
        rate_limited_count = 0
        rate_limited_channels = []
        
        processed_count = 0
        
        for i in range(0, len(new_channels), self.batch_size):
            batch = new_channels[i:i + self.batch_size]
            logger.info(f"🔄 Медленная обработка пакета {i//self.batch_size + 1}/{(len(new_channels) + self.batch_size - 1)//self.batch_size} ({len(batch)} каналов)")
            
            for channel_config in batch:
                try:
                    processed_count += 1
                    username = channel_config['username']
                    logger.debug(f"📡 Получение entity для НОВОГО канала {username} ({processed_count}/{len(new_channels)})")
                    
                    entity = await self.telegram_monitor.get_channel_entity(username)
                    if not entity:
                        failed_count += 1
                        continue
                    
                    try:
                        already = await self.telegram_monitor.is_already_joined(entity)
                        logger.info(f"🔍 Проверка подписки на {username}: {'ДА' if already else 'НЕТ'}")
                        if already:
                            self.subscription_cache.add_channel_to_cache(username)
                            monitored_channels.append(entity)
                            logger.info(f"📡 Добавлен в мониторинг: {username}")
                            await asyncio.sleep(self.delay_already_joined)
                            continue
                    except Exception as check_error:
                        logger.warning(f"⚠️ Ошибка проверки подписки на {username}: {check_error}")
                        already = False

                    try:
                        logger.info(f"🚀 Попытка подписки на канал: @{username}")
                        await self.telegram_monitor.client(JoinChannelRequest(entity))
                        
                        verification_attempts = 3
                        for attempt in range(verification_attempts):
                            await asyncio.sleep(self.delay_verification)
                            try:
                                now_joined = await self.telegram_monitor.is_already_joined(entity)
                                if now_joined:
                                    logger.success(f"✅ Успешно подписались на @{username}")
                                    subscribed_count += 1
                                    self.subscription_cache.add_channel_to_cache(username)
                                    monitored_channels.append(entity)
                                    break
                            except Exception as verify_error:
                                logger.warning(f"⚠️ Ошибка верификации подписки на {username} (попытка {attempt+1}): {verify_error}")
                        
                        await asyncio.sleep(self.delay_after_subscribe)
                        
                    except Exception as sub_error:
                        error_msg = str(sub_error).lower()
                        if any(keyword in error_msg for keyword in ["wait", "flood", "timeout", "seconds"]):
                            wait_time = self._extract_wait_time(str(sub_error))
                            if wait_time and wait_time > 3600:
                                logger.error(f"🚫 ДЛИТЕЛЬНАЯ БЛОКИРОВКА для @{username}: {wait_time//3600:.1f} часов ({wait_time} сек)")
                                logger.error(f"💡 Причины: частые перезапуски, подозрительная активность, нарушения правил Telegram")
                                logger.error(f"🔧 Решение: дождаться окончания блокировки или использовать другой аккаунт")
                            else:
                                logger.warning(f"⏳ Rate limit для @{username}: {sub_error}")
                            
                            rate_limited_count += 1
                            rate_limited_channels.append(channel_config)
                        elif any(keyword in error_msg for keyword in ["already", "участник", "member"]):
                            logger.info(f"✅ Уже подписан на @{username}")
                            self.subscription_cache.add_channel_to_cache(username)
                            monitored_channels.append(entity)
                        else:
                            logger.error(f"❌ Ошибка подписки на @{username}: {sub_error}")
                            failed_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ Общая ошибка обработки канала {channel_config.get('username', 'unknown')}: {e}")
                    failed_count += 1
            
            # Увеличенная пауза между пакетами для новых каналов
            await asyncio.sleep(self.delay_between_batches)
        
        logger.info(f"📊 Результаты медленной обработки:")
        logger.info(f"✅ Успешно подписался: {subscribed_count}")
        logger.info(f"💾 Уже был подписан: {len(monitored_channels) - subscribed_count}")
        logger.info(f"⏳ Rate limit: {rate_limited_count}")
        logger.info(f"❌ Ошибки: {failed_count}")
        
        return monitored_channels, rate_limited_channels

    async def _subscribe_to_channels(self, all_channels: List[Dict[str, Any]]) -> List:
        """🎯 ОПТИМИЗИРОВАННАЯ подписка: быстро для кешированных + медленно для новых"""
        if self.fast_start_mode:
            logger.info("🚀 РЕЖИМ БЫСТРОГО СТАРТА включен!")
            logger.info("⚡ Приоритет кешированным каналам для максимальной скорости")
        else:
            logger.info("🐌 Обычный режим - все каналы обрабатываются одинаково")
            
        logger.info(f"📊 Всего каналов для обработки: {len(all_channels)}")
        
        if not self.fast_start_mode:
            # Обычный режим - обрабатываем все каналы медленно
            return await self._slow_process_new_channels(all_channels)[0]
        
        # ЭТАП 1: Быстрая загрузка кешированных каналов (секунды)
        fast_channels, new_channels = await self._fast_load_cached_channels(all_channels)
        
        # ЭТАП 2: Решение по новым каналам
        if self.skip_new_on_startup and new_channels:
            logger.warning(f"⏭️ ПРОПУСК НОВЫХ КАНАЛОВ: {len(new_channels)} каналов будут пропущены при запуске")
            logger.warning("💡 Для обработки новых каналов используйте команду /force_subscribe в боте")
            slow_channels = []
            rate_limited_channels = []
        else:
            # ЭТАП 2: Медленная обработка новых каналов (минуты)
            slow_channels, rate_limited_channels = await self._slow_process_new_channels(new_channels)
        
        # Объединяем результаты
        all_monitored = fast_channels + slow_channels
        self._rate_limited_channels = rate_limited_channels
        
        logger.info(f"🎉 ИТОГО ЗАГРУЖЕНО: {len(all_monitored)} каналов")
        logger.info(f"⚡ Быстро (кеш): {len(fast_channels)}")
        logger.info(f"🐌 Медленно (новые): {len(slow_channels)}")
        if self.skip_new_on_startup and new_channels:
            logger.info(f"⏭️ Пропущено новых: {len(new_channels)}")
        logger.info(f"⏳ Rate limit: {len(rate_limited_channels)}")
        
        return all_monitored

    async def _test_telethon_client(self):
        logger.info("🧪 Проверяем работу Telethon client...")
        try:
            me = await self.telegram_monitor.client.get_me()
            logger.info(f"✅ Telethon client активен: {me.first_name} (ID: {me.id})")
        except Exception as e:
            logger.error(f"❌ Ошибка Telethon client: {e}")

    async def _retry_rate_limited_subscriptions(self, rate_limited_channels: List[Dict[str, Any]]):
        if not rate_limited_channels:
            return
        
        logger.info(f"🔄 Повторная попытка подписки на {len(rate_limited_channels)} каналов с rate limit через {self.delay_retry_wait//60} минут...")
        await asyncio.sleep(self.delay_retry_wait)
        
        from telethon.tl.functions.channels import JoinChannelRequest
        
        success_retry = 0
        failed_retry = 0
        
        for channel_config in rate_limited_channels:
            try:
                username = channel_config['username']
                entity = await self.telegram_monitor.get_channel_entity(username)
                if not entity:
                    continue
                
                logger.info(f"🔄 Повторная попытка подписки на @{username}")
                await self.telegram_monitor.client(JoinChannelRequest(entity))
                
                await asyncio.sleep(self.delay_retry_subscribe)
                
                now_joined = await self.telegram_monitor.is_already_joined(entity)
                if now_joined:
                    logger.success(f"✅ Повторная подписка успешна: @{username}")
                    success_retry += 1
                    self.subscription_cache.add_channel_to_cache(username)
                else:
                    logger.warning(f"⚠️ Повторная подписка не подтверждена: @{username}")
                    failed_retry += 1
                
            except Exception as e:
                logger.error(f"❌ Ошибка повторной подписки на @{username}: {e}")
                failed_retry += 1
            
            await asyncio.sleep(self.delay_between_retries)
        
        logger.info(f"🔄 Результаты повторной подписки: ✅ {success_retry} | ❌ {failed_retry}")

    def _extract_wait_time(self, error_message: str) -> Optional[int]:
        """Извлекает время ожидания (в секундах) из сообщения об ошибке Telegram"""
        try:
            # Ищем паттерн "wait of X seconds" в сообщении
            match = re.search(r'wait of (\d+) seconds', error_message)
            if match:
                return int(match.group(1))
            
            # Альтернативные паттерны
            match = re.search(r'(\d+) seconds is required', error_message)
            if match:
                return int(match.group(1))
                
            return None
        except Exception:
            return None

    def get_monitoring_stats(self) -> Dict[str, Any]:
        return {
            'subscription_cache': self.subscription_cache.get_cache_stats(),
            'channels_config_path': self.channels_config_path,
            'processor_media_groups': len(self.message_processor.processed_media_groups)
        }
