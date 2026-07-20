import telebot
from telebot.apihelper import ApiTelegramException
import sqlite3
import time
import threading
import sys

# =====================================================================
# ⚙️ CONFIGURATION 
# =====================================================================
API_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"  
OWNER_ID = 7415265825  
FREE_GROUP_ID = -4477244119
PRIVATE_CHANNEL_ID = -3870933647
# =====================================================================

bot = telebot.TeleBot(API_TOKEN)

# Database Setup
def init_db():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS member_activity (user_id INTEGER PRIMARY KEY, leave_timestamp REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS pending_channel_requests (user_id INTEGER, chat_id INTEGER, request_time REAL, PRIMARY KEY (user_id, chat_id))")
    conn.commit()
    conn.close()

init_db()

# 1. WELCOME & START COMMAND + NOTIFICATION
@bot.message_handler(commands=['start'])
def start_message(message):
    user = message.from_user
    # Admin ko notification
    bot.send_message(OWNER_ID, f"🔔 New User Started Bot:\nName: {user.first_name}\nID: {user.id}")
    
    # User ko Welcome
    welcome_text = (
        f"✨ Bismillah! Welcome to Gold Expert Fx, {user.first_name}!\n\n"
        "Your message has been received by our management. "
        "We will get back to you shortly."
    )
    bot.reply_to(message, welcome_text)

# 2. RELAY SYSTEM (USER -> ADMIN & ADMIN -> USER)
@bot.message_handler(func=lambda message: message.chat.type == 'private' and message.from_user.id != OWNER_ID)
def relay_to_owner(message):
    bot.forward_message(OWNER_ID, message.chat.id, message.message_id)

@bot.message_handler(func=lambda message: message.chat.id == OWNER_ID and message.reply_to_message)
def reply_to_user(message):
    target_user_id = message.reply_to_message.forward_from.id
    bot.send_message(target_user_id, message.text)

# 3. LINK FILTER & JOIN REQUESTS (Same as your logic but 7h)
@bot.chat_join_request_handler()
def catch_requests(update):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO pending_channel_requests VALUES (?, ?, ?)", 
                   (update.from_user.id, update.chat.id, time.time()))
    conn.commit()
    conn.close()

def continuous_request_processor():
    while True:
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, chat_id FROM pending_channel_requests")
        rows = cursor.fetchall()
        
        for user_id, chat_id in rows:
            cursor.execute("SELECT leave_timestamp FROM member_activity WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            # 7 Hours Logic (7 * 3600 = 25200 seconds)
            if not row or (time.time() - row[0]) >= 25200:
                try:
                    bot.approve_chat_join_request(chat_id, user_id)
                    cursor.execute("DELETE FROM pending_channel_requests WHERE user_id = ?", (user_id,))
                except: pass
        
        conn.commit()
        conn.close()
        time.sleep(60)

# 🚀 RUNNER
if __name__ == "__main__":
    threading.Thread(target=continuous_request_processor, daemon=True).start()
    print("🚀 Bot is running...")
    bot.polling(none_stop=True)
                     
