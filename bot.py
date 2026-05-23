import os
import json
import threading
import logging
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
import yt_dlp

# ─── Logging sozlamalari ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ─── Muhit o'zgaruvchilari ────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
PORT      = int(os.environ.get("PORT", 8080))

bot  = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app  = Flask(__name__)

# Foydalanuvchi qidiruv natijalarini vaqtinchalik saqlash
# { user_id: [ {title, url, duration, channel}, ... ] }
search_cache: dict[int, list[dict]] = {}

# ─── Flask health-check ───────────────────────────────────────────────────────
@app.route("/")
def index():
    return "🎵 Music Bot is running!", 200

@app.route("/health")
def health():
    return {"status": "ok"}, 200

# ─── Yordamchi funksiyalar ────────────────────────────────────────────────────

def search_youtube_music(query: str, max_results: int = 5) -> list[dict]:
    """yt-dlp orqali YouTube Music'dan qo'shiq qidiradi."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,          # faqat metadata, yuklamaydi
        "default_search": "ytsearch",
        "playlist_items": f"1-{max_results}",
    }
    search_query = f"ytsearch{max_results}:{query}"
    results = []

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_query, download=False)
        entries = info.get("entries", [])
        for entry in entries:
            if entry:
                duration_sec = entry.get("duration") or 0
                minutes, seconds = divmod(int(duration_sec), 60)
                results.append({
                    "title":    entry.get("title",    "Noma'lum"),
                    "url":      entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id','')}",
                    "duration": f"{minutes}:{seconds:02d}",
                    "channel":  entry.get("uploader") or entry.get("channel", "—"),
                    "video_id": entry.get("id", ""),
                })
    return results


def download_audio_mp3(video_url: str, output_dir: str = "/tmp") -> str | None:
    """YouTube URL'dan mp3 yuklab, fayl yo'lini qaytaradi."""
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{output_dir}/%(id)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [{
            "key":            "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        # Fayl hajmini cheklash (Telegram 50 MB limiti)
        "max_filesize": 48 * 1024 * 1024,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info      = ydl.extract_info(video_url, download=True)
            video_id  = info.get("id", "")
            file_path = f"{output_dir}/{video_id}.mp3"
            if os.path.exists(file_path):
                return file_path
            # Ba'zan kengaytma farq qiladi, topib olamiz
            for f in os.listdir(output_dir):
                if f.startswith(video_id) and f.endswith(".mp3"):
                    return os.path.join(output_dir, f)
    except Exception as e:
        logger.error(f"Audio yuklab olishda xato: {e}")
    return None


def make_results_keyboard(results: list[dict]) -> InlineKeyboardMarkup:
    """Top-5 natija uchun inline klaviatura yaratadi."""
    kb = InlineKeyboardMarkup(row_width=1)
    for i, track in enumerate(results):
        label = f"🎵 {i+1}. {track['title'][:40]} [{track['duration']}]"
        kb.add(InlineKeyboardButton(label, callback_data=f"play:{i}"))
    return kb


# ─── Bot handlerlar ───────────────────────────────────────────────────────────

@bot.message_handler(commands=["start", "help"])
def cmd_start(message):
    text = (
        "👋 <b>Music Bot'ga xush kelibsiz!</b>\n\n"
        "🎧 Qo'shiq nomi yoki ijrochi ismini yozing,\n"
        "men YouTube Music'dan <b>Top-5</b> variantni topib beraman.\n\n"
        "📌 <i>Misol:</i> <code>Dua Lipa Levitating</code>"
    )
    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_search(message):
    query   = message.text.strip()
    user_id = message.from_user.id

    if not query:
        bot.reply_to(message, "⚠️ Iltimos, qo'shiq nomi kiriting.")
        return

    # Qidiruv jarayoni xabarini yuborish
    wait_msg = bot.reply_to(message, "🔍 <b>Qidirilmoqda...</b>")

    try:
        results = search_youtube_music(query, max_results=5)

        if not results:
            bot.edit_message_text(
                "❌ Hech narsa topilmadi. Boshqa so'z bilan urinib ko'ring.",
                chat_id=message.chat.id,
                message_id=wait_msg.message_id
            )
            return

        # Keshga saqlash
        search_cache[user_id] = results

        # Natijalar ro'yxatini chiroyli chiqarish
        lines = ["🎶 <b>Topilgan natijalar:</b>\n"]
        for i, t in enumerate(results, 1):
            lines.append(
                f"{i}. <b>{t['title']}</b>\n"
                f"   👤 {t['channel']}  ⏱ {t['duration']}"
            )
        lines.append("\n👇 <b>Tinglamoqchi bo'lganingizni tanlang:</b>")

        bot.edit_message_text(
            "\n".join(lines),
            chat_id=message.chat.id,
            message_id=wait_msg.message_id,
            reply_markup=make_results_keyboard(results),
        )

    except Exception as e:
        logger.error(f"Qidiruv xatosi: {e}")
        bot.edit_message_text(
            "❌ Qidiruv vaqtida xato yuz berdi. Iltimos, qayta urinib ko'ring.",
            chat_id=message.chat.id,
            message_id=wait_msg.message_id,
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("play:"))
def handle_play(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    try:
        index   = int(call.data.split(":")[1])
        results = search_cache.get(user_id)

        if not results or index >= len(results):
            bot.answer_callback_query(call.id, "⚠️ Qidiruv muddati tugagan. Qayta qidiring.")
            return

        track = results[index]
        bot.answer_callback_query(call.id, "⏬ Yuklanmoqda...")

        # Progress xabari
        dl_msg = bot.send_message(
            chat_id,
            f"⏳ <b>{track['title']}</b> yuklanmoqda...\n"
            f"👤 {track['channel']}  ⏱ {track['duration']}"
        )

        file_path = download_audio_mp3(track["url"])

        if not file_path:
            bot.edit_message_text(
                "❌ Audio yuklab olishda xato. Boshqa qo'shiqni tanlang.",
                chat_id=chat_id,
                message_id=dl_msg.message_id,
            )
            return

        # Audiони yuborish
        with open(file_path, "rb") as audio_file:
            bot.send_audio(
                chat_id,
                audio_file,
                title=track["title"],
                performer=track["channel"],
                caption=(
                    f"🎵 <b>{track['title']}</b>\n"
                    f"👤 {track['channel']}  ⏱ {track['duration']}"
                ),
            )

        # Vaqtinchalik faylni o'chirish
        try:
            os.remove(file_path)
        except OSError:
            pass

        # Progress xabarini o'chirish
        bot.delete_message(chat_id, dl_msg.message_id)

    except Exception as e:
        logger.error(f"Play callback xatosi: {e}")
        try:
            bot.send_message(chat_id, "❌ Xato yuz berdi. Iltimos, qayta urinib ko'ring.")
        except Exception:
            pass


# ─── Asosiy ishga tushirish ───────────────────────────────────────────────────

def run_flask():
    """Flask serverni alohida threadda ishga tushiradi."""
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)


def run_bot():
    """Bot polling'ni doimiy xato ushlovchi bilan ishga tushiradi."""
    logger.info("🤖 Bot polling boshlandi...")
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=20)
        except Exception as e:
            logger.error(f"Polling xatosi, qayta ulanmoqda: {e}")
            import time; time.sleep(5)


if __name__ == "__main__":
    logger.info(f"🚀 Server port {PORT} da ishga tushirilmoqda...")

    # Flask — alohida thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Bot — asosiy thread
    run_bot()
