import telebot
from telebot.apihelper import ApiTelegramException
import sqlite3
import time
import threading
import re

# =====================================================================
# ⚙️ CONFIGURATION (Is naye bot ka Token aur details dalein)
# =====================================================================
API_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"  # ⚠️ Is naye bot ka real Telegram Token yahan dalein
OWNER_ID = 7415265825  # 👑 Aapki Admin ID locked hai

# Channel & Group IDs
FREE_GROUP_ID = -4477244119  
PRIVATE_CHANNEL_ID = -3870933647  
# =====================================================================

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


# 📥 New Join Requests Incoming Collector (Buffer - Never declines/dismisses)
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
    print(f"📥 New Join Request Buffered: User {user_id} in Chat {chat_id}")


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

    # 2. Strict Link Eraser (Automatic Channel Link Post Clear Included)
    if message.chat.id == FREE_GROUP_ID and message.text:
        # Regex to capture http, https, www, and t.me short links
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+)'
        has_link = re.search(url_pattern, message.text, re.IGNORECASE)

        if has_link:
            # Check 1: Agar private channel se auto-forward ho kar aaya hai (linked chat features)
            is_from_private_channel = False
            
            if message.forward_from_chat and message.forward_from_chat.id == PRIVATE_CHANNEL_ID:
                is_from_private_channel = True
            elif message.sender_chat and message.sender_chat.id == PRIVATE_CHANNEL_ID:
                is_from_private_channel = True

            if is_from_private_channel:
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                    print(f"🗑️ Deleted automatic linked channel post with link from ID: {message.message_id}")
                except Exception as e:
                    print(f"❌ Error deleting channel link: {e}")
                return

            # Check 2: Owner agar khud manually group khol kar text message likhe -> ALLOW
            if message.from_user and message.from_user.id == OWNER_ID and not message.forward_from_chat:
                print("👑 Owner manually sent a link. Allowed.")
                return

            # Check 3: Koi bhi aam member ya any other forwarded message jisme link ho -> DELETE
            try:
                bot.delete_message(message.chat.id, message.message_id)
                print(f"🗑️ Deleted link from user/sender: {message.text}")
            except Exception as e:
                print(f"❌ Error deleting user link: {e}")


# 🔄 24/7 Global Engine (Scans All Old Historical Data + Real-time Naye Join Requests)
def continuous_request_processor():
    while True:
        try:
            conn = sqlite3.connect("new_join_filter_bot.db")
            cursor = conn.cursor()
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

                if is_in_group:
                    continue

                conn = sqlite3.connect("new_join_filter_bot.db")
                cursor = conn.cursor()
                cursor.execute("SELECT leave_timestamp FROM member_activity WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                conn.close()

                if row:
                    leave_timestamp = row[0]
                    elapsed_time = current_now - leave_timestamp
                    
                    if elapsed_time >= twelve_hours_in_seconds:
                        execute_approval(user_id, chat_id)
                else:
                    execute_approval(user_id, chat_id)

        except Exception as e:
            print(f"⚠️ Background loop warning: {e}")
            
        time.sleep(20)

def execute_approval(user_id, chat_id):
    try:
        bot.approve_chat_join_request(chat_id, user_id)
        print(f"✅ Approved User {user_id} in Chat {chat_id}")
    except Exception as e:
        print(f"❌ Failed to approve user {user_id}: {e}")
    
    conn = sqlite3.connect("new_join_filter_bot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pending_channel_requests WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    threading.Thread(target=continuous_request_processor, daemon=True).start()
    
    print("🚀 New Gold Expert Filter Bot is fully active (Fixed Auto-Channel Links)...")
    bot.infinity_polling(timeout=15)
    
