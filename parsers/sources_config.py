"""
Configuration for parsing schedules and rules for each source

SIMPLIFIED SCHEDULE: All sources parse 3x daily (every 8 hours)
Main trigger: GitHub Actions wake-and-run at 9:00, 14:00, 20:00 UTC
Fallback: Interval-based auto-scheduling (if wake-and-run fails)
"""

PARSING_SCHEDULES = {
    'hacker_news': {
        'name': 'Hacker News',
        'enabled_by_default': True,
        'sections': {
            'ask_hn': {
                'interval_hours': 8,  # 3x daily
                'limit': 30,
                'description': 'Ask HN - вопросы и обсуждения'
            },
            'show_hn': {
                'interval_hours': 8,  # 3x daily
                'limit': 30,
                'description': 'Show HN - запуски и фидбэк'
            },
            'new': {
                'interval_hours': 8,  # 3x daily
                'limit': 50,
                'description': 'New - новые посты'
            }
        }
    },

    'reddit': {
        'name': 'Reddit',
        'enabled_by_default': False,
        'sections': {
            'startups': {
                'interval_hours': 8,  # 3x daily
                'limit': 50,
                'description': 'r/startups - стартап-сообщество'
            },
            'SaaS': {
                'interval_hours': 8,  # 3x daily
                'limit': 50,
                'description': 'r/SaaS - SaaS продукты и обсуждения'
            },
            'entrepreneur': {
                'interval_hours': 8,  # 3x daily
                'limit': 50,
                'description': 'r/Entrepreneur - предпринимательство'
            }
        }
    },

    'product_hunt': {
        'name': 'Product Hunt',
        'enabled_by_default': False,
        'sections': {
            'daily': {
                'interval_hours': 24,  # 1x daily (products update once per day)
                'limit': 50,
                'description': 'Product Hunt - ежедневные запуски продуктов'
            }
        }
    },

    'devto': {
        'name': 'Dev.to',
        'enabled_by_default': False,
        'sections': {
            'startup': {
                'interval_hours': 8,  # 3x daily
                'limit': 30,
                'description': 'Dev.to #startup - статьи про стартапы'
            },
            'entrepreneur': {
                'interval_hours': 8,  # 3x daily
                'limit': 30,
                'description': 'Dev.to #entrepreneur - предпринимательство'
            },
            'saas': {
                'interval_hours': 8,  # 3x daily
                'limit': 30,
                'description': 'Dev.to #saas - SaaS продукты'
            },
            'buildinpublic': {
                'interval_hours': 8,  # 3x daily
                'limit': 30,
                'description': 'Dev.to #buildinpublic - открытая разработка'
            },
            'indiehacker': {
                'interval_hours': 8,  # 3x daily
                'limit': 30,
                'description': 'Dev.to #indiehacker - независимые разработчики'
            }
        }
    },

    'vc_blogs': {
        'name': 'VC Blogs',
        'enabled_by_default': False,
        'sections': {
            'yc': {
                'interval_hours': 24,  # 1x daily (blogs update rarely)
                'limit': 15,
                'description': 'Y Combinator Blog - YC portfolio and advice'
            },
            'sequoia': {
                'interval_hours': 24,  # 1x daily
                'limit': 10,
                'description': 'Sequoia Capital - investment insights'
            },
            'a16z': {
                'interval_hours': 24,  # 1x daily
                'limit': 10,
                'description': 'a16z Future - tech trends and future'
            }
        }
    },

    'techcrunch': {
        'name': 'TechCrunch',
        'enabled_by_default': False,
        'sections': {
            'main': {
                'interval_hours': 8,  # 3x daily
                'limit': 30,
                'description': 'TechCrunch Main - все новости'
            },
            'startups': {
                'interval_hours': 8,  # 3x daily
                'limit': 30,
                'description': 'Startups - запуски и новости стартапов'
            },
            'funding': {
                'interval_hours': 8,  # 3x daily
                'limit': 30,
                'description': 'Venture - раунды финансирования'
            },
            'apps': {
                'interval_hours': 8,  # 3x daily
                'limit': 30,
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
