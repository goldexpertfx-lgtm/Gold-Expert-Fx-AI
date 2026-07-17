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
API_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"  # ⚠️ Apne bot ka real Telegram Token yahan dalein
OWNER_ID = 7415265825  # 👑 Admin ID locked

FREE_GROUP_ID = -4477244119
PRIVATE_CHANNEL_ID = -3870933647
# =====================================================================

if not API_TOKEN:
    print("❌ ERROR: API_TOKEN khali hai! Please insert your token.")
    sys.exit(1)

# Single thread mode to completely eliminate python level internal conflicts
bot = telebot.TeleBot(API_TOKEN, threaded=False)

# 🗄️ Database Setup
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
    print(f"📥 New Request Buffered into DB: User {user_id}")

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
            print(f"🚪 Left User Saved to DB: {left_user_id}")
        return

    # 2. Strict Link Catching System
    if message.text:
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+|[a-zA-r0-9\-\.]+\.(com|net|org|me|info|biz|co|xyz|io|cc|tk|ml|cf|gq|club|online|site|store|tech|vip|app|live|pro|icu|top|win|loan|men|bid|ren|stream|date|download|party|racing|trade|webcam|faith|review|science))'
        has_link = re.search(url_pattern, message.text, re.IGNORECASE)

        if has_link:
            is_from_private_channel = False
            if message.forward_from_chat and message.forward_from_chat.id == PRIVATE_CHANNEL_ID:
                is_from_private_channel = True
            elif message.sender_chat and message.sender_chat.id == PRIVATE_CHANNEL_ID:
                is_from_private_channel = True

            if is_from_private_channel:
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                except Exception:
                    pass
                return

            if message.from_user and message.from_user.id == OWNER_ID and not message.forward_from_chat:
                return

            try:
                bot.delete_message(message.chat.id, message.message_id)
                print(f"🗑️ SUCCESS: Deleted user link.")
            except Exception as e:
                print(f"❌ FAILED to delete link: {e}")

# 🔄 24/7 Global Engine For Join Requests (STRICT EXTRA SAFETY)
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
                # Default safety: Maan ke chalo user group mein ho sakta hai jab tak check confirm na ho
                is_in_group = True 
                network_error = False

                try:
                    chat_member = bot.get_chat_member(FREE_GROUP_ID, user_id)
                    if chat_member.status in ['left', 'kicked']:
                        is_in_group = False
                    else:
                        is_in_group = True
                except ApiTelegramException as api_ex:
                    if api_ex.error_code == 400: # User never even opened the group
                        is_in_group = False
                    else:
                        network_error = True
                except Exception:
                    network_error = True

                # 🛑 CRITICAL SAFEGUARD 1: Agar net gap/409 error aaya hai, to request ko touch nahi karna, agli bar check karenge
                if network_error:
                    print(f"⚠️ Network lag for {user_id}. Skipping to prevent wrong approval.")
                    continue

                # 🛑 CRITICAL SAFEGUARD 2: Agar banda already group me hai, to usey BILKUL approve nahi karna!
                if is_in_group:
                    print(f"❌ STRICT BLOCK: User {user_id} is ACTIVE in community. Keeping Pending.")
                    continue  

                # Group se leave karne walon ka data check karein
                conn = sqlite3.connect("new_join_filter_bot.db")
                cursor = conn.cursor()
                cursor.execute("SELECT leave_timestamp FROM member_activity WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                conn.close()

                # ⏳ RULE 2: Left users ke liye 12-hour penalty condition
                if row and (current_now - row[0]) >= twelve_hours:
                    print(f"✅ 12 Hours passed for left user {user_id}. Approving.")
                    execute_approval(user_id, chat_id)
                
                # ✨ RULE 3: Bilkul naya banda (no group history)
                elif not row:
                    print(f"✨ Completely new user {user_id}. Instant Entry.")
                    execute_approval(user_id, chat_id)

        except Exception as e:
            print(f"⚠️ Loop warning: {e}")
        time.sleep(12)

def execute_approval(user_id, chat_id):
    try:
        bot.approve_chat_join_request(chat_id, user_id)
    except Exception as e:
        print(f"❌ Execution fail for {user_id}: {e}")
        
    conn = sqlite3.connect("new_join_filter_bot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pending_channel_requests WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    conn.commit()
    conn.close()

# 🚀 Anti-Conflict Ultra Polling Loop
if __name__ == "__main__":
    threading.Thread(target=continuous_request_processor, daemon=True).start()
    print("🚀 Custom Ultra-Single Threaded Mode active. Booting...")
    
    while True:
        try:
            bot.remove_webhook()
            # strictly single session limits to avoid multiple hook catch loops on render
            bot.polling(none_stop=False, timeout=10, long_polling_timeout=3)
        except ApiTelegramException as ex:
            if ex.error_code == 409:
                print("⚠️ 409 Conflict handled. Waiting 10 seconds...")
                time.sleep(10)
            else:
                time.sleep(5)
        except Exception:
            time.sleep(5)
    
