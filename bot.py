import requests, sqlite3, time, threading, re, sys

API_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"  # ⚠️ Apna Real Token yahan dalein
OWNER_ID = 7415265825  # 👑 Admin ID

FREE_GROUP_ID = -4477244119  
PRIVATE_CHANNEL_ID = -3870933647  
DB_NAME = "gold_expert_premium.db"

if not API_TOKEN: sys.exit(1)
BASE_URL = f"https://api.telegram.org/bot{API_TOKEN}"

def db_run(query, params=(), fetch=False, multi=False):
    try:
        with sqlite3.connect(DB_NAME, timeout=20) as conn:
            c = conn.cursor(); c.execute(query, params)
            if fetch: return c.fetchall() if multi else c.fetchone()
            conn.commit()
    except Exception: return None

def init_db():
    db_run("CREATE TABLE IF NOT EXISTS member_activity (user_id INTEGER PRIMARY KEY, leave_timestamp REAL)")
    db_run("CREATE TABLE IF NOT EXISTS pending_channel_requests (user_id INTEGER, chat_id INTEGER, request_time REAL, PRIMARY KEY (user_id, chat_id))")
    db_run("CREATE TABLE IF NOT EXISTS users_profile (user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT, join_date REAL)")
    db_run("CREATE TABLE IF NOT EXISTS user_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action_type TEXT, details TEXT, timestamp REAL)")
    db_run("CREATE TABLE IF NOT EXISTS admin_state (admin_id INTEGER PRIMARY KEY, target_user_id INTEGER, chat_session_active INTEGER DEFAULT 0)")
    db_run("CREATE TABLE IF NOT EXISTS dynamic_content (service_key TEXT PRIMARY KEY, text_content TEXT)")
    db_run("CREATE TABLE IF NOT EXISTS admin_edit_state (admin_id INTEGER PRIMARY KEY, editing_service TEXT)")

init_db()

def get_content(k, d):
    r = db_run("SELECT text_content FROM dynamic_content WHERE service_key = ?", (k,), fetch=True)
    return r[0] if r and r[0] else d

def log_hist(uid, t, d): 
    db_run("INSERT INTO user_history (user_id, action_type, details, timestamp) VALUES (?, ?, ?, ?)", (uid, t, d, time.time()))

def get_main_keyboard():
    return {"inline_keyboard": [
        [{"text": "💼 Account Management Services", "callback_data": "srv_account"}],
        [{"text": "👑 VIP Premium Private Channel", "callback_data": "srv_vip"}],
        [{"text": "📋 Copy Trading Service", "callback_data": "srv_copy"}]
    ]}

