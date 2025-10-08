

Интеллектуальные модули для автоматического анализа и обработки новостей.





Автоматически анализирует новости и определяет их срочность с помощью:

- **HuggingFace AI моделей** - sentiment analysis и text classification
- **Ключевых слов** - список критических терминов по категориям
- **Временных маркеров** - "срочно", "только что", время публикации
- **Комбинированного скоринга** - AI + правила + эвристики



| Уровень | Эмодзи | Описание | Примеры |
|---------|--------|----------|---------|
| **urgent** | 🔴 | Экстренные события | ЧП, теракты, катастрофы |
| **important** | 🟡 | Значимые новости | Политика, экономика |
| **normal** | ⚪ | Обычные новости | Спорт, развлечения |




```bash
pip install transformers torch accelerate sentencepiece
```


В `config/config.yaml`:
```yaml
ai:
  enabled: true
  urgency_detection:
    enabled: true
    min_score_urgent: 0.7
    min_score_important: 0.4
    use_huggingface: true
```


```bash
python test_urgency.py
```




```python
from src.ai.urgency_detector import analyze_news_urgency


result = await analyze_news_urgency("Срочно! Пожар в центре города!")

print(result['urgency_level'])  
print(result['urgency_score'])  
print(result['emoji'])          
print(result['reasoning'])      
```


```python
from src.ai.urgency_detector import urgency_detector

original_text = "Авария на МКАД, есть пострадавшие"
urgency_data = await urgency_detector.detect_urgency(original_text)

formatted = urgency_detector.format_urgent_message(original_text, urgency_data)

```




```python

if final_score >= 0.7:      
    urgency_level = 'urgent'
elif final_score >= 0.4:    
    urgency_level = 'important'
else:                       
    urgency_level = 'normal'
```


```python
urgent_keywords = {
    'emergency': ['пожар', 'взрыв', 'авария', 'катастрофа'],
    'politics_urgent': ['отставка', 'арест', 'война'],
    'economy_urgent': ['дефолт', 'банкротство', 'кризис'],
    'crime_urgent': ['убийство', 'похищение', 'террор']
}
```


```python

sentiment_model = "cardiffnlp/twitter-xlm-roberta-base-sentiment"


classifier_model = "facebook/bart-large-mnli"
```




- **RAM**: 2-4 GB для моделей
- **CPU/GPU**: Torch автоматически определяет CUDA
- **Время анализа**: 0.5-2 сек на новость


- При недоступности AI → базовый анализ по ключевым словам
- При ошибке модели → продолжение работы без AI
- Кэширование моделей для ускорения



1. **Извлечение ключевых слов** из текста
2. **AI классификация** через HuggingFace
3. **Анализ тональности** (негативные новости часто срочные)
4. **Поиск временных маркеров** ("срочно", "сейчас")
5. **Комбинированный скоринг** всех факторов
6. **Присвоение уровня** и эмодзи
7. **Форматирование** сообщения




```bash

export LOG_LEVEL=DEBUG


tail -f logs/news_monitor.log | grep "🤖\|🎯\|🔴\|🟡"
```


```python
stats = await urgency_detector.get_statistics()
print(f"AI модели: {stats['ai_models_loaded']}")
print(f"Ключевых слов: {stats['total_keywords']}")
```


```bash

python test_urgency.py


python -c "
import asyncio
from src.ai.urgency_detector import analyze_news_urgency
result = asyncio.run(analyze_news_urgency('Ваш текст новости'))
print(result)
"
```




AI модуль автоматически интегрируется в `MessageProcessor`:
- Анализирует каждую новость
- Добавляет эмодзи и префиксы
- Сохраняет метаданные в БД
- Логирует результаты анализа


```bash

systemctl status news-monitor-*
journalctl -u news-monitor-* | grep "🤖"


grep "🔴 СРОЧНАЯ" logs/*.log | wc -l
```



- 📝 **Автосаммари** - краткие изложения длинных статей
- 🔍 **Поиск дубликатов** - обнаружение повторяющихся новостей
- 🏷️ **Автотеги** - извлечение ключевых тем
- 📊 **Аналитика трендов** - выявление популярных тем
- 🌐 **Мультиязычность** - поддержка других языков
