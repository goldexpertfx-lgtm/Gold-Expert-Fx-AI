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
OWNER_ID = 7415265825  # 👑 Prince Bhai Admin ID Locked

FREE_GROUP_ID = -4477244119
PRIVATE_CHANNEL_ID = -3870933647
# =====================================================================

if not API_TOKEN:
    print("❌ ERROR: API_TOKEN khali hai!")
    sys.exit(1)

# Threaded ko False rakhna hai taake naye background conflicts na banein
bot = telebot.TeleBot(API_TOKEN, threaded=False)

def init_db():
    conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
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

@bot.chat_join_request_handler()
def catch_and_buffer_requests(update):
    user_id = update.from_user.id
    chat_id = update.chat.id
    current_time = time.time()
    
    try:
        conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO pending_channel_requests (user_id, chat_id, request_time) 
            VALUES (?, ?, ?)
        """, (user_id, chat_id, current_time))
        conn.commit()
        conn.close()
        print(f"📥 Buffered Request: User {user_id}")
    except Exception as db_err:
        print(f"Database write delay: {db_err}")

@bot.message_handler(content_types=['text', 'new_chat_members', 'left_chat_member'])
def handle_group_messages(message):
    if message.content_type in ['new_chat_members', 'left_chat_member']:
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception:
            pass

        if message.chat.id == FREE_GROUP_ID and message.left_chat_member:
            left_user_id = message.left_chat_member.id
            leave_time = time.time()
            try:
                conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO member_activity VALUES (?, ?)", (left_user_id, leave_time))
                conn.commit()
                conn.close()
                print(f"🚪 Left User Saved: {left_user_id}")
            except Exception:
                pass
        return

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
                try: bot.delete_message(message.chat.id, message.message_id)
                except Exception: pass
                return

            if message.from_user and message.from_user.id == OWNER_ID and not message.forward_from_chat:
                return

            try:
                bot.delete_message(message.chat.id, message.message_id)
            except Exception:
                pass

def continuous_request_processor():
    while True:
        try:
            conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, chat_id FROM pending_channel_requests")
            pending_requests = cursor.fetchall()
            conn.close()

            current_now = time.time()
            twelve_hours = 12 * 60 * 60

            for user_id, chat_id in pending_requests:
                is_in_group = True 
                network_error = False

                try:
                    chat_member = bot.get_chat_member(FREE_GROUP_ID, user_id)
                    if chat_member.status in ['left', 'kicked']:
                        is_in_group = False
                    else:
                        is_in_group = True
                except ApiTelegramException as api_ex:
                    if api_ex.error_code == 400: 
                        is_in_group = False
                    else:
                        network_error = True
                except Exception:
                    network_error = True

                # 🛑 Agar background conflict chal raha ho, to chup chaap skip karein taake galat approval na ho
                if network_error:
                    continue

                # 🛑 Pehle se mojood member ko STRICTLY skip aur block karna hai
                if is_in_group:
                    print(f"❌ STRICT BLOCK: User {user_id} is ALREADY IN COMMUNITY. Skipping.")
                    continue  

                conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
                cursor = conn.cursor()
                cursor.execute("SELECT leave_timestamp FROM member_activity WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                conn.close()

                if row and (current_now - row[0]) >= twelve_hours:
                    print(f"✅ 12 Hours over for left user {user_id}. Approving.")
                    execute_approval(user_id, chat_id)
                elif not row:
                    print(f"✨ New subscriber {user_id}. Approving.")
                    execute_approval(user_id, chat_id)

        except Exception as e:
            print(f"Loop error handled: {e}")
        time.sleep(10)

def execute_approval(user_id, chat_id):
    try:
        bot.approve_chat_join_request(chat_id, user_id)
    except Exception as e:
        print(f"Approve action issue: {e}")
        
    try:
        conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pending_channel_requests WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        conn.commit()
        conn.close()
    except Exception:
        pass

if __name__ == "__main__":
    threading.Thread(target=continuous_request_processor, daemon=True).start()
    print("🚀 Bot starting in Anti-Conflict Single Thread Mode...")
    
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=False, timeout=5, long_polling_timeout=2)
        except ApiTelegramException as ex:
            if ex.error_code == 409:
                # Jab tak purana process completely kill nahi hota, yeh wait karega
                print("⚠️ 409 Conflict Detected (Old bot instance running on Render). Waiting 15 seconds...")
                time.sleep(15)
            else:
                time.sleep(5)
        except Exception:
            time.sleep(5)
        
