"""
📰 News Processor Module
Основной модуль обработки новостей
Координирует работу всех компонентов системы
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from loguru import logger

from .telegram_client import TelegramMonitor

from .database import DatabaseManager


class NewsProcessor:
    """Основной процессор новостей"""
    
    def __init__(self, database: DatabaseManager, 
                 telegram_bot=None, config: Dict = None, telegram_monitor: TelegramMonitor = None):
        self.telegram = telegram_monitor  
        self.telegram_bot = telegram_bot  
        self.database = database
        self.config = config or {}
        
        
        self.processed_channels = 0
        self.processed_messages = 0
        self.selected_news = 0
        self.errors_count = 0
        
        logger.info("📰 NewsProcessor инициализирован")
    
    async def process_channel(self, channel: Dict, is_vip: bool = False) -> Dict:
        """Обработка одного канала"""
        
        channel_username = channel.get('username')
        if not channel_username:
            logger.error("❌ Не указан username канала")
            return {'success': False, 'error': 'No username'}
        
        try:
            
            if not self.telegram:
                logger.warning(f"⚠️ Telegram мониторинг недоступен для {channel_username}")
                return {'success': False, 'error': 'Telegram мониторинг недоступен'}
            
            logger.info(f"📡 Обработка канала: {channel_username} (VIP: {is_vip})")
            
            
            messages = await self.telegram.get_recent_messages(
                channel_config=channel,
                limit=50 if is_vip else 30  
            )
            
            if not messages:
                logger.debug(f"📭 Нет новых сообщений в {channel_username}")
                return {'success': True, 'messages': 0, 'selected': 0}
            
            
            filtered_messages = await self.telegram.apply_prefilter(messages, self.config)
            
            if not filtered_messages:
                logger.debug(f"🔍 Все сообщения отфильтрованы в {channel_username}")
                return {'success': True, 'messages': len(messages), 'selected': 0}
            
            
            saved_count = await self.database.save_messages_batch(filtered_messages)
            
            
            
            latest_msg = max(filtered_messages, key=lambda m: m.get('date')) if filtered_messages else None
            messages_for_ai = [latest_msg] if latest_msg else []
            
            if messages_for_ai:
                
                logger.info(f"📝 Обрабатываем {len(messages_for_ai)} сообщений без AI анализа")
                
                
                await self.database.save_messages_batch(messages_for_ai)
                
                
                selected = messages_for_ai
                
                if selected:
                    
                    selected_ids = [msg['id'] for msg in selected]
                    await self.database.mark_as_selected(selected_ids)
                    
                    self.selected_news += len(selected)
                    
                    logger.info(f"✅ {channel_username}: {len(selected)} новостей отобрано (все сообщения)")
            
            self.processed_channels += 1
            self.processed_messages += len(messages)
            
            return {
                'success': True,
                'messages': len(messages),
                'filtered': len(filtered_messages),
                'analyzed': len(messages_for_ai) if messages_for_ai else 0,
                'selected': len(selected) if 'selected' in locals() else 0,
                'selected_news': selected if 'selected' in locals() else []
            }
            
        except Exception as e:
            self.errors_count += 1
            logger.error(f"❌ Ошибка обработки канала {channel_username}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def process_vip_channels_batch(self, vip_channels: List[Dict]) -> Dict:
        """Пакетная обработка VIP каналов"""
        
        logger.info(f"🔥 Обработка {len(vip_channels)} VIP каналов")
        
        results = []
        for channel in vip_channels:
            try:
                result = await self.process_channel(channel, is_vip=True)
                results.append(result)
                
                
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Ошибка обработки VIP канала {channel.get('username')}: {e}")
                results.append({'success': False, 'error': str(e)})
        
        
        successful = sum(1 for r in results if r.get('success'))
        total_selected = sum(r.get('selected', 0) for r in results if r.get('success'))
        
        logger.info(f"✅ VIP каналы: {successful}/{len(vip_channels)} успешно, {total_selected} новостей отобрано")
        
        
        all_selected_news = []
        for result in results:
            if result.get('success') and result.get('selected_news'):
                all_selected_news.extend(result['selected_news'])
        
        return {
            'processed': len(vip_channels),
            'successful': successful,
            'total_selected': total_selected,
            'selected_news': all_selected_news,
            'results': results
        }
    
    async def process_regular_channels_batch(self, regular_channels: List[Dict]) -> Dict:
        """Пакетная обработка обычных каналов"""
        
        logger.info(f"📰 Обработка {len(regular_channels)} обычных каналов")
        
        
        batch_size = self.config.get('max_concurrent_channels', 25)  
        total_results = []
        
        for i in range(0, len(regular_channels), batch_size):
            batch = regular_channels[i:i+batch_size]
            
            logger.info(f"📦 Обработка пакета {i//batch_size + 1}: {len(batch)} каналов")
            
            
            tasks = []
            for channel in batch:
                task = self.process_channel(channel, is_vip=False)
                tasks.append(task)
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"❌ Ошибка в пакете: {result}")
                    total_results.append({'success': False, 'error': str(result)})
                else:
                    total_results.append(result)
            
            
            await asyncio.sleep(5)
            
            
            try:
                import psutil
                memory_percent = psutil.virtual_memory().percent
                if memory_percent > 80:
                    logger.warning(f"⚠️ Высокое использование памяти: {memory_percent}%")
                    await asyncio.sleep(10)  
            except ImportError:
                pass
        
        
        successful = sum(1 for r in total_results if r.get('success'))
        total_selected = sum(r.get('selected', 0) for r in total_results if r.get('success'))
        
        logger.info(f"✅ Обычные каналы: {successful}/{len(regular_channels)} успешно, {total_selected} новостей отобрано")
        
        
        all_selected_news = []
        for result in total_results:
            if result.get('success') and result.get('selected_news'):
                all_selected_news.extend(result['selected_news'])
        
        return {
            'processed': len(regular_channels),
            'successful': successful,
            'total_selected': total_selected,
            'selected_news': all_selected_news,
            'results': total_results
        }
    
    async def generate_daily_digest(self) -> Optional[str]:
        """Генерация дневного дайджеста лучших новостей"""
        
        try:
            
            selected_news = await self.database.get_selected_news_today(
                limit=self.config.get('target_news_count', 999999)
            )
            
            if not selected_news:
                logger.info("📭 Нет отобранных новостей для дайджеста")
                return None
            
            
            sakhalin_news = [n for n in selected_news if n.get('channel_region') == 'sakhalin']
            kamchatka_news = [n for n in selected_news if n.get('channel_region') == 'kamchatka']
            
            
            digest_parts = []
            
            if sakhalin_news:
                digest_parts.append(f"🏝️ **САХАЛИН И КУРИЛЫ** ({len(sakhalin_news)} новостей)")
                for news in sakhalin_news[:5]:  
                    title = news.get('ai_analysis', {}).get('title', news['text'][:50] + '...')
                    score = news.get('ai_score', 0)
                    channel = news.get('channel_name', news.get('channel_username'))
                    digest_parts.append(f"• {title} (⭐ {score}/50) - {channel}")
            
            if kamchatka_news:
                digest_parts.append(f"\n🌋 **КАМЧАТКА** ({len(kamchatka_news)} новостей)")
                for news in kamchatka_news[:5]:  
                    title = news.get('ai_analysis', {}).get('title', news['text'][:50] + '...')
                    score = news.get('ai_score', 0)
                    channel = news.get('channel_name', news.get('channel_username'))
                    digest_parts.append(f"• {title} (⭐ {score}/50) - {channel}")
            
            
            total_processed = self.processed_messages
            total_channels = self.processed_channels
            
            digest_parts.extend([
                f"\n📊 **СТАТИСТИКА ЗА ДЕНЬ**",
                f"Обработано каналов: {total_channels}",
                f"Проанализировано сообщений: {total_processed}",
                f"Отобрано новостей: {len(selected_news)}",
                f"",
                f"🤖 Анализ выполнен ботом мониторинга новостей"
            ])
            
            digest = "\n".join(digest_parts)
            
            logger.info(f"📋 Дайджест создан: {len(selected_news)} новостей")
            return digest
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания дайджеста: {e}")
            return None
    
    async def send_to_output_channel(self, selected_news: List[Dict]) -> bool:
        """Отправка отобранных новостей через Telegram бота"""
        
        
        if not self.telegram_bot:
            logger.warning("⚠️ Telegram бот недоступен для отправки новостей")
            return False
        
        try:
            
            success = await self.telegram_bot.send_news_digest(selected_news)
            
            if success:
                logger.success(f"✅ Дайджест из {len(selected_news)} новостей отправлен через бота")
                return True
            else:
                logger.error("❌ Ошибка отправки дайджеста через бота")
                return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки в выходной канал: {e}")
            return False
    
    async def get_processing_statistics(self) -> Dict:
        """Получение статистики обработки"""
        
        db_stats = await self.database.get_statistics()
        
        return {
            'session_stats': {
                'processed_channels': self.processed_channels,
                'processed_messages': self.processed_messages,
                'selected_news': self.selected_news,
                'errors_count': self.errors_count
            },
            'database_stats': db_stats,
            'ai_stats': {}  
        }
    
    async def cleanup_session(self):
        """Очистка ресурсов сессии"""
        
        
        if self.telegram:
            await self.telegram.clear_cache()
        await self.database.clear_cache()
        
        
        self.processed_channels = 0
        self.processed_messages = 0
        self.selected_news = 0
        self.errors_count = 0
        
        logger.info("🧹 Очистка сессии NewsProcessor завершена")
