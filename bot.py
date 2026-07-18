import requests
import sqlite3
import time
import threading
import re
import sys
import random

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
API_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"  # ⚠️ Token yahan dalein
OWNER_ID = 7415265825  # 👑 Prince Bhai ID

FREE_GROUP_ID = -4477244119  
PRIVATE_CHANNEL_ID = -3870933647  
# ==========================================

if not API_TOKEN:
    print("❌ ERROR: API_TOKEN khali hai!")
    sys.exit(1)

BASE_URL = f"https://api.telegram.org/bot{API_TOKEN}"
EMOJI_POOL = ["🔥", "🚀", "👍", "❤️", "⚡", "🎉", "🤩"]

def init_db():
    conn = sqlite3.connect(
        "new_join_filter_bot.db", timeout=20
    )
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS member_activity "
        "(user_id INTEGER PRIMARY KEY, "
        "leave_timestamp REAL)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS "
        "pending_channel_requests (user_id INTEGER, "
        "chat_id INTEGER, request_time REAL, "
        "PRIMARY KEY (user_id, chat_id))"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS group_leaves "
        "(user_id INTEGER PRIMARY KEY, timestamp REAL)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS channel_leaves "
        "(user_id INTEGER PRIMARY KEY, timestamp REAL)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS users_profile ("
        "user_id INTEGER PRIMARY KEY, "
        "first_name TEXT, username TEXT, join_date REAL)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS user_history ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "user_id INTEGER, action_type TEXT, "
        "details TEXT, timestamp REAL)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS admin_state ("
        "admin_id INTEGER PRIMARY KEY, "
        "target_user_id INTEGER)"
    )
    conn.commit()
    conn.close()

init_db()

