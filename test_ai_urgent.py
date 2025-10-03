"""
Тест AI анализа срочности
"""
import asyncio
from src.ai.urgency_detector import analyze_news_urgency, initialize_urgency_detector

async def test_urgent_news():
    # Инициализируем AI детектор
    print("🔄 Инициализация AI детектора...")
    await initialize_urgency_detector()
    print("✅ AI детектор инициализирован\n")
    """Тестируем срочные новости"""
    
    test_cases = [
        "Три человека погибли в ДТП на трассе «Иркутск-Чита»",
        "Легковушка влетела в стоявшую на трассе в Забайкалье фуру - погибли три человека", 
        "В центре Москвы произошел взрыв",
        "Пожар в жилом доме, есть пострадавшие",
        "Задержаны двое граждан Молдовы с крупной партией мефедрона", 
        "Около 150 тонн мусора собрали возле Карповки"
    ]
    
    print("🧪 ТЕСТ AI АНАЛИЗА СРОЧНОСТИ\n" + "="*50)
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n📰 ТЕСТ {i}: {text[:60]}...")
        
        try:
            result = await analyze_news_urgency(text, "test_channel")
            
            print(f"   🎯 Уровень: {result['urgency_level']}")
            print(f"   📊 Скор: {result['urgency_score']:.2f}")
            print(f"   😊 Эмодзи: {result['emoji']}")
            print(f"   🔑 Ключевые слова: {result.get('keywords', [])}")
            
            if 'ai_classification' in result:
                ai_data = result['ai_classification']
                print(f"   🔍 AI доступен: {ai_data.get('ai_available', 'N/A')}")
                if 'raw_response' in ai_data:
                    print(f"   🤖 AI ответ: {ai_data['raw_response']}")
                else:
                    print(f"   ❌ AI ответ отсутствует: {ai_data}")
            else:
                print("   ❌ ai_classification отсутствует в результате")
                    
        except Exception as e:
            print(f"   ❌ ОШИБКА: {e}")
            import traceback
            print(f"   📋 Трейс: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_urgent_news())
