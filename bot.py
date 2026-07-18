import requests
import sqlite3
import time
import threading
import re
import sys
import os

# Render Environment Variables se Token uthayega
API_TOKEN = os.environ.get("8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4", "")
OWNER_ID = 7415265825
FREE_GROUP_ID = -4477244119
PRIVATE_CHANNEL_ID = -3870933647
BASE_URL = f"https://api.telegram.org/bot{API_TOKEN}"

# Memory-based DB (Disk issue khatam)
db = sqlite3.connect(":memory:", check_same_thread=False)

def init_db():
    c = db.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT)")
    db.commit()

def handle_incoming_message(msg):
    chat_id = msg.get("chat", {}).get("id")
    text = msg.get("text", "")
    if text == "/start":
        requests.post(f"{BASE_URL}/sendMessage", json={
            "chat_id": chat_id, 
            "text": "🚀 Bot is Online & Running!"
        })

if __name__ == "__main__":
    init_db()
    print("✅ BOT STARTED SUCCESSFULLY")
    offset = 0
    while True:
        try:
            res = requests.post(f"{BASE_URL}/getUpdates", json={"offset": offset, "timeout": 30}).json()
            if res.get("ok"):
                for update in res["result"]:
                    offset = update["update_id"] + 1
                    if "message" in update:
                        handle_incoming_message(update["message"])
        except Exception as e:
            time.sleep(5)
                      
