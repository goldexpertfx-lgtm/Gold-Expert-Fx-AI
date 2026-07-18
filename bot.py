import requests
import sqlite3
import time
import threading
import re
import sys

# =====================================================================
# ⚙️ CONFIGURATION 
# =====================================================================
API_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"  # ⚠️ Apna real Telegram Token yahan dalein
OWNER_ID = 7415265825  # 👑 Prince Bhai Admin ID

FREE_GROUP_ID = -4477244119  
PRIVATE_CHANNEL_ID = -3870933647  
# =====================================================================

if not API_TOKEN:
    print("❌ ERROR: API_TOKEN khali hai!")
    sys.exit(1)

BASE_URL = f"https://api.telegram.org/bot{API_TOKEN}"

def init_db():
    conn = sqlite3.connect("gold_expert_bot.db", timeout=20)
    cursor = conn.cursor()
    # Table for all registered users
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users_profile (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            join_date REAL
        )
    """)
    # Table for pending channel approval requests
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_channel_requests (
            user_id INTEGER, 
            chat_id INTEGER, 
            request_time REAL, 
            PRIMARY KEY (user_id, chat_id)
        )
    """)
    # Table for dynamic posts/messages editing
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dynamic_content (
            service_key TEXT PRIMARY KEY,
            text_content TEXT
        )
    """)
    # Table for tracking which message owner is currently editing
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_edit_state (
            admin_id INTEGER PRIMARY KEY,
            editing_service TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Content Helpers ---
def get_content(service_key, default_text):
    try:
        conn = sqlite3.connect("gold_expert_bot.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("SELECT text_content FROM dynamic_content WHERE service_key = ?", (service_key,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]: return row[0]
    except Exception: pass
    return default_text

def set_content(service_key, new_text):
    try:
        conn = sqlite3.connect("gold_expert_bot.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO dynamic_content VALUES (?, ?)", (service_key, new_text))
        conn.commit()
        conn.close()
        return True
    except Exception: return False

# --- Keyboards ---
def get_main_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "💼 Account Management Services", "callback_data": "srv_account"}],
            [{"text": "👑 VIP Premium Private Channel", "callback_data": "srv_vip"}],
            [{"text": "📋 Copy Trading Service", "callback_data": "srv_copy"}]
        ]
    }

def get_owner_menu():
    return {
        "keyboard": [
            [{"text": "👥 View Total Users"}, {"text": "✏️ Live Edit Messages"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

# --- Core Handlers ---
def handle_incoming_message(msg):
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")
    text = msg.get("text", "")
    from_user = msg.get("from", {})
    from_user_id = from_user.get("id")
    chat_type = msg.get("chat", {}).get("type")
    
    if not from_user_id: return

    # 1. System Logs & Auto-Clean Join/Leave messages
    if "new_chat_members" in msg or "left_chat_member" in msg:
        requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
        return

    # 2. Anti-Link Filter for Group (Only allow Owner/Forwards from own Channel)
    if text and chat_id == FREE_GROUP_ID and from_user_id != OWNER_ID:
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+|[a-zA-r0-9\-\.]+\.(com|net|org|xyz|info))'
        if re.search(url_pattern, text, re.IGNORECASE):
            if msg.get("forward_from_chat", {}).get("id") != PRIVATE_CHANNEL_ID:
                requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
                return

    # Private Chat Logic
    if chat_type == "private":
        # Save user to DB automatically
        try:
            conn = sqlite3.connect("gold_expert_bot.db", timeout=20)
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO users_profile VALUES (?, ?, ?, ?)", 
                           (from_user_id, from_user.get("first_name"), from_user.get("username"), time.time()))
            conn.commit()
            conn.close()
        except Exception: pass

        # Command /start handler
        if text and text.startswith("/start"):
            welcome = f"👋 **Hello, {from_user.get('first_name', 'Trader')}!**\n\nWelcome to **Gold Expert FX Automation Hub**. Select a service below:"
            payload = {"chat_id": chat_id, "text": welcome, "parse_mode": "Markdown", "reply_markup": get_main_keyboard()}
            
            if from_user_id == OWNER_ID:
                payload["reply_markup"] = get_owner_menu()
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": "👑 Welcome Back Prince Bhai! Custom Owner buttons are active below.", "reply_markup": get_owner_menu()})
            
            requests.post(f"{BASE_URL}/sendMessage", json=payload)
            return

        # Owner Special Keyboard Actions
        if from_user_id == OWNER_ID:
            if text == "👥 View Total Users":
                try:
                    conn = sqlite3.connect("gold_expert_bot.db", timeout=20)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM users_profile")
                    total_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT first_name, username FROM users_profile ORDER BY join_date DESC LIMIT 15")
                    latest_users = cursor.fetchall()
                    conn.close()
                    
                    user_list_text = f"📊 **Total Active Users Database:** `{total_count}`\n\n**Latest Joined Users:**\n"
                    for fname, uname in latest_users:
                        user_list_text += f"👤 {fname} ({"@" + uname if uname else 'No Username'})\n"
                        
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": user_list_text, "parse_mode": "Markdown"})
                except Exception as e:
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"❌ Error fetching users: {str(e)}"})
                return

            elif text == "✏️ Live Edit Messages":
                kb = {
                    "inline_keyboard": [
                        [{"text": "📝 Edit Account Management Text", "callback_data": "edt_account"}],
                        [{"text": "📝 Edit VIP Premium Text", "callback_data": "edt_vip"}],
                        [{"text": "📝 Edit Copy Trading Text", "callback_data": "edt_copy"}],
                        [{"text": "❌ Cancel Editing", "callback_data": "edt_cancel"}]
                    ]
                }
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "🛠️ **Prince Bhai, kaunsa service post content change karna chahte ho?**\n\nNeeche se choose karein aur uske baad seedha naya format text bhej dein.", "parse_mode": "Markdown", "reply_markup": kb})
                return

            # Check if Owner is currently submitting text updates
            try:
                conn = sqlite3.connect("gold_expert_bot.db", timeout=20)
                cursor = conn.cursor()
                cursor.execute("SELECT editing_service FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
                edit_row = cursor.fetchone()
                conn.close()

                if edit_row and edit_row[0]:
                    service_key = edit_row[0]
                    if set_content(service_key, text):
                        conn = sqlite3.connect("gold_expert_bot.db", timeout=20)
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
                        conn.commit()
                        conn.close()
                        requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"✅ **Live Update Successful!** New content saved for `{service_key}`.", "parse_mode": "Markdown"})
                    return
            except Exception: pass

def handle_callback_query(callback):
    c_id = callback["id"]
    from_user_id = callback["from"]["id"]
    chat_id = callback["message"]["chat"]["id"]
    message_id = callback["message"]["message_id"]
    data = callback["data"]
    
    requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": c_id})

    # Default Texts if DB is empty
    def_account = "💼 **Account Management Rules:**\n\n1. Profit split: 50/50.\n2. Minimum Account Size: $500.\n3. Safe and fully transparent execution."
    def_vip = "👑 **VIP Premium Channel:**\n\n- Daily 5-7 High Accuracy Gold Setups.\n- Entry, Stop Loss & Target targets detailed perfectly."
    def_copy = "📋 **Copy Trading Service:**\n\n- One-time setup.\n- Fully automated system directly connecting your broker account."

    # Live Edit Router (Owner Only)
    if data.startswith("edt_") and from_user_id == OWNER_ID:
        action = data.split("_")[1]
        if action == "cancel":
            conn = sqlite3.connect("gold_expert_bot.db", timeout=20)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
            conn.commit()
            conn.close()
            requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": "❌ Editing sequence cancelled safely."})
            return
        
        conn = sqlite3.connect("gold_expert_bot.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO admin_edit_state VALUES (?, ?)", (OWNER_ID, action))
        conn.commit()
        conn.close()
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": f"📥 **System Ready!**\n\nAb aap jo bhi text message yahan type karke bhejenge, woh live update ho jayega `{action}` post par.", "parse_mode": "Markdown"})
        return

    # Navigation Services for Users
    if data == "srv_account":
        current_text = get_content("account", def_account)
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": current_text, "parse_mode": "Markdown", "reply_markup": get_main_keyboard()})
    elif data == "srv_vip":
        current_text = get_content("vip", def_vip)
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": current_text, "parse_mode": "Markdown", "reply_markup": get_main_keyboard()})
    elif data == "srv_copy":
        current_text = get_content("copy", def_copy)
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": current_text, "parse_mode": "Markdown", "reply_markup": get_main_keyboard()})

# --- Automatic Join Request Process Thread ---
def automatic_join_processor():
    while True:
        try:
            conn = sqlite3.connect("gold_expert_bot.db", timeout=20)
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, chat_id FROM pending_channel_requests")
            pending_requests = cursor.fetchall()
            conn.close()

            for user_id, chat_id in pending_requests:
                # Instantly approve requests 
                approve_status = requests.post(f"{BASE_URL}/approveChatJoinRequest", json={"chat_id": chat_id, "user_id": user_id}).json()
                
                if approve_status.get("ok"):
                    conn = sqlite3.connect("gold_expert_bot.db", timeout=20)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM pending_channel_requests WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
                    conn.commit()
                    conn.close()
        except Exception: pass
        time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=automatic_join_processor, daemon=True).start()
    print("🚀 Tailored Premium Engine Active & Safe...")
    offset = 0
    while True:
        try:
            response = requests.post(f"{BASE_URL}/getUpdates", json={"offset": offset, "timeout": 10, "allowed_updates": ["message", "callback_query", "chat_join_request"]}, timeout=15).json()
            if response.get("ok"):
                for update in response["result"]:
                    offset = update["update_id"] + 1
                    
                    if "chat_join_request" in update:
                        req = update["chat_join_request"]
                        conn = sqlite3.connect("gold_expert_bot.db", timeout=20)
                        cursor = conn.cursor()
                        cursor.execute("INSERT OR IGNORE INTO pending_channel_requests VALUES (?, ?, ?)", (req["from"]["id"], req["chat"]["id"], time.time()))
                        conn.commit()
                        conn.close()
                        
                    elif "message" in update:
                        handle_incoming_message(update["message"])
                        
                    elif "callback_query" in update:
                        handle_callback_query(update["callback_query"])
            else:
                if response.get("error_code") == 409: time.sleep(10)
        except Exception: time.sleep(4)
    
