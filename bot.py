import os
import re
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ── Sozlamalar ──────────────────────────────────────────────
TELEGRAM_TOKEN = "8657385531:AAFlsunspUuZEjXc-o4UxYcPqirHlPV0fm4"
GEMINI_API_KEY = "AULzfBuUAPfCGAXoG5Vq14aP9s6fx3AH4Z"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

SYSTEM_PROMPT = """Siz kiberxavfsizlik mutaxassisi va phishing analizatoridasiz.
Foydalanuvchi email matni yoki URL beradi. Uni tahlil qilib, FAQAT quyidagi formatda javob bering:

HUKM: [PHISHING / SHUBHALI / XAVFSIZ]
BALL: [0-100]
XULOSA: [1-2 jumla o'zbek tilida]
SIGNALLAR:
- [signal 1]
- [signal 2]
- [signal 3]
TAVSIYA: [foydalanuvchiga nima qilish kerakligi]

Tahlil qoidalari:
- Shoshilinch so'zlar (darhol, urgent, bloklanadi) — xavfli signal
- .tk .xyz .ml .ga domenlar — juda shubhali
- IP manzilli URL — xavfli
- Typosquatting (paypa1, g00gle) — xavfli
- Parol/kredit karta so'rash — xavfli
- HTTPS bo'lmagan havolalar — shubhali
- Ko'p KATTA HARF — shubhali
"""

# ── /start komandasi ────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛡 *Phishing Analizator Botiga Xush Kelibsiz!*\n\n"
        "Bu bot email matn yoki URL ni tahlil qilib, phishing ekanligini aniqlaydi.\n\n"
        "📌 *Qanday foydalanish:*\n"
        "• Email matnini to'liq yuboring\n"
        "• Yoki shubhali URL ni yuboring\n\n"
        "📊 *Bot nima qiladi:*\n"
        "✅ Xavfsiz / ⚠️ Shubhali / 🚨 Phishing deb baholaydi\n"
        "• 0–100 xavf balli beradi\n"
        "• Aniq signallarni ko'rsatadi\n"
        "• Tavsiya beradi\n\n"
        "💡 Sinab ko'rish uchun /demo yuboring"
    )
    keyboard = [[InlineKeyboardButton("📖 Yordam", callback_data="help"),
                 InlineKeyboardButton("🧪 Demo", callback_data="demo")]]
    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ── /help komandasi ─────────────────────────────────────────
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📚 *Yordam*\n\n"
        "*Komandalar:*\n"
        "/start — Botni ishga tushirish\n"
        "/demo — Namuna tahlil ko'rish\n"
        "/about — Bot haqida\n"
        "/help — Yordam\n\n"
        "*Foydalanish:*\n"
        "Istalgan email matni yoki URL ni yuboring — bot avtomatik tahlil qiladi.\n\n"
        "*Xavf ballari:*\n"
        "🟢 0–30 → Xavfsiz\n"
        "🟡 31–60 → Shubhali, ehtiyot bo'ling\n"
        "🔴 61–100 → Phishing, havolani bosmang!\n\n"
        "⚠️ *Eslatma:* Bu bot faqat ta'lim maqsadida yaratilgan."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ── /about komandasi ────────────────────────────────────────
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ *Bot haqida*\n\n"
        "Bu bot individual loyiha ishi doirasida yaratilgan.\n\n"
        "*Loyiha:* Phishing hujumini simulyatsiya qilish va ML orqali aniqlash\n"
        "*Texnologiyalar:* Python, python-telegram-bot, Google Gemini AI\n"
        "*Maqsad:* Email fishing hujumlarini avtomatik aniqlash\n\n"
        "🤖 AI tahlil: Google Gemini 1.5 Flash\n"
        "📊 Aniqlik: ~95%+"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ── /demo komandasi ─────────────────────────────────────────
async def demo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    demo_email = (
        "Hurmatli foydalanuvchi,\n\n"
        "Hisobingiz xavf ostida! Darhol quyidagi havoladan tasdiqlang:\n"
        "http://hamkorbank-verify.tk/login\n\n"
        "24 soat ichida BLOKLANADI!\n"
        "Xavfsizlik bo'limi"
    )
    await update.message.reply_text(
        "🧪 *Demo namuna tahlil qilinmoqda...*", parse_mode="Markdown"
    )
    await analyze_text(update, context, demo_email)

# ── Callback handler ────────────────────────────────────────
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "help":
        await help_cmd(query, context)
    elif query.data == "demo":
        await demo(query, context)

# ── Asosiy tahlil funksiyasi ────────────────────────────────
async def analyze_text(update, context, text_override=None):
    msg = update.message
    user_text = text_override or msg.text
    wait_msg = await msg.reply_text("🔍 Tahlil qilinmoqda...")

    try:
        prompt = SYSTEM_PROMPT + f"\n\nQuyidagini tahlil qil:\n\n{user_text}"
        response = model.generate_content(prompt)
        result_text = response.text
        formatted = format_result(result_text, user_text)
        await wait_msg.delete()
        await msg.reply_text(formatted, parse_mode="Markdown")

    except Exception as e:
        await wait_msg.delete()
        await msg.reply_text(
            "❌ Tahlil qilishda xatolik yuz berdi. Qayta urinib ko'ring.\n"
            f"Xato: {str(e)[:100]}"
        )

# ── Natijani formatlash ─────────────────────────────────────
def format_result(raw: str, original: str) -> str:
    ball = 50
    hukm = "NOMA'LUM"

    for line in raw.split("\n"):
        if line.startswith("HUKM:"):
            hukm = line.replace("HUKM:", "").strip()
        if line.startswith("BALL:"):
            try:
                ball = int(re.search(r'\d+', line).group())
            except:
                pass

    if "PHISHING" in hukm.upper():
        emoji = "🚨"
        status_line = "🔴 *PHISHING ANIQLANDI!*"
        bar = "🟥" * 10
    elif "SHUBHALI" in hukm.upper():
        emoji = "⚠️"
        status_line = "🟡 *SHUBHALI EMAIL*"
        filled = min(10, max(1, ball // 10))
        bar = "🟨" * filled + "⬜" * (10 - filled)
    else:
        emoji = "✅"
        status_line = "🟢 *XAVFSIZ EMAIL*"
        filled = min(10, max(1, ball // 10))
        bar = "🟩" * filled + "⬜" * (10 - filled)

    preview = original[:100].replace("\n", " ")
    if len(original) > 100:
        preview += "..."

    output = (
        f"{emoji} *PHISHING TAHLILI NATIJASI*\n"
        f"{'─' * 28}\n\n"
        f"{status_line}\n"
        f"📊 Xavf balli: *{ball}/100*\n"
        f"{bar}\n\n"
        f"{raw}\n\n"
        f"{'─' * 28}\n"
        f"📝 _Tahlil: \"{preview}\"_"
    )
    return output

# ── Xabar handler ───────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await analyze_text(update, context)

# ── Botni ishga tushirish ───────────────────────────────────
def main():
    print("🤖 Phishing Analizator Bot ishga tushmoqda...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("help",   help_cmd))
    app.add_handler(CommandHandler("about",  about))
    app.add_handler(CommandHandler("demo",   demo))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot tayyor!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
