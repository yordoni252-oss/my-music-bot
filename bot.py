import os
import telebot
import requests

# Tokenni server sozlamalaridan oladi
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 Salom! Men sizga istalgan musiqani tez va muammosiz topib beruvchi botman.\n\n🎵 Qo'shiq nomini yoki ijrochini yozib yuboring:")

@bot.message_handler(func=lambda message: True)
def search_song(message):
    query = message.text
    status_msg = bot.reply_to(message, "🔍 Qo'shiq qidirilmoqda...")
    
    # Muammosiz va bepul ochiq musiqa API manzili
    search_url = f"https://itunes.apple.com/search?term={query}&entity=song&limit=5"
    
    try:
        response = requests.get(search_url).json()
        results = response.get('results', [])
        
        if not results:
            bot.edit_message_text("❌ Hech narsa topilmadi. Boshqa nom yozib ko'ring.", chat_id=message.chat.id, message_id=status_msg.message_id)
            return
        
        keyboard = telebot.types.InlineKeyboardMarkup()
        text = "🎵 **Topilgan qo'shiqlar:**\n\n"
        
        for i, track in enumerate(results, 1):
            title = track.get('trackName', 'Noma'lum trek')
            artist = track.get('artistName', 'Noma'lum ijrochi')
            track_id = track.get('trackId')
            
            text += f"{i}. {artist} - {title}\n"
            
            # Tugmaga qo'shiq IDsini biriktiramiz
            button = telebot.types.InlineKeyboardButton(
                text=f"🎵 {i}-qo'shiqni yuklash", 
                callback_data=f"itunes_{track_id}"
            )
            keyboard.add(button)
            
        bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
        bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        bot.edit_message_text("❌ Qidiruv tizimida xatolik yuz berdi.", chat_id=message.chat.id, message_id=status_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("itunes_"))
def play_song(call):
    track_id = call.data.split("_")[1]
    track_url = f"https://itunes.apple.com/lookup?id={track_id}"
    
    bot.answer_callback_query(call.id, "⚡ Musiqa yuborilmoqda...")
    
    try:
        response = requests.get(track_url).json()
        track = response.get('results', [])[0]
        
        audio_url = track.get('previewUrl') # To'g'ridan-to'g'ri audio havola
        title = track.get('trackName', 'Musiqa')
        performer = track.get('artistName', 'Ijrochi')
        
        # Hech qanday yuklashlarsiz, to'g'ridan-to'g'ri Telegram serveriga havola uzatiladi
        bot.send_audio(
            chat_id=call.message.chat.id,
            audio=audio_url,
            title=title,
            performer=performer
        )
    except Exception as e:
        bot.send_message(call.message.chat.id, "❌ Audio uzatishda xato yuz berdi.")
        
