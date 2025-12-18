# TechCrunch Parser Setup

## Обзор

TechCrunch parser парсит новости из одного из крупнейших технологических изданий через публичные RSS каналы.

**Ключевые особенности:**
- ✅ Не требует API ключей или регистрации
- ✅ Публичные RSS feeds без ограничений
- ✅ 4 категории: Main, Startups, Funding, Apps
- ✅ ~20 статей на каждый запрос
- ✅ Детекция фокус-тем (funding, launches, acquisitions)
- ✅ Повышенный importance_score для важных новостей

## Что парсим

### 1. Main Feed
- URL: `https://techcrunch.com/feed/`
- Содержание: все новости TechCrunch
- Частота обновления: несколько раз в час
- Рекомендуемый интервал: 6 часов

### 2. Startups Feed
- URL: `https://techcrunch.com/category/startups/feed/`
- Содержание: запуски и новости стартапов
- Фокус: new launches, startup announcements
- Рекомендуемый интервал: 8 часов

### 3. Funding Feed
- URL: `https://techcrunch.com/category/venture/feed/`
- Содержание: раунды финансирования, acquisitions
- Фокус: Series A/B/C, M&A, valuations
- Рекомендуемый интервал: 12 часов
- **Importance bonus:** +15 баллов

### 4. Apps Feed
- URL: `https://techcrunch.com/category/apps/feed/`
- Содержание: новые приложения и продукты
- Фокус: app launches, product updates
- Рекомендуемый интервал: 12 часов

## Установка

### Шаг 1: Установить зависимости

```bash
pip install feedparser requests loguru
```

Эти пакеты уже установлены, если вы настроили другие RSS парсеры (Reddit, Product Hunt, VC Blogs).

### Шаг 2: Проверить работу

```bash
# Тест RSS доступа
python test_techcrunch.py

# Тест парсера
python test_techcrunch_parser.py
```

Должен вернуть:
```
Available sections: ['main', 'startups', 'funding', 'apps']
Fetched 5 posts
SUCCESS: TechCrunch parser working correctly!
```

## Структура данных

### Что получаем из RSS:
- **title** - заголовок статьи
- **link** - URL статьи
- **published** - дата публикации
- **summary** - краткое описание (HTML)
- **author** - автор статьи
- **tags** - категории/теги

### Что НЕ доступно через RSS:
- ❌ Комментарии (TechCrunch использует сторонние системы комментариев)
- ❌ Количество просмотров
- ❌ Social shares

## Фокус-темы (Focus Themes)

Parser детектирует важные темы и дает +20 баллов к importance_score:

```python
FOCUS_THEMES = [
    r"raise[sd]?\s+\$\d+",          # "raised $10M"
    r"series\s+[abc]",               # "Series A"
    r"funding\s+round",
    r"acquisition",
    r"acquired?\s+by",
    r"launch(?:es|ed|ing)?",
    r"announces?\s+(?:new|launch)",
    r"valuation",
    r"unicorn",
    r"ipo",
    r"saas",
    r"b2b",
    r"ai[- ]powered",
]
```

### Примеры:
- ✅ "Company X raises $50M Series B" → +20 score
- ✅ "Startup launches AI-powered SaaS platform" → +20 score
- ✅ "Unicorn acquired by tech giant for $2B" → +20 score
- ⬜ "Company updates privacy policy" → no bonus

## Важность категорий (Importance Scoring)

**Base score:** 50 (все TechCrunch статьи)

**Бонусы:**
- Funding category: **+15** (раунды финансирования всегда важны)
- Startups category: **+10** (запуски стартапов)
- Focus themes detected: **+20** (ключевые темы)

**Примеры итоговых scores:**
- Обычная новость (Main): 50
- Новость о стартапе (Startups): 60
- Раунд финансирования (Funding): 65
- Раунд с фокус-темой: 85 (65 + 20)
- Максимальный score: 100

## Использование

### Простой запуск:

```python
from parsers.techcrunch.parser import TechCrunchParser
from storage.universal_database import UniversalDatabaseManager

# Initialize
parser = TechCrunchParser()
db = UniversalDatabaseManager('sqlite:///data/insights.db')

# Parse single category
saved = parser.parse_and_save(db, 'funding', limit=20)
print(f"Saved {saved} posts")
```

### Через Orchestrator:

```python
from parsers.orchestrator import create_orchestrator
from storage.universal_database import UniversalDatabaseManager

db = UniversalDatabaseManager('sqlite:///data/insights.db')
orchestrator = create_orchestrator(db)

# Parse all TechCrunch categories
results = orchestrator.parse_source('techcrunch')

# Parse specific category
results = orchestrator.parse_source('techcrunch', sections=['funding'], limit_per_section=20)
```

