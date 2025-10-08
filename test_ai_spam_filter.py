"""
Тест AI фильтра рекламы/спама
"""
import asyncio
from src.ai.urgency_detector import analyze_news_urgency, initialize_urgency_detector

async def test_ai_spam_filter():
    print("🧪 ТЕСТ AI ДЕТЕКТОРА РЕКЛАМЫ (с эмодзи 🚫)")
    print("=" * 60)
    
    
    print("🔄 Инициализация AI детектора...")
    await initialize_urgency_detector()
    print("✅ AI детектор инициализирован\n")
    
    
    test_messages = [
        
        ("Представьте, что прямо здесь — ваша реклама. Если вы делаете классный продукт и хотите, чтобы об этом узнали — пишите: @reklama_newsmedia2.", "IGNORE"),
        ("Продам квартиру в центре города, недорого! Звоните +7-999-123-45-67", "IGNORE"),
        ("🎉 АКЦИЯ! Скидки до 90% на все товары! Заказывайте прямо сейчас!", "IGNORE"),
        ("Требуется менеджер по продажам. Высокая зарплата. Обращайтесь: @work_channel", "IGNORE"),
        ("Предлагаю услуги по ремонту квартир. Качественно и недорого. Пишите в личку", "IGNORE"),
        
        
        ("Три человека погибли в ДТП на трассе Иркутск-Чита. Водитель потерял управление", "URGENT"),
        ("В центре Москвы произошел взрыв в жилом доме, есть пострадавшие", "URGENT"),
        ("Мэр города объявил о повышении тарифов на общественный транспорт с января", "IMPORTANT"),
        ("Завтра в городе ожидается дождь с переходом в снег, температура до -5", "NORMAL"),
        ("Местная футбольная команда выиграла матч со счетом 3:1", "NORMAL"),
    ]
    
    print("📝 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    
    success_count = 0
    total_count = len(test_messages)
    
    for i, (message, expected) in enumerate(test_messages, 1):
        try:
            result = await analyze_news_urgency(message, f"test_channel_{i}")
            actual = result['urgency_level'].upper()
            
            
            if (expected == "IGNORE" and actual == "IGNORE") or \
               (expected != "IGNORE" and actual != "IGNORE"):
                status = "✅"
                success_count += 1
            else:
                status = "❌"
            
            
            print(f"\n{i:2d}. {status} AI: {actual:8s} | Ожидался: {expected:8s}")
            print(f"     📰 {message[:80]}{'...' if len(message) > 80 else ''}")
            
            if status == "❌":
                print(f"     ⚠️  Ошибка! Ожидалось: {expected}, получили: {actual}")
                
        except Exception as e:
            print(f"\n{i:2d}. ❌ ОШИБКА: {e}")
            print(f"     📰 {message[:80]}...")
    
    print(f"\n" + "=" * 60)
    print(f"📊 ИТОГО: {success_count}/{total_count} правильно определены ({success_count/total_count*100:.1f}%)")
    
    if success_count == total_count:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! AI отлично определяет рекламу!")
    elif success_count >= total_count * 0.8:
        print("✅ ХОРОШИЙ РЕЗУЛЬТАТ! Есть небольшие неточности в определении")
    else:
        print("⚠️  ТРЕБУЮТСЯ ДОРАБОТКИ в AI промпте")

if __name__ == "__main__":
    asyncio.run(test_ai_spam_filter())
