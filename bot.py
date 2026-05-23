import os
import requests
import telebot

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot = telebot.TeleBot(BOT_TOKEN)

def format_duration(ms):
    if not ms:
        return "0:00"
    seconds = ms // 1000
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(
        message,
        "👋 Salom! Men sizga istalgan musiqani tez va muammosiz topib beruvchi botman.\n\n"
        "🎵 Qo'shiq nomini yoki ijrochini yozib yuboring:"
    )

@bot.message_handler(func=lambda message: True)
def search_song(message):
    query = message.text
    status_msg = bot.reply_to(message, "🔍 Qo'shiq qidirilmoqda...")

    search_url = f"https://itunes.apple.com/search?term={query}&entity=song&limit=5"

    try:
        response = requests.get(search_url, timeout=10).json()
        results = response.get('results', [])

        if not results:
            bot.edit_message_text(
                "❌ Hech narsa topilmadi. Boshqa nom yozib ko'ring.",
                chat_id=message.chat.id,
                message_id=status_msg.message_id
            )
            return

        keyboard = telebot.types.InlineKeyboardMarkup()
        text = "🎵 *Topilgan qo'shiqlar:*\n\n"

        for i, track in enumerate(results, 1):
            # FIX: apostrof muammosi — double quotes ishlatildi
            title = track.get('trackName', "Noma'lum trek")
            artist = track.get('artistName', "Noma'lum ijrochi")
            duration = format_duration(track.get('trackTimeMillis'))
            track_id = track.get('trackId')

            text += f"{i}. *{artist}* — {title} ⏱ {duration}\n"

            button = telebot.types.InlineKeyboardButton(
                text=f"🎵 {i}. {artist} - {title[:30]}",
                callback_data=f"itunes_{track_id}"
            )
            keyboard.add(button)

        bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    except Exception as e:
        bot.edit_message_text(
            "❌ Qidiruv tizimida xatolik yuz berdi.",
            chat_id=message.chat.id,
            message_id=status_msg.message_id
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("itunes_"))
def play_song(call):
    track_id = call.data.split("_")[1]
    track_url = f"https://itunes.apple.com/lookup?id={track_id}"

    bot.answer_callback_query(call.id, "⚡ Musiqa yuborilmoqda...")

    try:
        response = requests.get(track_url, timeout=10).json()
        results = response.get('results', [])

        if not results:
            bot.send_message(call.message.chat.id, "❌ Qo'shiq ma'lumoti topilmadi.")
            return

        track = results[0]
        audio_url = track.get('previewUrl')

        if not audio_url:
            bot.send_message(call.message.chat.id, "❌ Bu qo'shiq uchun audio mavjud emas.")
            return

        title = track.get('trackName', "Noma'lum")
        performer = track.get('artistName', "Noma'lum")

        # FIX: URL o'rniga bytes sifatida yuborish — ishonchliroq
        audio_response = requests.get(audio_url, timeout=15)
        audio_response.raise_for_status()

        bot.send_audio(
            chat_id=call.message.chat.id,
            audio=audio_response.content,
            title=title,
            performer=performer,
            caption="⚠️ Bu 30 soniyalik preview (iTunes cheklovi)"
        )

    except requests.exceptions.RequestException:
        bot.send_message(call.message.chat.id, "❌ Audio yuklab olishda tarmoq xatosi yuz berdi.")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Xatolik: {str(e)}")

bot.polling(none_stop=True)
