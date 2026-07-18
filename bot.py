import requests, sqlite3, time, threading, re, sys
from datetime import datetime

API_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"  # ⚠️ Yahan apna Real Token daalein
OWNER_ID = 7415265825  # 👑 Admin ID

FREE_GROUP_ID = -4477244119  
PRIVATE_CHANNEL_ID = -3870933647  
DB_NAME = "gold_expert_premium.db"

if not API_TOKEN: sys.exit(1)
BASE_URL = f"https://api.telegram.org/bot{API_TOKEN}"

def db_run(query, params=(), fetch=False, multi=False):
    try:
        with sqlite3.connect(DB_NAME, timeout=30) as conn:
            c = conn.cursor(); c.execute(query, params)
            if fetch: return c.fetchall() if multi else c.fetchone()
            conn.commit()
    except Exception as e: print(f"DB Error: {e}"); return None

def init_db():
    db_run("CREATE TABLE IF NOT EXISTS pending_channel_requests (user_id INTEGER, chat_id INTEGER, request_time REAL, PRIMARY KEY (user_id, chat_id))")
    db_run("CREATE TABLE IF NOT EXISTS users_profile (user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT, join_date REAL)")
    db_run("CREATE TABLE IF NOT EXISTS dynamic_content (service_key TEXT PRIMARY KEY, text_content TEXT)")
    db_run("CREATE TABLE IF NOT EXISTS admin_edit_state (admin_id INTEGER PRIMARY KEY, editing_service TEXT)")
    db_run("CREATE TABLE IF NOT EXISTS schedules (id INTEGER PRIMARY KEY AUTOINCREMENT, post_text TEXT, run_time TEXT, is_active INTEGER DEFAULT 1)")

init_db()

def get_content(k, d):
    r = db_run("SELECT text_content FROM dynamic_content WHERE service_key = ?", (k,), fetch=True)
    return r[0] if r and r[0] else d

def handle_incoming_message(msg):
    chat_id = msg.get("chat", {}).get("id")
    text = msg.get("text", "")
    f_user = msg.get("from", {})
    uid = f_user.get("id")
    
    if not uid: return

    # Admin Control Logic
    if uid == OWNER_ID:
        # Check Edit Mode
        edit_mode = db_run("SELECT editing_service FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,), fetch=True)
        if edit_mode and edit_mode[0]:
            target = edit_mode[0].replace("edt_", "")
            db_run("INSERT OR REPLACE INTO dynamic_content (service_key, text_content) VALUES (?, ?)", (target, text))
            db_run("DELETE FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"✅ **Saved:** `{target}` updated successfully!"})
            return

        if text.startswith("/schedule"):
            try:
                parts = text.split(" ", 2)
                db_run("INSERT INTO schedules (post_text, run_time, is_active) VALUES (?, ?, 1)", (parts[2], parts[1]))
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "✅ Scheduled (Mon-Fri)!"})
            except: requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "❌ Format: `/schedule HH:MM Message`"})
            return
        
        if text == "/start":
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "👑 Admin Control Active.", "reply_markup": {"keyboard": [[{"text": "✏️ Live Edit Messages"}]], "resize_keyboard": True}})
            return
        
        if text == "✏️ Live Edit Messages":
            kb = {"inline_keyboard": [
                [{"text": "📝 Account Mgmt", "callback_data": "edt_account"}],
                [{"text": "📝 Account Form", "callback_data": "edt_form_account"}],
                [{"text": "📝 VIP Main", "callback_data": "edt_vip"}],
                [{"text": "📝 VIP Form", "callback_data": "edt_form_vip"}],
                [{"text": "📝 Copy Trading", "callback_data": "edt_copy"}]
            ]}
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "🛠️ **Select section to update:**", "reply_markup": kb})
            return

    # Link Cleaner
    if text and chat_id == FREE_GROUP_ID and uid != OWNER_ID:
        if re.search(r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+|[a-zA-r0-9\-\.]+\.(com|net|org))', text, re.I):
            requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": msg.get("message_id")})

def handle_callback_query(cb):
    uid = cb["from"]["id"]
    chat_id = cb["message"]["chat"]["id"]
    msg_id = cb["message"]["message_id"]
    data = cb["data"]
    requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": cb["id"]})

    if data.startswith("edt_") and uid == OWNER_ID:
        db_run("INSERT OR REPLACE INTO admin_edit_state VALUES (?, ?)", (OWNER_ID, data))
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": f"📥 **Editing mode active for:** `{data}`.\n\nNow send the new text message below:"})
        return

    # User Navigation
    d_acc = "💼 **Account Management Service**\n\nMinimum Equity: $500"
    if data == "srv_account":
        kb = {"inline_keyboard": [[{"text": "🚀 Apply", "callback_data": "join_account"}], [{"text": "⬅️ Back", "callback_data": "m_menu"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("account", d_acc), "parse_mode": "Markdown", "reply_markup": kb})

def cron_worker():
    while True:
        # 1. Approvals
        reqs = db_run("SELECT user_id, chat_id FROM pending_channel_requests", fetch=True, multi=True)
        if reqs:
            for uid, cid in reqs:
                if requests.post(f"{BASE_URL}/approveChatJoinRequest", json={"chat_id": cid, "user_id": uid}).json().get("ok"):
                    db_run("DELETE FROM pending_channel_requests WHERE user_id = ? AND chat_id = ?", (uid, cid))
        
        # 2. Schedule
        now = datetime.now()
        if now.weekday() <= 4:
            jobs = db_run("SELECT id, post_text FROM schedules WHERE run_time = ? AND is_active = 1", (now.strftime("%H:%M"),), fetch=True, multi=True)
            for j in jobs:
                if requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": PRIVATE_CHANNEL_ID, "text": j[1]}).json().get("ok"):
                    db_run("UPDATE schedules SET is_active = 0 WHERE id = ?", (j[0],))
        time.sleep(30)

def main():
    threading.Thread(target=cron_worker, daemon=True).start()
    offset = 0
    while True:
        try:
            res = requests.post(f"{BASE_URL}/getUpdates", json={"offset": offset, "timeout": 20}).json()
            if res.get("ok"):
                for u in res["result"]:
                    offset = u["update_id"] + 1
                    if "message" in u: handle_incoming_message(u["message"])
                    elif "callback_query" in u: handle_callback_query(u["callback_query"])
                    elif "chat_join_request" in u:
                        r = u["chat_join_request"]
                        db_run("INSERT OR IGNORE INTO pending_channel_requests VALUES (?, ?, ?)", (r["from"]["id"], r["chat"]["id"], time.time()))
        except: time.sleep(5)

if __name__ == "__main__":
    main()
    
