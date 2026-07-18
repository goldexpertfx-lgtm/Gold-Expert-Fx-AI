import requests, sqlite3, time, threading, re, sys

# =====================================================================
# ⚙️ CONFIGURATION 
# =====================================================================
API_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"  # ⚠️ Apna Real Token yahan dalein
OWNER_ID = 7415265825  # 👑 Prince Bhai Admin ID

FREE_GROUP_ID = -4477244119  
PRIVATE_CHANNEL_ID = -3870933647  
DB_NAME = "gold_expert_premium.db"
# =====================================================================

if not API_TOKEN:
    print("❌ ERROR: API_TOKEN khali hai!"); sys.exit(1)

BASE_URL = f"https://api.telegram.org/bot{API_TOKEN}"

def init_db():
    conn = sqlite3.connect(DB_NAME, timeout=20); c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS member_activity (user_id INTEGER PRIMARY KEY, leave_timestamp REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS pending_channel_requests (user_id INTEGER, chat_id INTEGER, request_time REAL, PRIMARY KEY (user_id, chat_id))")
    c.execute("CREATE TABLE IF NOT EXISTS users_profile (user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT, join_date REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS user_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action_type TEXT, details TEXT, timestamp REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS admin_state (admin_id INTEGER PRIMARY KEY, target_user_id INTEGER, chat_session_active INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS dynamic_content (service_key TEXT PRIMARY KEY, text_content TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS admin_edit_state (admin_id INTEGER PRIMARY KEY, editing_service TEXT)")
    conn.commit(); conn.close()

init_db()

def get_content(key, default):
    try:
        conn = sqlite3.connect(DB_NAME, timeout=20); c = conn.cursor()
        c.execute("SELECT text_content FROM dynamic_content WHERE service_key = ?", (key,))
        row = c.fetchone(); conn.close()
        if row and row[0]: return row[0]
    except Exception: pass
    return default

def set_content(key, text):
    try:
        conn = sqlite3.connect(DB_NAME, timeout=20); c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO dynamic_content VALUES (?, ?)", (key, text))
        conn.commit(); conn.close()
        return True
    except Exception: return False

def log_user_history(uid, atype, details):
    try:
        conn = sqlite3.connect(DB_NAME, timeout=20); c = conn.cursor()
        c.execute("INSERT INTO user_history (user_id, action_type, details, timestamp) VALUES (?, ?, ?, ?)", (uid, atype, details, time.time()))
        conn.commit(); conn.close()
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
                conn = sqlite3.connect(DB_NAME, timeout=20); c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO member_activity VALUES (?, ?)", (left_id, time.time()))
                conn.commit(); conn.close()
            except Exception: pass
        return

    # Delete Links and Spam Controls
    if text and chat_id == FREE_GROUP_ID and from_user_id != OWNER_ID:
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+|[a-zA-r0-9\-\.]+\.(com|net|org))'
        if re.search(url_pattern, text, re.IGNORECASE) and msg.get("forward_from_chat", {}).get("id") != PRIVATE_CHANNEL_ID:
            requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
            log_user_history(from_user_id, "WARNING", f"Tried to share unauthorized link: {text}")
            return

    if chat_type == "private":
        try:
            conn = sqlite3.connect(DB_NAME, timeout=20); c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users_profile VALUES (?, ?, ?, ?)", (from_user_id, from_user.get("first_name"), from_user.get("username"), time.time()))
            conn.commit(); conn.close()
        except Exception: pass

        if text and text.startswith("/start"):
            log_user_history(from_user_id, "COMMAND", "/start triggered")
            welcome = f"👋 **Hello, {from_user.get('first_name', 'Trader')}!**\n\nWelcome to **Gold Expert FX Automation Hub**. Select a service below:"
            if from_user_id == OWNER_ID:
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": "👑 Welcome Prince Bhai. Custom System Active.", "reply_markup": get_owner_menu()})
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": welcome, "parse_mode": "Markdown", "reply_markup": get_main_keyboard()})
            return

        if from_user_id == OWNER_ID:
            if text == "👥 View Total Users":
                conn = sqlite3.connect(DB_NAME, timeout=20); c = conn.cursor()
                c.execute("SELECT user_id, first_name, username FROM users_profile ORDER BY join_date DESC")
                rows = c.fetchall(); conn.close()
                if not rows:
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "📭 No registered users yet."})
                    return
                kb = {"inline_keyboard": []}
                for u_id, fn, un in rows:
                    disp = f"{fn} (@{un})" if un else f"{fn}"
                    kb["inline_keyboard"].append([{"text": f"👤 {disp}", "callback_data": f"adm_view_{u_id}"}])
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"📊 **Total Active Users:** `{len(rows)}` \n\nClick a user to open their professional control panel dashboard:", "parse_mode": "Markdown", "reply_markup": kb})
                return

            elif text == "✏️ Live Edit Messages":
                kb = {"inline_keyboard": [
                    [{"text": "📝 Edit Account Management Main Text", "callback_data": "edt_account"}],
                    [{"text": "📝 Edit Account Management Format/Form", "callback_data": "edt_form_account"}],
                    [{"text": "📝 Edit VIP Premium Main Text", "callback_data": "edt_vip"}],
                    [{"text": "📝 Edit VIP Premium Package Formats/Timings", "callback_data": "edt_form_vip"}],
                    [{"text": "📝 Edit Copy Trading Main Text", "callback_data": "edt_copy"}],
                    [{"text": "❌ Cancel", "callback_data": "edt_cancel"}]
                ]}
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "🛠️ **Prince Bhai, select target string to overwrite:**", "reply_markup": kb})
                return

            # Check Admin Interactive Live Chat State
            conn = sqlite3.connect(DB_NAME, timeout=20); c = conn.cursor()
            c.execute("SELECT editing_service FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
            e_row = c.fetchone()
            c.execute("SELECT target_user_id, chat_session_active FROM admin_state WHERE admin_id = ?", (OWNER_ID,))
            t_row = c.fetchone(); conn.close()

            if e_row and e_row[0]:
                if set_content(e_row[0], text):
                    conn = sqlite3.connect(DB_NAME, timeout=20); c = conn.cursor()
                    c.execute("DELETE FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
                    conn.commit(); conn.close()
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "✅ **Live Update Complete!** Content saved into DB safely.", "parse_mode": "Markdown"})
                return

            elif t_row and t_row[1] == 1 and not text.startswith("/"):
                t_uid = t_row[0]
                payload = {"chat_id": t_uid, "text": f"💬 **Message from Prince Bhai (Admin):**\n\n{text}", "parse_mode": "Markdown"}
                res = requests.post(f"{BASE_URL}/sendMessage", json=payload).json()
                kb = {"inline_keyboard": [[{"text": "❌ Close Chat Session", "callback_data": "adm_close_chat"}]]}
                if res.get("ok"):
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"🚀 **Sent to User:** {text}", "reply_markup": kb})
                else:
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "❌ Sending failed. User might have blocked the bot."})
                return

        if from_user_id != OWNER_ID:
            log_user_history(from_user_id, "USER_MESSAGE", text)
            
            # Check if live chat is active from Admin Side for this specific user
            conn = sqlite3.connect(DB_NAME, timeout=20); c = conn.cursor()
            c.execute("SELECT admin_id FROM admin_state WHERE target_user_id = ? AND chat_session_active = 1", (from_user_id,))
            live_admin = c.fetchone(); conn.close()
            
            if live_admin:
                admin_msg = f"💬 **Live Client Reply [@{from_user.get('username','None')}]:**\n\n{text}"
                kb = {"inline_keyboard": [[{"text": "❌ Close Chat Session", "callback_data": "adm_close_chat"}]]}
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": admin_msg, "reply_markup": kb})
                return

            if any(x in text for x in ["Broker", "ID", "Password", "Login"]):
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": "⏳ **Form Format Received Perfectly!**\nOur team is validating parameters and will contact you directly.", "parse_mode": "Markdown"})
            
            kb = {"inline_keyboard": [[{"text": "🛠️ Open User Dashboard", "callback_data": f"adm_view_{from_user_id}"}]]}
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"📥 **Incoming Help Desk Message!**\n👤 {from_user.get('first_name')} [`{from_user_id}`]\n💬 {text}", "parse_mode": "Markdown", "reply_markup": kb})

