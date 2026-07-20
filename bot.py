import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ChatJoinRequestHandler, filters, ContextTypes

# --- CONFIG ---
BOT_TOKEN = "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4"
ADMIN_ID = 7415265825 
COMMUNITY_ID = -4477244119 
PRIVATE_ID = -3870933647   
OWNER_LINK = "https://t.me/GoldExpertFxCommunity"

logging.basicConfig(level=logging.INFO)

# --- 1. WELCOME MESSAGE (English) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Notify Admin
    await context.bot.send_message(ADMIN_ID, f"🔔 New User: {user.full_name} (@{user.username}) started the bot.")
    # Welcome User
    welcome_text = (
        f"✨ Bismillah! Welcome to Gold Expert Fx, {user.first_name}!\n\n"
        "We are glad to have you. Your message has been received by our management. "
        "We will get back to you shortly. Stay tuned!"
    )
    await update.message.reply_text(welcome_text)

# --- 2. LINK FILTERING (Strict) ---
async def filter_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    # Sirf Community ID mein delete karein
    if msg.chat.id == COMMUNITY_ID:
        if msg.text and ("http" in msg.text or "t.me/" in msg.text):
            # Agar Owner ka link hai, toh rehne dein
            if msg.from_user.id == ADMIN_ID and OWNER_LINK in msg.text:
                return
            # Baaki sab delete
            await msg.delete()

# --- 3. RELAY ONLY USER MESSAGES ---
async def relay_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Sirf Private messages relay karein, channel posts nahi
    if update.effective_chat.id > 0: 
        await context.bot.forward_message(ADMIN_ID, update.effective_chat.id, update.message.message_id)

async def reply_from_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.forward_from.id
        await context.bot.send_message(target_id, update.message.text)

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    # Relay sirf tab karein jab user bot ko message kare (Private Chat)
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & (~filters.Command()), relay_to_admin))
    app.add_handler(MessageHandler(filters.Chat(ADMIN_ID) & filters.REPLY, reply_from_admin))
    # Links filter
    app.add_handler(MessageHandler(filters.Chat(COMMUNITY_ID) & (filters.TEXT | filters.CAPTION), filter_links))
    
    app.run_polling()
    
