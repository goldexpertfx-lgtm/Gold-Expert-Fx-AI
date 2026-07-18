import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- Configuration ---
TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 7415265825  # Aapki ID
PARTNER_LINK = "https://www.brokeraccountguide.com/"
SUPPORT_LINK = "https://t.me/MuhammadPrince7"

# --- Data Stores ---
user_registry = {}  # {user_id: user_info}
reply_targets = {}  # {admin_id: target_user_id}

logging.basicConfig(level=logging.INFO)

# --- Admin Keyboard ---
def get_admin_keyboard():
    keyboard = [
        [KeyboardButton("👥 Users List"), KeyboardButton("✏️ Edit Start Text")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# ===== START FUNCTION =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_registry[user.id] = user  # User ko list mein add kiya

    # Admin check
    if user.id == ADMIN_ID:
        await update.message.reply_text("Welcome Admin, Gold Expert Fx Control Panel:", reply_markup=get_admin_keyboard())
    else:
        welcome_text = f"**Hey, {user.first_name}!** 👋\nWelcome to Broker Account Guide Bot!"
        await update.message.reply_text(welcome_text, parse_mode="Markdown")

# ===== ADMIN BUTTON HANDLERS =====
async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    if user.id != ADMIN_ID: return

    if text == "👥 Users List":
        buttons = []
        for uid, uinfo in user_registry.items():
            buttons.append([InlineKeyboardButton(f"{uinfo.first_name} (@{uinfo.username or 'NoUser'})", callback_data=f"user_{uid}")])
        
        await update.message.reply_text("Select a user to manage:", reply_markup=InlineKeyboardMarkup(buttons))

    elif text == "✏️ Edit Start Text":
        await update.message.reply_text("Feature coming soon! (Database update required)")

# ===== USER DASHBOARD (Admin Only) =====
async def user_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("user_"):
        target_id = int(query.data.split("_")[1])
        reply_targets[update.effective_user.id] = target_id # Admin ka target set kiya
        uinfo = user_registry.get(target_id)
        
        msg = f"👤 **Dashboard: {uinfo.first_name}**\nID: `{target_id}`\n\nSend a message here, and I will forward it to the user."
        await query.edit_message_text(msg, parse_mode="Markdown")

# ===== MESSAGE HANDLER =====
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    # 1. Agar Admin kisi ko reply kar raha hai
    if user.id == ADMIN_ID and user.id in reply_targets:
        target_id = reply_targets[user.id]
        try:
            await context.bot.send_message(chat_id=target_id, text=f"📢 **Message from Admin:**\n\n{text}")
            await update.message.reply_text("✅ Message sent to user!")
        except:
            await update.message.reply_text("❌ Could not send message (User might have blocked bot).")
        return

    # 2. General User flow (Save user and notify admin)
    user_registry[user.id] = user
    await update.message.reply_text("✅ Received! Our team will verify this shortly.")
    
    # Notify Admin
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 **New Msg from {user.first_name}**:\n{text}")
    except: pass

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(user_dashboard))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), admin_actions)) # Keyboard buttons
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    
    print("Bot is running...")
    app.run_polling()
        
