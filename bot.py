import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- Configuration ---
TOKEN = os.environ.get("BOT_TOKEN") # Render ke Environment Variables mein BOT_TOKEN set karein
ADMIN_ID = 7415265825 # Yahan apni Telegram ID dalen taaki notification mile
PARTNER_LINK = "https://www.brokeraccountguide.com/"
SUPPORT_LINK = "https://t.me/MuhammadPrince7"

logging.basicConfig(level=logging.INFO)

# ===== START FUNCTION =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"**Hey, {user.first_name}!** 👋\n\n"
        "Welcome to Broker Account Guide Bot!\n\n"
        "Choose your status below:"
    )
    inline_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🆕 New User", callback_data='new_here')],
        [InlineKeyboardButton("🔄 Existing User", callback_data='old_here')],
        [InlineKeyboardButton("🌐 From Website", callback_data='from_website')]
    ])
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=welcome_text, reply_markup=inline_kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text=welcome_text, reply_markup=inline_kb, parse_mode="Markdown")

# ===== BUTTON HANDLER =====
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "start_again": await start(update, context)
    
    elif data == "new_here":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Join Now", url=PARTNER_LINK)], [InlineKeyboardButton("🔙 Back", callback_data="start_again")]])
        await query.edit_message_text("Register using our partner link:", reply_markup=kb)

    elif data == "old_here":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("📩 Contact Support", url=SUPPORT_LINK)], [InlineKeyboardButton("🔙 Back", callback_data="start_again")]])
        await query.edit_message_text("Need help? Contact support:", reply_markup=kb)

    elif data == "from_website":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Registered", callback_data="registered"), InlineKeyboardButton("🔁 Changed IB", callback_data="changed_ib")],
            [InlineKeyboardButton("🔙 Back", callback_data="start_again")]
        ])
        await query.edit_message_text("Select your status:", reply_markup=kb)

    elif data in ["registered", "changed_ib"]:
        msg = "✅ **Detail Received!**\n\nPlease send your **Trading Account ID** in this chat."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="from_website")]])
        await query.edit_message_text(msg, reply_markup=kb, parse_mode="Markdown")

# ===== MESSAGE HANDLER (Notifications for Admin) =====
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    
    # 1. User ko reply
    await update.message.reply_text("✅ **Received!** Our team will verify your details shortly.")
    
    # 2. Admin (Prince) ko Notification bheje
    notification = (
        f"🔔 **New Message Received**\n\n"
        f"👤 **User:** {user.first_name} (@{user.username})\n"
        f"🆔 **ID:** `{user.id}`\n"
        f"💬 **Content:** {text}"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=notification, parse_mode="Markdown")
    except Exception as e:
        print(f"Failed to notify admin: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    
    print("Bot is running...")
    app.run_polling()
    
