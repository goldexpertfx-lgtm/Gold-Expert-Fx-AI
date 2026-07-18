import requests, sqlite3, time, threading, re, sys

# =====================================================================
# ⚙️ CONFIGURATION 
# =====================================================================
API_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"  # ⚠️ Real Token yahan dalein
OWNER_ID = 7415265825  # 👑 Prince Bhai Admin ID

FREE_GROUP_ID = -4477244119  
PRIVATE_CHANNEL_ID = -3870933647  
DB_NAME = "gold_expert_premium.db"
# =====================================================================

if not API_TOKEN:
    print("❌ ERROR: API_TOKEN khali hai!")
    sys.exit(1)

BASE_URL = f"https://api.telegram.org/bot{API_TOKEN}"

def init_db():
    conn = sqlite3.connect(DB_NAME, timeout=20)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS member_activity (user_id INTEGER PRIMARY KEY, leave_timestamp REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS pending_channel_requests (user_id INTEGER, chat_id INTEGER, request_time REAL, PRIMARY KEY (user_id, chat_id))")
    c.execute("CREATE TABLE IF NOT EXISTS users_profile (user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT, join_date REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS user_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action_type TEXT, details TEXT, timestamp REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS admin_state (admin_id INTEGER PRIMARY KEY, target_user_id INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS dynamic_content (service_key TEXT PRIMARY KEY, text_content TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS admin_edit_state (admin_id INTEGER PRIMARY KEY, editing_service TEXT)")
    conn.commit()
    conn.close()

init_db()

def get_content(key, default):
    try:
        conn = sqlite3.connect(DB_NAME, timeout=20)
        c = conn.cursor()
        c.execute("SELECT text_content FROM dynamic_content WHERE service_key = ?", (key,))
        row = c.fetchone()
        conn.close()
        if row and row[0]: return row[0]
    except Exception: pass
    return default

def set_content(key, text):
    try:
        conn = sqlite3.connect(DB_NAME, timeout=20)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO dynamic_content VALUES (?, ?)", (key, text))
        conn.commit()
        conn.close()
        return True
    except Exception: return False

def log_user_history(uid, atype, details):
    try:
        conn = sqlite3.connect(DB_NAME, timeout=20)
        c = conn.cursor()
        c.execute("INSERT INTO user_history (user_id, action_type, details, timestamp) VALUES (?, ?, ?, ?)", (uid, atype, details, time.time()))
        conn.commit()
        conn.close()
    except Exception: pass

def get_main_keyboard():
    return {"inline_keyboard": [
        [{"text": "💼 Account Management Services", "callback_data": "srv_account"}],
        [{"text": "👑 VIP Premium Private Channel", "callback_data": "srv_vip"}],
        [{"text": "📋 Copy Trading Service", "callback_data": "srv_copy"}]
    ]}

def get_owner_menu():
    return {"keyboard": [[{"text": "👥 View Total Users"}, {"text": "✏️ Live Edit Messages"}]], "resize_keyboard": True}

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
                conn = sqlite3.connect(DB_NAME, timeout=20)
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO member_activity VALUES (?, ?)", (left_id, time.time()))
                conn.commit()
                conn.close()
            except Exception: pass
        return

    if text and chat_id == FREE_GROUP_ID and from_user_id != OWNER_ID:
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+|[a-zA-r0-9\-\.]+\.(com|net|org))'
        if re.search(url_pattern, text, re.IGNORECASE) and msg.get("forward_from_chat", {}).get("id") != PRIVATE_CHANNEL_ID:
            requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
            return

    if chat_type == "private":
        try:
            conn = sqlite3.connect(DB_NAME, timeout=20)
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users_profile VALUES (?, ?, ?, ?)", (from_user_id, from_user.get("first_name"), from_user.get("username"), time.time()))
            conn.commit()
            conn.close()
        except Exception: pass

        if text and text.startswith("/start"):
            log_user_history(from_user_id, "COMMAND", "/start triggered")
            welcome = f"👋 **Hello, {from_user.get('first_name', 'Trader')}!**\n\nWelcome to **Gold Expert FX Automation Hub**. Select a service below:"
            if from_user_id == OWNER_ID:
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": "👑 Welcome Prince Bhai. Dashboard Active.", "reply_markup": get_owner_menu()})
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": welcome, "parse_mode": "Markdown", "reply_markup": get_main_keyboard()})
            return

        if from_user_id == OWNER_ID:
            if text == "👥 View Total Users":
                conn = sqlite3.connect(DB_NAME, timeout=20)
                c = conn.cursor()
                c.execute("SELECT user_id, first_name, username FROM users_profile ORDER BY join_date DESC")
                rows = c.fetchall()
                conn.close()
                if not rows:
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "📭 No registered users yet."})
                    return
                kb = {"inline_keyboard": []}
                for u_id, fn, un in rows:
                    disp = f"{fn} (@{un})" if un else f"{fn}"
                    kb["inline_keyboard"].append([{"text": f"👤 {disp}", "callback_data": f"adm_view_{u_id}"}])
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"📊 **Total Active Users:** `{len(rows)}`", "parse_mode": "Markdown", "reply_markup": kb})
                return

            elif text == "✏️ Live Edit Messages":
                kb = {"inline_keyboard": [
                    [{"text": "📝 Edit Account Management", "callback_data": "edt_account"}],
                    [{"text": "📝 Edit VIP Premium", "callback_data": "edt_vip"}],
                    [{"text": "📝 Edit Copy Trading", "callback_data": "edt_copy"}],
                    [{"text": "❌ Cancel", "callback_data": "edt_cancel"}]
                ]}
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "🛠️ Select content to modify:", "reply_markup": kb})
                return

            conn = sqlite3.connect(DB_NAME, timeout=20)
            c = conn.cursor()
            c.execute("SELECT editing_service FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
            e_row = c.fetchone()
            c.execute("SELECT target_user_id FROM admin_state WHERE admin_id = ?", (OWNER_ID,))
            t_row = c.fetchone()
            conn.close()

            if e_row and e_row[0]:
                if set_content(e_row[0], text):
                    conn = sqlite3.connect(DB_NAME, timeout=20)
                    c = conn.cursor()
                    c.execute("DELETE FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
                    conn.commit()
                    conn.close()
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "✅ **Live Updated Successfully!**", "parse_mode": "Markdown"})
                return
            elif t_row and not text.startswith("/"):
                res = requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": t_row[0], "text": f"💬 **Message from Admin:**\n\n{text}", "parse_mode": "Markdown"}).json()
                msg_txt = "🚀 Reply sent cleanly." if res.get("ok") else "❌ Delivery failed. User blocked the bot."
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": msg_txt})
                return

        if from_user_id != OWNER_ID:
            log_user_history(from_user_id, "USER_MESSAGE", text)
            if any(x in text for x in ["Broker name", "Login ID", "Password"]):
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": "⏳ **Format Received!** Our team is reviewing details.", "parse_mode": "Markdown"})
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"📥 **New Message!**\n👤 {from_user.get('first_name')} [`{from_user_id}`]\n💬 {text}", "parse_mode": "Markdown"})

