import os
import glob
import yt_dlp
import telebot

BOT_TOKEN = "8731179006:AAHhpMLPd8ljQPDvTGcwo7xwy_wDSaJQIEk"
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🎵 Salom! Qo'shiq nomini yozing, to'liq yuboraman!")

@bot.message_handler(func=lambda m: True)
def qushiq(message):
    uid = message.chat.id
    msg = bot.reply_to(message, "⬇️ Yuklanmoqda, kuting...")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"/tmp/{uid}.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"ytsearch1:{message.text}", download=True
            )
            if "entries" in info:
                info = info["entries"][0]

            title = info.get("title", "Musiqa")
            artist = info.get("uploader", "Ijrochi")
            duration = info.get("duration", 0)

        files = glob.glob(f"/tmp/{uid}.*")
        if not files:
            raise Exception("Fayl topilmadi")

        filepath = files[0]

        bot.edit_message_text("⬆️ Yuborilmoqda...", uid, msg.message_id)

        with open(filepath, "rb") as audio:
            bot.send_audio(
                uid, audio,
                title=title,
                performer=artist,
                duration=duration
            )

        bot.delete_message(uid, msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Xato: {e}", uid, msg.message_id)

    finally:
        for f in glob.glob(f"/tmp/{uid}.*"):
            os.remove(f)

bot.infinity_polling()