## Конфигурация расписания

В `parsers/sources_config.py`:

```python
'techcrunch': {
    'name': 'TechCrunch',
    'enabled_by_default': False,
    'sections': {
        'main': {
            'interval_hours': 6,    # 4 раза в день
            'limit': 20,
        },
        'startups': {
            'interval_hours': 8,    # 3 раза в день
            'limit': 20,
        },
        'funding': {
            'interval_hours': 12,   # 2 раза в день
            'limit': 20,
        },
        'apps': {
            'interval_hours': 12,   # 2 раза в день
            'limit': 20,
        }
    }
}
```

## Объем данных

**Прогнозируемое количество постов в день:**
- Main (6h interval, 20 limit): ~80 posts/day
- Startups (8h interval, 20 limit): ~60 posts/day
- Funding (12h interval, 20 limit): ~40 posts/day
- Apps (12h interval, 20 limit): ~40 posts/day

**Итого:** ~220 posts/day

**С учетом дедупликации:** ~150-180 posts/day (статьи могут появляться в нескольких категориях)

## Пример нормализованного поста

```python
{
    'source': 'techcrunch',
    'source_id': 'https://techcrunch.com/2025/12/16/startup-raises-100m',
    'source_url': 'https://techcrunch.com/2025/12/16/startup-raises-100m',
    'title': 'AI startup raises $100M Series B led by Sequoia',
    'content': 'The company announced today it has raised...',
    'author': 'Sarah Perez',
    'score': 0,                    # RSS doesn't provide
    'comments_count': 0,           # RSS doesn't provide
    'post_type': 'funding',        # Based on category
    'category': 'funding',         # startups/funding/apps/main
    'created_at': datetime(...),
    'content_hash': 'a1b2c3...',
    'importance_score': 85,        # 65 (funding) + 20 (focus theme)
    'metadata': {
        'tags': ['Venture', 'Startups', 'AI'],
        'has_focus_themes': True,
        'category': 'funding',
        'feed_url': 'https://techcrunch.com/category/venture/feed/'
    }
}
```

## Интеграция с другими источниками

TechCrunch отлично дополняет другие источники:

**Cross-source insights:**
- TechCrunch Funding + YC Blog → полная картина венчурного рынка
- TechCrunch Startups + Product Hunt → запуски продуктов
- TechCrunch Main + Hacker News → обсуждение новостей
- TechCrunch Apps + Dev.to → технические детали

**Пример сигнала:**
1. Product Hunt: "New AI tool launched"
2. TechCrunch: "AI tool raises $10M seed round"
3. Hacker News: Community discussion about the tool
4. Reddit r/startups: Founders asking about similar tools

→ **Strong signal:** validated product with funding and community interest

## Ограничения

### RSS Limitations:
- Только последние ~20 статей на feed
- Нет комментариев
- Нет метрик engagement (views, shares)
- HTML в summary нужно очищать

### Rate Limiting:
- RSS обычно не лимитируется
- Используем 1 sec delay между запросами
- Можно парсить все 4 категории подряд

## Troubleshooting

### Проблема: "No entries in feed"
```bash
# Проверить доступность RSS
curl https://techcrunch.com/feed/
```

**Решение:** TechCrunch RSS стабильны, но могут быть временные сбои. Повторить через 5-10 минут.

### Проблема: HTML tags в content
**Решение:** Parser автоматически очищает HTML через `re.sub(r'<[^>]+>', '', summary)`

### Проблема: Duplicate posts в разных категориях
**Решение:** Используем content_hash для дедупликации. Один пост может быть в Main и Startups, но сохранится только раз.

## Next Steps

После настройки TechCrunch:

1. ✅ **Активировать в конфиге:**
   ```python
   'enabled_by_default': True
   ```

2. **Настроить автопарсинг:** (будет в scheduler)
   - Main: каждые 6 часов
   - Startups: каждые 8 часов
   - Funding: каждые 12 часов
   - Apps: каждые 12 часов

3. **Мониторить качество:**
   - Проверить importance_scores
   - Убедиться что фокус-темы детектятся
   - Проверить дедупликацию с другими источниками

## Полезные ссылки

- [TechCrunch Main RSS](https://techcrunch.com/feed/)
- [TechCrunch Startups](https://techcrunch.com/category/startups/)
- [TechCrunch Venture](https://techcrunch.com/category/venture/)
- [RSS 2.0 Specification](https://www.rssboard.org/rss-specification)
