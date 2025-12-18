# Quick Start Guide

Быстрый старт News Insight Parser с веб-интерфейсом.

## Шаг 1: Установка зависимостей

```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать (Windows)
venv\Scripts\activate

# Активировать (Linux/Mac)
source venv/bin/activate

# Установить зависимости
pip install flask requests sqlalchemy loguru python-dotenv
```

## Шаг 2: Запуск веб-интерфейса

```bash
python app.py
```

После запуска откройте браузер: **http://localhost:5000**

## Шаг 3: Начало работы

1. **Dashboard (главная)** - общая статистика и управление парсером
2. Нажмите кнопку **"Start Parsing"** для запуска сбора данных
3. Парсер соберет данные из:
   - Ask HN (вопросы основателей)
   - Show HN (новые запуски, ранние фидбэки)
   - New (свежие новости)

## Шаг 4: Просмотр результатов

- **Posts** - все собранные посты с фильтрами
- **Signals** - обнаруженные паттерны и инсайты

## Что парсится

### Ask HN
- Вопросы от основателей
- Обсуждения проблем
- Запросы на советы

### Show HN
- Новые продукты
- Ранние запуски
- Запросы на фидбэк
- Обсуждения под Show HN

### New
- Свежие истории
- Актуальные темы

## Обнаруженные сигналы

Система автоматически анализирует контент и выявляет:

1. **Repeating Pains** - повторяющиеся проблемы
2. **Emerging Language** - новые термины и фразы
3. **Solution Patterns** - общие подходы к решению
4. **Behavioral Patterns** - изменения в поведении

## Структура данных

Все данные хранятся в SQLite: `data/insights.db`

- `hn_posts` - посты
- `hn_comments` - комментарии
- `signals` - обнаруженные сигналы
- `parser_runs` - история запусков

## API Endpoints

- `GET /` - Dashboard
- `GET /posts` - Список постов
- `GET /posts?type=ask_hn` - Только Ask HN
- `GET /signals` - Обнаруженные сигналы
- `POST /api/parse` - Запустить парсер
- `GET /api/status` - Статус парсера

## Расписание парсинга

Для автоматического запуска можно настроить cron (Linux/Mac) или Task Scheduler (Windows):

```bash
# Запуск каждый час
0 * * * * cd /path/to/parser && python -c "from parsers.hacker_news.parser import HackerNewsParser; from storage.database import DatabaseManager; HackerNewsParser().parse_all_sections()"
```

## Troubleshooting

### Ошибка "Module not found"
```bash
# Убедитесь что виртуальное окружение активировано
pip install -r requirements.txt
```

### База данных не создается
```bash
# Создайте папку data вручную
mkdir data
```

### Парсер не запускается
- Проверьте интернет-соединение
- HN API использует Firebase, не требует ключей
- Проверьте логи в консоли

## Следующие шаги

1. Запустите парсер несколько раз для накопления данных
2. Изучите обнаруженные сигналы
3. Добавьте другие источники (Reddit, Product Hunt)
4. Настройте автоматический запуск
