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

    # 🛡️ Link Filtering System
    if text and chat_id == FREE_GROUP_ID and uid != OWNER_ID:
        if re.search(r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+|[a-zA-r0-9\-\.]+\.(com|net|org|xyz|info|co|biz))', text, re.I):
            requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
            return

    if "new_chat_members" in msg or "left_chat_member" in msg:
        requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
        return

    if msg.get("chat", {}).get("type") == "private":
        db_run("INSERT OR IGNORE INTO users_profile VALUES (?, ?, ?, ?)", (uid, f_user.get("first_name"), f_user.get("username"), time.time()))

        if uid == OWNER_ID:
            # Handle Text Submission for Editing State
            edit_mode = db_run("SELECT editing_service FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,), fetch=True)
            if edit_mode and edit_mode[0]:
                target = edit_mode[0]  # Direct key mapping fix
                db_run("INSERT OR REPLACE INTO dynamic_content (service_key, text_content) VALUES (?, ?)", (target, text))
                db_run("DELETE FROM admin_edit_state WHERE admin_id = ?", (OWNER_ID,))
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"✅ **Saved:** `{target}` content has been updated successfully!"})
                return

            if text and text.startswith("/schedule"):
                try:
                    parts = text.split(" ", 2)
                    db_run("INSERT INTO schedules (post_text, run_time, is_active) VALUES (?, ?, 1)", (parts[2], parts[1]))
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"✅ **Scheduled!** Post set for `{parts[1]}`."})
                except: 
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "❌ Format: `/schedule HH:MM Message`"})
                return

            if text == "/start":
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "👑 **Control Panel Online.**", "reply_markup": {"keyboard": [[{"text": "👥 View Total Users"}, {"text": "✏️ Live Edit Messages"}]], "resize_keyboard": True}})
                return

            if text == "👥 View Total Users":
                rows = db_run("SELECT user_id, first_name, username FROM users_profile", fetch=True, multi=True)
                if not rows:
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "📭 No users registered yet."})
                    return
                out = f"📊 **Total Active Base Users:** `{len(rows)}` \n\n"
                for idx, r in enumerate(rows, 1):
                    usr_tag = f"@{r[2]}" if r[2] else "No Username"
                    out += f"{idx}. 👤 {r[1]} ({usr_tag}) - ID: `{r[0]}`\n"
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": out, "parse_mode": "Markdown"})
                return

            if text == "✏️ Live Edit Messages":
                kb = {"inline_keyboard": [
                    [{"text": "📝 Account Mgmt Text", "callback_data": "edt_account"}],
                    [{"text": "📝 Account Form Structure", "callback_data": "edt_form_account"}],
                    [{"text": "📝 VIP Main Details", "callback_data": "edt_vip"}],
                    [{"text": "📝 VIP Form", "callback_data": "edt_form_vip"}],
                    [{"text": "📝 Copy Trading Layout", "callback_data": "edt_copy"}]
                ]}
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "🛠️ **Select section to update:**", "reply_markup": kb})
                return

        if text == "/start":
            w_msg = f"👋 **Hello, {f_user.get('first_name', 'Trader')}!**\n\nWelcome to **Gold Expert FX Hub**. Select a service below:"
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": w_msg, "parse_mode": "Markdown", "reply_markup": get_main_keyboard()})

def handle_callback_query(cb):
    uid = cb["from"]["id"]; chat_id = cb["message"]["chat"]["id"]
    msg_id = cb["message"]["message_id"]; data = cb["data"]
    requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": cb["id"]})

    # Strict Admin Key Registration
    if data.startswith("edt_") and uid == OWNER_ID:
        clean_key = data.replace("edt_", "") # Store exact reading key mapping
        db_run("INSERT OR REPLACE INTO admin_edit_state VALUES (?, ?)", (OWNER_ID, clean_key))
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": f"📥 **Editing Mode Active for:** `{clean_key}`\n\nAb jo bhi text aap bhejenge wo save ho jayega. Type karein aur send karein:"})
        return

    # Client-Side Content Navigation
    d_acc = "💼 **Account Management Service**\n\nMinimum Equity: $500"
    d_f_acc = "Format Required:\n1) Broker Name -\n2) Account ID -\n3) Password -"
    d_vip = "👑 **VIP Premium Private Channel**\n\nJoin for Daily Gold signals."
    d_f_vip = "VIP Access Form:\nSend your payment screenshot."
    d_cpy = "📋 **Copy Trading Service**\n\nAutomate your portfolio seamlessly."

    if data == "m_menu":
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": "👋 Select system parameters:", "reply_markup": get_main_keyboard()})
    
    elif data == "srv_account":
        kb = {"inline_keyboard": [[{"text": "🚀 Apply Now", "callback_data": "join_account"}], [{"text": "⬅️ Back", "callback_data": "m_menu"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("account", d_acc), "reply_markup": kb})
    
    elif data == "join_account":
        kb = {"inline_keyboard": [[{"text": "⬅️ Back", "callback_data": "srv_account"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("form_account", d_f_acc), "reply_markup": kb})
        
    elif data == "srv_vip":
        kb = {"inline_keyboard": [[{"text": "⭐ Join VIP", "callback_data": "join_vip"}], [{"text": "⬅️ Back", "callback_data": "m_menu"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("vip", d_vip), "reply_markup": kb})
        
    elif data == "join_vip":
        kb = {"inline_keyboard": [[{"text": "⬅️ Back", "callback_data": "srv_vip"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("form_vip", d_f_vip), "reply_markup": kb})

    elif data == "srv_copy":
        kb = {"inline_keyboard": [[{"text": "⬅️ Back", "callback_data": "m_menu"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("copy", d_cpy), "reply_markup": kb})

def cron_worker():
    while True:
        try:
            reqs = db_run("SELECT user_id, chat_id FROM pending_channel_requests", fetch=True, multi=True)
            if reqs:
                for uid, cid in reqs:
                    if requests.post(f"{BASE_URL}/approveChatJoinRequest", json={"chat_id": cid, "user_id": uid}).json().get("ok"):
                        db_run("DELETE FROM pending_channel_requests WHERE user_id = ? AND chat_id = ?", (uid, cid))
        except: pass
        
        try:
            now = datetime.now()
            if now.weekday() <= 4:
                jobs = db_run("SELECT id, post_text FROM schedules WHERE run_time = ? AND is_active = 1", (now.strftime("%H:%M"),), fetch=True, multi=True)
                if jobs:
                    for j in jobs:
                        if requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": PRIVATE_CHANNEL_ID, "text": j[1]}).json().get("ok"):
                            db_run("UPDATE schedules SET is_active = 0 WHERE id = ?", (j[0],))
        except: pass
        time.sleep(25)

def main():
    threading.Thread(target=cron_worker, daemon=True).start()
    offset = 0
    while True:
        try:
            res = requests.post(f"{BASE_URL}/getUpdates", json={"offset": offset, "timeout": 20, "allowed_updates": ["message", "callback_query", "chat_join_request"]}).json()
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
    
