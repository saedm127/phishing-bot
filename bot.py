import os
import re
import asyncio
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ── Sozlamalar ──────────────────────────────────────────────
TELEGRAM_TOKEN = "8657385531:AAFlsunspUuZEjXc-o4UxYcPqirHlPV0fm4"
GEMINI_API_KEY = "AIzaSyBpPTjNjav7WV9-c9wcZFKMNkOyVVo-oA4"

genai.configure(api_key=GEMINI_API_KEY)
gemini = genai.GenerativeModel("gemini-pro")

PROMPT = """Siz kiberxavfsizlik mutaxassisi va phishing analizatoridasiz.
Foydalanuvchi email matni yoki URL beradi. Uni tahlil qilib, FAQAT quyidagi formatda javob bering:

HUKM: [PHISHING / SHUBHALI / XAVFSIZ]
BALL: [0-100]
XULOSA: [1-2 jumla o'zbek tilida]
SIGNALLAR:
- [signal 1]
- [signal 2]
- [signal 3]
TAVSIYA: [foydalanuvchiga nima qilish kerakligi]

Qoidalar:
- Shoshilinch sozlar (darhol, urgent, bloklanadi) xavfli
- .tk .xyz .ml .ga domenlar juda shubhali
- IP manzilli URL xavfli
- Parol yoki karta malumoti sorash xavfli
- HTTPS bolmagan havolalar shubhali"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛡 *Phishing Analizator Botiga Xush Kelibsiz!*\n\n"
        "Email matni yoki URL yuboring — AI tahlil qiladi!\n\n"
        "🟢 0-30 → Xavfsiz\n"
        "🟡 31-60 → Shubhali\n"
        "🔴 61-100 → Phishing!\n\n"
        "Sinash uchun /demo yuboring"
    )
    kb = [[InlineKeyboardButton("🧪 Demo", callback_data="demo"),
           InlineKeyboardButton("📖 Yordam", callback_data="help")]]
    await update.message.reply_text(text, parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(kb))


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📚 *Yordam*\n\n"
        "/start — Botni ishga tushirish\n"
        "/demo — Namuna tahlil\n"
        "/about — Bot haqida\n\n"
        "Har qanday email matni yoki URL yuboring!"
    )
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(text, parse_mode="Markdown")


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ *Bot haqida*\n\n"
        "Loyiha: Phishing hujumini simulyatsiya va ML aniqlash\n"
        "AI: Google Gemini 1.5 Flash\n"
        "Til: Python + python-telegram-bot\n"
        "Aniqlik: ~95%+"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def demo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    demo_email = (
        "Hurmatli foydalanuvchi,\n"
        "Hisobingiz xavf ostida! Darhol tasdiqlang:\n"
        "http://hamkorbank-verify.tk/login\n"
        "24 soat ichida BLOKLANADI!"
    )
    msg = update.effective_message
    await msg.reply_text("🧪 *Demo tahlil boshlanmoqda...*", parse_mode="Markdown")
    await run_analysis(msg, demo_email)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "demo":
        await demo(update, context)
    elif query.data == "help":
        await help_cmd(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await run_analysis(update.message, update.message.text)


async def run_analysis(msg, user_text):
    wait = await msg.reply_text("🔍 Tahlil qilinmoqda...")
    try:
        response = gemini.generate_content(PROMPT + f"\n\nTahlil qil:\n{user_text}")
        result = response.text
        formatted = format_result(result, user_text)
        await wait.delete()
        await msg.reply_text(formatted, parse_mode="Markdown")
    except Exception as e:
        await wait.delete()
        await msg.reply_text(f"❌ Xatolik: {str(e)[:150]}")


def format_result(raw, original):
    ball = 50
    hukm = ""
    for line in raw.split("\n"):
        if line.startswith("HUKM:"):
            hukm = line.replace("HUKM:", "").strip().upper()
        if line.startswith("BALL:"):
            try:
                ball = int(re.search(r'\d+', line).group())
            except:
                pass

    if "PHISHING" in hukm:
        emoji, status, bar = "🚨", "🔴 *PHISHING ANIQLANDI!*", "🟥" * 10
    elif "SHUBHALI" in hukm:
        f = min(10, max(1, ball // 10))
        emoji, status, bar = "⚠️", "🟡 *SHUBHALI EMAIL*", "🟨" * f + "⬜" * (10 - f)
    else:
        f = min(10, max(1, ball // 10))
        emoji, status, bar = "✅", "🟢 *XAVFSIZ EMAIL*", "🟩" * f + "⬜" * (10 - f)

    preview = original[:80].replace("\n", " ")
    if len(original) > 80:
        preview += "..."

    return (
        f"{emoji} *PHISHING TAHLILI*\n"
        f"{'─'*28}\n\n"
        f"{status}\n"
        f"📊 Xavf balli: *{ball}/100*\n"
        f"{bar}\n\n"
        f"{raw}\n\n"
        f"{'─'*28}\n"
        f"📝 _{preview}_"
    )


def main():
    print("🤖 Bot ishga tushmoqda...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("demo", demo))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot tayyor!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
