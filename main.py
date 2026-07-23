import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables se Token uthayega (Render par Environment Variable mein BOT_TOKEN set karein)
TOKEN = os.getenv("BOT_TOKEN", "8851943854:AAEflzhn0eOh4345gmekFRcZBgpn72REaqc")
WEBSITE_URL = "https://goldexpertfx.com/"

# --- START COMMAND ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    welcome_text = (
        f"👋 **Welcome to Gold Expert Fx AI, {user.first_name}!**\n\n"
        f"Your ultimate gateway for professional XAUUSD (Gold) market analysis, VIP signals, and account management services.\n\n"
        f"Choose an option below or visit our official website: {WEBSITE_URL}"
    )
    
    keyboard = [
        [InlineKeyboardButton("💎 VIP Packages", callback_data="vip_packages"),
         InlineKeyboardButton("📈 Account Management", callback_data="account_management")],
        [InlineKeyboardButton("🔗 Broker Guide & Setup", callback_data="broker_setup"),
         InlineKeyboardButton("👥 Community & Channels", callback_data="community")],
        [InlineKeyboardButton("🌐 Visit Website", url=WEBSITE_URL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# --- HELP COMMAND ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "🤖 **Gold Expert Fx Bot Commands:**\n\n"
        "/start - Launch the main menu\n"
        "/vip_packages - View active VIP membership plans\n"
        "/account_management - Learn about our account management services\n"
        "/broker_setup - Get broker registration and partner guide\n"
        "/community - Join our official discussion group\n"
        "/support - Connect with admin assistance"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

# --- VIP PACKAGES COMMAND ---
async def vip_packages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "💎 **VIP Membership Packages**\n\n"
        "Get high-accuracy XAUUSD trading signals and daily institutional market breakdowns.\n\n"
        f"👉 Select and purchase your package directly on our website: {WEBSITE_URL}"
    )
    keyboard = [[InlineKeyboardButton("🌐 Open VIP Store", url=WEBSITE_URL)]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- ACCOUNT MANAGEMENT COMMAND ---
async def account_management(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📈 **Professional Account Management**\n\n"
        "Let our expert traders manage your trading account with strict risk management and steady growth targets on Gold.\n\n"
        f"👉 Check terms and requirements on our website: {WEBSITE_URL}"
    )
    keyboard = [[InlineKeyboardButton("🌐 View Management Plans", url=WEBSITE_URL)]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- BROKER SETUP COMMAND ---
async def broker_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🔗 **Broker Account Setup & Guide**\n\n"
        "Follow our step-by-step registration guide and link your partner code to unlock exclusive benefits.\n\n"
        f"👉 Visit Broker Guide: {WEBSITE_URL}"
    )
    keyboard = [[InlineKeyboardButton("🌐 Open Broker Guide", url=WEBSITE_URL)]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- COMMUNITY COMMAND ---
async def community(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "👥 **Gold Expert Fx Community**\n\n"
        "Connect with fellow traders, share chart analysis, and discuss daily market trends.\n\n"
        f"👉 Join via website links: {WEBSITE_URL}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# --- SUPPORT COMMAND ---
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "💬 For any support or queries, please reach out through our official website or contact our admin team directly."
    keyboard = [[InlineKeyboardButton("🌐 Visit Support", url=WEBSITE_URL)]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- BUTTON CLICK HANDLER (CALLBACK QUERY) ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == "vip_packages":
        await vip_packages(query, context)
    elif query.data == "account_management":
        await account_management(query, context)
    elif query.data == "broker_setup":
        await broker_setup(query, context)
    elif query.data == "community":
        await community(query, context)

# --- MAIN FUNCTION ---
def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # Command Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("vip_packages", vip_packages))
    application.add_handler(CommandHandler("account_management", account_management))
    application.add_handler(CommandHandler("broker_setup", broker_setup))
    application.add_handler(CommandHandler("community", community))
    application.add_handler(CommandHandler("support", support))

    # Callback Query Handler for Inline Buttons
    application.add_handler(CallbackQueryHandler(button_handler))

    # Start the Bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
    
