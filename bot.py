from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
# Apni ID yahan sahi se daalein
TOKEN = '8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4' 
ADMIN_ID = 7415265825          

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
    # User ko save kar rahe hain (username agar na ho to 'N/A' save hoga)
    user_registry[user.id] = user.username or user.first_name
    
    welcome_text = f"**Welcome to Gold Expert Fx, {user.first_name}!** 🥇\n\nHum aapki trading journey ko professional banane ke liye yahan hain."
    
    if user.id == ADMIN_ID:
        await update.message.reply_text("Admin Panel Active:", reply_markup=get_admin_keyboard())
    
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=get_user_menu())

async def service_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    responses = {
        "svc_acc": "🛠 **Account Management:**\nHum aapke account ko expert levels par manage karte hain. Contact: @MuhammadPrince7",
        "svc_vip": "💎 **VIP Services:**\nExclusive signals aur daily market analysis ke liye hamara VIP group join karein.",
        "svc_copy": "📈 **Copy Trading:**\nHamare trades ko auto-copy karein. Join link: https://www.brokeraccountguide.com/"
    }
    await query.edit_message_text(responses.get(query.data, "Service unavailable."), parse_mode="Markdown")

async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if update.effective_user.id != ADMIN_ID: 
        return

    if text == "👥 Users List":
        if not user_registry:
            await update.message.reply_text("Abhi tak koi user nahi hai.")
        else:
            list_str = "\n".join([f"• {name}" for name in user_registry.values()])
            await update.message.reply_text(f"**Total Users: {len(user_registry)}**\n\n{list_str}", parse_mode="Markdown")
            
    elif text == "⚙️ Status":
        await update.message.reply_text("Bot status: Online & Working perfectly! ✅")

# --- MAIN ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(service_buttons, pattern="svc_"))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), admin_actions))
    
    print("Bot is running successfully...")
    app.run_polling(drop_pending_updates=True)
    
