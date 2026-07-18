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
    
    # 📌 Leave Tracking Tables for cross-checking
    cursor.execute("CREATE TABLE IF NOT EXISTS group_leaves (user_id INTEGER PRIMARY KEY, timestamp REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS channel_leaves (user_id INTEGER PRIMARY KEY, timestamp REAL)")
    
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

def log_user_history(user_id, action_type, details):
    try:
        conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO user_history (user_id, action_type, details, timestamp) VALUES (?, ?, ?, ?)",
                       (user_id, action_type, details, time.time()))
        conn.commit()
        conn.close()
    except Exception: pass

# 🧱 Keyboards Setup
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
        "keyboard": [[{"text": "👥 View All Users (Admin Panel)"}]],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

# 🔍 Cross-Check double leaves and ping user
def verify_and_ping_double_leave(user_id):
    try:
        conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp FROM group_leaves WHERE user_id = ?", (user_id,))
        g_row = cursor.fetchone()
        cursor.execute("SELECT timestamp FROM channel_leaves WHERE user_id = ?", (user_id,))
        c_row = cursor.fetchone()
        conn.close()

        if g_row and c_row:
            leave_msg = (
                "👋 Hello, Trader!\n\n"
                "We noticed that you have left both our **Gold Expert Fx Community** and **VIP Premium Signals Channel**.\n\n"
                "Could you please share your feedback with us? If there was any issue with the signals, community rules, "
                "or if you need any specific customization, please let us know directly here so we can improve our services for you. Thank you!"
            )
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": user_id, "text": leave_msg, "parse_mode": "Markdown"})
            log_user_history(user_id, "LEAVE_FEEDBACK_SENT", "Sent double leave inquiry to user inbox")
            
            conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM group_leaves WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM channel_leaves WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
    except Exception: pass

# 🛡️ Main Message & Event Handler
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
                cursor.execute("INSERT OR REPLACE INTO group_leaves VALUES (?, ?)", (left_user_id, time.time()))
                conn.commit()
                conn.close()
                threading.Thread(target=verify_and_ping_double_leave, args=(left_user_id,), daemon=True).start()
            except Exception: pass
        return

    if text and chat_id == FREE_GROUP_ID:
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+|[a-zA-r0-9\-\.]+\.(com|net|org|xyz|info|co))'
        if re.search(url_pattern, text, re.IGNORECASE):
            if not (msg.get("forward_from_chat", {}).get("id") == PRIVATE_CHANNEL_ID or from_user_id == OWNER_ID):
                requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
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

        if from_user_id == OWNER_ID and text == "👥 View All Users (Admin Panel)":
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
                "chat_id": OWNER_ID, 
                "text": "👥 **Select a user to view full log details & open direct chat box:**", 
                "parse_mode": "Markdown", 
                "reply_markup": kb
            })
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
                res = requests.post(f"{BASE_URL}/sendMessage", json=payload).json()
                if res.get("ok"):
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"✅ Message delivered to User ID: {target_id}"})
                else:
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "❌ Delivery failed. User may have blocked the bot."})
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
            
            payload = {"chat_id": chat_id, "text": welcome, "parse_mode": "Markdown", "reply_markup": get_main_keyboard()}
            if from_user_id == OWNER_ID:
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": "👑 Welcome Back Prince Bhai. Admin menu activated below.", "reply_markup": get_owner_menu()})
            
            requests.post(f"{BASE_URL}/sendMessage", json=payload)
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
                f"👉 Use the Admin Panel menu to inspect history and reply."
            )
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": admin_alert, "parse_mode": "Markdown"})

    if chat_id == FREE_GROUP_ID and from_user_id == OWNER_ID:
        threading.Thread(target=lambda: requests.post(f"{BASE_URL}/setMessageReaction", json={
            "chat_id": chat_id, "message_id": message_id, 
            "reaction": [{"type": "emoji", "emoji": random.choice(EMOJI_POOL)}]}
        ), daemon=True).start()

