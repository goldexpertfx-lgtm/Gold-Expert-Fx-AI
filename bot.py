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
OWNER_ID = 7415265825  # 👑 Aapki Admin ID locked hai

FREE_GROUP_ID = -4477244119
PRIVATE_CHANNEL_ID = -3870933647
# =====================================================================

if not API_TOKEN:
    print("❌ ERROR: API_TOKEN khali hai! Please insert your token.")
    sys.exit(1)

bot = telebot.TeleBot(API_TOKEN)

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
    print(f"📥 New Join Request Buffered: User {user_id}")

# 🛡️ Group Link Filter & Auto-Delete Engine
@bot.message_handler(content_types=['text', 'new_chat_members', 'left_chat_member'])
def handle_group_messages(message):
    
    if message.text:
        print(f"📩 [LOG] Message in Chat: {message.chat.id} from User: {message.from_user.id if message.from_user else 'Unknown'}")

    # 1. System Clean (Join/Leave Notification Remover)
    if message.content_type in ['new_chat_members', 'left_chat_member']:
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            print(f"❌ System notification delete failed: {e}")

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
                print(f"🗑️ SUCCESS: Deleted link.")
            except Exception as e:
                print(f"❌ FAILED to delete link: {e}")

# 🔄 24/7 Global Engine For Join Requests (STRICT CHECK)
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

                # 🛑 STRICT RULE 1: Agar user ALREADY group ka subscriber/member hai, to usey BILKUL approve nahi karna, pending rakhna hai
                if is_in_group:
                    print(f"⏳ User {user_id} is already in community. SKIPPING APPROVAL (Keeping Pending).")
                    continue  

                # Group se leave karne walon ka data check karein
                conn = sqlite3.connect("new_join_filter_bot.db")
                cursor = conn.cursor()
                cursor.execute("SELECT leave_timestamp FROM member_activity WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                conn.close()

                # ⏳ RULE 2: Agar user ne group leave kiya tha, to 12 ghante baad hi approve hoga
                if row and (current_now - row[0]) >= twelve_hours:
                    print(f"✅ 12 Hours passed for left user {user_id}. Approving now.")
                    execute_approval(user_id, chat_id)
                
                # ✨ RULE 3: Agar bilkul naya banda hai (jiski database mein koi history nahi hai)
                elif not row:
                    print(f"✨ Completely new user {user_id}. Approving request instantly.")
                    execute_approval(user_id, chat_id)

        except Exception as e:
            print(f"⚠️ Loop warning: {e}")
        time.sleep(15)

def execute_approval(user_id, chat_id):
    try:
        bot.approve_chat_join_request(chat_id, user_id)
    except Exception as e:
        print(f"❌ Could not approve user {user_id}: {e}")
        
    conn = sqlite3.connect("new_join_filter_bot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pending_channel_requests WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    conn.commit()
    conn.close()

# 🚀 Anti-Conflict Custom Polling Loop (No Threading Exception)
if __name__ == "__main__":
    threading.Thread(target=continuous_request_processor, daemon=True).start()
    print("🚀 Anti-Conflict System active. Booting up...")
    
    while True:
        try:
            bot.remove_webhook()
            # use_keys=True lagane se internal threads handle hoti hain single-thread mode me
            bot.polling(none_stop=True, timeout=20, long_polling_timeout=5, restart_on_change=False)
        except ApiTelegramException as ex:
            if ex.error_code == 409:
                print("⚠️ 409 Conflict! Render overlay running. Waiting 15 seconds to auto-heal...")
                time.sleep(15)
            else:
                time.sleep(5)
        except Exception as e:
            print(f"System gap handled: {e}")
            time.sleep(5)
                
