import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    ChatJoinRequestHandler, filters, ContextTypes
)

# --- CONFIGURATION ---
BOT_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"
ADMIN_ID = 7415265825  # Replace with your ID
COMMUNITY_ID = -4477244119 # Replace with Community ID
PRIVATE_ID = -3870933647   # Replace with Private Channel ID
OWNER_LINK = "https://t.me/GoldExpertFxCommunity"

logging.basicConfig(level=logging.INFO)

# --- 1. WELCOME MESSAGE ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Admin Notification
    await context.bot.send_message(ADMIN_ID, f"🆕 New User Started Bot:\nName: {user.full_name}\nID: {user.id}")
    # User Welcome
    await update.message.reply_text(
        "✨ Bismillah! Welcome to Gold Expert Fx.\n\n"
        "Your message has been received by the management. "
        "We will get back to you shortly."
    )

# --- 2. JOIN REQUEST (7h Logic) ---
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.chat_join_request.user_id
    chat_id = update.chat_join_request.chat.id
    
    # Agar Private Channel ki request hai
    if chat_id == PRIVATE_ID:
        # Note: 'community_members' check karne ke liye bot ko group mein admin hona chahiye
        # Filhal, 7 ghante ka wait har kisi ke liye
        context.job_queue.run_once(approve_user, 25200, data={'user_id': user_id, 'chat_id': chat_id})

async def approve_user(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.approve_chat_join_request(chat_id=job.data['chat_id'], user_id=job.data['user_id'])

# --- 3. STRICT LINK FILTERING ---
async def filter_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    # Sirf Community mein check karein
    if msg.chat.id == COMMUNITY_ID:
        # Check for any link
        if "http" in msg.text or "t.me/" in msg.text or "www." in msg.text:
            # Agar Owner hai ya Link aapka official hai, toh allow karein
            if msg.from_user.id == ADMIN_ID or OWNER_LINK in msg.text:
                return
            # Baaki sab delete
            await msg.delete()

# --- 4. RELAY LOGIC ---
async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Sirf Private messages relay (User -> Bot -> Admin)
    if update.effective_chat.type == "private":
        await context.bot.forward_message(ADMIN_ID, update.effective_chat.id, update.message.message_id)

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        target = update.message.reply_to_message.forward_from.id
        await context.bot.send_message(target, update.message.text)

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    # Relay Handlers
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & (~filters.COMMAND), relay))
    app.add_handler(MessageHandler(filters.Chat(ADMIN_ID) & filters.REPLY, reply))
    # Link Filter - Text aur Captions dono ke liye
    app.add_handler(MessageHandler(filters.Chat(COMMUNITY_ID) & (filters.TEXT | filters.CAPTION), filter_links))
    
    app.run_polling()
    
