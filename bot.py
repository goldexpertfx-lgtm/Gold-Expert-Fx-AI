import requests, sqlite3, time, threading, re, sys
from datetime import datetime

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
    db_run("CREATE TABLE IF NOT EXISTS schedules (id INTEGER PRIMARY KEY AUTOINCREMENT, post_text TEXT, run_time TEXT, is_active INTEGER DEFAULT 1)")

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

    # Link & Service System Messages Cleaner
    if "new_chat_members" in msg or "left_chat_member" in msg:
        requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
        return

    if text and chat_id == FREE_GROUP_ID and uid != OWNER_ID:
        if re.search(r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+|[a-zA-r0-9\-\.]+\.(com|net|org))', text, re.I):
            requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
            return

    if msg.get("chat", {}).get("type") == "private":
        db_run("INSERT OR IGNORE INTO users_profile VALUES (?, ?, ?, ?)", (uid, f_user.get("first_name"), f_user.get("username"), time.time()))

        if text and text.startswith("/start"):
            if uid == OWNER_ID:
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": "👑 Welcome Prince Bhai. Custom Schedule and Live Edit System Active.\n\nUse `/schedule HH:MM Text` to set Mon-Fri tasks.", "reply_markup": {"keyboard": [[{"text": "👥 View Total Users"}, {"text": "✏️ Live Edit Messages"}]], "resize_keyboard": True}})
            w_msg = f"👋 **Hello, {f_user.get('first_name', 'Trader')}!**\n\nWelcome to **Gold Expert FX Automation Hub**."
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": w_msg, "parse_mode": "Markdown", "reply_markup": get_main_keyboard()})
            return

        # Schedule Parser Action Command
        if uid == OWNER_ID and text and text.startswith("/schedule"):
            try:
                parts = text.split(" ", 2)
                time_target = parts[1] # Format expected HH:MM
                content_to_post = parts[2]
                datetime.strptime(time_target, "%H:%M") # Validation check
                db_run("INSERT INTO schedules (post_text, run_time, is_active) VALUES (?, ?, 1)", (content_to_post, time_target))
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"✅ **Signal/Post Scheduled!**\n⏰ Time: `{time_target}`\n📅 Rule: Mon-Fri Only.", "parse_mode": "Markdown"})
            except Exception:
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "❌ **Wrong Format!** Use exactly like this:\n`/schedule 14:30 Gold Buy Now @ 2420`", "parse_mode": "Markdown"})
            return

        if uid == OWNER_ID:
            if text == "👥 View Total Users":
                rows = db_run("SELECT user_id, first_name, username FROM users_profile ORDER BY join_date DESC", fetch=True, multi=True)
                if not rows: return requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "📭 No registered users."})
                kb = {"inline_keyboard": [[{"text": f"👤 {r[1]} (@{r[2]})" if r[2] else f"👤 {r[1]}", "callback_data": f"adm_v_{r[0]}"}] for r in rows]}
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"📊 Total Active Users: `{len(rows)}`", "parse_mode": "Markdown", "reply_markup": kb})
                return

            elif text == "✏️ Live Edit Messages":
                kb = {"inline_keyboard": [
                    [{"text": "📝 Edit Account Management Text", "callback_data": "edt_account"}],
                    [{"text": "📝 Edit Account Form", "callback_data": "edt_form_account"}],
                    [{"text": "📝 Edit VIP Main Text", "callback_data": "edt_vip"}],
                    [{"text": "📝 Edit VIP Timing Form", "callback_data": "edt_form_vip"}],
                    [{"text": "📝 Edit Copy Trading Text", "callback_data": "edt_copy"}],
                    [{"text": "❌ Cancel", "callback_data": "edt_cancel"}
                ]]}
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "🛠️ **Select section to update:**", "reply_markup": kb})
                return

            e_row = db_run("SELECT editing_service FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,), fetch=True)
            if e_row and e_row[0]:
                clean_key = e_row[0].replace("edt_", "")
                db_run("INSERT OR REPLACE INTO dynamic_content (service_key, text_content) VALUES (?, ?)", (clean_key, text))
                db_run("DELETE FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"✅ **Live Database Update Saved for '{clean_key}'!**"})
                return

        if any(x in text for x in ["Broker", "ID", "Password"]):
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": "⏳ **Form Received perfectly.** Team is validating metrics."})

def handle_callback_query(cb):
    c_id = cb["id"]; uid = cb["from"]["id"]; chat_id = cb["message"]["chat"]["id"]
    msg_id = cb["message"]["message_id"]; data = cb["data"]
    requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": c_id})

    d_acc = "💼 **Account Management Service**\n\nMinimum Equity Required: $500"
    d_f_acc = "Format Required:\n1) Broker Name -\n2) Account ID -\n3) Password -"
    d_vip = "👑 **VIP Premium Channel**\n\nJoin our standard target setups dashboard."
    d_f_vip = "🎯 **VIP Operational Framework Setup Timing**"
    d_cpy = "📋 **Copy Trading System**\n\nAutomate your trades setup instantly."

    if data == "m_menu":
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": "👋 Select system parameters:", "reply_markup": get_main_keyboard()})
        return

    if data.startswith("edt_") and uid == OWNER_ID:
        if data == "edt_cancel":
            db_run("DELETE FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
            requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": "❌ Editing process cancelled."})
        else:
            db_run("INSERT OR REPLACE INTO admin_edit_state VALUES (?, ?)", (OWNER_ID, data))
            requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": f"📥 Copy/Send the new text message layout for `{data}` now:"})
        return

    if data == "srv_account":
        kb = {"inline_keyboard": [[{"text": "🚀 Apply Now", "callback_data": "join_account"}], [{"text": "⬅️ Back", "callback_data": "m_menu"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("account", d_acc), "parse_mode": "Markdown", "reply_markup": kb})
    elif data == "join_account":
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("form_account", d_f_acc), "reply_markup": {"inline_keyboard": [[{"text": "⬅️ Back", "callback_data": "srv_account"}]]}})
    elif data == "srv_vip":
        kb = {"inline_keyboard": [[{"text": "💎 Join VIP", "callback_data": "join_vip"}], [{"text": "⬅️ Back", "callback_data": "m_menu"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("vip", d_vip), "parse_mode": "Markdown", "reply_markup": kb})
    elif data == "join_vip":
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("form_vip", d_f_vip), "reply_markup": {"inline_keyboard": [[{"text": "⬅️ Back", "callback_data": "srv_vip"}]]}})
    elif data == "srv_copy":
        kb = {"inline_keyboard": [[{"text": "⬅️ Back", "callback_data": "m_menu"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("copy", d_cpy), "parse_mode": "Markdown", "reply_markup": kb})

def cron_scheduler_and_approver():
    while True:
        # 1. Handle Auto-Approvals
        try:
            reqs = db_run("SELECT user_id, chat_id FROM pending_channel_requests", fetch=True, multi=True)
            if reqs:
                for uid, cid in reqs:
                    if requests.post(f"{BASE_URL}/approveChatJoinRequest", json={"chat_id": cid, "user_id": uid}).json().get("ok"):
                        db_run("DELETE FROM pending_channel_requests WHERE user_id = ? AND chat_id = ?", (uid, cid))
        except Exception: pass

        # 2. Handle Mon-Fri Cron Post Transmitter
        try:
            now = datetime.now()
            # 0 = Monday, 4 = Friday. > 4 means Saturday & Sunday
            if now.weekday() <= 4:
                current_time_str = now.strftime("%H:%M")
                jobs = db_run("SELECT id, post_text FROM schedules WHERE run_time = ? AND is_active = 1", (current_time_str,), fetch=True, multi=True)
                if jobs:
                    for job_id, post_text in jobs:
                        res = requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": PRIVATE_CHANNEL_ID, "text": post_text, "parse_mode": "Markdown"}).json()
                        if res.get("ok"):
                            db_run("UPDATE schedules SET is_active = 0 WHERE id = ?", (job_id,))
        except Exception: pass
        time.sleep(15)

def main():
    threading.Thread(target=cron_scheduler_and_approver, daemon=True).start()
    print("🚀 System Online & Guarded...")
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
            elif res.get("error_code") == 409: time.sleep(5)
        except Exception: time.sleep(2)

if __name__ == "__main__":
    main()
    
