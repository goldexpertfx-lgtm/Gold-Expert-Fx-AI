import telebot
import sqlite3
import time
import threading
import re

# ================= CONFIGURATION =================
API_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"  # Apna token daalein
OWNER_ID = 7415265825
FREE_GROUP_ID = -4477244119 # Gold Expert Fx Community
PRIVATE_CHANNEL_ID = -3870933647 # Private Channel
# =================================================

bot = telebot.TeleBot(API_TOKEN)

# Database Setup
def init_db():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS pending_requests (user_id INTEGER, chat_id INTEGER, request_time REAL, PRIMARY KEY (user_id, chat_id))")
    conn.commit()
    conn.close()

init_db()

# 1. WELCOME MESSAGE & NOTIFICATION
@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    bot.send_message(OWNER_ID, f"🔔 New User: {user.first_name} (@{user.username}) ID: {user.id}")
    welcome_text = "✨ Bismillah! Welcome to Gold Expert Fx. Your message has been received by our management. We will get back to you shortly."
    bot.reply_to(message, welcome_text)

# 2. RELAY SYSTEM (User <-> Owner)
@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.from_user.id != OWNER_ID)
def relay_to_owner(message):
    bot.forward_message(OWNER_ID, message.chat.id, message.message_id)

@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def reply_to_user(message):
    bot.send_message(message.reply_to_message.forward_from.id, message.text)

# 3. LINK FILTERING (Strict)
@bot.message_handler(content_types=['text', 'caption'])
def filter_links(message):
    if message.chat.id == FREE_GROUP_ID:
        text = (message.text or message.caption or "").lower()
        # Link detect karein (Owner ka link allowed)
        if ("http" in text or "t.me/" in text or "www." in text):
            if message.from_user.id != OWNER_ID and "goldexpertfxcommunity" not in text:
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                except: pass

# 4. JOIN REQUEST (7h DELAY)
@bot.chat_join_request_handler()
def handle_requests(update):
    if update.chat.id == PRIVATE_CHANNEL_ID:
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO pending_requests VALUES (?, ?, ?)", (update.from_user.id, update.chat.id, time.time()))
        conn.commit()
        conn.close()

def process_requests():
    while True:
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, chat_id, request_time FROM pending_requests")
        for user_id, chat_id, r_time in cursor.fetchall():
            if time.time() - r_time >= 25200: # 7 Hours
                try:
                    bot.approve_chat_join_request(chat_id, user_id)
                    cursor.execute("DELETE FROM pending_requests WHERE user_id = ?", (user_id,))
                except: pass
        conn.commit()
        conn.close()
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=process_requests, daemon=True).start()
    bot.polling(none_stop=True)
    
