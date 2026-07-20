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
PRIVATE_ID = -3870933647   # Replace with Private ID
OWNER_LINK = "https://t.me/GoldExpertFxCommunity"

logging.basicConfig(level=logging.INFO)

# --- 1. FAST LINK DELETION (Priority 0) ---
async def filter_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    # Text ya Caption dono mein check karein
    text = (msg.text or msg.caption or "").lower()
    
    # Check if inside community
    if msg.chat.id == COMMUNITY_ID:
        # Check for link patterns
        if "http" in text or "t.me/" in text or "www." in text:
            # Bypass: Agar Admin hai ya Link aapka official link hai
            if msg.from_user.id == ADMIN_ID or OWNER_LINK in text:
                return
            # Delete instantly
            await msg.delete()

# --- 2. START & WELCOME ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Admin Alert
    await context.bot.send_message(ADMIN_ID, f"🔔 New User: {user.full_name} (@{user.username}) joined.")
    # Professional Welcome
    await update.message.reply_text(
        f"✨ Bismillah! Welcome to Gold Expert Fx, {user.first_name}!\n\n"
        "Your request is received. Our management will assist you shortly."
    )

# --- 3. JOIN REQUEST (7h DELAY) ---
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.chat_join_request.chat.id == PRIVATE_ID:
        context.job_queue.run_once(approve_user, 25200, data={
            'user_id': update.chat_join_request.user_id, 
            'chat_id': PRIVATE_ID
        })

async def approve_user(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.approve_chat_join_request(
        chat_id=context.job.data['chat_id'], 
        user_id=context.job.data['user_id']
    )

# --- 4. RELAY ---
async def relay_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await context.bot.forward_message(ADMIN_ID, update.effective_chat.id, update.message.message_id)

async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        target = update.message.reply_to_message.forward_from.id
        await context.bot.send_message(target, update.message.text)

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Priority 0: Link Filter (Sabse pehle ye chalega)
    app.add_handler(MessageHandler(filters.Chat(COMMUNITY_ID) & (filters.TEXT | filters.CAPTION), filter_links), group=0)
    
    # Baki Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & (~filters.COMMAND), relay_to_admin))
    app.add_handler(MessageHandler(filters.Chat(ADMIN_ID) & filters.REPLY, reply_to_user))
    
    app.run_polling(drop_pending_updates=True)
    