def handle_incoming_message(msg):
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")
    text = msg.get("text", "")
    f_user = msg.get("from", {})
    uid = f_user.get("id")
    
    if not uid: return

    if "new_chat_members" in msg or "left_chat_member" in msg:
        requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
        if chat_id == FREE_GROUP_ID and "left_chat_member" in msg:
            l_id = msg["left_chat_member"]["id"]
            log_hist(l_id, "STATUS", "Left Free Community Group")
            db_run("INSERT OR REPLACE INTO member_activity VALUES (?, ?)", (l_id, time.time()))
        return

    if text and chat_id == FREE_GROUP_ID and uid != OWNER_ID:
        if re.search(r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+|[a-zA-r0-9\-\.]+\.(com|net|org))', text, re.I) and msg.get("forward_from_chat", {}).get("id") != PRIVATE_CHANNEL_ID:
            requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
            log_hist(uid, "WARNING", f"Link filter triggered: {text}")
            return

    if msg.get("chat", {}).get("type") == "private":
        db_run("INSERT OR IGNORE INTO users_profile VALUES (?, ?, ?, ?)", (uid, f_user.get("first_name"), f_user.get("username"), time.time()))

        if text and text.startswith("/start"):
            log_hist(uid, "COMMAND", "/start triggered")
            if uid == OWNER_ID:
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": "👑 Welcome Prince Bhai. Custom System Active.", "reply_markup": {"keyboard": [[{"text": "👥 View Total Users"}, {"text": "✏️ Live Edit Messages"}]], "resize_keyboard": True}})
            w_msg = f"👋 **Hello, {f_user.get('first_name', 'Trader')}!**\n\nWelcome to **Gold Expert FX Automation Hub**. Select a service below:"
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": w_msg, "parse_mode": "Markdown", "reply_markup": get_main_keyboard()})
            return

        if uid == OWNER_ID:
            if text == "👥 View Total Users":
                rows = db_run("SELECT user_id, first_name, username FROM users_profile ORDER BY join_date DESC", fetch=True, multi=True)
                if not rows: return requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "📭 No registered users."})
                kb = {"inline_keyboard": [[{"text": f"👤 {r[1]} (@{r[2]})" if r[2] else f"👤 {r[1]}", "callback_data": f"adm_v_{r[0]}"}] for r in rows]}
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"📊 **Total Active Users:** `{len(rows)}` \n\nClick a user to open CRM Panel:", "parse_mode": "Markdown", "reply_markup": kb})
                return

            elif text == "✏️ Live Edit Messages":
                kb = {"inline_keyboard": [
                    [{"text": "📝 Edit Account Management Text", "callback_data": "edt_account"}],
                    [{"text": "📝 Edit Account Form", "callback_data": "edt_form_account"}],
                    [{"text": "📝 Edit VIP Main Text", "callback_data": "edt_vip"}],
                    [{"text": "📝 Edit VIP Timing Form", "callback_data": "edt_form_vip"}],
                    [{"text": "📝 Edit Copy Trading Text", "callback_data": "edt_copy"}],
                    [{"text": "❌ Cancel", "callback_data": "edt_cancel"}]
                ]}
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "🛠️ **Select section to update:**", "reply_markup": kb})
                return

            e_row = db_run("SELECT editing_service FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,), fetch=True)
            t_row = db_run("SELECT target_user_id, chat_session_active FROM admin_state WHERE admin_id = ?", (OWNER_ID,), fetch=True)

            if e_row and e_row[0]:
                if db_run("INSERT OR REPLACE INTO dynamic_content VALUES (?, ?)", (e_row[0].replace("edt_", ""), text)) or True:
                    db_run("DELETE FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "✅ **Live Update Saved into DB!**", "parse_mode": "Markdown"})
                return
            elif t_row and t_row[1] == 1 and not text.startswith("/"):
                res = requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": t_row[0], "text": f"💬 **Message from Prince Bhai (Admin):**\n\n{text}", "parse_mode": "Markdown"}).json()
                kb = {"inline_keyboard": [[{"text": "❌ Close Chat Session", "callback_data": "adm_c_chat"}]]}
                msg_s = f"🚀 **Sent to User:** {text}" if res.get("ok") else "❌ Sending failed. Blocked by user."
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": msg_s, "reply_markup": kb})
                return

        log_hist(uid, "USER_MSG", text)
        live_adm = db_run("SELECT admin_id FROM admin_state WHERE target_user_id = ? AND chat_session_active = 1", (uid,), fetch=True)
        if live_adm:
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"💬 **Live Client Reply [@{f_user.get('username','None')}]:**\n\n{text}", "reply_markup": {"inline_keyboard": [[{"text": "❌ Close Chat Session", "callback_data": "adm_c_chat"}]]}})
            return

        if any(x in text for x in ["Broker", "ID", "Password", "Login"]):
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": "⏳ **Form Format Received Perfectly!** Team is validating specifications.", "parse_mode": "Markdown"})
        
        requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"📥 **Incoming Support Desk Message!**\n👤 {f_user.get('first_name')} [`{uid}`]\n💬 {text}", "parse_mode": "Markdown", "reply_markup": {"inline_keyboard": [[{"text": "🛠️ Open Dashboard", "callback_data": f"adm_v_{uid}"}]]}})

