import requests
import sqlite3
import time
import threading
import re
import sys
import random

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
API_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"  # ⚠️ Apna Token yahan dalen
OWNER_ID = 7415265825  
FREE_GROUP_ID = -4477244119  
PRIVATE_CHANNEL_ID = -3870933647  

BASE_URL = f"https://api.telegram.org/bot{API_TOKEN}"
EMOJI_POOL = ["🔥", "🚀", "👍", "❤️", "⚡"]

# ==========================================
# 🛠️ HELPER: SAFE STRING HANDLING
# ==========================================
def get_vip_wait_text():
    part1 = "⏳ **Please wait, our team will share "
    part2 = "the deposit address shortly.**"
    return part1 + part2

def get_join_account_text():
    part1 = "1) Broker name -\n2) Server name -\n"
    part2 = "3) Platform - (MT4/MT5)\n"
    part3 = "4) Deposit Amount - (Minimum $500)\n"
    part4 = "5) Login ID -\n6) Password -\n"
    part5 = "7) Leverage - ( Minimum 1:500)\n"
    part6 = "8) How you will send money? \n"
    part7 = "(Binance, Skrill, Neteller, Crypto, Bank)\n\n"
    part8 = "📝 Fill this format and send it right here."
    return part1 + part2 + part3 + part4 + part5 + part6 + part7 + part8

# ==========================================
# 💾 DATABASE FUNCTIONS
# ==========================================
def init_db():
    conn = sqlite3.connect("new_join_filter_bot.db", timeout=20)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS member_activity (user_id INTEGER PRIMARY KEY, leave_timestamp REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS pending_channel_requests (user_id INTEGER, chat_id INTEGER, request_time REAL, PRIMARY KEY (user_id, chat_id))")
    cursor.execute("CREATE TABLE IF NOT EXISTS group_leaves (user_id INTEGER PRIMARY KEY, timestamp REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS channel_leaves (user_id INTEGER PRIMARY KEY, timestamp REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS users_profile (user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT, join_date REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS user_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action_type TEXT, details TEXT, timestamp REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS admin_state (admin_id INTEGER PRIMARY KEY, target_user_id INTEGER)")
    conn.commit()
    conn.close()

init_db()

# ... (Baki ka logic wahi rahega, bas strings ko function se call karein)

def handle_callback_query(callback):
    # ... (Callback handlers mein ye change karein)
    
    if data == "join_account":
        payload = {
            "chat_id": callback["message"]["chat"]["id"], 
            "message_id": callback["message"]["message_id"],
            "text": get_join_account_text()
        }
        requests.post(f"{BASE_URL}/editMessageText", json=payload)

    elif data == "vip_addr_wait":
        payload = {
            "chat_id": callback["message"]["chat"]["id"], 
            "message_id": callback["message"]["message_id"],
            "text": get_vip_wait_text()
        }
        requests.post(f"{BASE_URL}/editMessageText", json=payload)

# ... (Baaki code file mein waisa hi rahega)