def handle_callback_query(callback):
    c_id = callback["id"]; from_user_id = callback["from"]["id"]; chat_id = callback["message"]["chat"]["id"]
    message_id = callback["message"]["message_id"]; data = callback["data"]
    requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": c_id})

    # Massive Restored Defaults
    def_account = "💼 **Account Management Service**\n\n1. Profit/Loss shared 50/50.\n2. Funds remain secure in your broker terminal.\n3. Send credentials to register.\n\nMinimum Equity: $500"
    def_form_account = "Format Required:\n1) Broker Name -\n2) Server Name -\n3) MT4/MT5 Terminal -\n4) Deposit Equity -\n5) Account Login ID -\n6) Password -\n\n📝 Fill details and send text here."
    def_vip = "👑 **VIP Premium Channel**\n\n- 5-7 High Accuracy Gold Setups Daily\n- Lifetime Access: $700\n- 1 Year Package: $500\n- 1 Month Package: $300"
    def_form_vip = "🎯 **VIP Packages Timings & Processing Form**\n\nTo subscribe, choose payment framework setup below. Processing time takes less than 15 minutes."
    def_copy = "📋 **Copy Trading System**\n\n- Minimum Capital Required: $200\n- License Fee: $1,000 One-Time Lifetime Payment\n- Zero ongoing performance commissions."

    if data == "main_menu_home":
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": "👋 Welcome back! Select target automation platform parameters:", "reply_markup": get_main_keyboard()})
        return

    if data.startswith("edt_") and from_user_id == OWNER_ID:
        action = data.split("_")[1]
        conn = sqlite3.connect(DB_NAME, timeout=20); c = conn.cursor()
        if action == "cancel":
            c.execute("DELETE FROM admin_edit_state WHERE admin_id = ?")
            txt = "❌ Content edit workflow aborted."
        else:
            full_key = data.replace("edt_", "")
            c.execute("INSERT OR REPLACE INTO admin_edit_state VALUES (?, ?)", (OWNER_ID, full_key))
            txt = f"📥 Send new raw layout design layout string text to overwrite key token `{full_key}`:"
        conn.commit(); conn.close()
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": txt})
        return

    # User Dashboard Control Panel Router
    if data.startswith("adm_view_") and from_user_id == OWNER_ID:
        t_uid = int(data.split("_")[2])
        conn = sqlite3.connect(DB_NAME, timeout=20); c = conn.cursor()
        c.execute("SELECT first_name, username FROM users_profile WHERE user_id = ?", (t_uid,))
        prof = c.fetchone()
        c.execute("SELECT action_type, details, timestamp FROM user_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5", (t_uid,))
        logs = c.fetchall()
        c.execute("INSERT OR REPLACE INTO admin_state (admin_id, target_user_id, chat_session_active) VALUES (?, ?, 0)", (OWNER_ID, t_uid))
        conn.commit(); conn.close()
        
        if not prof: return
        history = f"🖥️ **USER MONITOR INTERACTIVE DASHBOARD**\n\n👤 **Name:** {prof[0]}\n🆔 **User ID:** `{t_uid}`\n🌐 **Username:** @{prof[1] if prof[1] else 'None'}\n\n📝 **Recent Footprints Logs:**\n"
        for atype, det, ts in logs:
            history += f"▪️ `[{time.strftime('%H:%M', time.localtime(ts))}]` **{atype}**: {det}\n"
        
        kb = {"inline_keyboard": [
            [{"text": "💬 Start Live Chat Session", "callback_data": f"adm_start_chat_{t_uid}"}],
            [{"text": "👥 Back to Active Users List", "callback_data": "adm_refresh_users"}]
        ]}
        requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": history, "parse_mode": "Markdown", "reply_markup": kb})
        return

    if data.startswith("adm_start_chat_") and from_user_id == OWNER_ID:
        t_uid = int(data.split("_")[3])
        conn = sqlite3.connect(DB_NAME, timeout=20); c = conn.cursor()
        c.execute("UPDATE admin_state SET chat_session_active = 1 WHERE admin_id = ?", (OWNER_ID,))
        conn.commit(); conn.close()
        kb = {"inline_keyboard": [[{"text": "❌ Close Chat Session", "callback_data": "adm_close_chat"}]]}
        requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"🟢 **Live Chat Active!**\nEvery message you send now mirrors to client `{t_uid}` screen instantly.", "reply_markup": kb})
        return

    if data == "adm_close_chat" and from_user_id == OWNER_ID:
        conn = sqlite3.connect(DB_NAME, timeout=20); c = conn.cursor()
        c.execute("UPDATE admin_state SET chat_session_active = 0 WHERE admin_id = ?", (OWNER_ID,))
        conn.commit(); conn.close()
        requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "🔴 **Chat Session Closed.** System back to monitoring terminal defaults."})
        return

    if data == "adm_refresh_users" and from_user_id == OWNER_ID:
        requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
        # Trigger re-evaluation list directly
        conn = sqlite3.connect(DB_NAME, timeout=20); c = conn.cursor()
        c.execute("SELECT user_id, first_name, username FROM users_profile ORDER BY join_date DESC")
        rows = c.fetchall(); conn.close()
        kb = {"inline_keyboard": []}
        for u_id, fn, un in rows:
            kb["inline_keyboard"].append([{"text": f"👤 {fn}", "callback_data": f"adm_view_{u_id}"}])
        requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "📊 **Total Active Users Panel:**", "reply_markup": kb})
        return

    # Client Facing Navigation Engine with Back Keyboards
    if data == "srv_account":
        log_user_history(from_user_id, "NAVIGATE", "Viewed Account Management")
        kb = {"inline_keyboard": [
            [{"text": "🚀 Apply / Join Request", "callback_data": "join_account"}],
            [{"text": "⬅️ Back to Main Menu", "callback_data": "main_menu_home"}]
        ]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": get_content("account", def_account), "parse_mode": "Markdown", "reply_markup": kb})

    elif data == "join_account":
        kb = {"inline_keyboard": [[{"text": "⬅️ Back", "callback_data": "srv_account"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": get_content("form_account", def_form_account), "reply_markup": kb})

    elif data == "srv_vip":
        log_user_history(from_user_id, "NAVIGATE", "Viewed VIP Packages")
        kb = {"inline_keyboard": [
            [{"text": "💎 Join VIP Premium Request", "callback_data": "join_vip_packages"}],
            [{"text": "⬅️ Back to Main Menu", "callback_data": "main_menu_home"}]
        ]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": get_content("vip", def_vip), "parse_mode": "Markdown", "reply_markup": kb})

    elif data == "join_vip_packages":
        kb = {"inline_keyboard": [
            [{"text": "💳 Lifetime Framework Access", "callback_data": "pay_wait"}],
            [{"text": "📅 1 Year Standard Account", "callback_data": "pay_wait"}],
            [{"text": "⬅️ Back", "callback_data": "srv_vip"}]
        ]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": get_content("form_vip", def_form_vip), "reply_markup": kb})

    elif data == "srv_copy":
        log_user_history(from_user_id, "NAVIGATE", "Viewed Copy Trading")
        kb = {"inline_keyboard": [
            [{"text": "📋 Connect Copy Trading Service Setup", "callback_data": "pay_wait"}],
            [{"text": "⬅️ Back to Main Menu", "callback_data": "main_menu_home"}]
        ]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": get_content("copy", def_copy), "parse_mode": "Markdown", "reply_markup": kb})

    elif data == "pay_wait":
        kb = {"inline_keyboard": [[{"text": "⬅️ Back to Main Menu", "callback_data": "main_menu_home"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": message_id, "text": "⏳ **Please wait...** Team is compiling transaction details parameters. Form layout structure will be pushed here.", "reply_markup": kb})

def check_and_approve():
    try:
        conn = sqlite3.connect(DB_NAME, timeout=20); c = conn.cursor()
        c.execute("SELECT user_id, chat_id FROM pending_channel_requests")
        reqs = c.fetchall(); conn.close()
        for uid, cid in reqs:
            if requests.post(f"{BASE_URL}/approveChatJoinRequest", json={"chat_id": cid, "user_id": uid}).json().get("ok"):
                log_user_history(uid, "APPROVAL", "Channel Request Approved Automatically")
                conn = sqlite3.connect(DB_NAME, timeout=20); c = conn.cursor()
                c.execute("DELETE FROM pending_channel_requests WHERE user_id = ? AND chat_id = ?", (uid, cid))
                conn.commit(); conn.close()
    except Exception: pass

def auto_reque
