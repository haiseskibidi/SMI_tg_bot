# 🤖 AI Модули для новостного бота

Интеллектуальные модули для автоматического анализа и обработки новостей.

## 🎯 Функции

### 🚨 Определение срочности (`urgency_detector.py`)

Автоматически анализирует новости и определяет их срочность с помощью:

- **HuggingFace AI моделей** - sentiment analysis и text classification
- **Ключевых слов** - список критических терминов по категориям
- **Временных маркеров** - "срочно", "только что", время публикации
- **Комбинированного скоринга** - AI + правила + эвристики

### 📊 Уровни срочности

| Уровень | Эмодзи | Описание | Примеры |
|---------|--------|----------|---------|
| **urgent** | 🔴 | Экстренные события | ЧП, теракты, катастрофы |
| **important** | 🟡 | Значимые новости | Политика, экономика |
| **normal** | ⚪ | Обычные новости | Спорт, развлечения |

## ⚙️ Установка

### 1. Зависимости
```bash
pip install transformers torch accelerate sentencepiece
```

### 2. Конфигурация
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

### 3. Тестирование
```bash
python test_urgency.py
```

## 🔧 Использование

### Автоматический анализ
```python
from src.ai.urgency_detector import analyze_news_urgency

# Анализ новости
result = await analyze_news_urgency("Срочно! Пожар в центре города!")

print(result['urgency_level'])  # 'urgent'
print(result['urgency_score'])  # 0.85
print(result['emoji'])          # '🔴'
print(result['reasoning'])      # 'Факторы: Ключевые слова: 2, Временные маркеры'
```

### Форматирование сообщений
```python
from src.ai.urgency_detector import urgency_detector

original_text = "Авария на МКАД, есть пострадавшие"
urgency_data = await urgency_detector.detect_urgency(original_text)

formatted = urgency_detector.format_urgent_message(original_text, urgency_data)
# Результат: "🔴 **🚨 СРОЧНО 🚨**\n\nАвария на МКАД, есть пострадавшие"
```

## 🎛️ Настройка

### Пороги срочности
```python
# В urgency_detector.py
if final_score >= 0.7:      # Срочные
    urgency_level = 'urgent'
elif final_score >= 0.4:    # Важные  
    urgency_level = 'important'
else:                       # Обычные
    urgency_level = 'normal'
```

### Ключевые слова
```python
urgent_keywords = {
    'emergency': ['пожар', 'взрыв', 'авария', 'катастрофа'],
    'politics_urgent': ['отставка', 'арест', 'война'],
    'economy_urgent': ['дефолт', 'банкротство', 'кризис'],
    'crime_urgent': ['убийство', 'похищение', 'террор']
}
```

### AI модели
```python
# Анализ тональности (поддерживает русский язык)
sentiment_model = "cardiffnlp/twitter-xlm-roberta-base-sentiment"

# Классификация текста
classifier_model = "facebook/bart-large-mnli"
```

## 📈 Производительность

### Системные требования
- **RAM**: 2-4 GB для моделей
- **CPU/GPU**: Torch автоматически определяет CUDA
- **Время анализа**: 0.5-2 сек на новость

### Fallback логика
- При недоступности AI → базовый анализ по ключевым словам
- При ошибке модели → продолжение работы без AI
- Кэширование моделей для ускорения

## 🔍 Алгоритм работы

1. **Извлечение ключевых слов** из текста
2. **AI классификация** через HuggingFace
3. **Анализ тональности** (негативные новости часто срочные)
4. **Поиск временных маркеров** ("срочно", "сейчас")
5. **Комбинированный скоринг** всех факторов
6. **Присвоение уровня** и эмодзи
7. **Форматирование** сообщения

## 🐛 Отладка

### Логи
```bash
# Включение debug логов
export LOG_LEVEL=DEBUG

# Просмотр AI анализа
tail -f logs/news_monitor.log | grep "🤖\|🎯\|🔴\|🟡"
```

### Статистика
```python
stats = await urgency_detector.get_statistics()
print(f"AI модели: {stats['ai_models_loaded']}")
print(f"Ключевых слов: {stats['total_keywords']}")
```

### Тестирование
```bash
# Полный тест системы
python test_urgency.py

# Тест конкретной новости
python -c "
import asyncio
from src.ai.urgency_detector import analyze_news_urgency
result = asyncio.run(analyze_news_urgency('Ваш текст новости'))
print(result)
"
```

## 🚀 Производственное использование

### Интеграция в мониторинг
AI модуль автоматически интегрируется в `MessageProcessor`:
- Анализирует каждую новость
- Добавляет эмодзи и префиксы
- Сохраняет метаданные в БД
- Логирует результаты анализа

### Мониторинг AI
```bash
# Проверка работы AI
systemctl status news-monitor-*
journalctl -u news-monitor-* | grep "🤖"

# Статистика срочных новостей
grep "🔴 СРОЧНАЯ" logs/*.log | wc -l
```

## 🔮 Планы развития

- 📝 **Автосаммари** - краткие изложения длинных статей
- 🔍 **Поиск дубликатов** - обнаружение повторяющихся новостей
- 🏷️ **Автотеги** - извлечение ключевых тем
- 📊 **Аналитика трендов** - выявление популярных тем
- 🌐 **Мультиязычность** - поддержка других языков
