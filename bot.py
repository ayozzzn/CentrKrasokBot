import os
import json
import sqlite3
import logging
from google import genai
from google.genai import types
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from company_knowledge import COMPANY_INFO
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не задан!")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY не задан!")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

MAX_HISTORY = 10
DB_PATH = "conversations.db"

SYSTEM_PROMPT = f"""Ты — AI-ассистент компании «Центр Красок #1», специализированного магазина лакокрасочных материалов в Казахстане.

ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе базы знаний о компании, приведённой ниже.
2. Если вопрос касается компании, но ответа нет в базе — честно скажи, что не знаешь, и предложи связаться напрямую: +7 (777) 292-84-01 или info@centr-krasok.kz.
3. Если вопрос совсем не связан с компанией или красками — вежливо объясни, что ты специализированный ассистент Центра Красок #1, и можешь помочь только по теме компании.
4. Никогда не придумывай цены, характеристики товаров или информацию, которой нет в базе.
5. Отвечай ИСКЛЮЧИТЕЛЬНО на русском языке.
6. Используй эмодзи умеренно для структурирования ответа.
7. СТРОГО ЗАПРЕЩЕНО использовать символы форматирования: **, __, *, #, [], (). Пиши только обычными словами и предложениями.
8. Помни контекст диалога — если пользователь уточняет предыдущий вопрос, учитывай это.
9. Отвечай кратко и по делу — 2-4 предложения, если вопрос простой. Подробно — только если спросили конкретно.
10. Если не уверен в информации — лучше направь к менеджеру, чем угадывать.

=== БАЗА ЗНАНИЙ О КОМПАНИИ ===
{COMPANY_INFO}
=== КОНЕЦ БАЗЫ ЗНАНИЙ ===
"""

START_MESSAGE = """Привет! Я AI-ассистент компании Центр Красок #1.

Я помогу вам с вопросами о:
🎨 Нашем ассортименте красок и материалов
🏪 Адресах и режиме работы магазинов
🚚 Доставке и оплате
🖌️ Подборе краски для вашего проекта
💼 Актуальных вакансиях компании

Просто напишите свой вопрос и я отвечу!

📞 Или звоните напрямую: +7 (777) 292-84-01"""


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                chat_id INTEGER PRIMARY KEY,
                history TEXT NOT NULL DEFAULT '[]',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def load_history(chat_id: int) -> list:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT history FROM conversations WHERE chat_id = ?", (chat_id,)
        ).fetchone()
    return json.loads(row[0]) if row else []


def save_history(chat_id: int, history: list) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO conversations (chat_id, history, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(chat_id) DO UPDATE SET
                history = excluded.history,
                updated_at = excluded.updated_at
        """, (chat_id, json.dumps(history, ensure_ascii=False)))
        conn.commit()


def clear_history(chat_id: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM conversations WHERE chat_id = ?", (chat_id,))
        conn.commit()


def build_gemini_contents(history: list, user_text: str) -> list:
    """Собирает историю + новое сообщение в формат Gemini."""
    contents = []
    recent = history[-MAX_HISTORY * 2:] if len(history) > MAX_HISTORY * 2 else history
    for msg in recent:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=user_text)]))
    return contents


def clean_response(text: str) -> str:
    """Убирает markdown-символы из ответа модели."""
    for sym in ["**", "__", "##", "# ", "### "]:
        text = text.replace(sym, "")
    return text.strip()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    clear_history(chat_id)
    await update.message.reply_text(START_MESSAGE)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    clear_history(chat_id)
    await update.message.reply_text("История диалога очищена! Начнём сначала 🎨")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_text = update.message.text.strip()

    if not user_text or len(user_text) < 2:
        return

    if len(user_text) > 1000:
        await update.message.reply_text(
            "Сообщение слишком длинное. Пожалуйста, сформулируйте вопрос короче 🙂"
        )
        return

    history = load_history(chat_id)

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        contents = build_gemini_contents(history, user_text)

        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=1000,
                temperature=0.3,
            ),
        )

        assistant_reply = clean_response(response.text)

        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": assistant_reply})
        save_history(chat_id, history)

        await update.message.reply_text(assistant_reply)

    except Exception as e:
        logger.error(f"Ошибка при обращении к Gemini API: {e}")
        await update.message.reply_text(
            "Произошла ошибка. Попробуйте позже или свяжитесь с нами: "
            "+7 (777) 292-84-01"
        )


def main() -> None:
    init_db()

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()