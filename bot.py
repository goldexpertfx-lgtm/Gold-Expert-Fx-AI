import requests
import sqlite3
import time
import threading
import re
import sys

# =====================================================================
# ⚙️ CONFIGURATION 
# =====================================================================
API_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"  # ⚠️ Apne bot ka real Telegram Token yahan dalein
OWNER_ID = 7415265825  # 👑 Admin ID Locked

FREE_GROUP_ID = -4477244119
PRIVATE_CHANNEL_ID = -3870933647
# =====================================================================

if not API_TOKEN:
    print("❌ ERROR: API_TOKEN khali hai!")
    sys.exit(1)

BASE_URL = f"https://api.telegram.org/bot{API_TOKEN}"

# 🗄️ Database Setup
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

# 🛡️ Link Cleaner & Message Engine
def handle_incoming_message(msg):
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")
    text = msg.get("text", "")
    
    # 1. System Clean (Join/Leave Notification Remover)
    if "new_chat_members" in msg or "left_chat_member" in msg:
        requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
        
        if chat_id == FREE_GROUP_ID and "left_chat_member" in msg:
            left_user_id = msg["left_chat_member"]["id"]
            leave_time = time.time()
            try:
                conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO member_activity VALUES (?, ?)", (left_user_id, leave_time))
                conn.commit()
                conn.close()
                print(f"🚪 Left User Saved: {left_user_id}")
            except Exception: pass
        return

    # 2. Strict Link Catching System
    if text:
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+|[a-zA-r0-9\-\.]+\.(com|net|org|me|info|biz|co|xyz|io|cc|tk|ml|cf|gq|club|online|site|store|tech|vip|app|live|pro|icu|top|win|loan|men|bid|ren|stream|date|download|party|racing|trade|webcam|faith|review|science))'
        if re.search(url_pattern, text, re.IGNORECASE):
            # Check for forward channel bypass
            is_from_private_channel = False
            if msg.get("forward_from_chat", {}).get("id") == PRIVATE_CHANNEL_ID:
                is_from_private_channel = True
            elif msg.get("sender_chat", {}).get("id") == PRIVATE_CHANNEL_ID:
                is_from_private_channel = True

            if is_from_private_channel:
                requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
                return

            from_user_id = msg.get("from", {}).get("id")
            if from_user_id == OWNER_ID and "forward_from_chat" not in msg:
                return

            requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})

# 🔄 24/7 Global Engine For Join Requests (STRICT BYPASS SAFETY)
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
                
                # Check status via direct API post
                try:
                    res = requests.post(f"{BASE_URL}/getChatMember", json={"chat_id": FREE_GROUP_ID, "user_id": user_id}, timeout=10).json()
                    if res.get("ok"):
                        status = res["result"]["status"]
                        if status in ["left", "kicked"]:
                            is_in_group = False
                        else:
                            is_in_group = True
                    else:
                        # Agar conflict chal raha ho ya API error ho, to safe side rehne ke liye true rakhein taake galat approve na ho
                        continue 
                except Exception:
                    continue

                # 🛑 STRICT RULE: Agar user ALREADY group ka subscriber/member hai, to process block!
                if is_in_group:
                    print(f"❌ STRICT BLOCK: User {user_id} is active in community. Skipping Approval.")
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
                    print(f"✨ Completely new user {user_id}. Approving.")
                    execute_approval(user_id, chat_id)

        except Exception as e:
            print(f"Engine Loop delay: {e}")
        time.sleep(10)

def execute_approval(user_id, chat_id):
    try:
        res = requests.post(f"{BASE_URL}/approveChatJoinRequest", json={"chat_id": chat_id, "user_id": user_id}, timeout=10).json()
        if res.get("ok"):
            print(f"🚀 Successfully Approved User: {user_id}")
    except Exception as e:
        print(f"Approval fail: {e}")
        
    try:
        conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pending_channel_requests WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        conn.commit()
        conn.close()
    except Exception:
        pass

# 🚀 100% Pure Custom Manual Fetcher (No Telebot Polling Conflict)
if __name__ == "__main__":
    threading.Thread(target=continuous_request_processor, daemon=True).start()
    print("🚀 Bot running on Manual Safe Loop Mode...")
    
    offset = 0
    while True:
        try:
            # Direct network call without library threads
            response = requests.post(
                f"{BASE_URL}/getUpdates", 
                json={"offset": offset, "timeout": 10, "allowed_updates": ["message", "chat_join_request"]}, 
                timeout=15
            ).json()
            
            if response.get("ok"):
                for update in response["result"]:
                    offset = update["update_id"] + 1
                    
                    # Catch requests manually
                    if "chat_join_request" in update:
                        req = update["chat_join_request"]
                        u_id = req["from"]["id"]
                        c_id = req["chat"]["id"]
                        
                        conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
                        cursor = conn.cursor()
                        cursor.execute("INSERT OR IGNORE INTO pending_channel_requests VALUES (?, ?, ?)", (u_id, c_id, time.time()))
                        conn.commit()
                        conn.close()
                        print(f"📥 Request Captured Manually: {u_id}")
                        
                    elif "message" in update:
                        handle_incoming_message(update["message"])
            else:
                # Response not ok (409 conflict handles gracefully here)
                if response.get("error_code") == 409:
                    print("⚠️ 409 Conflict (Old ghost bot alive on Render). Pausing thread for 15s...")
                    time.sleep(15)
                    
        except Exception as err:
            time.sleep(5)
        
