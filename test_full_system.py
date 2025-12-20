#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ПОЛНЫЙ ТЕСТ СИСТЕМЫ АВТОМАТИЗАЦИИ

Этот скрипт тестирует все компоненты пошагово:
1. TopicSelector
2. ContentGenerator
3. ReelGenerator
4. TelegramPoster
5. AutoContentSystem (end-to-end)

Запуск: python test_full_system.py
"""

import os
import sys
import asyncio
from datetime import datetime

# Цвета для вывода
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def print_info(text):
    print(f"{YELLOW}ℹ️  {text}{RESET}")

def print_step(num, total, text):
    print(f"\n{BLUE}[ШАГ {num}/{total}] {text}{RESET}")

async def test_full_system():
    """Полное тестирование системы"""

    print_header("ТЕСТИРОВАНИЕ СИСТЕМЫ АВТОМАТИЗАЦИИ")
    print_info(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Импорты
    try:
        from storage.universal_database import UniversalDatabaseManager
        from automation.topic_selector import TopicSelector
        from automation.telegram_poster import TelegramPoster
        from automation.reel_generator import create_reel_generator
        from automation.auto_content_system import AutoContentSystem
        from analyzers.content_generator import ContentGenerator
        print_success("Все модули импортированы")
    except Exception as e:
        print_error(f"Ошибка импорта: {e}")
        return False

    # Проверка переменных окружения
    print_step(1, 8, "Проверка конфигурации")

    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/techcrunch.db')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

    if not GROQ_API_KEY:
        print_error("GROQ_API_KEY не установлен!")
        return False
    print_success(f"GROQ_API_KEY: {GROQ_API_KEY[:20]}...")

    if TELEGRAM_BOT_TOKEN:
        print_success(f"TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN[:20]}...")
        print_success(f"TELEGRAM_CHANNEL_ID: {TELEGRAM_CHANNEL_ID}")
    else:
        print_info("Telegram не настроен (опционально)")

    # Инициализация компонентов
    print_step(2, 8, "Инициализация компонентов")

    try:
        db = UniversalDatabaseManager(DATABASE_URL)
        print_success("База данных подключена")

        topic_selector = TopicSelector(db)
        print_success("TopicSelector инициализирован")

        content_generator = ContentGenerator(api_key=GROQ_API_KEY)
        print_success("ContentGenerator инициализирован")

        reel_generator = create_reel_generator()
        print_success("ReelGenerator инициализирован")

        telegram_poster = None
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID:
            telegram_poster = TelegramPoster(TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID)
            print_success("TelegramPoster инициализирован")

        auto_system = AutoContentSystem(
            db_manager=db,
            content_generator=content_generator,
            topic_selector=topic_selector,
            telegram_poster=telegram_poster,
            reel_generator=reel_generator,
            config={
                'topic_exclude_days': 30,
                'content_language': 'ru',
                'content_format': 'long_post',
                'enable_telegram': telegram_poster is not None
            }
        )
        print_success("AutoContentSystem инициализирован")
    except Exception as e:
        print_error(f"Ошибка инициализации: {e}")
        return False

    # Тест 1: Проверка базы данных
    print_step(3, 8, "Проверка базы данных")

    try:
        from storage.universal_models import UniversalPost
        post_count = db.session.query(UniversalPost).count()
        print_info(f"Всего постов в БД: {post_count}")

        if post_count == 0:
            print_error("В базе данных нет постов!")
            print_info("Запусти сначала: curl -X POST http://localhost:5001/api/parse")
            return False
        print_success(f"В базе есть {post_count} постов")
    except Exception as e:
        print_error(f"Ошибка проверки БД: {e}")
        return False

    # Тест 2: TopicSelector
    print_step(4, 8, "Тест TopicSelector")

    try:
        topic = topic_selector.select_next_topic(min_posts=2)
        if topic:
            print_success(f"Тема найдена: {topic['keywords'][:3]}")
            print_info(f"  - Постов: {topic['post_count']}")
            print_info(f"  - Трендовая: {topic['is_trending']}")
        else:
            print_error("Тем не найдено!")
            print_info("Запусти сначала: curl -X POST http://localhost:5001/api/run-insights")
            return False
    except Exception as e:
        print_error(f"Ошибка TopicSelector: {e}")
        return False

    # Тест 3: ContentGenerator
    print_step(5, 8, "Тест ContentGenerator")

    try:
        from storage.universal_models import UniversalPost
        posts = db.session.query(UniversalPost).filter(
            UniversalPost.id.in_(topic['posts'][:5])
        ).all()

        print_info(f"Генерирую контент из {len(posts)} постов...")
        content = content_generator.generate_from_topic(
            posts=posts,
            format_type='long_post',
            language='ru',
            tone='professional'
        )

        if content:
            print_success("Контент сгенерирован!")
            print_info(f"  - Заголовок: {content.get('title', 'N/A')[:50]}...")
            print_info(f"  - Длина: {len(content['content'])} символов")
            print_info(f"  - Хештеги: {', '.join(content.get('hashtags', [])[:3])}")
        else:
            print_error("Не удалось сгенерировать контент")
            return False
    except Exception as e:
        print_error(f"Ошибка генерации контента: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Тест 4: ReelGenerator
    print_step(6, 8, "Тест ReelGenerator")

    try:
        image_path = reel_generator.generate_from_content(
            content,
            aspect_ratio='reel',
            style='modern'
        )
        print_success(f"Картинка сгенерирована: {image_path}")
    except Exception as e:
        print_error(f"Ошибка ReelGenerator: {e}")
        print_info("Продолжаем без картинки...")
        image_path = None

    # Тест 5: TelegramPoster (если настроен)
    print_step(7, 8, "Тест TelegramPoster")

    if telegram_poster:
        print_info("Отправляю тестовое сообщение в Telegram...")
        try:
            result = await telegram_poster.test_connection()
            if result:
                print_success("Telegram бот подключен!")

                # Спросим пользователя
                answer = input(f"\n{YELLOW}Хочешь опубликовать тестовый пост в @{TELEGRAM_CHANNEL_ID}? (y/n): {RESET}")
                if answer.lower() == 'y':
                    post_result = await telegram_poster.post_content(
                        content=content,
                        media_path=image_path
                    )
                    if post_result['success']:
                        print_success(f"Пост опубликован! Message ID: {post_result['message_id']}")
                        print_info(f"Проверь канал: https://t.me/{TELEGRAM_CHANNEL_ID.lstrip('@')}")
                    else:
                        print_error(f"Ошибка публикации: {post_result['error']}")
                else:
                    print_info("Пропускаем публикацию")
            else:
                print_error("Telegram бот не подключен")
        except Exception as e:
            print_error(f"Ошибка Telegram: {e}")
            import traceback
            traceback.print_exc()
    else:
        print_info("Telegram не настроен - пропускаем тест")

    # Тест 6: AutoContentSystem (end-to-end)
    print_step(8, 8, "Тест AutoContentSystem (полный цикл)")

    answer = input(f"\n{YELLOW}Запустить ПОЛНЫЙ цикл автоматизации? (y/n): {RESET}")
    if answer.lower() == 'y':
        try:
            print_info("Запускаю полный цикл...")
            result = await auto_system.generate_and_post()

            if result['success']:
                print_success("ПОЛНЫЙ ЦИКЛ ЗАВЕРШЕН!")
                print_info(f"  - Content ID: {result['content_id']}")
                if result.get('message_id'):
                    print_info(f"  - Message ID: {result['message_id']}")
                if result.get('image_path'):
                    print_info(f"  - Image: {result['image_path']}")
                print_info(f"  - Тема: {result['topic']['keywords'][:3]}")
            else:
                print_error(f"Ошибка: {result['error']}")
        except Exception as e:
            print_error(f"Ошибка AutoContentSystem: {e}")
            import traceback
            traceback.print_exc()
    else:
        print_info("Пропускаем полный цикл")

    # Итоги
    print_header("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print_success("Все компоненты работают!")
    print_info(f"Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return True

if __name__ == "__main__":
    print(f"\n{BLUE}Starting async event loop...{RESET}\n")

    try:
        # Запуск асинхронного теста
        result = asyncio.run(test_full_system())

        if result:
            print(f"\n{GREEN}{'='*60}")
            print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
            print(f"{'='*60}{RESET}\n")
            sys.exit(0)
        else:
            print(f"\n{RED}{'='*60}")
            print("❌ ТЕСТЫ НЕ ПРОЙДЕНЫ")
            print(f"{'='*60}{RESET}\n")
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Тестирование прервано пользователем{RESET}\n")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}Критическая ошибка: {e}{RESET}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
