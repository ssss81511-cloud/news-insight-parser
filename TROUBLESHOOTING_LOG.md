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

---

### Ошибка #5: Telegram не настроен на Render
**Время обнаружения:** 2025-12-21 (проверка API)
**Endpoint:** GET /api/automation-status

**Результат:**
```json
{
  "enabled": false,
  "telegram_enabled": false,
  "schedule": null,
  "jobs": []
}
```

**Причина:**
Environment variables не установлены на Render:
- `TELEGRAM_BOT_TOKEN` - не установлен
- `TELEGRAM_CHANNEL_ID` - не установлен
- `AUTO_GENERATE_ENABLED` - не установлен

**Решение:**
Пользователь должен зайти в Render Dashboard и добавить:
```
TELEGRAM_BOT_TOKEN=8568827955:AAFagsX78hhOuWUEafW7DedgT64oRMhAH3Q
TELEGRAM_CHANNEL_ID=@newsinsigth
AUTO_GENERATE_ENABLED=true
AUTO_GENERATE_HOUR=9
GROQ_API_KEY=(проверить установлен ли)
```

**Статус:** ⏳ Требует действий пользователя

---

### Ошибка #6: Content generation failed
**Время обнаружения:** 2025-12-21 (тест POST /api/auto-generate)
**Симптомы:**
```json
{
  "error": "Content generation failed",
  "topic": {"keywords": ["discussion","link","ai","new","make"], "post_count": 15}
}
```

**Что работает:**
✅ TopicSelector нашёл тему с 15 постами
✅ detect_topics() работает (GET /api/topics возвращает темы)
✅ 304 поста в БД

**Что НЕ работает:**
❌ ContentGenerator.generate_from_topic() падает

**Возможные причины:**
1. GROQ_API_KEY не установлен на Render
2. Посты не имеют достаточно контента
3. Ошибка в коде ContentGenerator

**Решение:**
Нужны логи с Render чтобы увидеть точную ошибку ContentGenerator.
Или пользователь должен проверить что GROQ_API_KEY установлен.

**Статус:** ⏳ Требуется проверка env vars на Render

---

### Ошибка #7: AutoContentSystem вызывает неправильный метод ContentGenerator
**Время обнаружения:** 2025-12-21 (после установки env vars)
**Файл:** `automation/auto_content_system.py:290`

**Симптомы:**
```json
{
  "error": "Content generation failed",
  "topic": {"keywords": ["discussion","link","ai"], "post_count": 15}
}
```

**Причина:**
```python
# automation/auto_content_system.py:290
self.content_generator.generate_from_topic(
    posts=posts,  # ← НЕПРАВИЛЬНО! Параметр не существует
    format_type=...,
    language=...,
    tone=...
)

# analyzers/content_generator.py:129
def generate_from_topic(self,
                       topic_keywords: List[str],  # ← Ожидает topic_keywords!
                       lookback_days: int = 7,
                       ...)
```

**Mismatch:**
- AutoContentSystem передаёт `posts=posts` (список объектов UniversalPost)
- Но generate_from_topic() ожидает `topic_keywords` (список строк)

**Решение:**
AutoContentSystem должен вызывать `generate_from_cluster()` вместо `generate_from_topic()`:

```python
# automation/auto_content_system.py:290
# БЫЛО:
return self.content_generator.generate_from_topic(
    posts=posts,
    format_type=...,
    language=...,
    tone=...
)

# ДОЛЖНО БЫТЬ:
return self.content_generator.generate_from_cluster(
    cluster_posts=posts,
    format_type=self.config['content_format'],
    tone=self.config['content_tone'],
    language=self.config['content_language']
)
```

**Статус:** ✅ Исправлено в следующем коммите

---

