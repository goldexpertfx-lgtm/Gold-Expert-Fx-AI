import requests, sqlite3, time, threading, re

API_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"  # ⚠️ Yahan apna Real Token daalein
OWNER_ID = 7415265825  # 👑 Admin ID

FREE_GROUP_ID = -4477244119  
PRIVATE_CHANNEL_ID = -3870933647  
DB_NAME = "gold_expert_master.db"

BASE_URL = f"https://api.telegram.org/bot{API_TOKEN}"

# --- DATABASE SETUP ---
def db_run(query, params=(), fetch=False, multi=False):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor(); c.execute(query, params)
        if fetch: return c.fetchall() if multi else c.fetchone()
        conn.commit()

db_run("CREATE TABLE IF NOT EXISTS users_profile (user_id INTEGER PRIMARY KEY, name TEXT)")
db_run("CREATE TABLE IF NOT EXISTS dynamic_content (service_key TEXT PRIMARY KEY, text_content TEXT)")
db_run("CREATE TABLE IF NOT EXISTS admin_state (admin_id INTEGER PRIMARY KEY, mode TEXT, target_id TEXT)")

def get_content(k, d):
    r = db_run("SELECT text_content FROM dynamic_content WHERE service_key = ?", (k,), fetch=True)
    return r[0] if r and r[0] else d

# --- CORE HANDLERS ---
def handle_msg(msg):
    chat_id = msg.get("chat", {}).get("id")
    msg_id = msg.get("message_id")
    text = msg.get("text", "")
    f_user = msg.get("from", {})
    uid = f_user.get("id")

    # 1. LINK CLEANER (Only for Group)
    if chat_id == FREE_GROUP_ID and uid != OWNER_ID and text:
        if re.search(r'(https?://[^\s]+|www\.[^\s]+|\bt\.me/[^\s]+|\.com|\.net|\.org)', text, re.I):
            requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id})
            return

    # 2. ADMIN PANEL
    if uid == OWNER_ID:
        state = db_run("SELECT mode, target_id FROM admin_state WHERE admin_id = ?", (OWNER_ID,), fetch=True)
        
        # EDIT MODE
        if state and state[0] == "EDITING":
            db_run("INSERT OR REPLACE INTO dynamic_content (service_key, text_content) VALUES (?, ?)", (state[1], text))
            db_run("DELETE FROM admin_state WHERE admin_id = ?", (OWNER_ID,))
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "✅ **Updated Successfully!**"})
            return

        # REPLY MODE
        if state and state[0] == "REPLYING":
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": state[1], "text": f"📩 **Admin Message:**\n\n{text}"})
            db_run("DELETE FROM admin_state WHERE admin_id = ?", (OWNER_ID,))
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "✅ Message sent to user."})
            return

        if text == "/start":
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "👑 **Control Console**", "reply_markup": {"keyboard": [[{"text": "👥 View Users"}, {"text": "✏️ Edit Services"}]], "resize_keyboard": True}})
            return
        
        if text == "👥 View Users":
            users = db_run("SELECT user_id, name FROM users_profile", fetch=True, multi=True)
            kb = {"inline_keyboard": [[{"text": f"👤 {u[1]}", "callback_data": f"user_{u[0]}"}] for u in users]}
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "Select user to chat:", "reply_markup": kb})
            return

        if text == "✏️ Edit Services":
            kb = {"inline_keyboard": [[{"text": "Edit Account", "callback_data": "edit_account"}], [{"text": "Edit VIP", "callback_data": "edit_vip"}]]}
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": OWNER_ID, "text": "What to edit?", "reply_markup": kb})
            return

    # Save new users
    if msg.get("chat", {}).get("type") == "private":
        db_run("INSERT OR IGNORE INTO users_profile VALUES (?, ?)", (uid, f_user.get("first_name")))

def handle_cb(cb):
    uid = cb["from"]["id"]; data = cb["data"]; mid = cb["message"]["message_id"]; cid = cb["message"]["chat"]["id"]
    
    # Edit Logic
    if data.startswith("edit_"):
        db_run("INSERT OR REPLACE INTO admin_state VALUES (?, ?, ?)", (OWNER_ID, "EDITING", data.replace("edit_", "")))
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": cid, "message_id": mid, "text": "📥 Send the new text now:"})
    
    # User Reply Logic
    elif data.startswith("user_"):
        target_uid = data.split("_")[1]
        db_run("INSERT OR REPLACE INTO admin_state VALUES (?, ?, ?)", (OWNER_ID, "REPLYING", target_uid))
        requests.post(f"{BASE_URL}/editMessageText", json={"chat_id": cid, "message_id": mid, "text": "⌨️ Type your reply to this user:"})

# --- WORKER ---
def run_bot():
    offset = 0
    while True:
        try:
            res = requests.post(f"{BASE_URL}/getUpdates", json={"offset": offset, "timeout": 20, "allowed_updates": ["message", "callback_query", "chat_join_request"]}).json()
            if res.get("ok"):
                for u in res["result"]:
                    offset = u["update_id"] + 1
                    if "message" in u: handle_msg(u["message"])
                    elif "callback_query" in u: handle_cb(u["callback_query"])
                    elif "chat_join_request" in u:
                        req = u["chat_join_request"]
                        requests.post(f"{BASE_URL}/approveChatJoinRequest", json={"chat_id": req["chat"]["id"], "user_id": req["from"]["id"]})
        except: time.sleep(5)

if __name__ == "__main__":
    run_bot()
    
