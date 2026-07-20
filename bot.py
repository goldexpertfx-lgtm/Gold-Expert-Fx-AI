import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    ChatJoinRequestHandler, filters, ContextTypes
)

# --- CONFIGURATION (Yahan apni Details daalein) ---
BOT_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"
ADMIN_ID = 7415265825  # Apni Telegram ID yahan likhein
COMMUNITY_ID = -4477244119  # Gold Expert Fx Community ID
PRIVATE_CHANNEL_ID = -3870933647 # Private Channel ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 1. Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to Gold Expert Fx! Aapka message hamein mil gaya hai, hum jald hi reply karenge.")

# 2. User to Admin Relay
async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        # User ka message Admin ko forward karein
        await context.bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )

# 3. Admin to User Reply
async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == ADMIN_ID and update.message.reply_to_message:
        # Reply ko original user ko send karein
        target_user_id = update.message.reply_to_message.forward_from.id
        await context.bot.send_message(chat_id=target_user_id, text=update.message.text)

# 4. Join Request (7-hour Delay)
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.chat_join_request.user_id
    # 7 ghante = 25200 seconds
    context.job_queue.run_once(approve_user, 25200, data={'user_id': user_id, 'chat_id': update.chat_join_request.chat.id})

async def approve_user(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.approve_chat_join_request(chat_id=job.data['chat_id'], user_id=job.data['user_id'])

# 5. Link Filter (Sirf Community mein)
async def filter_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Sirf Community ID check karein
    if update.effective_chat.id == COMMUNITY_ID:
        # Agar sender Admin nahi hai, toh link check karein
        if update.effective_user.id != ADMIN_ID:
            msg_text = update.message.text or update.message.caption or ""
            if "t.me/" in msg_text or "http" in msg_text:
                await update.message.delete()

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
    application.add_handler(MessageHandler(filters.Chat(ADMIN_ID) & filters.REPLY, reply_to_user))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.Chat(ADMIN_ID)), forward_to_admin))
    application.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, filter_links))
    
    application.run_polling()
    
