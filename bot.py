import os
import yt_dlp
import telebot

BOT_TOKEN = os.environ.get("BOT_TOKEN", "TOKEN_SHUNGA_YOZING")
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🎵 Qo'shiq nomini yozing — to'liq MP3 yuboraman!")

@bot.message_handler(func=lambda m: True)
def qushiq(message):
    msg = bot.reply_to(message, "🔍 Qidirilmoqda...")

    query = message.text
    filepath = f"/tmp/{message.chat.id}.mp3"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"/tmp/{message.chat.id}.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "default_search": "ytsearch1",
        "quiet": True,
        "no_warnings": True,
    }

    try:
        bot.edit_message_text("⬇️ Yuklanmoqda...", message.chat.id, msg.message_id)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            if "entries" in info:
                info = info["entries"][0]

            title = info.get("title", "Musiqa")
            artist = info.get("uploader", "Ijrochi")
            duration = info.get("duration", 0)

        bot.edit_message_text("⬆️ Yuborilmoqda...", message.chat.id, msg.message_id)

        with open(filepath, "rb") as f:
            bot.send_audio(
                message.chat.id,
                f,
                title=title,
                performer=artist,
                duration=duration
            )

        bot.delete_message(message.chat.id, msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Xato yuz berdi: {e}", message.chat.id, msg.message_id)

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

bot.infinity_polling()
