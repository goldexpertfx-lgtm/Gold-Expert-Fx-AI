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
    conn = sqlite3.connect("gold_expert_premium.db", timeout=20)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS member_activity (user_id INTEGER PRIMARY KEY, leave_timestamp REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS pending_channel_requests (user_id INTEGER, chat_id INTEGER, request_time REAL, PRIMARY KEY (user_id, chat_id))")
    
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dynamic_content (
            service_key TEXT PRIMARY KEY,
            text_content TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_edit_state (
            admin_id INTEGER PRIMARY KEY,
            editing_service TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_content(service_key, default_text):
    try:
        conn = sqlite3.connect("gold_expert_premium.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("SELECT text_content FROM dynamic_content WHERE service_key = ?", (service_key,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]: return row[0]
    except Exception: pass
    return default_text

def set_content(service_key, new_text):
    try:
        conn = sqlite3.connect("gold_expert_premium.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO dynamic_content VALUES (?, ?)", (service_key, new_text))
        conn.commit()
        conn.close()
        return True
    except Exception: return False

def log_user_history(user_id, action_type, details):
    try:
        conn = sqlite3.connect("gold_expert_premium.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO user_history (user_id, action_type, details, timestamp) VALUES (?, ?, ?, ?)",
                       (user_id, action_type, details, time.time()))
        conn.commit()
        conn.close()
    except Exception: pass

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

def handle_incoming_message(msg):
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")
    text = msg.get("text", "")
    from_user = msg.get("from", {})
    from_user_id = from_user.get("id")
    chat_type = msg.get("chat", {}).get("type")
    
    if not from_user_id: return

    if "new_chat_members" in msg or "left_chat_member" in msg:
        requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
        if chat_id == FREE_GROUP_ID and "left_chat_member" in msg:
            left_id = msg["left_chat_member"]["id"]
            log_user_history(left_id, "STATUS", "Left the Free Community Group")
            try:
                conn = sqlite3.connect("gold_expert_premium.db", timeout=20)
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO member_activity VALUES (?, ?)", (left_id, time.time()))
                conn.commit()
                conn.close()
            except Exception: pass
        return

    if text and chat_id == FREE_GROUP_ID and from_user_id != OWNER_ID:
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+|[a-zA-r0-9\-\.]+\.(com|net|org))'
        if re.search(url_pattern, text, re.IGNORECASE):
            if msg.get("forward_from_chat", {}).get("id") != PRIVATE_CHANNEL_ID:
                requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
                return

    if chat_type == "private":
        try:
            conn = sqlite3.connect("gold_expert_premium.db", timeout=20)
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO users_profile VALUES (?, ?, ?, ?)", 
                           (from_user_id, from_user.get("first_name"), from_user.get("username"), time.time()))
            conn.commit()
            conn.close()
        except Exception: pass

        if text and text.startswith("/start"):
            log_user_history(from_user_id, "COMMAND", "/start target triggered")
            welcome = f"👋 **Hello, {from_user.get('first_name', 'Trader')}!**\n\nWelcome to **Gold Expert FX Automation Hub**. Please select a service below:"
            payload = {"chat_id": chat_id, "text": welcome, "parse_mode": "Markdown", "reply_markup": get_main_keyboard()}
            if from_user_id == OWNER_ID:
                payload["reply_markup"] = get_owner_menu()
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": "👑 Welcome Prince Bhai. Custom Dashboard active.", "reply_markup": get_owner_menu()})
            requests.post(f"{BASE_URL}/sendMessage", json=payload)
            return

        if from_user_id == OWNER_ID:
            if text == "👥 View Total Users":
                conn = sqlite3.connect("gold_expert_premium.db", timeout=20)
                cursor = conn.cursor()
                cursor.execute("SELECT user_id, first_name, username FROM users_profile ORDER BY join_date DESC")
                rows = cursor.fetchall()
                conn.close()
                
                if not rows:
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "📭 Database contains zero logged users yet."})
                    return
                
                kb = {"inline_keyboard": []}
                for u_id, fn, un in rows:
                    disp = f"{fn} (@{un})" if un else f"{fn}"
                    kb["inline_keyboard"].append([{"text": f"👤 {disp} [ID: {u_id}]", "callback_data": f"adm_view_{u_id}"}])
                
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"📊 **Total Active Users Registered:** `{len(rows)}` \n\nClick on any user below to open their operational chatbox history logs:", "parse_mode": "Markdown", "reply_markup": kb})
                return

            elif text == "✏️ Live Edit Messages":
                kb = {
                    "inline_keyboard": [
                        [{"text": "📝 Edit Account Management Text", "callback_data": "edt_account"}],
                        [{"text": "📝 Edit VIP Premium Text", "callback_data": "edt_vip"}],
                        [{"text": "📝 Edit Copy Trading Text", "callback_data": "edt_copy"}],
                        [{"text": "❌ Cancel", "callback_data": "edt_cancel"}]
                    ]
                }
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "🛠️ **Prince Bhai, select the post content you want to modify live:**", "reply_markup": kb})
                return

            # Handle incoming edit texts or active chatbox replies
            conn = sqlite3.connect("gold_expert_premium.db", timeout=20)
            cursor = conn.cursor()
            cursor.execute("SELECT editing_service FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
            edit_row = cursor.fetchone()
            
            cursor.execute("SELECT target_user_id FROM admin_state WHERE admin_id = ?", (OWNER_ID,))
            target_row = cursor.fetchone()
            conn.close()

            if edit_row and edit_row[0]:
                service_key = edit_row[0]
                if set_content(service_key, text):
                    conn = sqlite3.connect("gold_expert_premium.db", timeout=20)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
                    conn.commit()
                    conn.close()
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"✅ **Live Updated!** New text saved for `{service_key}` perfectly.", "parse_mode": "Markdown"})
                return

            elif target_row and not text.startswith("/"):
                t_id = target_row[0]
                payload = {"chat_id": t_id, "text": f"💬 **Message from Admin (Prince Bhai):**\n\n{text}", "parse_mode": "Markdown"}
                res = requests.post(f"{BASE_URL}/sendMessage", json=payload).json()
                if res.get("ok"):
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "🚀 Reply dispatched cleanly to client chat field."})
                else:
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "❌ Delivery failed. User might have blocked the bot."})
                return

        if from_user_id != OWNER_ID:
            log_user_history(from_user_id, "USER_MESSAGE", text)
            if "Broker name" in text or "Login ID" in text or "Password" in text:
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": "⏳ **Format Received Successfully!**\n\nPlease wait while our team reviews your trading details and initializes your connection. We will notify you here directly.", "parse_mode": "Markdown"})
            
            admin_alert = f"📥 **New Chat Box Message!**\n👤 **From:** {from_user.get('first_name')} [ID: `{from_user_id}`]\n💬 **Text:** {text}\n\n👉 Click 'View Total Users' to open this chat logs history and reply."
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": admin_alert, "parse_mode": "Markdown"})

