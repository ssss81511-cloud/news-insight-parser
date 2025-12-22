# UptimeRobot Setup - Решение проблемы с Render Sleep

## Проблема
- Render Free Tier засыпает через 15 минут неактивности
- GitHub Actions cron jobs ненадежны (задержки 5-30 минут)
- Сервер постоянно спит несмотря на GitHub workflow

## Решение: UptimeRobot

UptimeRobot - бесплатный сервис мониторинга который будет пинговать ваш сервер **точно каждые 5 минут**.

### Инструкция (5 минут):

1. **Регистрация**
   - Перейдите: https://uptimerobot.com
   - Нажмите "Free Sign Up"
   - Зарегистрируйтесь (email + пароль)

2. **Создание монитора**
   - После входа нажмите "+ Add New Monitor"
   - Заполните:
     ```
     Monitor Type: HTTP(s)
     Friendly Name: News Insight Parser
     URL: https://news-insight-parser.onrender.com/
     Monitoring Interval: 5 minutes
     ```
   - Нажмите "Create Monitor"

3. **Готово!** ✅
   - UptimeRobot начнет пинговать каждые 5 минут
   - Сервер больше не будет засыпать
   - Бонус: Получите email если сервер упал

### Лимиты бесплатного плана:
- ✅ 50 мониторов
- ✅ Проверка каждые 5 минут
- ✅ Email/SMS уведомления
- ✅ Без ограничений по времени

### Альтернативы:

**Better Uptime** (https://betteruptime.com)
- Бесплатно до 10 мониторов
- Проверка каждые 3 минуты
- Красивый dashboard

**cron-job.org** (https://cron-job.org)
- Бесплатно
- Проверка каждые 1 минуту (!)
- Но нужно подтверждать email раз в месяц

## Что делать с GitHub Actions?

Можете оставить как есть - дополнительная защита не помешает.
Или удалить workflow если хотите:

```bash
git rm .github/workflows/keepalive.yml
git commit -m "Remove GitHub Actions keepalive (replaced with UptimeRobot)"
git push
```

## Проверка что работает:

После настройки UptimeRobot подождите 20-30 минут и проверьте:

```bash
curl https://news-insight-parser.onrender.com/api/status
```

Сервер должен отвечать мгновенно (не через 30+ секунд как при "пробуждении").