def log_user_history(user_id, action_type, details):
    try:
        conn = sqlite3.connect(
            "new_join_filter_bot.db", timeout=20
        )
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_history (user_id, "
            "action_type, details, timestamp) "
            "VALUES (?, ?, ?, ?)",
            (user_id, action_type, details, time.time())
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_main_keyboard():
    return {
        "inline_keyboard": [
            [{
                "text": "💼 Account Management Services",
                "callback_data": "srv_account"
            }],
            [{
                "text": "👑 VIP Premium Private Channel",
                "callback_data": "srv_vip"
            }],
            [{
                "text": "📋 Copy Trading Service",
                "callback_data": "srv_copy"
            }]
        ]
    }

def get_owner_menu():
    return {
        "keyboard": [[{
            "text": "👥 View All Users (Admin Panel)"
        }]],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

def verify_and_ping_double_leave(user_id):
    try:
        conn = sqlite3.connect(
            "new_join_filter_bot.db", timeout=20
        )
        cursor = conn.cursor()
        cursor.execute(
            "SELECT timestamp FROM group_leaves "
            "WHERE user_id = ?", (user_id,)
        )
        g_row = cursor.fetchone()
        cursor.execute(
            "SELECT timestamp FROM channel_leaves "
            "WHERE user_id = ?", (user_id,)
        )
        c_row = cursor.fetchone()
        conn.close()

        if g_row and c_row:
            chunks = [
                "👋 Hello, Trader!\n\n",
                "We noticed that you have left both our ",
                "**Gold Expert Fx Community** and ",
                "**VIP Premium Signals Channel**.\n\n",
                "Could you please share your feedback? ",
                "If there was any issue with signals, ",
                "rules, or if you need customization, ",
                "please let us know here directly. Thanks!"
            ]
            leave_msg = "".join(chunks)
            requests.post(
                f"{BASE_URL}/sendMessage",
                json={
                    "chat_id": user_id,
                    "text": leave_msg,
                    "parse_mode": "Markdown"
                }
            )
            log_user_history(
                user_id, "LEAVE_FEEDBACK_SENT",
                "Sent double leave inquiry to inbox"
            )
            
            conn = sqlite3.connect(
                "new_join_filter_bot.db", timeout=20
            )
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM group_leaves "
                "WHERE user_id = ?", (user_id,)
            )
            cursor.execute(
                "DELETE FROM channel_leaves "
                "WHERE user_id = ?", (user_id,)
            )
            conn.commit()
            conn.close()
    except Exception:
        pass

def handle_incoming_message(msg):
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")
    text = msg.get("text", "")
    from_user = msg.get("from", {})
    from_user_id = from_user.get("id")
    chat_type = msg.get("chat", {}).get("type")
    
    if "new_chat_members" in msg or "left_chat_member" in msg:
        requests.post(
            f"{BASE_URL}/deleteMessage",
            json={"chat_id": chat_id, "message_id": message_id}
        )
        
        if (chat_id == FREE_GROUP_ID and 
                "left_chat_member" in msg):
            left_user_id = msg["left_chat_member"]["id"]
            try:
                conn = sqlite3.connect(
                    "new_join_filter_bot.db", timeout=20
                )
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO member_activity "
                    "VALUES (?, ?)", (left_user_id, time.time())
                )
                cursor.execute(
                    "INSERT OR REPLACE INTO group_leaves "
                    "VALUES (?, ?)", (left_user_id, time.time())
                )
                conn.commit()
                conn.close()
                threading.Thread(
                    target=verify_and_ping_double_leave,
                    args=(left_user_id,), daemon=True
                ).start()
            except Exception:
                pass
        return

    if text and chat_id == FREE_GROUP_ID:
        url_pattern = (
            r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+|'
            r'[a-zA-r0-9\-\.]+\.(com|net|org|xyz|info|co))'
        )
        if re.search(url_pattern, text, re.IGNORECASE):
            fwd_id = msg.get(
                "forward_from_chat", {}
            ).get("id")
            if not (fwd_id == PRIVATE_CHANNEL_ID or 
                    from_user_id == OWNER_ID):
                requests.post(
                    f"{BASE_URL}/deleteMessage",
                    json={
                        "chat_id": chat_id,
                        "message_id": message_id
                    }
                )
                return

    if chat_type == "private":
        try:
            conn = sqlite3.connect(
                "new_join_filter_bot.db", timeout=20
            )
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO users_profile "
                "VALUES (?, ?, ?, ?)", 
                (
                    from_user_id,
                    from_user.get("first_name"),
                    from_user.get("username"),
                    time.time()
                )
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

        if (from_user_id == OWNER_ID and 
                text == "👥 View All Users (Admin Panel)"):
            conn = sqlite3.connect(
                "new_join_filter_bot.db", timeout=20
            )
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, first_name, username "
                "FROM users_profile ORDER BY join_date "
                "DESC LIMIT 30"
            )
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                requests.post(
                    f"{BASE_URL}/sendMessage",
                    json={
                        "chat_id": OWNER_ID,
                        "text": "📭 No logged users found."
                    }
                )
                return
                
            kb = {"inline_keyboard": []}
            for u_id, f_name, u_name in rows:
                disp = (
                    f"{f_name} (@{u_name})" if u_name 
                    else f"{f_name}"
                )
                kb["inline_keyboard"].append([{
                    "text": f"👤 {disp}",
                    "callback_data": f"adm_view_{u_id}"
                }])
            
            requests.post(
                f"{BASE_URL}/sendMessage",
                json={
                    "chat_id": OWNER_ID, 
                    "text": "👥 **Select user to view logs:**", 
                    "parse_mode": "Markdown", 
                    "reply_markup": kb
                }
            )
            return

        if (from_user_id == OWNER_ID and text and 
                not text.startswith("/")):
            conn = sqlite3.connect(
                "new_join_filter_bot.db", timeout=20
            )
            cursor = conn.cursor()
            cursor.execute(
                "SELECT target_user_id FROM admin_state "
                "WHERE admin_id = ?", (OWNER_ID,)
            )
            row = cursor.fetchone()
            conn.close()
            
            if row:
                target_id = row[0]
                payload = {
                    "chat_id": target_id,
                    "text": f"💬 **Message from Admin:**\n\n{text}",
                    "parse_mode": "Markdown"
                }
                res = requests.post(
                    f"{BASE_URL}/sendMessage", json=payload
                ).json()
                if res.get("ok"):
                    requests.post(
                        f"{BASE_URL}/sendMessage",
                        json={
                            "chat_id": OWNER_ID,
                            "text": f"✅ Sent to: {target_id}"
                        }
                    )
                else:
                    requests.post(
                        f"{BASE_URL}/sendMessage",
                        json={
                            "chat_id": OWNER_ID,
                            "text": "❌ User blocked bot."
                        }
                    )
                return

        if text and text.startswith("/start"):
            log_user_history(
                from_user_id, "COMMAND", "/start executed"
            )
            name = from_user.get("first_name", "Trader")
            raw_un = from_user.get('username')
            uname = f"@{raw_un}" if raw_un else "No Username"
            
            chunks = [
                f"👋 **Hello, {name}!**\n",
                f"🌐 **Username:** {uname}\n",
                f"🆔 **Your Telegram ID:** `{from_user_id}`\n\n",
                "Welcome to **Gold Expert FX Automation Hub**.",
                " Please select any service from the buttons ",
                "below to view terms or apply:"
            ]
            welcome = "".join(chunks)
            
            payload = {
                "chat_id": chat_id,
                "text": welcome,
                "parse_mode": "Markdown",
                "reply_markup": get_main_keyboard()
            }
            if from_user_id == OWNER_ID:
                requests.post(
                    f"{BASE_URL}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": "👑 Welcome Prince Bhai.",
                        "reply_markup": get_owner_menu()
                    }
                )
            
            requests.post(f"{BASE_URL}/sendMessage", json=payload)
            return

        if text and from_user_id != OWNER_ID:
            log_user_history(from_user_id, "USER_MESSAGE", text)
            
            if ("Broker name" in text or "Login ID" in text 
                    or "Password" in text):
                requests.post(
                    f"{BASE_URL}/sendMessage",
                    json={
                        "chat_id": chat_id, 
                        "text": "⏳ **Format Received!**\n\n"
                        "Please wait while team reviews your "
                        "details. We will notify you here.",
                        "parse_mode": "Markdown"
                    }
                )
            
            admin_alert = (
                f"📥 **New User Message!**\n\n"
                f"👤 **From:** {from_user.get('first_name')} "
                f"| ID: `{from_user_id}`\n"
                f"💬 **Content:** {text}\n\n"
                f"👉 Use Admin Panel menu to reply."
            )
            requests.post(
                f"{BASE_URL}/sendMessage",
                json={
                    "chat_id": OWNER_ID,
                    "text": admin_alert,
                    "parse_mode": "Markdown"
                }
            )

    if chat_id == FREE_GROUP_ID and from_user_id == OWNER_ID:
        threading.Thread(target=lambda: requests.post(
            f"{BASE_URL}/setMessageReaction",
            json={
                "chat_id": chat_id, "message_id": message_id, 
                "reaction": [{
                    "type": "emoji",
                    "emoji": random.choice(EMOJI_POOL)
                }]
            }
        ), daemon=True).start()

