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
    
    # 📝 DEBUG LOG: Har message ko track karne ke liye (Render logs me dikhega)
    if message.text:
        print(f"📩 [LOG] Message received in Chat ID: {message.chat.id} from User ID: {message.from_user.id if message.from_user else 'Unknown'}")
        print(f"📝 [LOG] Text: {message.text[:50]}")

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
            print(f"🚪 Left User Saved to DB: {left_user_id} at {leave_time}")
        return

    # 2. Strict Link Catching System
    if message.text:
        # Regex to catch any link (http, https, www, t.me, .com, .net, etc.)
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+|[a-zA-r0-9\-\.]+\.(com|net|org|me|info|biz|co|xyz|io|cc|tk|ml|cf|gq|club|online|site|store|tech|vip|app|live|pro|icu|top|win|loan|men|bid|ren|stream|date|download|party|racing|trade|webcam|faith|review|science))'
        has_link = re.search(url_pattern, message.text, re.IGNORECASE)

        if has_link:
            print(f"🚨 Link Detected! Analyzing sender status...")
            
            # CONDITION A: Linked Private Channel ki auto-forwarded posts ko delete karega
            is_from_private_channel = False
            if message.forward_from_chat and message.forward_from_chat.id == PRIVATE_CHANNEL_ID:
                is_from_private_channel = True
            elif message.sender_chat and message.sender_chat.id == PRIVATE_CHANNEL_ID:
                is_from_private_channel = True

            if is_from_private_channel:
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                    print(f"🗑️ SUCCESS: Deleted automatic channel linked post.")
                except Exception as e:
                    print(f"❌ FAILED to delete channel post. Check Bot Admin Permissions: {e}")
                return

            # CONDITION B: Agar Owner manually link send kare (Bypass)
            if message.from_user and message.from_user.id == OWNER_ID and not message.forward_from_chat:
                print("👑 Owner detected. Link allowed.")
                return

            # CONDITION C: Koi bhi normal user ya doosra admin link send kare (Strict Delete)
            try:
                bot.delete_message(message.chat.id, message.message_id)
                print(f"🗑️ SUCCESS: Deleted standard link from member/admin.")
            except Exception as e:
                print(f"❌ FAILED to delete user link. Ensure bot is Admin with delete rights! Error: {e}")

# 🔄 24/7 Global Engine For Join Requests (FIXED LOGIC)
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

                # 🚫 FIX 1: Agar user ALREADY group ka subscriber/member hai, to auto-approve NAHI karega
                if is_in_group:
                    print(f"⏳ User {user_id} is an active group member. Keeping request PENDING.")
                    continue  # Loop agle user par chala jayega, iski request pending rahegi

                # Group se leave karne walon ka data check karein
                conn = sqlite3.connect("new_join_filter_bot.db")
                cursor = conn.cursor()
                cursor.execute("SELECT leave_timestamp FROM member_activity WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                conn.close()

                # ⏳ FIX 2: Agar user ne group leave kiya تھا, to 12 ghante baad hi approve hoga
                if row and (current_now - row[0]) >= twelve_hours:
                    print(f"✅ 12 Hours passed for left user {user_id}. Approving now.")
                    execute_approval(user_id, chat_id)
                
                # ✨ FIX 3: Agar bilkul naya banda hai (jiski database mein koi history nahi hai)
                elif not row:
                    print(f"✨ Completely new user {user_id}. Approving request instantly.")
                    execute_approval(user_id, chat_id)

        except Exception as e:
            print(f"⚠️ Loop warning: {e}")
        time.sleep(20)

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

# 🚀 Anti-Conflict Execution Loop (UPDATED FOR RENDER)
if __name__ == "__main__":
    # Background thread for join request approval
    threading.Thread(target=continuous_request_processor, daemon=True).start()
    print("🚀 Anti-Conflict System active. Booting up polling...")
    
    # Pehle se maujood kisi bhi purane webhook ko saaf karein
    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"Webhook remove warning: {e}")
        
    # Advanced infinity polling jo crash nahi hoti aur logs ko clear rakhti hai
    bot.infinity_polling(timeout=20, long_polling_timeout=5)
    
