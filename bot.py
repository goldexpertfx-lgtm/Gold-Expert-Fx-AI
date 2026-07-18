import requests
import sqlite3
import time
import threading
import re
import sys
import random

# =====================================================================
# ⚙️ CONFIGURATION 
# =====================================================================
API_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"  # ⚠️ Apne bot ka real Telegram Token yahan dalein
OWNER_ID = 7415265825  # 👑 Prince Bhai Admin ID Locked

FREE_GROUP_ID = -4477244119  # Gold Expert Fx Community
PRIVATE_CHANNEL_ID = -3870933647  # Gold Expert FX | XAUUSD Signals
# =====================================================================

if not API_TOKEN:
    print("❌ ERROR: API_TOKEN khali hai!")
    sys.exit(1)

BASE_URL = f"https://api.telegram.org/bot{API_TOKEN}"
EMOJI_POOL = ["🔥", "🚀", "👍", "❤️", "⚡", "🎉", "🤩"]

# 🗄️ Database Setup with Dynamic Logging
def init_db():
    conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS member_activity (user_id INTEGER PRIMARY KEY, leave_timestamp REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS pending_channel_requests (user_id INTEGER, chat_id INTEGER, request_time REAL, PRIMARY KEY (user_id, chat_id))")
    
    # 🌟 New CRM Tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users_profile (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            join_date REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action_type TEXT,
            details TEXT,
            timestamp REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_state (
            admin_id INTEGER PRIMARY KEY,
            target_user_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()

# 📝 Helper to log history
def log_user_history(user_id, action_type, details):
    try:
        conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO user_history (user_id, action_type, details, timestamp) VALUES (?, ?, ?, ?)",
                       (user_id, action_type, details, time.time()))
        conn.commit()
        conn.close()
    except Exception: pass

# 🧱 Keyboards
def get_main_keyboard(user_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "💼 Account Management Services", "callback_data": "srv_account"}],
            [{"text": "👑 VIP Premium Private Channel", "callback_data": "srv_vip"}],
            [{"text": "📋 Copy Trading Service", "callback_data": "srv_copy"}]
        ]
    }
    if user_id == OWNER_ID:
        keyboard["inline_keyboard"].append([{"text": "👥 View All Users (Admin Only)", "callback_data": "adm_users_list"}])
    return keyboard

def get_back_keyboard():
    return {"inline_keyboard": [[{"text": "⬅️ Back to Services", "callback_data": "go_main"}]]}

# 🛡️ Link Cleaner & Message Processor
def handle_incoming_message(msg):
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")
    text = msg.get("text", "")
    from_user = msg.get("from", {})
    from_user_id = from_user.get("id")
    chat_type = msg.get("chat", {}).get("type")
    
    if "new_chat_members" in msg or "left_chat_member" in msg:
        requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
        if chat_id == FREE_GROUP_ID and "left_chat_member" in msg:
            left_user_id = msg["left_chat_member"]["id"]
            try:
                conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO member_activity VALUES (?, ?)", (left_user_id, time.time()))
                conn.commit()
                conn.close()
            except Exception: pass
        return

    # 🌟 PRIVATE CHAT SYSTEM
    if chat_type == "private":
        # Save profile
        try:
            conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO users_profile VALUES (?, ?, ?, ?)", 
                           (from_user_id, from_user.get("first_name"), from_user.get("username"), time.time()))
            conn.commit()
            conn.close()
        except Exception: pass

        # Handle Admin Message Routing (If Prince bhai is sending a message to a user)
        if from_user_id == OWNER_ID:
            conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
            cursor = conn.cursor()
            cursor.execute("SELECT target_user_id FROM admin_state WHERE admin_id = ?", (OWNER_ID,))
            row = cursor.fetchone()
            conn.close()
            
            if row and text and not text.startswith("/"):
                target_id = row[0]
                payload = {"chat_id": target_id, "text": f"💬 **Message from Admin:**\n\n{text}", "parse_mode": "Markdown"}
                res = requests.post(f"{BASE_URL}/sendMessage", json=payload).json()
                if res.get("ok"):
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"✅ Message successfully sent to User ID: {target_id}"})
                else:
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "❌ Failed to send message. User might have blocked the bot."})
                return

        # Regular /start Command
        if text and text.startswith("/start"):
            log_user_history(from_user_id, "COMMAND", "/start executed")
            name = from_user.get("first_name", "Trader")
            uname = f"@{from_user.get('username')}" if from_user.get('username') else "No Username"
            
            welcome = (
                f"👋 **Hello, {name}!**\n"
                f"👤 **Username:** {uname}\n"
                f"🆔 **Your Telegram ID:** `{from_user_id}`\n\n"
                "Welcome to **Gold Expert FX System**. Please select a service from the options below to view complete details:"
            )
            requests.post(f"{BASE_URL}/sendMessage", json={
                "chat_id": chat_id, "text": welcome, "parse_mode": "Markdown", "reply_markup": get_main_keyboard(from_user_id)
            })
            return

        # If user sends a regular text message to bot, log it and notify Prince bhai
        if text and from_user_id != OWNER_ID:
            log_user_history(from_user_id, "USER_MESSAGE", text)
            # Forward / Notify Prince Bhai
            admin_alert = (
                f"📥 **New Message Received!**\n\n"
                f"👤 **From:** {from_user.get('first_name')} ({f'@{from_user.get(username)}' if from_user.get('username') else 'No User'})\n"
                f"🆔 **ID:** `{from_user_id}`\n"
                f"💬 **Message:** {text}\n\n"
                f"👉 Click 'View All Users' or use buttons to inspect history and reply."
            )
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": admin_alert, "parse_mode": "Markdown"})

    # Group / Channel Filters
    if chat_id == FREE_GROUP_ID and from_user_id == OWNER_ID:
        threading.Thread(target=lambda: requests.post(f"{BASE_URL}/setMessageReaction", json={
            "chat_id": chat_id, "message_id": message_id, 
            "reaction": [{"type": "emoji", "emoji": random.choice(EMOJI_POOL)}]}
        ), daemon=True).start()

    if text and chat_id == FREE_GROUP_ID:
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+|[a-zA-r0-9\-\.]+\.(com|net|org))'
        if re.search(url_pattern, text, re.IGNORECASE):
            if not (msg.get("forward_from_chat", {}).get("id") == PRIVATE_CHANNEL_ID or from_user_id == OWNER_ID):
                requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})

