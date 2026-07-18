from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = 'YOUR_BOT_TOKEN_HERE' # Apna token yahan dalen
ADMIN_ID = 7415265825          # Apni Telegram ID yahan dalen

# Database for users
user_registry = {}

# --- KEYBOARDS ---
def get_user_menu():
    keyboard = [
        [InlineKeyboardButton("📊 Account Management", callback_data="svc_acc")],
        [InlineKeyboardButton("💎 VIP Services", callback_data="svc_vip")],
        [InlineKeyboardButton("📈 Copy Trading", callback_data="svc_copy")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_keyboard():
    keyboard = [["👥 Users List", "⚙️ Status"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_registry[user.id] = user.username
    
    welcome_text = f"Welcome {user.first_name}! Gold Expert Fx mein khush amdeed."
    
    if user.id == ADMIN_ID:
        await update.message.reply_text("Admin Panel Active:", reply_markup=get_admin_keyboard())
    
    await update.message.reply_text(welcome_text, reply_markup=get_user_menu())

async def service_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    responses = {
        "svc_acc": "🛠 Account Management: Detail yahan hai...",
        "svc_vip": "💎 VIP Services: Join karne ke liye click karein...",
        "svc_copy": "📈 Copy Trading: Link: https://www.brokeraccountguide.com/"
    }
    await query.edit_message_text(responses.get(query.data, "Service unavailable."))

async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if update.effective_user.id != ADMIN_ID: return

    if text == "👥 Users List":
        user_list = "\n".join([f"{name} (@{uname})" for uname in user_registry.values()])
        await update.message.reply_text(f"Total Users: {len(user_registry)}\n\n{user_list}")

# --- MAIN ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(service_buttons, pattern="svc_"))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), admin_actions))
    
    print("Bot is running...")
    app.run_polling(drop_pending_updates=True)
    
