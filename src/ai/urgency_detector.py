"""
Модуль для автоматического определения срочности новостей с помощью Ollama
"""

import asyncio
import re
import json
from typing import Dict, List, Optional, Tuple
from loguru import logger
import httpx


class UrgencyDetector:
    """Детектор срочности новостей на основе Ollama AI"""
    
    def __init__(self):
        self.ollama_client = None
        self.model_name = "qwen2.5:7b"
        self.ollama_url = "http://localhost:11434"
        self.urgent_keywords = {
            'emergency': [
                'пожар', 'взрыв', 'авария', 'катастрофа', 'теракт', 'стрельба',
                'землетрясение', 'наводнение', 'цунами', 'ураган', 'штorm',
                'чп', 'чрезвычайная ситуация', 'экстренно', 'срочно', 'alarm',
                'breaking', 'urgent', 'emergency', 'disaster', 'crash', 'explosion',
                # ДТП и транспорт
                'дтп', 'влетел', 'влетела', 'столкновение', 'лобовое', 'фура', 'грузовик',
                'переворот авто', 'сбил пешехода', 'наезд', 'столкнулись'
            ],
            'deaths_critical': [
                'погиб', 'погибла', 'погибли', 'погибших', 'смерть', 'умер', 'умерла',
                'жертвы', 'жертв', 'пострадавшие', 'скончался', 'скончалась',
                'тело', 'труп', 'мертвый', 'убит', 'убита', 'убиты'
            ],
            'politics_urgent': [
                'отставка', 'арест', 'задержание', 'обыск', 'санкции',
                'война', 'конфликт', 'переворот', 'революция', 'протесты',
                'митинг', 'демонстрация', 'выборы', 'референдум'
            ],
            'economy_urgent': [
                'дефолт', 'банкротство', 'крах', 'обвал', 'девальвация',
                'кризис', 'рецессия', 'инфляция', 'скачок цен', 'падение курса'
            ],
            'crime_urgent': [
                'убийство', 'похищение', 'ограбление', 'налет', 'захват',
                'заложники', 'террор', 'взятка', 'коррупция', 'мошенничество'
            ]
        }
        
    async def initialize(self):
        """Асинхронная инициализация Ollama AI"""
        try:
            logger.info("🤖 Подключение к Ollama AI для анализа срочности...")
            
            # Создаем HTTP клиент с увеличенным timeout
            self.ollama_client = httpx.AsyncClient(timeout=60.0)  # Увеличили до 60 секунд
            
            # Проверяем доступность Ollama сервера
            response = await self.ollama_client.get(f"{self.ollama_url}/api/tags")
            if response.status_code != 200:
                raise Exception(f"Ollama сервер недоступен: {response.status_code}")
            
            models = response.json().get("models", [])
            model_names = [model["name"] for model in models]
            
            if self.model_name not in model_names:
                logger.warning(f"⚠️ Модель {self.model_name} не найдена. Доступные: {model_names}")
                logger.info(f"🔄 Попытка загрузки модели {self.model_name}...")
                
                # Пытаемся загрузить модель
                pull_response = await self.ollama_client.post(
                    f"{self.ollama_url}/api/pull", 
                    json={"name": self.model_name}
                )
                
                if pull_response.status_code != 200:
                    raise Exception(f"Не удалось загрузить модель {self.model_name}")
                
                logger.info("✅ Модель успешно загружена")
            
            # Тестовый запрос для проверки работоспособности
            test_response = await self._make_ollama_request("Тест")
            if not test_response:
                raise Exception("Тестовый запрос к модели не прошел")
            
            logger.success(f"✅ Ollama AI успешно подключен (модель: {self.model_name})")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Ollama: {e}")
            logger.info("🔄 Бот продолжит работу без AI функций")
            if self.ollama_client:
                await self.ollama_client.aclose()
            self.ollama_client = None
    
    async def _make_ollama_request(self, prompt: str) -> Optional[str]:
        """Отправляет запрос к Ollama и возвращает ответ"""
        if not self.ollama_client:
            logger.warning("⚠️ Ollama клиент не инициализирован")
            return None
            
        try:
            logger.debug(f"📤 Отправляем запрос в Ollama: {prompt[:50]}...")
            
            response = await self.ollama_client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "num_predict": 100
                    }
                }
            )
            
            logger.debug(f"📥 Статус ответа Ollama: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                ollama_response = result.get("response", "").strip()
                logger.debug(f"✅ Получен ответ Ollama: {ollama_response}")
                return ollama_response
            else:
                logger.warning(f"⚠️ Ошибка Ollama запроса: {response.status_code}")
                logger.warning(f"📋 Содержимое ошибки: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка при запросе к Ollama: {e}")
            import traceback
            logger.error(f"📋 Трейс: {traceback.format_exc()}")
            return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Извлекает ключевые слова из текста"""
        text_lower = text.lower()
        found_keywords = []
        
        for category, keywords in self.urgent_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    found_keywords.append(f"{category}:{keyword}")
                    
        return found_keywords
    
    def _calculate_keyword_urgency(self, text: str) -> Tuple[float, List[str]]:
        """Базовый расчет срочности по ключевым словам"""
        keywords = self._extract_keywords(text)
        
        if not keywords:
            return 0.0, []
            
        # Весовые коэффициенты для разных категорий
        weights = {
            'emergency': 1.0,      # Максимальная срочность
            'crime_urgent': 0.8,   # Высокая срочность
            'politics_urgent': 0.6, # Средняя срочность
            'economy_urgent': 0.4   # Низкая срочность
        }
        
        total_score = 0.0
        for keyword in keywords:
            category = keyword.split(':')[0]
            total_score += weights.get(category, 0.2)
            
        # Нормализуем счет (максимум 1.0)
        urgency_score = min(total_score / 2, 1.0)
        
        return urgency_score, keywords
    
    async def _ai_classify_urgency(self, text: str) -> Dict:
        """AI классификация срочности с помощью Ollama"""
        if not self.ollama_client:
            return {'scores': [], 'ai_available': False}
            
        try:
            prompt = f"""Определи срочность новости по правилам СМИ. Ответь ТОЛЬКО одним словом:

ИГНОРИРОВАТЬ - если это РЕКЛАМА или СПАМ:
• Прямые призывы купить/заказать что-то
• Предложения услуг, товаров
• Контакты для связи (@username, телефоны)
• Слова: "реклама", "пишите", "обращайтесь", "заказать"
• Призывы подписаться на каналы

СРОЧНО - если есть ЖЕРТВЫ или НЕПОСРЕДСТВЕННАЯ УГРОЗА:
• Погибли/умерли люди (любое количество)  
• Пострадавшие в больнице
• Пожары, взрывы, обрушения
• Стрельба, теракты, захваты
• Стихийные бедствия
• Крупные аварии/катастрофы

ВАЖНО - события БЕЗ жертв, но общественно значимые:
• Политические решения, отставки
• Экономические изменения
• Аресты чиновников/известных лиц
• Забастовки, протесты

ОБЫЧНО - рутинные новости:
• Спорт, культура, развлечения
• Планы, анонсы мероприятий
• Статистика, отчеты

Новость: {text[:500]}

Ответ:"""

            response = await self._make_ollama_request(prompt)
            if not response:
                return {'scores': [], 'ai_available': False}
            
            # Парсим ответ
            response_lower = response.lower().strip()
            if "игнорировать" in response_lower or "игнор" in response_lower:
                urgency_level = "ignore"
                score = 0.0
            elif "срочно" in response_lower:
                urgency_level = "urgent"
                score = 0.9
            elif "важно" in response_lower:
                urgency_level = "important" 
                score = 0.6
            else:
                urgency_level = "normal"
                score = 0.2
            
            return {
                'labels': [urgency_level],
                'scores': [score],
                'ai_available': True,
                'raw_response': response
            }
            
        except Exception as e:
            logger.warning(f"⚠️ AI классификация недоступна: {e}")
            return {'scores': [], 'ai_available': False}
    
    async def _analyze_sentiment(self, text: str) -> Dict:
        """Анализ тональности с помощью Ollama"""
        if not self.ollama_client:
            return {'sentiment': 'neutral', 'confidence': 0.5, 'ai_available': False}
            
        try:
            prompt = f"""Определи тональность текста. Ответь ТОЛЬКО одним словом:

НЕГАТИВНАЯ - если текст о плохих событиях, проблемах, конфликтах
ПОЗИТИВНАЯ - если текст о хороших событиях, достижениях, успехах  
НЕЙТРАЛЬНАЯ - если текст нейтральный, информационный

Текст: {text[:300]}

Ответ:"""

            response = await self._make_ollama_request(prompt)
            if not response:
                return {'sentiment': 'neutral', 'confidence': 0.5, 'ai_available': False}
            
            # Парсим ответ
            response_lower = response.lower().strip()
            if "негативн" in response_lower:
                sentiment = "negative"
                confidence = 0.8
            elif "позитивн" in response_lower:
                sentiment = "positive"
                confidence = 0.8
            else:
                sentiment = "neutral"
                confidence = 0.6
            
            return {
                'sentiment': sentiment,
                'confidence': confidence,
                'ai_available': True,
                'raw_response': response
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Анализ тональности недоступен: {e}")
            return {'sentiment': 'neutral', 'confidence': 0.5, 'ai_available': False}
    
    def _detect_time_markers(self, text: str) -> float:
        """Определяет временные маркеры срочности"""
        urgent_time_patterns = [
            r'\b(только что|сейчас|прямо сейчас|в эту минуту)\b',
            r'\b(breaking|срочно|экстренно|внимание)\b',
            r'\b(just now|right now|urgent|breaking news)\b',
            r'\b\d{1,2}:\d{2}\b',  # Время вида 15:30
        ]
        
        score = 0.0
        for pattern in urgent_time_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                score += 0.2
                
        return min(score, 1.0)
    
    async def detect_urgency(self, news_text: str, source_channel: str = "") -> Dict:
        """
        Главная функция определения срочности новости
        
        Returns:
            Dict с полной информацией о срочности:
            {
                'urgency_level': 'urgent'|'important'|'normal',
                'urgency_score': float (0.0-1.0),
                'emoji': str,
                'keywords': List[str],
                'ai_classification': Dict,
                'sentiment': Dict,
                'reasoning': str
            }
        """
        try:
            # 1. Базовый анализ по ключевым словам
            keyword_score, keywords = self._calculate_keyword_urgency(news_text)
            
            # 2. AI классификация (если доступна)
            ai_result = await self._ai_classify_urgency(news_text)
            
            # 3. Анализ тональности
            sentiment = await self._analyze_sentiment(news_text)
            
            # 4. Временные маркеры
            time_score = self._detect_time_markers(news_text)
            
            # 5. AI-приоритетный расчет
            ai_level = None  # По умолчанию
            
            if ai_result['ai_available'] and ai_result['labels']:
                # AI - главный судья!
                ai_level = ai_result['labels'][0]
                ai_score = ai_result['scores'][0]
                
                # Базируемся на AI решении
                if ai_level == 'ignore':
                    # AI определил как спам/рекламу - возвращаем специальный статус
                    final_score = 0.0
                    urgency_level = 'ignore'
                    emoji = '🚫'
                elif ai_level == 'urgent':
                    final_score = max(0.8, ai_score)  # Минимум 0.8 для срочного
                    urgency_level = 'urgent'
                    emoji = '🔴'
                elif ai_level == 'important':
                    final_score = max(0.5, min(ai_score, 0.7))  # 0.5-0.7 для важного
                    urgency_level = 'important'
                    emoji = '🟡'
                else:
                    final_score = min(ai_score, 0.4)  # Максимум 0.4 для обычного
                    urgency_level = 'normal'
                    emoji = '⚪'
                
                # Ключевые слова только корректируют AI решение
                if keywords:
                    keyword_bonus = min(keyword_score * 0.2, 0.15)  # Максимум +15%
                    final_score = min(final_score + keyword_bonus, 1.0)
                
                # Временные маркеры усиливают срочность
                if time_score > 0 and urgency_level in ['urgent', 'important']:
                    final_score = min(final_score + time_score * 0.1, 1.0)
                
            else:
                # Fallback на ключевые слова если AI недоступен
                final_score = keyword_score + time_score * 0.3
                final_score = min(final_score, 1.0)
                
                if final_score >= 0.7:
                    urgency_level = 'urgent'
                    emoji = '🔴'
                elif final_score >= 0.4:
                    urgency_level = 'important' 
                    emoji = '🟡'
                else:
                    urgency_level = 'normal'
                    emoji = '⚪'
            
            # 7. Создаем объяснение решения  
            reasoning_parts = []
            if ai_level:
                ai_response = ai_result.get('raw_response', 'N/A')[:30]
                reasoning_parts.append(f"AI: {ai_level} ({ai_response}...)")
            elif ai_result['ai_available']:
                reasoning_parts.append("AI: недоступен")
            if keywords:
                reasoning_parts.append(f"Ключевые слова: {len(keywords)}")
            if time_score > 0:
                reasoning_parts.append("Временные маркеры")
                
            reasoning = f"Факторы: {', '.join(reasoning_parts) if reasoning_parts else 'Базовая оценка'}. Итог: {final_score:.2f}"
            
            result = {
                'urgency_level': urgency_level,
                'urgency_score': round(final_score, 3),
                'emoji': emoji,
                'keywords': keywords,
                'ai_classification': ai_result,
                'sentiment': sentiment,
                'reasoning': reasoning,
                'time_markers': time_score > 0
            }
            
            logger.debug(f"🎯 Анализ срочности: {urgency_level} ({final_score:.2f}) - {reasoning}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа срочности: {e}")
            # Fallback результат
            return {
                'urgency_level': 'normal',
                'urgency_score': 0.0,
                'emoji': '⚪',
                'keywords': [],
                'ai_classification': {'ai_available': False},
                'sentiment': {'ai_available': False},
                'reasoning': f'Ошибка анализа: {str(e)}',
                'time_markers': False
            }
    
    def format_urgent_message(self, original_text: str, urgency_data: Dict) -> str:
        """Форматирует сообщение с маркером срочности"""
        emoji = urgency_data['emoji']
        level = urgency_data['urgency_level']
        
        # Добавляем префикс в зависимости от уровня
        if level == 'urgent':
            prefix = f"{emoji} **СРОЧНО**"
        elif level == 'important':
            prefix = f"{emoji} **ВАЖНО**"
        else:
            prefix = f"{emoji}"
            
        return f"{prefix}\n\n{original_text}"
    
    async def get_statistics(self) -> Dict:
        """Получает статистику работы детектора"""
        return {
            'ai_models_loaded': self.sentiment_analyzer is not None,
            'total_keywords': sum(len(keywords) for keywords in self.urgent_keywords.values()),
            'categories': list(self.urgent_keywords.keys())
        }


# Глобальный экземпляр детектора
urgency_detector = UrgencyDetector()


async def initialize_urgency_detector():
    """Инициализация детектора срочности"""
    await urgency_detector.initialize()


async def analyze_news_urgency(text: str, source: str = "") -> Dict:
    """Быстрая функция для анализа срочности новости"""
    return await urgency_detector.detect_urgency(text, source)
