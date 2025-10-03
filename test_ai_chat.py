"""
Быстрый тест AI чата
"""
import asyncio
from src.handlers.commands.ai_chat import AIChatHandler

class MockBot:
    def __init__(self):
        self.monitor_bot = None
        
    async def send_message(self, text):
        print(f"🤖 Бот отправил: {text}")

async def test_ai_chat():
    print("🧪 ТЕСТ AI ЧАТА")
    print("=" * 40)
    
    # Создаем мок бота  
    mock_bot = MockBot()
    ai_chat = AIChatHandler(mock_bot)
    
    # Инициализируем
    print("🔄 Инициализация AI чата...")
    await ai_chat.initialize()
    
    # Тестируем вопросы
    test_messages = [
        {"text": "/ask Привет, как дела?"},
        {"text": "AI: Какая столица России?"},
        {"text": "ИИ: Напиши короткий стих про осень"},
        {"text": "/ask "},  # Пустой вопрос
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n📝 ТЕСТ {i}: {message['text']}")
        await ai_chat.handle_ai_question(message)
        await asyncio.sleep(1)
    
    print("\n" + "=" * 40)
    print("✅ Тест завершен!")

if __name__ == "__main__":
    asyncio.run(test_ai_chat())