# 🎛️ Callback Queries Engine (Seamless Transitions)
def handle_callback_query(callback):
    c_id = callback["id"]
    from_user = callback["from"]
    from_user_id = from_user["id"]
    chat_id = callback["message"]["chat"]["id"]
    message_id = callback["message"]["message_id"]
    data = callback["data"]
    
    requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": c_id})
    
    account_management_text = (
        "Account Management Service – Terms & Rules\n\n"
        "Please read the following terms carefully before joining our Account Management Service.\n\n"
        "1. Trading Account\n"
        "You will provide your MT4 or MT5 login details so we can manage your trading account professionally.\n\n"
        "2. Fund Security\n"
        "Your funds always remain in your own trading account. We cannot deposit, withdraw, or transfer your money. Only you have full control over your funds.\n\n"
        "3. Profit Sharing\n"
        "All trading profits will be shared 50% for you and 50% for us.\n\n"
        "4. Loss Sharing\n"
        "If a trading loss occurs, the loss will also be shared 50/50. Since we receive 50% of the profit, we also accept 50% of the trading loss.\n\n"
        "5. Profit Payment\n"
        "After profit is generated, we will notify you. You can then send our 50% profit share using any of the payment methods listed below.\n\n"
        "6. No Scam\n"
        "This is a transparent and honest service. There are no hidden charges, no scams, and no fake promises.\n\n"
        "7. No Long-Term Commitment\n"
        "You are free to start or stop the service at any time. There is no pressure or obligation to continue working with us.\n\n"
        "Accepted Brokers\n"
        "✅ All Brokers Accepted\n\n"
        "Accepted Payment Methods\n"
        "- Binance\n- USDT\n- Skrill\n- Neteller\n- Bitcoin (BTC)\n- Ethereum (ETH)\n- Perfect Money\n- WebMoney\n\n"
        "Thank you for choosing our Account Management Service. We look forward to building a successful and long-term partnership with you."
    )
    
    vip_text = (
        "Join Our VIP Premium Group\n\n"
        "If you ever miss our free signals or want more trading opportunities with higher consistency, you can join our VIP Premium Group.\n\n"
        "What You Get:\n"
        "- ✅ 5–7 XAUUSD signals daily\n"
        "- ✅ High-accuracy trade setups\n"
        "- ✅ Point-by-point trade updates\n"
        "- ✅ Entry, Take Profit & Stop Loss levels\n"
        "- ✅ Market analysis & chart analysis\n"
        "- ✅ Trading rules and risk management guidance\n"
        "- ✅ Learning and educational support\n\n"
        "If, after joining, you feel the VIP Premium Group does not provide the services described above, you may contact our support team to request cancellation. In that case, we will deduct 30% as a service fee and refund the remaining 70% of your payment, subject to our refund policy.\n\n"
        "VIP Membership Packages\n"
        "- 💎 Lifetime Access: $700 (One-Time Payment)\n"
        "- 📅 1 Year: $500\n"
        "- 📆 1 Month: $300\n"
        "- 📈 1 Week: $100\n\n"
        "«Note: All packages include the same VIP features. The only difference is the membership duration.»\n\n"
        "You can judge our trading accuracy by following our Free Signals Channel/Group before upgrading.\n\n"
        "If you need more information or have any questions, feel free to contact us. Our support team will be happy to assist you."
    )
    
    copy_trading_text = (
        "📋 Copy Trading Terms & Conditions\n\n"
        "Gold Expert FX | Copy Trading Rules\n\n"
        "1. Account Requirement\n"
        "- Client ke paas MT4 ya MT5 trading account hona chahiye.\n"
        "- Account kisi supported broker par hona chahiye.\n\n"
        "2. Copy Trading Setup\n"
        "- Client apna Investor Password ya Copy Trading connection details provide karega.\n"
        "- Account ki ownership hamesha client ke paas rahegi.\n\n"
        "3. Minimum Deposit\n"
        "- Recommended minimum deposit: $200 ya us se zyada.\n\n"
        "4. Risk Warning\n"
        "- Forex aur Gold trading high-risk business hai.\n"
        "- Profit guaranteed nahi hota.\n"
        "- Market ki volatility ki wajah se loss bhi ho sakta.\n\n"
        "5. Profit & Loss\n"
        "- Account ka sara profit aur loss client ke account mein hi hoga.\n"
        "- Gold Expert FX market conditions ke mutabiq trades provide karega.\n\n"
        "6. No Deposit Withdrawal\n"
        "- Hum kabhi bhi client ke account se funds withdraw nahi kar sakte.\n"
        "- Funds par sirf account owner ka control hota hai.\n\n"
        "7. VPS & Internet\n"
        "- Copy Trading ko smoothly chalane ke liye stable internet ya VPS use karna recommended hai.\n\n"
        "8. Account Changes\n"
        "- Client bina inform kiye leverage, password, ya account settings change na kare.\n"
        "- Agar changes kiye gaye to service temporarily stop ki ja sakti hai.\n\n"
        "9. Responsibility\n"
        "- Client apne account aur broker ki policies ka khud zimmedar hoga.\n"
        "- Broker ki kisi technical problem ya slippage ke liye Gold Expert FX responsible nahi hoga.\n\n"
        "10. Trading Results\n"
        "- Past performance future profit ki guarantee nahi hoti.\n"
        "- Har trade mein risk hota hai.\n\n"
        "11. Service Cancellation\n"
        "- Gold Expert FX kisi bhi waqt rules violation ya misuse ki surat mein Copy Trading service terminate kar sakta hai.\n\n"
        "12. Agreement\n"
        "- Copy Trading service join karte hi client in tamam Terms & Conditions ko accept karta hai.\n\n"
        "Copy Trading Service\n\n"
        "If you don't have enough time to analyze the market or place trades manually, you can join our Copy Trading Service.\n\n"
        "Our Copy Trading Service allows our trades to be copied automatically to your trading account. Simply complete the setup once, and your account will receive our trades automatically. You don't need to monitor the market or trade manually.\n\n"
        "What You Get\n"
        "- ✅ Automatic trade copying\n"
        "- ✅ Professional trade management\n"
        "- ✅ No daily market analysis required\n"
        "- ✅ Save your valuable time\n"
        "- ✅ One-time setup\n"
        "- ✅ No monthly subscription\n"
        "- ✅ No hidden charges\n"
        "- ✅ One-time payment only\n\n"
        "Supported Brokers\n"
        "We support all MT4 and MT5 brokers.\n\n"
        "After your payment has been successfully confirmed, we will provide you with all the required Copy Trading details and guide you through the complete setup process.\n\n"
        "Copy Trading Fee\n"
        "💰 One-Time Payment: $1,000\n\n"
        "There are no monthly fees, no profit-sharing, and no hidden commissions. After paying the one-time fee, you can use our Copy Trading Service without any additional service charges.\n\n"
        "Risk & Refund Policy\n"
        "We use professional risk management and always try to protect our clients' accounts. However, trading in financial markets always involves risk, and no one can guarantee that losses will never occur or that profits are guaranteed.\n\n"
        "If you decide to cancel the Copy Trading Service, you may contact our support team.\n\n"
        "According to our refund policy:\n"
        "- We will deduct 30% as a service and administration fee.\n"
        "- The remaining 70% of your one-time payment will be refunded to you.\n\n"
        "Contact Us\n"
        "If you have any questions or need more information, feel free to contact our support team. We will be happy to assist you with the registration and setup process."
    )

    # Clean multi-line structure to ensure text never cuts off mid-string
    if data == "srv_account":
        log_user_history(from_user_id, "NAVIGATE", "Viewed Account Management Rules")
        kb = {"inline_keyboard": [[{"text": "🚀 Join Service Now", "callback_data": "join_account"}]]}
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": account_management_text,
            "reply_markup": kb
        }
        requests.post(f"{BASE_URL}/editMessageText", json=payload)

    elif data == "join_account":
        log_user_history(from_user_id, "CLICK_BUTTON", "Clicked Join Account Management")
        format_text = (
            "1) Broker name -\n"
            "2) Server name -\n"
            "3) Platform - (MT4/MT5)\n"
            "4) Deposit Amount - (Minimum $500)\n"
            "5) Login ID -\n"
            "6) Password -\n"
 
