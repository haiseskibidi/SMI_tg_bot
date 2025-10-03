"""
AI чат - общение с нейросетью прямо в группе
"""
import asyncio
from typing import Dict, Any, Optional
from loguru import logger
import httpx

class AIChatHandler:
    def __init__(self, bot):
        self.bot = bot
        self.ollama_client = None
        self.model_name = "qwen2.5:7b"
        self.ollama_url = "http://localhost:11434"
        self.chat_history = {}  # Простое хранение истории диалогов
        self.max_history = 6    # Максимум последних сообщений    
        
    async def initialize(self):
        """Инициализируем прямое подключение к Ollama"""
        try:
            logger.info("🤖 Инициализация AI чата - подключение к Ollama...")
            
            # Создаем собственный HTTP клиент для Ollama
            self.ollama_client = httpx.AsyncClient(timeout=60.0)
            
            # Проверяем доступность Ollama
            response = await self.ollama_client.get(f"{self.ollama_url}/api/tags")
            if response.status_code != 200:
                raise Exception(f"Ollama сервер недоступен: {response.status_code}")
            
            # Проверяем наличие модели
            models = response.json().get("models", [])
            model_names = [model["name"] for model in models]
            
            if self.model_name not in model_names:
                logger.warning(f"⚠️ Модель {self.model_name} не найдена для AI чата")
                logger.info(f"📋 Доступные модели: {model_names}")
            
            logger.success(f"✅ AI чат успешно подключен к Ollama (модель: {self.model_name})")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации AI чата: {e}")
            if self.ollama_client:
                await self.ollama_client.aclose()
            self.ollama_client = None
    
    async def handle_ai_question(self, message: Optional[Dict[str, Any]]) -> None:
        """Обработка вопросов к AI"""
        try:
            if not message or 'text' not in message:
                await self.bot.send_message("❌ Сообщение пустое")
                return
                
            text = message['text'].strip()
            
            # Убираем префикс команды
            if text.startswith('/ask '):
                question = text[5:].strip()
            elif text.lower().startswith('ai:'):
                question = text[3:].strip()
            elif text.lower().startswith('ии:'):
                question = text[3:].strip()
            else:
                # Если вызвали команду без текста
                await self.bot.send_message(
                    "🤖 <b>AI Помощник</b>\n\n"
                    "Задайте вопрос одним из способов:\n"
                    "• <code>/ask ваш вопрос</code>\n"
                    "• <code>AI: ваш вопрос</code>\n"
                    "• <code>ИИ: ваш вопрос</code>\n\n"
                    "Например: <code>/ask Какая погода в Москве?</code>"
                )
                return
                
            if not question:
                await self.bot.send_message("❓ А что спросить-то хотели?")
                return
            
            chat_id = message.get("chat", {}).get("id")
            
            # Показываем индикатор "печатает..."
            await self.bot.send_chat_action(chat_id, "typing")
            
            # Отправляем вопрос в AI
            answer = await self._ask_ai(question, chat_id)
            
            if answer:
                await self.bot.send_message(answer, chat_id=chat_id)
            else:
                await self.bot.send_message(
                    "😔 <b>Арнольд временно недоступен</b>\n\n"
                    "Попробуйте позже или проверьте, что Ollama запущен",
                    chat_id=chat_id
                )
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки AI вопроса: {e}")
            await self.bot.send_message("❌ Произошла ошибка при обработке вопроса")
    
    def _add_to_history(self, chat_id: int, user_message: str, ai_response: str):
        """Добавляет сообщение в историю диалога"""
        if chat_id not in self.chat_history:
            self.chat_history[chat_id] = []
        
        self.chat_history[chat_id].append({
            "user": user_message,
            "assistant": ai_response
        })
        
        # Простое FIFO ограничение - удаляем старые сообщения
        if len(self.chat_history[chat_id]) > self.max_history:
            self.chat_history[chat_id] = self.chat_history[chat_id][-self.max_history:]
    
    def _get_history_context(self, chat_id: int) -> str:
        """Формирует контекст из истории диалога"""
        if chat_id not in self.chat_history or not self.chat_history[chat_id]:
            return ""
        
        history_text = "\nPREVIOUS CONVERSATION CONTEXT:\n"
        for msg in self.chat_history[chat_id]:
            history_text += f"User: {msg['user']}\n"
            history_text += f"Арнольд: {msg['assistant']}\n\n"
        
        return history_text
    
    def clear_chat_history(self, chat_id: int):
        """Очищает историю диалога для указанного чата"""
        if chat_id in self.chat_history:
            del self.chat_history[chat_id]
            logger.info(f"🧹 Очищена история диалога для чата {chat_id}")

    async def _ask_ai(self, question: str, chat_id: Optional[int] = None) -> Optional[str]:
        """Отправляет вопрос в AI и получает ответ"""
        try:
            if not self.ollama_client:
                logger.warning("⚠️ Ollama клиент недоступен для AI чата")
                return None
            
            prompt = f"""You are Арнольд, an AI analyst assistant for SMI#1 media holding. You help journalists with analysis, ideas, and editorial tasks.

CRITICAL: Respond ONLY in Russian. Never use Chinese or other languages.
IMPORTANT: Never use letter "ё" - always write "е" instead (елки не "ёлки", все не "всё")

🎯 ГЛАВНОЕ ПРАВИЛО:
- Если пользователь просто задает вопрос (без слов "заголовок", "байты", "новость"), отвечай как обычный помощник
- Создавай заголовки и байты ТОЛЬКО при явном запросе

🔍 ТВОИ ФУНКЦИИ:
- Отвечать на вопросы о любых темах
- Объяснять сложные понятия простым языком  
- Помогать с анализом текстов (факты, цифры, источники)
- Создавать заголовки и байты только по запросу

PERSONALITY: Ты Арнольд - умный, полезный помощник. Отвечай по существу, кратко и понятно.

{self._get_history_context(chat_id) if chat_id else ""}

Вопрос пользователя: {question}

Твой ответ на русском языке:"""

            response = await self._make_ollama_request(prompt)
            
            if response:
                # Ограничиваем длину ответа для Telegram (4096 символов максимум)
                if len(response) > 4000:
                    response = response[:3950] + "\n\n... (ответ сокращен)"
                
                # Сохраняем в историю диалога
                if chat_id:
                    self._add_to_history(chat_id, question, response)
                    
                return response
            else:
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка запроса к AI: {e}")
            return None
    
    async def _make_ollama_request(self, prompt: str) -> Optional[str]:
        """Отправляет запрос к Ollama и возвращает ответ"""
        if not self.ollama_client:
            return None
            
        try:
            response = await self.ollama_client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Чуть больше креативности для чата
                        "top_p": 0.9,
                        "num_predict": 800   
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                logger.warning(f"⚠️ Ошибка Ollama запроса в AI чате: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка при запросе к Ollama в AI чате: {e}")
            return None
    
    async def handle_ai_info(self, message: Optional[Dict[str, Any]]) -> None:
        """Показывает информацию об AI системе"""
        try:
            ai_status = "🟢 Активен" if self.ollama_client else "🔴 Недоступен"
            
            info_text = (
                f"🤖 <b>Арнольд - AI Аналитик SMI#1</b>\n\n"
                f"📊 <b>Статус:</b> {ai_status}\n"
                f"🧠 <b>Модель:</b> {self.model_name}\n"
                f"🔍 <b>Роль:</b> Помощник-аналитик для журналистов\n\n"
                f"🎯 <b>Основные функции:</b>\n"
                f"  • 🔍 Анализ текстов (факты, цифры, источники)\n"
                f"  • 💡 Генерация идей (заголовки, хештеги)\n"
                f"  • 📱 Создание байтов (реакции к новостям)\n"
                f"  • ⚡ Быстрые проверки (ошибки, запрещенные слова)\n"
                f"  • 📝 Редакторская помощь (объяснения, форматирование)\n"
                f"  • 🌐 Справки по медиа-терминам\n\n"
                f"💬 <b>Примеры запросов:</b>\n"
                f"  <code>Найди все числа в этом тексте</code>\n"
                f"  <code>Есть ли запрещенные слова?</code>\n"
                f"  <code>Придумай байты для новости про юристов</code>\n"
                f"  <code>Придумай заголовок, 3 варианта</code>\n"
                f"  <code>Сделай реакции к посту про погоду</code>\n"
                f"  <code>Какие источники упомянуты?</code>\n\n"
                f"🔍 <b>Форматы ответов:</b>\n"
                f"  • <b>Заголовки:</b>\n"
                f"    🏥 Открыли выставку в больнице Якутска\n"
                f"    🌲 Подрядчики повредили деревья в Елизово\n\n"
                f"  • <b>Байты (только из 41 разрешенного эмодзи):</b>\n"
                f"    😱 — многострадальные деревья;\n"
                f"    👍 — надеемся на восстановление;\n"
                f"    <i>Список: ⭐ ❤️ 👍 😡 😱 🌙 😔 🤓 💔 😐 🔥 🐳 🎉 😃 👎 👏 😬 😁 🤦 🎭 🤮 👑 😊 😈 😢 😍 😎 💯 😂 ⚡ 🏆 💖 😄 👿 😭 💜 👻 👀 🤔 🙄 🤯</i>\n\n"
                f"💭 <b>Память диалогов:</b>\n"
                f"  • Арнольд помнит последние {self.max_history} сообщений\n"
                f"  • Используйте <code>/clear_ai</code> для очистки истории\n\n"
                f"❌ <b>НЕ делает:</b> полные рерайты новостей (много ошибок в тексте)\n\n"
                f"ℹ️ <code>/ai_info</code> - это справка"
            )
            
            await self.bot.send_message(info_text)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения AI информации: {e}")
            await self.bot.send_message("❌ Ошибка получения информации об AI")

    async def cleanup(self):
        """Очистка ресурсов при завершении работы"""
        if self.ollama_client:
            await self.ollama_client.aclose()
            logger.info("🧹 Арнольд: HTTP клиент закрыт")
