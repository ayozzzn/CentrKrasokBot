# 🎨 Центр Красок #1 — AI Telegram-бот

Telegram-бот с AI-ассистентом для компании «Центр Красок #1». Отвечает на вопросы клиентов о компании на основе собранной базы знаний — без галлюцинаций и выдумок.

## Что умеет бот

- Рассказывает о компании, брендах и ассортименте
- Отвечает на вопросы о доставке, оплате и возврате товара
- Сообщает адреса и режим работы салонов в Алматы и Астане
- Объясняет термины (грунтовка, адгезия, износостойкость и т.д.)
- Информирует об актуальных вакансиях
- Помнит контекст диалога в рамках сессии

## Стек

- Python 3.11
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) 21.5
- Google Gemini 1.5 Flash (бесплатный API)
- SQLite — хранение истории диалогов
- Docker
- Деплой: Railway

## Структура проекта

```
centr-krasok-bot/
├── bot.py                # основная логика бота
├── company_knowledge.py  # база знаний о компании
├── requirements.txt
├── Dockerfile
├── .env                  # переменные окружения (не в репо)
├── .gitignore
└── .dockerignore
```

## Локальный запуск

### 1. Клонируй репозиторий

```bash
git clone https://github.com/ayozzzn/CentrKrasokBot.git
cd CentrKrasokBot
```

### 2. Создай виртуальное окружение

```bash
python -m venv venv
source venv/bin/activate  # на Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Создай файл .env

```env
TELEGRAM_TOKEN=твой_токен_от_BotFather
GEMINI_API_KEY=твой_ключ_от_Google_AI_Studio
```

Получить ключи:
- Telegram токен — через [@BotFather](https://t.me/BotFather)
- Gemini API ключ — на [aistudio.google.com](https://aistudio.google.com) (бесплатно)

### 4. Запусти бота

```bash
python bot.py
```

## Запуск через Docker

```bash
docker build -t centr-krasok-bot .
docker run --env-file .env centr-krasok-bot
```

## Деплой на Railway

1. Зайди на [railway.app](https://railway.app) и войди через GitHub
2. New Project → Deploy from GitHub repo → выбери `CentrKrasokBot`
3. В разделе Variables добавь:
   - `TELEGRAM_TOKEN`
   - `GEMINI_API_KEY`
4. Railway автоматически найдёт Dockerfile и задеплоит бота

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Запустить бота / сбросить историю |
| `/reset` | Очистить историю диалога |

## Как устроена база знаний

Вся информация о компании хранится в `company_knowledge.py` в виде структурированного текста и передаётся модели через системный промпт. Модель отвечает строго на основе этих данных — если информации нет в базе, бот честно об этом говорит и предлагает связаться с менеджером.