import requests, sqlite3, time, threading, re, sys
from datetime import datetime

API_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"  # ⚠️ Yahan apna Real Token daalein
OWNER_ID = 7415265825  # 👑 Admin ID (Prince Bhai)

FREE_GROUP_ID = -4477244119  
PRIVATE_CHANNEL_ID = -3870933647  
DB_NAME = "gold_expert_final.db"

if not API_TOKEN: sys.exit(1)
BASE_URL = f"https://api.telegram.org/bot{API_TOKEN}"

# --- DATABASE ENGINE ---
def db_run(query, params=(), fetch=False, multi=False):
    try:
        with sqlite3.connect(DB_NAME, timeout=30) as conn:
            c = conn.cursor(); c.execute(query, params)
            if fetch: return c.fetchall() if multi else c.fetchone()
            conn.commit()
    except Exception as e:
        print(f"DB Error: {e}")
        return None

def init_db():
    db_run("CREATE TABLE IF NOT EXISTS pending_channel_requests (user_id INTEGER, chat_id INTEGER, request_time REAL, PRIMARY KEY (user_id, chat_id))")
    db_run("CREATE TABLE IF NOT EXISTS users_profile (user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT, join_date REAL)")
    db_run("CREATE TABLE IF NOT EXISTS dynamic_content (service_key TEXT PRIMARY KEY, text_content TEXT)")
    db_run("CREATE TABLE IF NOT EXISTS admin_state (admin_id INTEGER PRIMARY KEY, mode TEXT, target_id TEXT)")
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

# --- MAIN INCOMING MESSAGE HANDLER ---
def handle_incoming_message(msg):
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")
    text = msg.get("text", "")
    f_user = msg.get("from", {})
    uid = f_user.get("id")
    
    if not uid: return

    # 🛡️ 1. Group Link Cleaner & System Messages Remover
    if "new_chat_members" in msg or "left_chat_member" in msg:
        requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
        return

    if text and chat_id == FREE_GROUP_ID and uid != OWNER_ID:
        if re.search(r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+|[a-zA-r0-9\-\.]+\.(com|net|org|xyz|info|co|biz))', text, re.I):
            requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
            return

    # Private Chat Processing
    if msg.get("chat", {}).get("type") == "private":
        db_run("INSERT OR IGNORE INTO users_profile VALUES (?, ?, ?, ?)", (uid, f_user.get("first_name"), f_user.get("username"), time.time()))

        # 👑 Admin Console Powers
        if uid == OWNER_ID:
            state = db_run("SELECT mode, target_id FROM admin_state WHERE admin_id = ?", (OWNER_ID,), fetch=True)
            
            # A. Process Live Editing Save
            if state and state[0] == "EDITING":
                target_key = state[1]
                db_run("INSERT OR REPLACE INTO dynamic_content (service_key, text_content) VALUES (?, ?)", (target_key, text))
                db_run("DELETE FROM admin_state WHERE admin_id = ?", (OWNER_ID,))
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"✅ **Saved Successfully:** Content for `{target_key}` updated live!"})
                return

            # B. Process Live User Reply Chatting
            if state and state[0] == "REPLYING":
                target_user = state[1]
                res = requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": target_user, "text": f"📩 **Message From Admin:**\n\n{text}"}).json()
                db_run("DELETE FROM admin_state WHERE admin_id = ?", (OWNER_ID,))
                if res.get("ok"):
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "✅ Your message has been sent to the user successfully!"})
                else:
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "❌ Could not send message. User might have blocked the bot."})
                return

            # C. Process Mon-Fri Post Scheduler Command
            if text and text.startswith("/schedule"):
                try:
                    parts = text.split(" ", 2)
                    db_run("INSERT INTO schedules (post_text, run_time, is_active) VALUES (?, ?, 1)", (parts[2], parts[1]))
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"📅 **Scheduled!** Target post will be sent at `{parts[1]}` (Mon-Fri Rule Active)."})
                except: 
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "❌ **Format:** `/schedule HH:MM Your Message`"})
                return

            if text == "/start":
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "👑 **Welcome Prince Bhai.** Master Engine Online.", "reply_markup": {"keyboard": [[{"text": "👥 View Total Users"}, {"text": "✏️ Live Edit Messages"}]], "resize_keyboard": True}})
                return

            if text == "👥 View Total Users":
                rows = db_run("SELECT user_id, first_name, username FROM users_profile", fetch=True, multi=True)
                if not rows:
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "📭 No active users found in database."})
                    return
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"📊 Total Active Users: `{len(rows)}`. Select any user below to text/reply them directly:"})
                for r in rows:
                    tag = f"(@{r[2]})" if r[2] else ""
                    kb = {"inline_keyboard": [[{"text": f"💬 Chat with {r[1]}", "callback_data": f"chat_usr_{r[0]}"}]]}
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"👤 **User:** {r[1]} {tag}\n🆔 **ID:** `{r[0]}`", "parse_mode": "Markdown", "reply_markup": kb})
                return

            if text == "✏️ Live Edit Messages":
                kb = {"inline_keyboard": [
                    [{"text": "📝 Account Management Main Text", "callback_data": "edt_account"}],
                    [{"text": "📝 Account Submission Form", "callback_data": "edt_form_account"}],
                    [{"text": "📝 VIP Channel Main Text", "callback_data": "edt_vip"}],
                    [{"text": "📝 VIP Submission Form", "callback_data": "edt_form_vip"}],
                    [{"text": "📝 Copy Trading Layout Text", "callback_data": "edt_copy"}]
                ]}
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "🛠️ **Select section to update dynamic content:**", "reply_markup": kb})
                return

        # Public Client Panel View Trigger
        if text == "/start":
            w_msg = f"👋 **Hello, {f_user.get('first_name', 'Trader')}!**\n\nWelcome to **Gold Expert FX Automation Hub**. Select our services below:"
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": w_msg, "parse_mode": "Markdown", "reply_markup": get_main_keyboard()})

