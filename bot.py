import telebot
from telebot.apihelper import ApiTelegramException
import sqlite3
import time
import threading
import re

# =====================================================================
# ⚙️ CONFIGURATION (Sirf is naye bot ka Token aur details dalein)
# =====================================================================
API_TOKEN = "8851943854:AAHz1KdIVND5QPw2t-PAKPqj6Th4j7eTO28"  # Is naye bot ka real token dalein
OWNER_ID = 7415265825  # ⚠️ APNI Telegram ID dalein

# Channel & Group IDs
FREE_GROUP_ID = -4477244119  
PRIVATE_CHANNEL_ID = -3870933647  
# =====================================================================

bot = telebot.TeleBot(API_TOKEN)

# Database Setup (Is naye bot ke liye alag database name use kiya hai taake purana safe rahe)
def init_db():
    conn = sqlite3.connect("new_join_filter_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS member_activity (
            user_id INTEGER PRIMARY KEY,
            leave_timestamp REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_channel_requests (
            user_id INTEGER,
            chat_id INTEGER,
            request_time REAL,
            PRIMARY KEY (user_id, chat_id)
        )
    """)
    conn.commit()
    conn.close()

init_db()


# 📥 New Join Requests Incoming Collector (Buffer - Saves requests, never declines/dismisses them)
@bot.chat_join_request_handler()
def catch_and_buffer_requests(update):
    user_id = update.from_user.id
    chat_id = update.chat.id
    current_time = time.time()
    
    conn = sqlite3.connect("new_join_filter_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO pending_channel_requests (user_id, chat_id, request_time) 
        VALUES (?, ?, ?)
    """, (user_id, chat_id, current_time))
    conn.commit()
    conn.close()


# 🛡️ Main Group Filter (System Notification Cleaner + Strict Link Only Remover)
@bot.message_handler(content_types=['text', 'new_chat_members', 'left_chat_member'])
def handle_group_messages(message):
    # 1. System Notifications Auto Clear (Join/Leave messages)
    if message.content_type in ['new_chat_members', 'left_chat_member']:
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception:
            pass

        # Track the exact leave time log for 12 hours check
        if message.chat.id == FREE_GROUP_ID and message.left_chat_member:
            left_user_id = message.left_chat_member.id
            leave_time = time.time()
            
            conn = sqlite3.connect("new_join_filter_bot.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO member_activity (user_id, leave_timestamp) 
                VALUES (?, ?)
            """, (left_user_id, leave_time))
            conn.commit()
            conn.close()
        return

    # 2. Strict Link Eraser (Only erases links, no ban/kick/remove commands applied)
    if message.chat.id == FREE_GROUP_ID and message.text:
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+)'
        has_link = re.search(url_pattern, message.text, re.IGNORECASE)

        if has_link:
            # Condition A: Owner posts directly by hand opening the group -> ALLOW
            if message.from_user.id == OWNER_ID and message.forward_from_chat is None:
                return

            # Condition B: Auto-forwarded message linked from Private Channel -> DELETE
            if message.forward_from_chat and message.forward_from_chat.id == PRIVATE_CHANNEL_ID:
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                except Exception:
                    pass
                return

            # Condition C: Any other ordinary member sends a link -> DELETE
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except Exception:
                pass


# 🔄 24/7 Global Engine (Scans All Old Historical Data + Real-time Naye Join Requests)
def continuous_request_processor():
    while True:
        try:
            conn = sqlite3.connect("new_join_filter_bot.db")
            cursor = conn.cursor()
            # Grabs old historical logs as well as new buffered records
            cursor.execute("SELECT user_id, chat_id FROM pending_channel_requests")
            pending_requests = cursor.fetchall()
            conn.close()

            current_now = time.time()
            twelve_hours_in_seconds = 12 * 60 * 60

            for user_id, chat_id in pending_requests:
                is_in_group = False
                try:
                    chat_member = bot.get_chat_member(FREE_GROUP_ID, user_id)
                    if chat_member.status in ['member', 'administrator', 'creator']:
                        is_in_group = True
                except Exception:
                    is_in_group = False

                # If the user is actively inside the free group -> DO NOT APPROVE (Hold in buffer safely)
                if is_in_group:
                    continue

                # If user is outside the free community group, verify logs
                conn = sqlite3.connect("new_join_filter_bot.db")
                cursor = conn.cursor()
                cursor.execute("SELECT leave_timestamp FROM member_activity WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                conn.close()

                if row:
                    leave_timestamp = row[0]
                    elapsed_time = current_now - leave_timestamp
                    
                    # Approve ONLY after 12 full hours have elapsed since leaving
                    if elapsed_time >= twelve_hours_in_seconds:
                        execute_approval(user_id, chat_id)
                else:
                    # Fresh user or request cleared for entry
                    execute_approval(user_id, chat_id)

        except Exception:
            pass
            
        time.sleep(20)

def execute_approval(user_id, chat_id):
    try:
        bot.approve_chat_join_request(chat_id, user_id)
    except Exception:
        pass
    
    conn = sqlite3.connect("new_join_filter_bot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pending_channel_requests WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    # Runs the multi-threaded scanning process continuously in the background
    threading.Thread(target=continuous_request_processor, daemon=True).start()
    
    print("New Gold Expert Filter Bot is fully active (Links + Join Requests Only)...")
    bot.infinity_polling(timeout=15)
                      
