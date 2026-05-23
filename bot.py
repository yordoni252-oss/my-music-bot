import os
import telebot
import yt_dlp

# Tokenni server sozlamalaridan oladi
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 Salom! Men sizga YouTube'dan musiqa topib beruvchi botman.\n\n🎵 Qo'shiq nomini yozib yuboring:")

@bot.message_handler(func=lambda message: True)
def search_song(message):
    query = message.text
    status_msg = bot.reply_to(message, "🔍 Qo'shiq qidirilmoqda, bir oz kuting...")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 5 ta eng yaxshi natijani qidiramiz
            search_results = ydl.extract_info(f"ytsearch5:{query}", download=False)['entries']
            
            if not search_results:
                bot.edit_message_text("❌ Hech narsa topilmadi. Boshqa nom yozib ko'ring.", chat_id=message.chat.id, message_id=status_msg.message_id)
                return
            
            keyboard = telebot.types.InlineKeyboardMarkup()
            text = "🎵 **Topilgan qo'shiqlar:**\n\n"
            
            for i, video in enumerate(search_results, 1):
                title = video.get('title', 'Noma'lum')
                duration = video.get('duration', 0)
                minutes = duration // 60
                seconds = duration % 60
                time_str = f"{minutes}:{seconds:02d}"
                
                text += f"{i}. {title} ⏱️ {time_str}\n"
                
                # Tugmaga video IDsini bog'laymiz
                button = telebot.types.InlineKeyboardButton(
                    text=f"🎵 {i}-qo'shiqni tinglash", 
                    callback_data=f"song_{video['id']}"
                )
                keyboard.add(button)
                
            bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
            bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode="Markdown")
            
    except Exception as e:
        bot.edit_message_text("❌ Qidiruvda xatolik yuz berdi.", chat_id=message.chat.id, message_id=status_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("song_"))
def play_song(call):
    video_id = call.data.split("_")[1]
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    bot.answer_callback_query(call.id, "⚡ Musiqa yuklanmoqda...")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            audio_url = info['url']
            title = info.get('title', 'Musiqa')
            performer = info.get('uploader', 'Uz Music')
            
            # Qo'shiqni serverga yuklamasdan, to'g'ridan-to'g'ri Telegram'ga uzatamiz
            bot.send_audio(
                chat_id=call.message.chat.id,
                audio=audio_url,
                title=title,
                performer=performer
            )
    except Exception as e:
        bot.send_message(call.message.chat.id, "❌ Audio uzatishda xato. Boshqa qo'shiqni tanlang.")
        
                     
