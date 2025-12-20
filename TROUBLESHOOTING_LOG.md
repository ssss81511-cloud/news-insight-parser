# 🔧 TROUBLESHOOTING LOG - News Insight Parser
## Дата: 2025-12-21

---

## 🎯 КАК ДОЛЖНА РАБОТАТЬ СИСТЕМА (PLAN)

### Полный цикл автоматизации:

```
1. ПАРСИНГ (POST /api/parse)
   ↓ Собирает посты с TechCrunch
   ↓ Сохраняет в БД (UniversalPost)
   ↓ Запускает AI анализ постов

2. АНАЛИТИКА (POST /api/run-insights)
   ↓ Анализирует посты за 30 дней
   ↓ Использует detect_topics() - LDA алгоритм
   ↓ Возвращает список тем с keywords
   ↓ НЕ сохраняет в БД (работает in-memory)

3. ВЫБОР ТЕМЫ (в AutoContentSystem.generate_and_post)
   ↓ TopicSelector.select_next_topic()
   ↓ Проверяет UsedTopic таблицу
   ↓ Выбирает неиспользованную тему

4. ГЕНЕРАЦИЯ КОНТЕНТА (ContentGenerator)
   ↓ Достаёт посты по выбранной теме
   ↓ Генерирует текст через GROQ API
   ↓ Сохраняет в GeneratedContent

5. ГЕНЕРАЦИЯ REEL (ReelGenerator)
   ↓ Создаёт картинку из контента
   ↓ Сохраняет в generated_reels/

6. ПУБЛИКАЦИЯ (TelegramPoster)
   ↓ Постит в @newsinsigth
   ↓ Обновляет GeneratedContent.published = True
   ↓ Сохраняет telegram_message_id

7. МАРКИРОВКА ТЕМЫ КАК ИСПОЛЬЗОВАННОЙ
   ↓ Сохраняет в UsedTopic
   ↓ Тема не будет повторно использована
```

---

## ❌ ОБНАРУЖЕННЫЕ ОШИБКИ

### Ошибка #1: JavaScript fetch без Content-Type header
**Время обнаружения:** 00:11:21
**Симптомы:**
```
Ошибка парсинга: Unexpected token '<', "<!doctype "... is not valid JSON
```

**Причина:**
- JavaScript не отправлял header `Content-Type: application/json`
- Flask endpoint делал `request.get_json()` без `force=True`
- Flask возвращал HTTP 415 с HTML страницей
- JavaScript пытался парсить HTML как JSON

**Исправление #1.1 (НЕПОЛНОЕ):**
```javascript
// templates/test_dashboard.html
fetch('/api/parse', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
})
```
**Статус:** ✅ Исправлено в коммите `dde50cc`

---

### Ошибка #2: Вызов несуществующего метода analyze_topics()
**Время обнаружения:** 00:19:18
**Симптомы:**
```
Аналитика завершена! Создано тем: 0
Ошибка: No suitable topic found
```

**Причина:**
- Endpoint `/api/run-insights` вызывал `insights_analyzer.analyze_topics()`
- Но в `InsightsAnalyzer` есть только метод `detect_topics()`
- Метод падал молча или возвращал None

**Исправление #2.1:**
```python
# app_v2.py:291
# Было:
topics = insights_analyzer.analyze_topics()

# Стало:
topics = insights_analyzer.detect_topics(lookback_days=30, n_topics=10, n_words=10)
```
**Статус:** ✅ Исправлено в коммите `047ea09`

---

### Ошибка #3: Импорт несуществующей модели Topic
**Время обнаружения:** 00:19:18
**Симптомы:**
```json
{
  "status": "error",
  "message": "cannot import name 'Topic' from 'storage.universal_models'"
}
```

**Причина:**
- Endpoint `/api/topics` пытался импортировать `Topic` model
- Модель `Topic` НЕ существует в `storage/universal_models.py`
- Темы генерируются динамически через `detect_topics()`, не сохраняются в БД

**Исправление #3.1:**
```python
# app_v2.py:694
# Было:
from storage.universal_models import Topic
topics = db.session.query(Topic).all()

# Стало:
topics = insights_analyzer.detect_topics(lookback_days=30, n_topics=10, n_words=10)
return jsonify(topics if topics else [])
```
**Статус:** ✅ Исправлено в коммите `047ea09`

---

## 🔍 ТЕКУЩИЙ СТАТУС

### ✅ Что работает:
- Flask сервер запущен на Render
- База данных PostgreSQL подключена
- 253 поста в базе
- Telegram бот подключен
- GitHub → Render auto-deploy работает