def handle_callback_query(callback):
    c_id = callback["id"]
    from_user_id = callback["from"]["id"]
    chat_id = callback["message"]["chat"]["id"]
    message_id = callback["message"]["message_id"]
    data = callback["data"]
    
    requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": c_id})

    def_account = "💼 **Account Management Service**\n\n1. Profit/Loss shared 50/50.\n2. Funds remain in your account.\n3. Send credentials to join.\n\nMinimum Deposit: $500"
    def_vip = "👑 **VIP Premium Channel**\n\n- 5-7 High Accuracy Signals Daily\n- Lifetime: $700\n- 1 Year: $500\n- 1 Month: $300"
    def_copy = "📋 **Copy Trading Rules**\n\n- Minimum Deposit: $200\n- Fee: $1,000 One-Time Payment\n- No profit sharing or monthly fees."

    if data.startswith("edt_") and from_user_id == OWNER_ID:
        action = data.split("_")[1]
        conn = sqlite3.connect(DB_NAME, timeout=20)
        c = conn.cursor()
        if action == "cancel":
            c.execute("DELETE FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
            txt = "❌ Cancelled safely."
        else:
            c.execute("INSERT OR REPLACE INTO admin_edit_state VALUES (?, ?)", (OWNER_ID, action))
            txt = f"📥 Send new message text to overwrite `{action}`:"
        conn.commit()
        conn.close()
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": txt})
        return

    if data.startswith("adm_view_") and from_user_id == OWNER_ID:
        t_uid = int(data.split("_")[2])
        conn = sqlite3.connect(DB_NAME, timeout=20)
        c = conn.cursor()
        c.execute("SELECT first_name, username FROM users_profile WHERE user_id = ?", (t_uid,))
        prof = c.fetchone()
        c.execute("SELECT action_type, details, timestamp FROM user_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10", (t_uid,))
        logs = c.fetchall()
        c.execute("INSERT OR REPLACE INTO admin_state VALUES (?, ?)", (OWNER_ID, t_uid))
        conn.commit()
        conn.close()
        
        if not prof: return
        history = f"👤 **Name:** {prof[0]} (`{t_uid}`)\n🌐 **User:** @{prof[1] if prof[1] else 'None'}\n\n📝 **Logs:**\n"
        for atype, det, ts in logs:
            history += f"▪️ `[{time.strftime('%H:%M', time.localtime(ts))}]` **{atype}**: {det}\n"
        history += "\n💬 Type your reply message to send directly to user."
        requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": history, "parse_mode": "Markdown"})
        return

    if data == "srv_account":
        log_user_history(from_user_id, "NAVIGATE", "Viewed Account Management")
        kb = {"inline_keyboard": [[{"text": "🚀 Join Now", "callback_data": "join_account"}]]}
        if from_user_id == OWNER_ID: kb["inline_keyboard"].append([{"text": "⚡ Edit Content", "callback_data": "edt_account"}])
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": get_content("account", def_account), "parse_mode": "Markdown", "reply_markup": kb})

    elif data == "join_account":
        fmt = "Format:\n1) Broker -\n2) Server -\n3) MT4/MT5 -\n4) Deposit -\n5) Login ID -\n6) Password -\n\n📝 Fill and send here."
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": fmt})

    elif data == "srv_vip":
        log_user_history(from_user_id, "NAVIGATE", "Viewed VIP Packages")
        kb = {"inline_keyboard": [[{"text": "💎 Join VIP", "callback_data": "join_vip_packages"}]]}
        if from_user_id == OWNER_ID: kb["inline_keyboard"].append([{"text": "⚡ Edit Content", "callback_data": "edt_vip"}])
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": get_content("vip", def_vip), "parse_mode": "Markdown", "reply_markup": kb})

    elif data == "join_vip_packages":
        kb = {"inline_keyboard": [[{"text": "💎 Lifetime - $700", "callback_data": "pay_wait"}], [{"text": "📅 1 Year - $500", "callback_data": "pay_wait"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": "🎯 Select Package Tier:", "reply_markup": kb})

    elif data == "srv_copy":
        log_user_history(from_user_id, "NAVIGATE", "Viewed Copy Trading")
        kb = {"inline_keyboard": [[{"text": "📋 Connect Copy Trading", "callback_data": "pay_wait"}]]}
        if from_user_id == OWNER_ID: kb["inline_keyboard"].append([{"text": "⚡ Edit Content", "callback_data": "edt_copy"}])
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": get_content("copy", def_copy), "parse_mode": "Markdown", "reply_markup": kb})

    elif data == "pay_wait":
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": "⏳ **Please wait...** Team will send transaction details shortly."})

def check_and_approve():
    try:
        conn = sqlite3.connect(DB_NAME, timeout=20)
        c = conn.cursor()
        c.execute("SELECT user_id, chat_id FROM pending_channel_requests")
        reqs = c.fetchall()
        conn.close()
        for uid, cid in reqs:
            if requests.post(f"{BASE_URL}/approveChatJoinRequest", json={"chat_id": cid, "user_id": uid}).json().get("ok"):
                log_user_history(uid, "APPROVAL", "Approved Automatically")
                conn = sqlite3.connect(DB_NAME, timeout=20)
                c = conn.cursor()
                c.execute("DELETE FROM pending_channel_requests WHERE user_id = ? AND chat_id = ?", (uid, cid))
                conn.commit()
                conn.close()
    except Exception: pass

def auto_request_approver():
    while True:
        check_and_approve()
        time.sleep(4)

def main():
    threading.Thread(target=auto_request_approver, daemon=True).start()
    print("🚀 CRM Engine Activated...")
    offset = 0
    while True:
        try:
            res = requests.post(f"{BASE_URL}/getUpdates", json={"offset": offset, "timeout": 10, "allowed_updates": ["message", "callback_query", "chat_join_request"]}, timeout=15).json()
            if res.get("ok"):
                for upd in res["result"]:
                    offset = upd["update_id"] + 1
                    if "chat_join_request" in upd:
                        r = upd["chat_join_request"]
                        conn = sqlite3.connect(DB_NAME, timeout=20)
                        c = conn.cursor()
                        c.execute("INSERT OR IGNORE INTO pending_channel_requests VALUES (?, ?, ?)", (r["from"]["id"], r["chat"]["id"], time.time()))
                        conn.commit()
                        conn.close()
                    elif "message" in upd: handle_incoming_message(upd["message"])
                    elif "callback_query" in upd: handle_callback_query(upd["callback_query"])
            elif res.get("error_code") == 409: time.sleep(10)
        except Exception: time.sleep(4)

if __name__ == "__main__":
    main()
        