def handle_callback_query(cb):
    c_id = cb["id"]; uid = cb["from"]["id"]; chat_id = cb["message"]["chat"]["id"]
    msg_id = cb["message"]["message_id"]; data = cb["data"]
    requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": c_id})

    d_acc = "💼 **Account Management Service**\n\n1. Profit/Loss shared 50/50.\n2. Funds remain in your terminal.\n\nMinimum Equity: $500"
    d_f_acc = "Format Required:\n1) Broker Name -\n2) Server Name -\n3) MT4/MT5 Terminal -\n4) Deposit Equity -\n5) Account ID -\n6) Password -\n\n📝 Fill details & send here."
    d_vip = "👑 **VIP Premium Channel**\n\n- 5-7 Signals Daily\n- Lifetime: $700 | 1 Year: $500"
    d_f_vip = "🎯 **VIP Form**\n\nChoose payment framework setup below. Setup takes ~15 minutes."
    d_cpy = "📋 **Copy Trading System**\n\n- Min Capital: $200\n- License Fee: $1,000 One-Time\n- 0% ongoing performance commissions."

    if data == "m_menu":
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": "👋 Select system parameters:", "reply_markup": get_main_keyboard()})
        return

    if data.startswith("edt_") and uid == OWNER_ID:
        action = data.split("_")[1]
        if action == "cancel":
            db_run("DELETE FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
            txt = "❌ Workspace workflow aborted."
        else:
            db_run("INSERT OR REPLACE INTO admin_edit_state VALUES (?, ?)", (OWNER_ID, data))
            txt = f"📥 Send new layout design text for `{data}`:"
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": txt})
        return

    if data.startswith("adm_v_") and uid == OWNER_ID:
        t_uid = int(data.split("_")[2])
        p = db_run("SELECT first_name, username FROM users_profile WHERE user_id = ?", (t_uid,), fetch=True)
        logs = db_run("SELECT action_type, details, timestamp FROM user_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5", (t_uid,), fetch=True, multi=True)
        db_run("INSERT OR REPLACE INTO admin_state (admin_id, target_user_id, chat_session_active) VALUES (?, ?, 0)", (OWNER_ID, t_uid))
        
        if not p: return
        h = f"🖥️ **USER DASHBOARD**\n👤 **Name:** {p[0]} | @{p[1] if p[1] else 'None'}\n🆔 ID: `{t_uid}`\n\n📝 **Logs:**\n"
        if logs:
            for at, dt, ts in logs: h += f"▪️ `[{time.strftime('%H:%M', time.localtime(ts))}]` **{at}**: {dt}\n"
        kb = {"inline_keyboard": [[{"text": "💬 Start Live Chat Session", "callback_data": f"adm_s_ch_{t_uid}"}], [{"text": "👥 Active Users List", "callback_data": "adm_ref_u"}]]}
        requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": h, "parse_mode": "Markdown", "reply_markup": kb})
        return

    if data.startswith("adm_s_ch_") and uid == OWNER_ID:
        db_run("UPDATE admin_state SET chat_session_active = 1 WHERE admin_id = ?", (OWNER_ID,))
        requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "🟢 **Live Chat Active!** Messages will now mirror instantly.", "reply_markup": {"inline_keyboard": [[{"text": "❌ Close Chat Session", "callback_data": "adm_c_chat"}]]}})
        return

    if data == "adm_c_chat" and uid == OWNER_ID:
        db_run("UPDATE admin_state SET chat_session_active = 0 WHERE admin_id = ?", (OWNER_ID,))
        requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "🔴 **Chat Session Closed.** Hub monitoring system online."})
        return

    if data == "adm_ref_u" and uid == OWNER_ID:
        requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id})
        rows = db_run("SELECT user_id, first_name FROM users_profile ORDER BY join_date DESC", fetch=True, multi=True)
        kb = {"inline_keyboard": [[{"text": f"👤 {r[1]}", "callback_data": f"adm_v_{r[0]}"}] for r in rows]}
        requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "📊 **Active Users Panel:**", "reply_markup": kb})
        return

    # Client Menus
    if data == "srv_account":
        kb = {"inline_keyboard": [[{"text": "🚀 Apply / Join Request", "callback_data": "join_account"}], [{"text": "⬅️ Back", "callback_data": "m_menu"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("account", d_acc), "parse_mode": "Markdown", "reply_markup": kb})
    elif data == "join_account":
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("form_account", d_f_acc), "reply_markup": {"inline_keyboard": [[{"text": "⬅️ Back", "callback_data": "srv_account"}]]}})
    elif data == "srv_vip":
        kb = {"inline_keyboard": [[{"text": "💎 Join VIP Premium Request", "callback_data": "join_vip"}], [{"text": "⬅️ Back", "callback_data": "m_menu"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("vip", d_vip), "parse_mode": "Markdown", "reply_markup": kb})
    elif data == "join_vip":
        kb = {"inline_keyboard": [[{"text": "💳 Lifetime Framework Access", "callback_data": "p_wait"}], [{"text": "⬅️ Back", "callback_data": "srv_vip"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("form_vip", d_f_vip), "reply_markup": kb})
    elif data == "srv_copy":
        kb = {"inline_keyboard": [[{"text": "📋 Connect Copy Trading Setup", "callback_data": "p_wait"}], [{"text": "⬅️ Back", "callback_data": "m_menu"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("copy", d_cpy), "parse_mode": "Markdown", "reply_markup": kb})
    elif data == "p_wait":
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": "⏳ **Please wait...** Processing infrastructure parameters. Team will reach out.", "reply_markup": {"inline_keyboard": [[{"text": "⬅️ Back to Main Menu", "callback_data": "m_menu"}]]}})

def auto_request_approver():
    while True:
        try:
            reqs = db_run("SELECT user_id, chat_id FROM pending_channel_requests", fetch=True, multi=True)
            if reqs:
                for uid, cid in reqs:
                    if requests.post(f"{BASE_URL}/approveChatJoinRequest", json={"chat_id": cid, "user_id": uid}).json().get("ok"):
                        log_hist(uid, "APPROVAL", "Approved Automatically")
                        db_run("DELETE FROM pending_channel_requests WHERE user_id = ? AND chat_id = ?", (uid, cid))
        except Exception: pass
        time.sleep(4)

def main():
    threading.Thread(target=auto_request_approver, daemon=True).start()
    print("🚀 Help Desk Engine Armed...")
    offset = 0
    while True:
        try:
            res = requests.post(f"{BASE_URL}/getUpdates", json={"offset": offset, "timeout": 10, "allowed_updates": ["message", "callback_query", "chat_join_request"]}, timeout=15).json()
            if res.get("ok"):
                for upd in res["result"]:
                    offset = upd["update_id"] + 1
                    if "chat_join_request" in upd:
                        r = upd["chat_join_request"]
                        db_run("INSERT OR IGNORE INTO pending_channel_requests VALUES (?, ?, ?)", (r["from"]["id"], r["chat"]["id"], time.time()))
                    elif "message" in upd: handle_incoming_message(upd["message"])
                    elif "callback_query" in upd: handle_callback_query(upd["callback_query"])
            elif res.get("error_code") == 409: time.sleep(10)
        except Exception: time.sleep(4)

if __name__ == "__main__":
    main()
        
