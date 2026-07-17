import telebot
from telebot.apihelper import ApiTelegramException
import sqlite3
import time
import threading
import re
import sys

# =====================================================================
# ⚙️ CONFIGURATION 
# =====================================================================
API_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"  # ⚠️ Is naye bot ka real Telegram Token yahan dalein
OWNER_ID = 7415265825  # 👑 Aapki Admin ID locked hai

FREE_GROUP_ID = -4477244119
PRIVATE_CHANNEL_ID = -3870933647
# =====================================================================

# Strict Token Check
if not API_TOKEN:
    print("❌ ERROR: API_TOKEN is empty! Please insert your token.")
    sys.exit(1)

bot = telebot.TeleBot(API_TOKEN)

# Database Setup
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

# 📥 Join Requests Collector
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
    print(f"📥 New Join Request Buffered: User {user_id}")

# 🛡️ Group Link Filter & Auto-Delete Engine
@bot.message_handler(content_types=['text', 'new_chat_members', 'left_chat_member'])
def handle_group_messages(message):
    # 1. System Clean (Join/Leave Notification Remover)
    if message.content_type in ['new_chat_members', 'left_chat_member']:
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception:
            pass

        if message.chat.id == FREE_GROUP_ID and message.left_chat_member:
            left_user_id = message.left_chat_member.id
            leave_time = time.time()
            
            conn = sqlite3.connect("new_join_filter_bot.db")
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO member_activity VALUES (?, ?)", (left_user_id, leave_time))
            conn.commit()
            conn.close()
        return

    # 2. Channel Auto-Forward Link Cleaner
    if message.chat.id == FREE_GROUP_ID and message.text:
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+)'
        has_link = re.search(url_pattern, message.text, re.IGNORECASE)

        if has_link:
            is_from_private_channel = False
            
            # Channel linked feature tracking
            if message.forward_from_chat and message.forward_from_chat.id == PRIVATE_CHANNEL_ID:
                is_from_private_channel = True
            elif message.sender_chat and message.sender_chat.id == PRIVATE_CHANNEL_ID:
                is_from_private_channel = True

            # Drop link if matched from target channel
            if is_from_private_channel:
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                    print(f"🗑️ Deleted automatic linked channel post with link.")
                except Exception as e:
                    print(f"❌ Link deletion failed: {e}")
                return

            # Owner manual bypass check
            if message.from_user and message.from_user.id == OWNER_ID and not message.forward_from_chat:
                return

            # Delete any other standard links from members
            try:
                bot.delete_message(message.chat.id, message.message_id)
                print(f"🗑️ Deleted link from group user.")
            except Exception as e:
                print(f"❌ Error deleting member link: {e}")

# 🔄 24/7 Global Engine
def continuous_request_processor():
    while True:
        try:
            conn = sqlite3.connect("new_join_filter_bot.db")
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, chat_id FROM pending_channel_requests")
            pending_requests = cursor.fetchall()
            conn.close()

            current_now = time.time()
            twelve_hours = 12 * 60 * 60

            for user_id, chat_id in pending_requests:
                is_in_group = False
                try:
                    chat_member = bot.get_chat_member(FREE_GROUP_ID, user_id)
                    if chat_member.status in ['member', 'administrator', 'creator']:
                        is_in_group = True
                except Exception:
                    is_in_group = False

                if is_in_group:
                    continue

                conn = sqlite3.connect("new_join_filter_bot.db")
                cursor = conn.cursor()
                cursor.execute("SELECT leave_timestamp FROM member_activity WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                conn.close()

                if row and (current_now - row[0]) >= twelve_hours:
                    execute_approval(user_id, chat_id)
                elif not row:
                    execute_approval(user_id, chat_id)

        except Exception as e:
            print(f"⚠️ Loop warning: {e}")
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

# 🚀 Anti-Conflict Execution Loop
if __name__ == "__main__":
    threading.Thread(target=continuous_request_processor, daemon=True).start()
    print("🚀 Anti-Conflict System active. Booting up polling...")
    
    while True:
        try:
            bot.remove_webhook()
            # Smooth polling session setup
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
        except ApiTelegramException as ex:
            if ex.error_code == 409:
                print("⚠️ 409 Conflict occurred. Waiting 10 seconds for old session to close...")
                time.sleep(10)
            else:
                time.sleep(5)
        except Exception:
            time.sleep(5)
            