def handle_callback_query(callback):
    c_id = callback["id"]
    from_user = callback["from"]
    from_user_id = from_user["id"]
    chat_id = callback["message"]["chat"]["id"]
    message_id = callback["message"]["message_id"]
    data = callback["data"]
    
    requests.post(
        f"{BASE_URL}/answerCallbackQuery",
        json={"callback_query_id": c_id}
    )
    
    ac_chunks = [
        "Account Management Service – Terms & Rules\n\n",
        "1. Trading Account: You provide MT4/5 log details.\n",
        "2. Fund Security: Funds remain in your account.\n",
        "3. Profit Sharing: 50% for you, 50% for us.\n",
        "4. Loss Sharing: Losses are also shared 50/50.\n",
        "5. Payment: Send profit via listed methods.\n",
        "6. Transparency: No hidden charges, no scams.\n",
        "7. Commitment: Stop/start service anytime.\n\n",
        "✅ All Brokers Accepted\n\n",
        "Accepted Payment Methods:\n",
        "- Binance / USDT / Crypto\n- Skrill / Neteller\n",
        "- Perfect Money / WebMoney"
    ]
    account_management_text = "".join(ac_chunks)
    
    vip_chunks = [
        "Join Our VIP Premium Group\n\n",
        "What You Get:\n",
        "- ✅ 5–7 XAUUSD signals daily\n",
        "- ✅ High-accuracy trade setups\n",
        "- ✅ Entry, Take Profit & Stop Loss levels\n",
        "- ✅ Market analysis & risk guidance\n\n",
        "Refund: 30% service fee deduction, 70% refund.\n\n",
        "VIP Membership Packages:\n",
        "- 💎 Lifetime Access: $700 (One-Time)\n",
        "- 📅 1 Year: $500\n- 📆 1 Month: $300\n",
        "- 📈 1 Week: $100\n\n",
        "Note: All packages include the same features."
    ]
    vip_text = "".join(vip_chunks)
    
    copy_chunks = [
        "📋 Copy Trading Terms & Conditions\n\n",
        "1. Requirement: Client needs MT4/MT5 account.\n",
        "2. Setup: Client provides access details.\n",
        "3. Minimum Deposit: $200 recommended.\n",
        "4. Risk Warning: Forex/Gold trading is risky.\n",
        "5. Control: We cannot withdraw your funds.\n",
        "6. VPS: Stable connection recommended.\n",
        "7. Past results don't guarantee future profit.\n\n",
        "Copy Trading Fee:\n",
        "💰 One-Time Payment: $1,000\n",
        "No monthly fees or profit-sharing.\n\n",
        "Refund Policy:\n",
        "- 30% admin fee deduction.\n",
        "- 70% of payment will be refunded."
    ]
    copy_trading_text = "".join(copy_chunks)

    if data == "srv_account":
        log_user_history(
            from_user_id, "NAVIGATE", "Viewed Account Terms"
        )
        kb = {"inline_keyboard": [[{
            "text": "🚀 Join Service Now",
            "callback_data": "join_account"
        }]]}
        payload = {
            "chat_id": chat_id, "message_id": message_id,
            "text": account_management_text, "reply_markup": kb
        }
        requests.post(f"{BASE_URL}/editMessageText", json=payload)

    elif data == "join_account":
        log_user_history(
            from_user_id, "CLICK_BUTTON", "Join Account Form"
        )
        form_chunks = [
            "1) Broker name -\n2) Server name -\n",
            "3) Platform - (MT4/MT5)\n",
            "4) Deposit Amount - (Minimum $500)\n",
            "5) Login ID -\n6) Password -\n",
            "7) Leverage - ( Minimum 1:500)\n",
            "8) How you will send money? \n",
            "(Binance, Skrill, Neteller, Crypto, Bank)\n\n",
            "📝 Fill this format and send it right here."
        ]
        payload = {
            "chat_id": chat_id, "message_id": message_id,
            "text": "".join(form_chunks)
        }
        requests.post(f"{BASE_URL}/editMessageText", json=payload)

    elif data == "srv_vip":
        log_user_history(
            from_user_id, "NAVIGATE", "Viewed VIP Rules"
        )
        kb = {"inline_keyboard": [[{
            "text": "💎 Join VIP Premium Now",
            "callback_data": "join_vip_packages"
        }]]}
        payload = {
            "chat_id": chat_id, "message_id": message_id,
            "text": vip_text, "reply_markup": kb
        }
        requests.post(f"{BASE_URL}/editMessageText", json=payload)

    elif data == "join_vip_packages":
        log_user_history(
            from_user_id, "NAVIGATE", "Viewing VIP Plans"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "💎 Lifetime - $700", 
                  "callback_data": "pay_vip_pkg"}],
                [{"text": "📅 1 Year - $500", 
                  "callback_data": "pay_vip_pkg"}],
                [{"text": "📆 1 Month - $300", 
                  "callback_data": "pay_vip_pkg"}],
                [{"text": "📈 1 Week - $100", 
                  "callback_data": "pay_vip_pkg"}]
            ]
        }
        payload = {
            "chat_id": chat_id, "message_id": message_id,
            "text": "🎯 **Select Your Membership Plan:**",
            "reply_markup": kb
        }
        requests.post(f"{BASE_URL}/editMessageText", json=payload)

    elif data == "pay_vip_pkg":
        log_user_history(
            from_user_id, "NAVIGATE", "VIP Payment Gateway"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "🪙 Binance Pay / USDT", 
                  "callback_data": "vip_addr_wait"}],
                [{"text": "💳 Skrill / Neteller / PM", 
                  "callback_data": "vip_addr_wait"}],
                [{"text": "₿ Bitcoin / Crypto", 
                  "callback_data": "vip_addr_wait"}]
            ]
        }
        payload = {
            "chat_id": chat_id, "message_id": message_id,
            "text": "💳 **Select Your Payment Method:**",
            "reply_markup": kb
        }
        requests.post(f"{BASE_URL}/editMessageText", json=payload)

    elif data == "vip_addr_wait":
        log_user_history(
            from_user_id, "ACTION", "Completed VIP Flow"
        )
        payload = {
            "chat_id": chat_id, "message_id": message_id,
            "text": "⏳ **Please wait, our team will share "
            "the deposit address s