# --- CALLBACK ROUTER SYSTEM ---
def handle_callback_query(cb):
    uid = cb["from"]["id"]; chat_id = cb["message"]["chat"]["id"]
    msg_id = cb["message"]["message_id"]; data = cb["data"]
    requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": cb["id"]})

    # Admin Callback Actions
    if uid == OWNER_ID:
        if data.startswith("edt_"):
            clean_key = data.replace("edt_", "") # Maps perfectly with client reading key
            db_run("INSERT OR REPLACE INTO admin_state VALUES (?, ?, ?)", (OWNER_ID, "EDITING", clean_key))
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"📥 **Editing Mode Activated for Key:** `{clean_key}`\n\nNow type or paste your updated text message layout and hit send:"})
            return
            
        if data.startswith("chat_usr_"):
            target_id = data.replace("chat_usr_", "")
            db_run("INSERT OR REPLACE INTO admin_state VALUES (?, ?, ?)", (OWNER_ID, "REPLYING", target_id))
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"⌨️ **Direct Chat Activated for ID:** `{target_id}`\n\nType your message below to send it live to this user's inbox:"})
            return

    # Client Panel Dynamic Rendering Engine
    d_acc = "💼 **Account Management Service**\n\nMinimum Equity: $500"
    d_f_acc = "Format Required:\n1) Broker Name -\n2) Account ID -\n3) Password -"
    d_vip = "👑 **VIP Premium Private Channel**\n\nJoin for Daily Gold target setups."
    d_f_vip = "🎯 VIP Access Operational Framework Form Process Setup Timing Trigger."
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
        kb = {"inline_keyboard": [[{"text": "⭐ Join VIP Panel", "callback_data": "join_vip"}], [{"text": "⬅️ Back", "callback_data": "m_menu"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("vip", d_vip), "reply_markup": kb})
    elif data == "join_vip":
        kb = {"inline_keyboard": [[{"text": "⬅️ Back", "callback_data": "srv_vip"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("form_vip", d_f_vip), "reply_markup": kb})
    elif data == "srv_copy":
        kb = {"inline_keyboard": [[{"text": "⬅️ Back", "callback_data": "m_menu"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("copy", d_cpy), "reply_markup": kb})

# --- CRON SCHEDULER & AUTO APPROVALS ---
def cron_worker():
    while True:
        # 1. Instant Automated Approval Loop
        try:
            reqs = db_run("SELECT user_id, chat_id FROM pending_channel_requests", fetch=True, multi=True)
            if reqs:
                for uid, cid in reqs:
                    if requests.post(f"{BASE_URL}/approveChatJoinRequest", json={"chat_id": cid, "user_id": uid}).json().get("ok"):
                        db_run("DELETE FROM pending_channel_requests WHERE user_id = ? AND chat_id = ?", (uid, cid))
        except: pass
        
        # 2. Mon-Fri Content Dispatcher
        try:
            now = datetime.now()
            if now.weekday() <= 4:  # 0=Mon, 4=Fri. Strict filter
                jobs = db_run("SELECT id, post_text FROM schedules WHERE run_time = ? AND is_active = 1", (now.strftime("%H:%M"),), fetch=True, multi=True)
                if jobs:
                    for j in jobs:
                        if requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": PRIVATE_CHANNEL_ID, "text": j[1], "parse_mode": "Markdown"}).json().get("ok"):
                            db_run("UPDATE schedules SET is_active = 0 WHERE id = ?", (j[0],))
        except: pass
        time.sleep(20)

# --- ENGINE MAIN EXECUTION ---
def main():
    threading.Thread(target=cron_worker, daemon=True).start()
    print("🚀 Master Premium Control Engine Deployed Successfully...")
    offset = 0
    while True:
        try:
            res = requests.post(f"{BASE_URL}/getUpdates", json={"offset": offset, "timeout": 20, "allowed_updates": ["message", "callback_query", "chat_join_request"]}).json()
            if res.get("ok"):
                for u in res["result"]:
                    offset = u["update_id"] + 1
                    if "chat_join_request" in u:
                        r = u["chat_join_request"]
                        # Auto-approves instantly or backups to DB if rate-limited
                        if not requests.post(f"{BASE_URL}/approveChatJoinRequest", json={"chat_id": r["chat"]["id"], "user_id": r["from"]["id"]}).json().get("ok"):
                            db_run("INSERT OR IGNORE INTO pending_channel_requests VALUES (?, ?, ?)", (r["from"]["id"], r["chat"]["id"], time.time()))
                    elif "message" in u: handle_incoming_message(u["message"])
                    elif "callback_query" in u: handle_callback_query(u["callback_query"])
        except: time.sleep(4)

if __name__ == "__main__":
    main()
    
