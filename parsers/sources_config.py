"""
Configuration for parsing schedules and rules for each source

Each source has predefined optimal intervals based on:
- Update frequency
- API rate limits
- Data importance
"""

PARSING_SCHEDULES = {
    'hacker_news': {
        'name': 'Hacker News',
        'enabled_by_default': True,
        'sections': {
            'ask_hn': {
                'interval_hours': 6,
                'limit': 20,
                'description': 'Ask HN - вопросы и обсуждения (обновляется несколько раз в день)'
            },
            'show_hn': {
                'interval_hours': 6,
                'limit': 20,
                'description': 'Show HN - запуски и фидбэк (обновляется несколько раз в день)'
            },
            'new': {
                'interval_hours': 1,
                'limit': 30,
                'description': 'New - новые посты (обновляется постоянно, парсим чаще)'
            }
        }
    },

    'reddit': {
        'name': 'Reddit',
        'enabled_by_default': False,  # Не активен пока не добавлен парсер
        'sections': {
            'startups': {
                'interval_hours': 4,
                'limit': 50,
                'description': 'r/startups - стартап-сообщество'
            },
            'SaaS': {
                'interval_hours': 6,
                'limit': 50,
                'description': 'r/SaaS - SaaS продукты и обсуждения'
            },
            'entrepreneur': {
                'interval_hours': 6,
                'limit': 50,
                'description': 'r/Entrepreneur - предпринимательство'
            }
        }
    },

    'product_hunt': {
        'name': 'Product Hunt',
        'enabled_by_default': False,  # Активируется после тестирования
        'sections': {
            'daily': {
                'interval_hours': 24,  # Раз в день (новые продукты обновляются ежедневно)
                'limit': 50,
                'description': 'Product Hunt - ежедневные запуски продуктов'
            }
        }
    },

    'devto': {
        'name': 'Dev.to',
        'enabled_by_default': False,  # Активируется после тестирования
        'sections': {
            'startup': {
                'interval_hours': 12,  # Два раза в день
                'limit': 30,
                'description': 'Dev.to #startup - статьи про стартапы'
            },
            'entrepreneur': {
                'interval_hours': 12,
                'limit': 30,
                'description': 'Dev.to #entrepreneur - предпринимательство'
            },
            'saas': {
                'interval_hours': 12,
                'limit': 30,
                'description': 'Dev.to #saas - SaaS продукты'
            },
            'buildinpublic': {
                'interval_hours': 24,  # Раз в день
                'limit': 20,
                'description': 'Dev.to #buildinpublic - открытая разработка'
            },
            'indiehacker': {
                'interval_hours': 24,
                'limit': 20,
                'description': 'Dev.to #indiehacker - независимые разработчики'
            }
        }
    },

    'vc_blogs': {
        'name': 'VC Blogs',
        'enabled_by_default': False,  # Активируется после тестирования
        'sections': {
            'yc': {
                'interval_hours': 48,  # Раз в 2 дня (блоги обновляются редко)
                'limit': 15,
                'description': 'Y Combinator Blog - YC portfolio and advice'
            },
            'sequoia': {
                'interval_hours': 48,
                'limit': 10,
                'description': 'Sequoia Capital - investment insights'
            },
            'a16z': {
                'interval_hours': 48,
                'limit': 10,
                'description': 'a16z Future - tech trends and future'
            }
        }
    },

    'techcrunch': {
        'name': 'TechCrunch',
        'enabled_by_default': False,  # Активируется после тестирования
        'sections': {
            'main': {
                'interval_hours': 6,  # 4 раза в день (новости обновляются часто)
                'limit': 20,
                'description': 'TechCrunch Main - все новости'
            },
            'startups': {
                'interval_hours': 8,  # 3 раза в день
                'limit': 20,
                'description': 'Startups - запуски и новости стартапов'
            },
            'funding': {
                'interval_hours': 12,  # 2 раза в день
                'limit': 20,
                'description': 'Venture - раунды финансирования'
            },
            'apps': {
                'interval_hours': 12,  # 2 раза в день
                'limit': 20,
                'description': 'Apps - новые приложения и продукты'
            }
        }
    }
}


def get_source_schedule(source_name: str) -> dict:
    """Get schedule configuration for a source"""
    return PARSING_SCHEDULES.get(source_name, {})


def get_all_sources() -> list:
    """Get list of all configured sources"""
    return list(PARSING_SCHEDULES.keys())


def is_source_available(source_name: str, registered_sources: list) -> bool:
    """Check if source is both configured and has a parser registered"""
    return source_name in PARSING_SCHEDULES and source_name in registered_sources
