import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ChatJoinRequestHandler, filters, ContextTypes

# --- CONFIGURATION ---
BOT_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"
ADMIN_ID = 7415265825  # Apni ID
COMMUNITY_ID = -4477244119 # Community Channel ID
PRIVATE_ID = -3870933647   # Private Channel ID
OWNER_LINK = "https://t.me/GoldExpertFxCommunity"

logging.basicConfig(level=logging.INFO)

# --- DATABASE (Simple Memory) ---
# Yahan hum store karenge ki kaun community mein hai
community_members = set()

# --- 1. START & WELCOME ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Admin ko notification
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🆕 New User Started Bot:\nName: {user.full_name}\nUsername: @{user.username}\nID: {user.id}"
    )
    # User ko Welcome
    await update.message.reply_text("✨ Bismillah! Gold Expert Fx mein khush amdeed. Aapka message humein mil gaya hai, hum jald raabta karenge.")

# --- 2. JOIN REQUEST LOGIC ---
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.chat_join_request.user_id
    chat_id = update.chat_join_request.chat.id

    if chat_id == PRIVATE_ID:
        # Check agar user Community mein hai
        if user_id in community_members:
            # Community mein hai toh 7h ka wait
            context.job_queue.run_once(approve_user, 25200, data={'user_id': user_id, 'chat_id': chat_id})
        else:
            # Nahi hai toh instant approve
            await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)

async def approve_user(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.approve_chat_join_request(chat_id=job.data['chat_id'], user_id=job.data['user_id'])

# --- 3. LINK FILTERING (STRICT) ---
async def filter_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    # Check if link exists
    if msg.text and ("t.me/" in msg.text or "http" in msg.text):
        # Allow only if sender is Admin AND link is exactly OWNER_LINK
        if msg.from_user.id == ADMIN_ID and msg.text.strip() == OWNER_LINK:
            return 
        # Otherwise delete EVERYTHING (private or community)
        await msg.delete()

# --- 4. RELAY LOGIC ---
async def relay_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)

async def reply_from_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.forward_from.id
        await context.bot.send_message(chat_id=target_id, text=update.message.text)

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.Chat(ADMIN_ID)), relay_to_admin))
    app.add_handler(MessageHandler(filters.Chat(ADMIN_ID) & filters.REPLY, reply_from_admin))
    app.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, filter_links))
    
    app.run_polling()
    