# 🎛️ Callback Query Engine (Button Clicks)
def handle_callback_query(callback):
    c_id = callback["id"]
    from_user = callback["from"]
    from_user_id = from_user["id"]
    chat_id = callback["message"]["chat"]["id"]
    message_id = callback["message"]["message_id"]
    data = callback["data"]
    
    requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": c_id})
    
    # 📑 SERVICE DETAILS CONTENT
    account_management_text = (
        "📊 **Account Management Service – Terms & Rules**\n\n"
        "1. **Trading Account:** You will provide your MT4 or MT5 login details so we can manage your trading account professionally.\n"
        "2. **Fund Security:** Your funds always remain in your own trading account. We cannot deposit, withdraw, or transfer your money.\n"
        "3. **Profit Sharing:** All trading profits will be shared 50% for you and 50% for us.\n"
        "4. **Loss Sharing:** If a trading loss occurs, the loss will also be shared 50/50.\n"
        "5. **Profit Payment:** After profit is generated, you can send our 50% profit share via accepted methods.\n"
        "6. **No Scam:** Transparent and honest service. No hidden charges.\n"
        "7. **No Long-Term Commitment:** Free to start or stop the service at any time.\n\n"
        "✅ **Accepted Brokers:** All Brokers Accepted\n\n"
        "💰 **Accepted Payment Methods:**\n"
        "- Binance / USDT\n- Skrill / Neteller\n- Bitcoin (BTC) / Ethereum (ETH)\n- Perfect Money / WebMoney"
    )
    
    vip_text = (
        "👑 **VIP Premium Private Channel**\n\n"
        "Gain elite access to our high-accuracy Gold (XAUUSD) signals daily.\n\n"
        "✨ **What you get:**\n"
        "- 2 to 5 High Probability Gold Signals daily\n"
        "- Exact Entry, Stop Loss, and Multiple Take Profits\n"
        "- Real-time market updates and execution adjustments\n\n"
        "📩 *To request admission or verify your registration status, keep your request active. Our automated system checks group membership criteria continuously.*"
    )
    
    copy_trading_text = (
        "📋 **Copy Trading Terms & Conditions**\n\n"
        "**1. Account Requirement:** Client must have an MT4 or MT5 account on a supported broker.\n"
        "**2. Setup:** Ownership stays with the client. Provide connection/investor details.\n"
        "**3. Minimum Deposit:** Recommended minimum $200 or more.\n"
        "**4. Risk Warning:** Forex/Gold trading contains risk. Profit is not guaranteed.\n"
        "**5. Rules:** Do not change leverage or settings without informing us.\n\n"
        "🚀 **Benefits:** Automatic copying, no manual analysis required, save time, professional management.\n\n"
        "💰 **Copy Trading Fee:** One-Time Payment of **$1,000** (No monthly charges, no profit split).\n"
        "🛡️ **Refund Policy:** 30% administrative fee deduction, 70% remaining balance fully refundable upon cancellation request."
    )

    if data == "go_main":
        name = from_user.get("first_name", "Trader")
        uname = f"@{from_user.get('username')}" if from_user.get('username') else "No Username"
        welcome = f"👋 **Hello, {name}!**\n👤 **Username:** {uname}\n🆔 **Your Telegram ID:** `{from_user_id}`\n\nChoose a service:"
        requests.post(f"{BASE_URL}/editMessageText", json={
            "chat_id": chat_id, "message_id": message_id, "text": welcome, "parse_mode": "Markdown", "reply_markup": get_main_keyboard(from_user_id)
        })
        
    elif data.startswith("srv_"):
        srv_name = data.split("_")[1]
        log_user_history(from_user_id, "CLICK_BUTTON", f"Clicked on {srv_name} details")
        
        target_text = account_management_text if srv_name == "account" else (vip_text if srv_name == "vip" else copy_trading_text)
        requests.post(f"{BASE_URL}/editMessageText", json={
            "chat_id": chat_id, "message_id": message_id, "text": target_text, "parse_mode": "Markdown", "reply_markup": get_back_keyboard()
        })

    # 👑 ADMIN ACTIONS (PRINCE BHAI LOCK)
    elif data == "adm_users_list" and from_user_id == OWNER_ID:
        conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, first_name, username FROM users_profile ORDER BY join_date DESC LIMIT 30")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": "📭 No logged users found yet.", "reply_markup": get_back_keyboard()})
            return
            
        kb = {"inline_keyboard": []}
        for u_id, f_name, u_name in rows:
            disp = f"{f_name} (@{u_name})" if u_name else f"{f_name}"
            kb["inline_keyboard"].append([{"text": f"👤 {disp}", "callback_data": f"adm_view_{u_id}"}])
        kb["inline_keyboard"].append([{"text": "⬅️ Back", "callback_data": "go_main"}])
        
        requests.post(f"{BASE_URL}/editMessageText", json={
            "chat_id": chat_id, "message_id": message_id, "text": "👥 **Select a user to view full log details & history:**", "reply_markup": kb
        })

    elif data.startswith("adm_view_") and from_user_id == OWNER_ID:
        target_uid = int(data.split("_")[2])
        
        conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("SELECT first_name, username FROM users_profile WHERE user_id = ?", (target_uid,))
        p_row = cursor.fetchone()
        
        cursor.execute("SELECT action_type, details, timestamp FROM user_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 15", (target_uid,))
        h_rows = cursor.fetchall()
        conn.close()
        
        if not p_row: return
        
        # Save active chat state so Prince Bhai can just type a message to reply
        conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO admin_state VALUES (?, ?)", (OWNER_ID, target_uid))
        conn.commit()
        conn.close()
        
        history_text = f"⚙️ **User File Log:**\n👤 **Name:** {p_row[0]}\n🆔 **ID:** `{target_uid}`\n🌐 **Username:** @{p_row[1] if p_row[1] else 'None'}\n\n📝 **Recent Actions History:**\n"
        if not h_rows:
            history_text += "_No actions recorded yet._"
        else:
            for act, det, ts in h_rows:
                tm = time.strftime('%d-%m %H:%M', time.localtime(ts))
                history_text += f"▪️ `[{tm}]` **{act}**: {det}\n"
        
        history_text += "\n💬 📝 **How to Reply:**\nJust type your message normal here in chat and send it. The bot will automatically deliver it directly to this user!"
        
        kb = {"inline_keyboard": [[{"text": "⬅️ Back to Users List", "callback_data": "adm_users_list"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={
            "chat_id": chat_id, "message_id": message_id, "text": history_text, "parse_mode": "Markdown", "reply_markup": kb
        })

# 🔄 24/7 Global Engine For Join Requests (7 Hours Rule)
def continuous_request_processor():
    while True:
        try:
            conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, chat_id FROM pending_channel_requests")
            pending_requests = cursor.fetchall()
            conn.close()

            current_now = time.time()
            seven_hours = 7 * 60 * 60

            for user_id, chat_id in pending_requests:
                is_in_group = True
                try:
                    res = requests.post(f"{BASE_URL}/getChatMember", json={"chat_id": FREE_GROUP_ID, "user_id": user_id}, timeout=10).json()
                    if res.get("ok"):
                        is_in_group = res["result"]["status"] not in ["left", "kicked"]
                except Exception: continue

                if is_in_group: continue  

                conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
                cursor = conn.cursor()
                cursor.execute("SELECT leave_timestamp FROM member_activity WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                conn.close()

                if (row and (current_now - row[0]) >= seven_hours) or not row:
                    requests.post(f"{BASE_URL}/approveChatJoinRequest", json={"chat_id": chat_id, "user_id": user_id})
                    try:
                        conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM pending_channel_requests WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
                        conn.commit()
                        conn.close()
                    except Exception: pass
        except Exception: pass
        time.sleep(15)

# 🚀 Main Safe Loop
if __name__ == "__main__":
    threading.Thread(target=continuous_request_processor, daemon=True).start()
    print("🚀 CRM Active. Listening safely...")
    offset = 0
    while True:
        try:
            response = requests.post(f"{BASE_URL}/getUpdates", json={"offset": offset, "timeout": 10, "allowed_updates": ["message", "callback_query", "chat_join_request"]}, timeout=15).json()
            if response.get("ok"):
                for update in response["result"]:
                    offset = update["update_id"] + 1
                    if "chat_join_request" in update:
                        req = update["chat_join_request"]
                        conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
                        cursor = conn.cursor()
                        cursor.execute("INSERT OR IGNORE INTO pending_channel_requests VALUES (?, ?, ?)", (req["from"]["id"], req["chat"]["id"], time.time()))
                        conn.commit()
                        conn.close()
                    elif "message" in update:
                        handle_incoming_message(update["message"])
                    elif "callback_query" in update:
                        handle_callback_query(update["callback_query"])
            else:
                if response.get("error_code") == 409: time.sleep(15)
        except Exception: time.sleep(5)
    
