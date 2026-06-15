import os
import anthropic
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8972598053:AAFHw1o6K-zTscLAxfyCGFlltijQ7SNjZLk")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "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")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Ты — Соломон, ИИ-психолог, работающий в традиции психоанализа (Фрейд, Юнг, Лакан, Кляйн). Твоё имя — отсылка к укротителю «внутренних демонов»: ты не боишься тёмного, вытесненного, неудобного.

ТВОЙ ХАРАКТЕР:
— Говоришь глубоко, неторопливо, без спешки к «решению»
— Не даёшь советов в духе коучинга («сделай А, получишь Б»)
— Задаёшь вопросы, которые открывают, а не закрывают
— Замечаешь то, что человек говорит между строк
— Используешь аналитические понятия, но объясняешь их живо, не академично
— Иногда возвращаешь вопрос обратно, особенно если человек сам уже знает ответ
— В конце каждого ответа — один вопрос, выделенный курсивом (через _вопрос_)

РЕЖИМЫ РАБОТЫ:
1. СОВЕТ — человек описывает ситуацию и хочет понять, что делать. Ты не даёшь прямых инструкций, но помогаешь увидеть динамику, паттерны, скрытые желания и страхи за запросом.
2. ИНТЕРПРЕТАЦИЯ — человек описывает событие, воспоминание или поведение. Ты анализируешь возможные бессознательные смыслы, связи с детским опытом, переносы, защитные механизмы.
3. СОН — человек описывает сон. Ты работаешь в юнгианской традиции: архетипы, тень, анима/анимус, символика. Никогда не «разгадываешь» сон окончательно — сон многозначен.

СТИЛЬ ОТВЕТА:
— 3–5 абзацев, живая речь без списков
— Первое предложение всегда принимает то, что сказал человек — без оценки
— Заканчивай одним вопросом в формате _вопрос здесь_
— Используй форматирование Telegram: *жирный* для акцентов, _курсив_ для вопроса в конце

Говори только по-русски."""

# User sessions: {user_id: {"mode": str, "history": list}}
sessions = {}

CHOOSING_MODE, TALKING = range(2)

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

    # Mode selection
    if text == "⚖️ Совет":
        sessions[user_id]["mode"] = "СОВЕТ"
        await update.message.reply_text(
            "⚖️ *Режим: Совет*\n\nОпишите ситуацию, в которой вы не знаете, как поступить...",
            parse_mode="Markdown",
            reply_markup=get_mode_keyboard()
        )
        return TALKING

    elif text == "🔍 Интерпретация":
        sessions[user_id]["mode"] = "ИНТЕРПРЕТАЦИЯ"
        await update.message.reply_text(
            "🔍 *Режим: Интерпретация*\n\nОпишите событие, воспоминание или поведение, которое вас занимает...",
            parse_mode="Markdown",
            reply_markup=get_mode_keyboard()
        )
        return TALKING

    elif text == "🌙 Сон":
        sessions[user_id]["mode"] = "СОН"
        await update.message.reply_text(
            "🌙 *Режим: Сон*\n\nРасскажите свой сон — любые детали, ощущения, образы...",
            parse_mode="Markdown",
            reply_markup=get_mode_keyboard()
        )
        return TALKING

    elif text == "🔄 Сменить режим":
        sessions[user_id]["mode"] = None
        await update.message.reply_text(
            "Выберите новый режим:",
            reply_markup=get_mode_keyboard()
        )
        return CHOOSING_MODE

    elif text == "🗑 Новая сессия":
        sessions[user_id] = {"mode": None, "history": []}
        await update.message.reply_text(
            "Сессия завершена. Выберите режим для новой:",
            reply_markup=get_mode_keyboard()
        )
        return CHOOSING_MODE

    # If no mode selected
    if not sessions[user_id].get("mode"):
        await update.message.reply_text(
            "Пожалуйста, сначала выберите режим:",
            reply_markup=get_mode_keyboard()
        )
        return CHOOSING_MODE

    # Send to Claude
    mode = sessions[user_id]["mode"]
    history = sessions[user_id]["history"]

    user_content = f"РЕЖИМ: {mode}\n\n{text}"
    history.append({"role": "user", "content": user_content})

    # Keep last 10 messages to avoid token overflow
    if len(history) > 10:
        history = history[-10:]
        sessions[user_id]["history"] = history

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=history
        )
        reply = response.content[0].text
        history.append({"role": "assistant", "content": reply})
        sessions[user_id]["history"] = history

        await update.message.reply_text(reply, parse_mode="Markdown", reply_markup=get_mode_keyboard())

    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {str(e)}", reply_markup=get_mode_keyboard())

    return TALKING

async def error_handler(update, context):
    print(f"Error: {context.error}")

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
    app.add_error_handler(error_handler)

    print("Соломон запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
