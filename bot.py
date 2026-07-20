from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Configuration ---
ADMIN_ID = "7415265825"
COMMUNITY_ID = "4477244119"
PRIVATE_CHANNEL_ID = "3870933647"

# --- 1. User Message to Admin Relay ---
async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.id != int(ADMIN_ID):
        # Admin ko forward karega
        await context.bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=update.message.chat.id,
            message_id=update.message.message_id
        )

# --- 2. Admin Reply to User ---
async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Agar admin kisi forwarded message ka reply karta hai
    if update.message.reply_to_message and update.message.chat.id == int(ADMIN_ID):
        original_user_id = update.message.reply_to_message.forward_from.id
        await context.bot.send_message(chat_id=original_user_id, text=update.message.text)

# --- 3. Join Request Approval (7-hour Delay) ---
async def approve_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.chat_join_request.user_id
    # 7 ghante (25200 seconds) baad approve karne ka job schedule karein
    context.job_queue.run_once(callback_approve, 25200, data={'user_id': user_id, 'chat_id': COMMUNITY_ID})

async def callback_approve(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.approve_chat_join_request(chat_id=job.data['chat_id'], user_id=job.data['user_id'])

# --- 4. Link Deletion Logic (Community Only) ---
async def filter_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.id == int(COMMUNITY_ID):
        # Admin ka ID check karein taake Owner ka message delete na ho
        if update.message.from_user.id != int(ADMIN_ID):
            if "t.me/" in update.message.text or "http" in update.message.text:
                await update.message.delete()
                
