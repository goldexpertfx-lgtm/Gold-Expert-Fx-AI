import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    ChatJoinRequestHandler, filters, ContextTypes
)

# --- CONFIGURATION (UPDATE THESE) ---
BOT_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"
ADMIN_ID = 7415265825  # Replace with your Telegram ID
COMMUNITY_ID = -3870933647 # Gold Expert Fx Community ID
PRIVATE_ID = -100987654321   # Gold Expert Fx Private Channel ID
OWNER_LINK = "https://t.me/GoldExpertFxCommunity"

logging.basicConfig(level=logging.INFO)

# --- 1. WELCOME & START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Notify Admin
    await context.bot.send_message(ADMIN_ID, f"🔔 New User:\nName: {user.full_name}\nID: {user.id}")
    # Welcome Message
    welcome = (
        f"✨ Bismillah! Welcome to Gold Expert Fx, {user.first_name}!\n\n"
        "Your message has been received by our management. "
        "We will get back to you shortly."
    )
    await update.message.reply_text(welcome)

# --- 2. JOIN REQUEST (7h DELAY) ---
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.chat_join_request.chat.id
    user_id = update.chat_join_request.user_id
    
    # Sirf Private Channel ke liye 7h delay
    if chat_id == PRIVATE_ID:
        context.job_queue.run_once(approve_user, 25200, data={'user_id': user_id, 'chat_id': chat_id})

async def approve_user(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.approve_chat_join_request(chat_id=job.data['chat_id'], user_id=job.data['user_id'])

# --- 3. STRICT LINK FILTERING (COMMUNITY ONLY) ---
async def filter_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = (msg.text or msg.caption or "").lower()
    
    # Check if Community and contains link
    if msg.chat.id == COMMUNITY_ID:
        # Check for link patterns
        if "http" in text or "t.me/" in text or "www." in text:
            # Bypass: Agar Admin hai ya Link aapka specific link hai
            if msg.from_user.id == ADMIN_ID or OWNER_LINK in text:
                return
            # Delete message
            await msg.delete()

# --- 4. RELAY SYSTEM (USER -> ADMIN) ---
async def relay_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Sirf private chat relay hogi
    if update.effective_chat.type == "private":
        await context.bot.forward_message(ADMIN_ID, update.effective_chat.id, update.message.message_id)

async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Sirf Admin reply relay karega
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.forward_from.id
        await context.bot.send_message(target_id, update.message.text)

if __name__ == '__main__':
    # Build Application
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    
    # Relay Handlers
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & (~filters.COMMAND), relay_to_admin))
    app.add_handler(MessageHandler(filters.Chat(ADMIN_ID) & filters.REPLY, reply_to_user))
    
    # Link Filter (Priority Order)
    app.add_handler(MessageHandler(filters.Chat(COMMUNITY_ID) & (filters.TEXT | filters.CAPTION), filter_links))
    
    # Run
    app.run_polling(drop_pending_updates=True)
    
