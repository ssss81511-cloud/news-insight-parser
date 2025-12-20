# Как проверить что AI работает

## 1️⃣ Перезапусти сервис на Render

**ОБЯЗАТЕЛЬНО после добавления HUGGING_FACE_TOKEN:**

1. Зайди в Render Dashboard
2. Выбери свой сервис (news-insight-parser)
3. Нажми **Manual Deploy** → **Deploy latest commit**
   ИЛИ
4. Settings → **Restart Service**

⚠️ **БЕЗ ПЕРЕЗАПУСКА ТОКЕН НЕ ПРИМЕНИТСЯ!**

---

## 2️⃣ Проверь логи при запуске

**Render Dashboard → Logs**

Ищи при старте приложения:

### ✅ ПРАВИЛЬНО (токен есть):
```
[REEL GENERATOR] Initialized: AI=True, HF Token=✅ Set
```

### ❌ НЕПРАВИЛЬНО (токена нет):
```
[REEL GENERATOR] Initialized: AI=True, HF Token=❌ MISSING
[REEL GENERATOR] ⚠️  WARNING: AI generation enabled but NO HF TOKEN!
[REEL GENERATOR] ⚠️  Get free token: https://huggingface.co/settings/tokens
```

---

## 3️⃣ Сгенерируй НОВЫЙ пост

После перезапуска сервиса:

1. Зайди на dashboard: `https://news-insight-parser.onrender.com`
2. Нажми **"Generate & Post"**
3. Смотри логи в реальном времени

---

## 4️⃣ Проверь логи генерации изображения

### ✅ AI РАБОТАЕТ:
```
[REEL] ✅ AI generation ENABLED - attempting to generate AI image
[REEL] 🏷️  Keywords for AI: ['AI', 'healthcare', 'technology']
[REEL] 📝 Prompt created: Professional modern tech illustration about AI, healthcare, technology...
[AI IMAGE] Generating with prompt: Professional modern...
[AI IMAGE] Generated successfully: (512, 512)
[REEL] ✅ Using AI-generated background (size: (512, 512))
```

### ❌ AI НЕ РАБОТАЕТ (нет токена):
```
[REEL] ✅ AI generation ENABLED - attempting to generate AI image
[REEL] 🏷️  Keywords for AI: ['AI', 'healthcare', 'technology']
[REEL] 📝 Prompt created: Professional modern tech...
[AI IMAGE] ❌ No HF token - skipping AI generation
[REEL] ❌ AI generation FAILED - using colored fallback background
```

### ❌ AI НЕ РАБОТАЕТ (токен неправильный):
```
[AI IMAGE] Generating with prompt: Professional modern...
[AI IMAGE] Error 401: {"error":"Invalid token"}
[REEL] ❌ AI generation FAILED - using colored fallback background
```

### ⏳ API ЗАГРУЖАЕТСЯ:
```
[AI IMAGE] Generating with prompt: Professional modern...
[AI IMAGE] Model loading... waiting 20s (attempt 1/3)
[AI IMAGE] Model loading... waiting 20s (attempt 2/3)
[AI IMAGE] Generated successfully: (512, 512)
```

---

## 5️⃣ Проверь текущий коммит

В Render Dashboard → Events:
- Последний deploy должен быть: **cefde92** или новее
- Если старее - нажми Manual Deploy

---

## 6️⃣ Проверь токен

Render Dashboard → Environment:
- `HUGGING_FACE_TOKEN` = `hf_...` (должен начинаться с hf_)
- Без лишних пробелов
- Без кавычек

---

## ❓ Что делать если не работает

### Если в логах: "HF Token=❌ MISSING"
→ Перезапусти сервис вручную

### Если в логах: "Error 401" или "Invalid token"
→ Проверь токен на https://huggingface.co/settings/tokens
→ Убедись что токен скопирован правильно (нет пробелов)

### Если в логах: "Model loading..." 3 раза
→ API перегружен, подожди 5 минут и попробуй снова

### Если в логах вообще ничего про AI
→ Старый код, нажми Manual Deploy