def handle_callback_query(callback):
    c_id = callback["id"]
    from_user_id = callback["from"]["id"]
    chat_id = callback["message"]["chat"]["id"]
    message_id = callback["message"]["message_id"]
    data = callback["data"]
    
    requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": c_id})

    # Massive Restored Formats
    def_account_text = """Account Management Service – Terms & Rules

Please read the following terms carefully before joining our Account Management Service.

1. Trading Account
You will provide your MT4 or MT5 login details so we can manage your trading account professionally.

2. Fund Security
Your funds always remain in your own trading account. We cannot deposit, withdraw, or transfer your money. Only you have full control over your funds.

3. Profit Sharing
All trading profits will be shared 50% for you and 50% for us.

4. Loss Sharing
If a trading loss occurs, the loss will also be shared 50/50. Since we receive 50% of the profit, we also accept 50% of the trading loss.

5. Profit Payment
After profit is generated, we will notify you. You can then send our 50% profit share using any of the payment methods listed below.

6. No Scam
This is a transparent and honest service. There are no hidden charges, no scams, and no fake promises.

7. No Long-Term Commitment
You are free to start or stop the service at any time. There is no pressure or obligation to continue working with us.

Accepted Brokers
✅ All Brokers Accepted

Accepted Payment Methods
- Binance / USDT
- Skrill / Neteller
- Bitcoin (BTC) / Crypto
- Perfect Money / WebMoney

Thank you for choosing our Account Management Service."""

    def_vip_text = """Join Our VIP Premium Group

If you ever miss our free signals or want more trading opportunities with higher consistency, you can join our VIP Premium Group.

What You Get:
- ✅ 5–7 XAUUSD signals daily
- ✅ High-accuracy trade setups
- ✅ Point-by-point trade updates
- ✅ Entry, Take Profit & Stop Loss levels
- ✅ Market analysis & chart analysis

VIP Membership Packages
- 💎 Lifetime Access: $700 (One-Time Payment)
- 📅 1 Year: $500
- 📆 1 Month: $300
- 📈 1 Week: $100

You can judge our trading accuracy by following our Free Signals Channel before upgrading."""

    def_copy_text = """📋 Copy Trading Terms & Conditions

Gold Expert FX | Copy Trading Rules

1. Account Requirement
- Client ke paas MT4 ya MT5 trading account hona chahiye.
- Recommended minimum deposit: $200 ya us se zyada.

2. No Deposit Withdrawal
- Hum kabhi bhi client ke account se funds withdraw nahi kar sakte. Only you hold structural access.

Copy Trading Fee
💰 One-Time Payment: $1,000

There are no monthly fees, no profit-sharing, and no hidden commissions. After paying the one-time fee, you can use our Copy Trading Service without any additional service charges."""

    if data.startswith("edt_") and from_user_id == OWNER_ID:
        action = data.split("_")[1]
        if action == "cancel":
            conn = sqlite3.connect("gold_expert_premium.db", timeout=20)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
            conn.commit()
            conn.close()
            requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": "❌ Sequence cancelled smoothly."})
            return
        
        conn = sqlite3.connect("gold_expert_premium.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO admin_edit_state VALUES (?, ?)", (OWNER_ID, action))
        conn.commit()
        conn.close()
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": f"📥 **System Ready!**\n\nSend the new raw string message now to overwrite `{action}` completely down in the server database.", "parse_mode": "Markdown"})
        return

    if data.startswith("adm_view_") and from_user_id == OWNER_ID:
        t_uid = int(data.split("_")[2])
        conn = sqlite3.connect("gold_expert_premium.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("SELECT first_name, username FROM users_profile WHERE user_id = ?", (t_uid,))
        prof = cursor.fetchone()
        cursor.execute("SELECT action_type, details, timestamp FROM user_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 20", (t_uid,))
        logs = cursor.fetchall()
        cursor.execute("INSERT OR REPLACE INTO admin_state VALUES (?, ?)", (OWNER_ID, t_uid))
        conn.commit()
        conn.close()
        
        if not prof: return
        history_text = f"⚙️ **User Chatbox & Historical Activity Logs:**\n👤 **Name:** {prof[0]}\n🆔 **ID:** `{t_uid}`\n🌐 **User:** @{prof[1] if prof[1] else 'None'}\n\n📝 **Timeline Tracking Trace:**\n"
        if not logs:
            history_text += "_No previous footprints logged for this user profile._"
        else:
            for atype, det, ts in logs:
                tm = time.strftime('%d-%m %H:%M', time.localtime(ts))
                history_text += f"▪️ `[{tm}]` **{atype}**: {det}\n"
        
        history_text += "\n💬 **Direct Reply System:**\nType your normal message text here in this chat box interface and hit send. The engine will instantly mirror it to the user's private bot screen!"
        requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": history_text, "parse_mode": "Markdown"})
        return

    if data == "srv_account":
        log_user_history(from_user_id, "NAVIGATE", "Looked up Account Management Details")
        txt = get_content("account", def_account_text)
        kb = {"inline_keyboard": [[{"text": "🚀 Join Service Now", "callback_data": "join_account"}]]}
        if from_user_id == OWNER_ID: kb["inline_keyboard"].append([{"text": "⚡ Direct Edit Post Content", "callback_data": "edt_account"}])
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": txt, "parse_mode": "Markdown", "reply_markup": kb})

    elif data == "join_account":
        log_user_history(from_user_id, "CLICK", "Requested Account Management Application Form")
        fmt = "1) Broker name -\n2) Server name -\n3) Platform - (MT4/MT5)\n4) Deposit Amount - (Minimum $500)\n5) Login ID -\n6) Password -\n7) Leverage - ( Minimum 1:500)\n8) How you will send money?\n\n📝 **Fill this format and send it directly here in the chat.**"
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": fmt, "parse_mode": "Markdown"})

    elif data == "srv_vip":
        log_user_history(from_user_id, "NAVIGATE", "Viewed VIP Packages Structure")
        txt = get_content("vip", def_vip_text)
        kb = {"inline_keyboard": [[{"text": "💎 Join VIP Premium", "callback_data": "join_vip_packages"}]]}
        if from_user_id == OWNER_ID: kb["inline_keyboard"].append([{"text": "⚡ Direct Edit Post Content", "callback_data": "edt_vip"}])
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": txt, "parse_mode": "Markdown", "reply_markup": kb})

    elif data == "join_vip_packages":
        kb = {
            "inline_keyboard": [
                [{"text": "💎 Lifetime Access - $700", "callback_data": "pay_wait"}],
                [{"text": "📅 1 Year Access - $500", "callback_data": "pay_wait"}],
                [{"text": "📆 1 Month Access - $300", "callback_data": "pay_wait"}]
            ]
        }
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": "🎯 **Select Your Desired Membership package tier:**", "reply_markup": kb})

    elif data == "srv_copy":
        log_user_history(from_user_id, "NAVIGATE", "Opened Copy Trading Terms Summary")
        txt = get_content("copy", def_copy_text)
        kb = {"inline_keyboard": [[{"text": "📋 Connect Copy Trading Service", "callback_data": "pay_wait"}]]}
        if from_user_id == OWNER_ID: kb["inline_keyboard"].append([{"text": "⚡ Direct Edit Post Content", "callback_data": "edt_copy"}])
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": txt, "parse_mode": "Markdown", "reply_markup": kb})

    elif data == "pay_wait":
        log_user_history(from_user_id, "ACTION", "Selected Payment Setup Execution Flow")
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": "⏳ **Please wait...** our team is compiling your exclusive secure transaction parameters. Standby instructions will follow shortly here."})

def check_and_approve():
    try:
        conn = sqlite3.connect("gold_expert_premium.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, chat_id FROM pending_channel_requests")
        reqs = cursor.fetchall()
   
