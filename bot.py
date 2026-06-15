import os
import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8972598053:AAFHw1o6K-zTscLAxfyCGFlltijQ7SNjZLk")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "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")

SYSTEM_PROMPT = """Ты — Соломон, ИИ-психолог, работающий в традиции психоанализа (Фрейд, Юнг, Лакан, Кляйн). Твоё имя — отсылка к укротителю «внутренних демонов»: ты не боишься тёмного, вытесненного, неудобного.

ТВОЙ ХАРАКТЕР:
— Говоришь глубоко, неторопливо, без спешки к «решению»
— Не даёшь советов в духе коучинга («сделай А, получишь Б»)
— Задаёшь вопросы, которые открывают, а не закрывают
— Замечаешь то, что человек говорит между строк
— Используешь аналитические понятия, но объясняешь их живо, не академично
— В конце каждого ответа — один вопрос, выделенный курсивом (через _вопрос_)

РЕЖИМЫ РАБОТЫ:
1. СОВЕТ — помоги увидеть динамику, паттерны, скрытые желания и страхи за запросом.
2. ИНТЕРПРЕТАЦИЯ — анализируй бессознательные смыслы, защитные механизмы, переносы.
3. СОН — юнгианский подход: архетипы, тень, анима/анимус. Никогда не разгадывай окончательно.

СТИЛЬ: 3–5 абзацев, живая речь, без списков. Заканчивай вопросом в формате _вопрос_
Говори только по-русски."""

sessions = {}
CHOOSING_MODE, TALKING = range(2)

def call_claude(messages):
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 1000,
            "system": SYSTEM_PROMPT,
            "messages": messages,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["content"][0]["text"]

def get_mode_keyboard():
    keyboard = [
        [KeyboardButton("⚖️ Совет"), KeyboardButton("🔍 Интерпретация"), KeyboardButton("🌙 Сон")],
        [KeyboardButton("🔄 Сменить режим"), KeyboardButton("🗑 Новая сессия")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sessions[user_id] = {"mode": None, "history": []}
    await update.message.reply_text(
        "✦ *Соломон*\n_Психоаналитический советник_\n\n«Назови демона по имени — и он потеряет власть над тобой»\n\nВыберите режим работы:",
        parse_mode="Markdown",
        reply_markup=get_mode_keyboard()
    )
    return CHOOSING_MODE

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in sessions:
        sessions[user_id] = {"mode": None, "history": []}

    if text == "⚖️ Совет":
        sessions[user_id]["mode"] = "СОВЕТ"
        await update.message.reply_text("⚖️ *Режим: Совет*\n\nОпишите ситуацию...", parse_mode="Markdown", reply_markup=get_mode_keyboard())
        return TALKING
    elif text == "🔍 Интерпретация":
        sessions[user_id]["mode"] = "ИНТЕРПРЕТАЦИЯ"
        await update.message.reply_text("🔍 *Режим: Интерпретация*\n\nОпишите событие или воспоминание...", parse_mode="Markdown", reply_markup=get_mode_keyboard())
        return TALKING
    elif text == "🌙 Сон":
        sessions[user_id]["mode"] = "СОН"
        await update.message.reply_text("🌙 *Режим: Сон*\n\nРасскажите свой сон...", parse_mode="Markdown", reply_markup=get_mode_keyboard())
        return TALKING
    elif text == "🔄 Сменить режим":
        sessions[user_id]["mode"] = None
        await update.message.reply_text("Выберите новый режим:", reply_markup=get_mode_keyboard())
        return CHOOSING_MODE
    elif text == "🗑 Новая сессия":
        sessions[user_id] = {"mode": None, "history": []}
        await update.message.reply_text("Сессия завершена. Выберите режим:", reply_markup=get_mode_keyboard())
        return CHOOSING_MODE

    if not sessions[user_id].get("mode"):
        await update.message.reply_text("Пожалуйста, сначала выберите режим:", reply_markup=get_mode_keyboard())
        return CHOOSING_MODE

    mode = sessions[user_id]["mode"]
    history = sessions[user_id]["history"]
    history.append({"role": "user", "content": f"РЕЖИМ: {mode}\n\n{text}"})
    if len(history) > 10:
        history = history[-10:]
        sessions[user_id]["history"] = history

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        reply = call_claude(history)
        history.append({"role": "assistant", "content": reply})
        sessions[user_id]["history"] = history
        await update.message.reply_text(reply, parse_mode="Markdown", reply_markup=get_mode_keyboard())
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}", reply_markup=get_mode_keyboard())

    return TALKING

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_MODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
            TALKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    app.add_handler(conv_handler)
    print("Соломон запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