### ⏳ Что нужно протестировать:
- [ ] POST /api/parse - запуск парсеров
- [ ] POST /api/run-insights - создание тем
- [ ] GET /api/topics - получение списка тем
- [ ] POST /api/auto-generate - полный цикл генерации

### ❓ НАЙДЕННЫЕ ПРОБЛЕМЫ:

**Проблема А: TopicSelector пытается запросить несуществующую таблицу**
**Файл:** `automation/topic_selector.py:120`
**Код:**
```sql
SELECT topic_id, keywords, post_count, avg_importance, created_at
FROM topics  -- ❌ ЭТА ТАБЛИЦА НЕ СУЩЕСТВУЕТ!
WHERE post_count >= :min_posts
```

**Что происходит:**
1. TopicSelector._get_available_topics() пытается SELECT из таблицы `topics`
2. Таблица не существует → SQL ошибка
3. Exception caught → fallback к _generate_adhoc_topics()
4. _generate_adhoc_topics() ищет посты с ai_summary и ai_topics
5. Если постов без AI анализа нет → возвращает []
6. TopicSelector.select_next_topic() возвращает None
7. AutoContentSystem получает "No suitable topic found"

**Решение:**
TopicSelector должен использовать InsightsAnalyzer.detect_topics() вместо SQL запроса.

**План исправления:**
```python
# automation/topic_selector.py

class TopicSelector:
    def __init__(self, db_manager, insights_analyzer=None):
        self.db = db_manager
        self.insights_analyzer = insights_analyzer  # ← добавить

    def _get_available_topics(self, min_posts=3):
        # УДАЛИТЬ SQL запрос к topics table
        # ВМЕСТО ЭТОГО:
        if self.insights_analyzer:
            topics_data = self.insights_analyzer.detect_topics(
                lookback_days=30,
                n_topics=10,
                n_words=10
            )
            # Преобразовать формат detect_topics в формат TopicSelector
            return self._convert_insights_to_topics(topics_data, min_posts)
        else:
            # Fallback
            return self._generate_adhoc_topics(min_posts)
```

**Проблема В: Кэширование браузера**
- Пользователь должен делать Hard Refresh (Ctrl+F5)
- Иначе видит старую версию dashboard

**Решение:**
- Добавить cache-busting query params в HTML
- Или добавить no-cache headers

---

### Ошибка #4: TopicSelector пытается SELECT из несуществующей таблицы 'topics'
**Время обнаружения:** 00:19:18 (причина "No suitable topic found")
**Файл:** `automation/topic_selector.py:120-131`

**Причина:**
- TopicSelector._get_available_topics() делал SQL запрос к таблице `topics`
- Таблица не существует → Exception
- Fallback к _generate_adhoc_topics() требует ai_summary/ai_topics
- Если AI анализ не запущен → возвращает []
- select_next_topic() возвращает None

**Исправление #4.1:**
```python
# automation/topic_selector.py

# 1. Добавить insights_analyzer в __init__
def __init__(self, db_manager, insights_analyzer=None):
    self.db = db_manager
    self.insights_analyzer = insights_analyzer

# 2. Переписать _get_available_topics()
def _get_available_topics(self, min_posts=3):
    if self.insights_analyzer:
        # Использовать LDA topic modeling
        insights_topics = self.insights_analyzer.detect_topics(
            lookback_days=30,
            n_topics=10,
            n_words=10
        )
        # Конвертировать в формат TopicSelector
        return self._convert_topics(insights_topics, min_posts)
    else:
        # Fallback
        return self._generate_adhoc_topics(min_posts)
```

**Исправление #4.2:**
```python
# app_v2.py:86
# Было:
topic_selector = TopicSelector(db)

# Стало:
topic_selector = TopicSelector(db, insights_analyzer=insights_analyzer)
```
**Статус:** ✅ Исправлено в следующем коммите

---

## 📝 СЛЕДУЮЩИЕ ШАГИ

1. ✅ Создать этот лог
2. ✅ Проверить код TopicSelector - найдена попытка SELECT из topics
3. ✅ Переписать TopicSelector для использования InsightsAnalyzer
4. ✅ Обновить app_v2.py для передачи insights_analyzer
5. ⏳ Закоммитить и запушить исправления
6. ⏳ Подождать деплой на Render
7. ⏳ Протестировать полный цикл на дашборде

---

## 🚀 ИСТОРИЯ КОММИТОВ

1. `2bee8bf` - "fix: Add missing /api/run-insights endpoint for test dashboard"
2. `dde50cc` - "fix: Add Content-Type headers to POST requests in test dashboard"
3. `047ea09` - "fix: Use detect_topics() instead of analyze_topics() and fix /api/topics endpoint"

---

*Лог будет обновляться по мере обнаружения и исправления ошибок*