### Ошибка #8: Telegram connection pool timeout
**Время обнаружения:** 2025-12-21 (после исправления ошибки #7)
**Файл:** `automation/telegram_poster.py:44`

**Симптомы:**
```json
{
  "error": "Telegram posting failed: Pool timeout: All connections in the connection pool are occupied."
}
```

**Причина:**
```python
# automation/telegram_poster.py:44
self.bot = Bot(token=bot_token)  # ← Default httpx client
# Default connection_pool_size = 1
# Default pool_timeout = 5.0 seconds
```

python-telegram-bot использует httpx под капотом.
По умолчанию:
- `connection_pool_size=1` - только 1 соединение
- `pool_timeout=5.0` - 5 секунд ожидания

При отправке фото + текста нужно минимум 2 соединения.

**Решение:**
```python
# automation/telegram_poster.py:48
from telegram.request import HTTPXRequest

request = HTTPXRequest(
    connection_pool_size=20,  # Увеличено с 1 до 20
    connect_timeout=30.0,
    read_timeout=30.0,
    write_timeout=30.0,
    pool_timeout=30.0  # Увеличено с 5.0 до 30.0
)

self.bot = Bot(token=bot_token, request=request)
```

**Статус:** ✅ Исправлено в коммите 3afbd78

---

### Ошибка #9: Test dashboard застревает на шаге 3 и прыгает к шагу 6
**Время обнаружения:** 2025-12-21 (тестирование пользователя)
**Файл:** `templates/test_dashboard.html`

**Симптомы:**
- Шаг 3 "Выбор уникальной темы" горит желтым и застревает
- Затем сразу прыгает к шагу 6
- Шаги 4 и 5 пропускаются

**Причина:**
```javascript
// templates/test_dashboard.html:528
async function testAutoGenerate() {
    updateProgress(10, 3, 'active');  // ← Активирует шаг 3

    const response = await fetch('/api/auto-generate', { method: 'POST' });
    const data = await response.json();

    if (data.status === 'success') {
        updateProgress(100, 6, 'completed');  // ← Сразу прыгает к шагу 6!
    }
}
```

API `/api/auto-generate` делает всё за один вызов:
- Выбор темы (step 3)
- Генерация контента (step 4)
- Генерация картинки (step 5)
- Публикация в Telegram (step 6)

Но JavaScript не знает о промежуточных шагах.

**Решение:**
Добавить промежуточные обновления прогресса:
```javascript
async function testAutoGenerate() {
    updateProgress(10, 3, 'active');
    log('[3/6] Выбор уникальной темы...', 'info');

    updateProgress(25, 4, 'active');
    log('[4/6] Генерация контента...', 'info');

    updateProgress(50, 5, 'active');
    log('[5/6] Генерация картинки...', 'info');

    const response = await fetch('/api/auto-generate', { method: 'POST' });
    const data = await response.json();

    if (data.status === 'success') {
        updateProgress(75, 6, 'active');
        log('[6/6] Публикация в Telegram...', 'info');

        updateProgress(100, 6, 'completed');
        log('✅ УСПЕХ!', 'success');
    }
}
```

**Статус:** ⏳ Исправляю сейчас

---

### Ошибка #10: Reel генератор создаёт "набор пикселей" вместо нормальной картинки
**Время обнаружения:** 2025-12-21 (тестирование пользователя)
**Файл:** `automation/reel_generator.py:132`

**Симптомы:**
- Сгенерированная картинка выглядит как "полная чушь"
- "Набор пикселей" вместо читаемого текста
- Текст почти невидимый

**Причина:**
```python
# automation/reel_generator.py:132
try:
    title_font = ImageFont.truetype("arial.ttf", size=80)  # ← arial.ttf не существует на Linux!
except:
    title_font = ImageFont.load_default(size=80)  # ← load_default игнорирует size parameter
                                                   # ← возвращает крошечный bitmap font
```

На Render (Linux):
- `arial.ttf` не существует → Exception
- `ImageFont.load_default()` возвращает tiny bitmap font ~10px
- Параметр `size=80` игнорируется для default font
- Результат: нечитаемый текст

**Решение:**
Использовать font, который существует на Linux:
```python
import os

def _get_font(self, size):
    """Get font with fallback chain"""
    # Try Linux system fonts
    linux_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for font_path in linux_fonts:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue

    # Fallback: возвращаем default но предупреждаем
    print(f"[WARNING] No system fonts found, using default (will look bad)", flush=True)
    return ImageFont.load_default()
```

**Статус:** ⏳ Исправляю сейчас

---

## 📝 СЛЕДУЮЩИЕ ШАГИ

1. ✅ Создать этот лог
2. ✅ Проверить код TopicSelector - найдена попытка SELECT из topics
3. ✅ Переписать TopicSelector для использования InsightsAnalyzer
4. ✅ Обновить app_v2.py для передачи insights_analyzer
5. ✅ Закоммитить и запушить исправления
6. ✅ Подождать деплой на Render
7. ✅ Протестировать endpoints на Render
8. **⏳ КРИТИЧНО: Пользователь должен установить env vars на Render:**
   - TELEGRAM_BOT_TOKEN
   - TELEGRAM_CHANNEL_ID
   - AUTO_GENERATE_ENABLED=true
   - Проверить GROQ_API_KEY
9. ⏳ После установки env vars - перезапустить Render service
10. ⏳ Протестировать полный цикл на дашборде

---

## 🚀 ИСТОРИЯ КОММИТОВ

1. `2bee8bf` - "fix: Add missing /api/run-insights endpoint for test dashboard"
2. `dde50cc` - "fix: Add Content-Type headers to POST requests in test dashboard"
3. `047ea09` - "fix: Use detect_topics() instead of analyze_topics() and fix /api/topics endpoint"

---

*Лог будет обновляться по мере обнаружения и исправления ошибок*
