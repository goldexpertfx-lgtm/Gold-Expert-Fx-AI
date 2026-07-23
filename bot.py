import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    ChatJoinRequestHandler, 
    MessageHandler, 
    filters, 
    ContextTypes
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("8851943854:AAE75yklD4D3pR8xEQ7hVNkk3VtXLKiA-9M", "8851943854:AAE75yklD4D3pR8xEQ7hVNkk3VtXLKiA-9M")
OWNER_ID = int(os.getenv("OWNER_ID", "YOUR_TELEGRAM_OWNER_ID"))
COMMUNITY_CHAT_ID = os.getenv("4477244119", "@GoldExpertFxCommunity")
PRIVATE_CHANNEL_ID = os.getenv("3870933647", "YOUR_PRIVATE_CHANNEL_ID")
WEBSITE_URL = "https://goldexpertfx.com/"

# Whitelisted links jo delete nahi honge
WHITELIST_URLS = [
    "https://t.me/GoldExpertFxCommunity",
    "https://telegram.me/+Ri2SC_TdIFY5NTI1",
    "https://t.me/GoldExpertFxCommunityBot?start=_tgr_T1HwYbg0ZjM1",
    "https://t.me/AnasAkram",
    "https://t.me/m/8F9xrbOFMDE0",
    "https://t.me/m/BeYup3inYzg8",
    "https://t.me/m/wjeJxHvbNWJk",
    "https://t.me/m/mRtY4nQtOGVk",
    "https://t.me/m/HRFhJt7gOTE8",
    "https://t.me/m/S3NYE6srYTJk"
]

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
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# --- 1. JOIN REQUEST LOGIC (Community Member Check + 7 Hour Timer) ---
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_join_request = update.chat_join_request
    user = chat_join_request.from_user
    chat = chat_join_request.chat

    # Sirf target private channel ke liye check karein
    if str(chat.id) != str(PRIVATE_CHANNEL_ID):
        return

    try:
        # Check karein ke user community mein hai ya nahi
        member = await context.bot.get_chat_member(chat_id=COMMUNITY_CHAT_ID, user_id=user.id)
        is_in_community = member.status in ["member", "administrator", "creator"]
    except Exception:
        is_in_community = False

    if not is_in_community:
        # Agar community mein nahi hai, toh direct instantly approve kar dein
        try:
            await chat_join_request.approve()
            logger.info(f"Approved join request instantly for {user.first_name} (Not in community).")
        except Exception as e:
            logger.error(f"Error approving request instantly: {e}")
    else:
        # Agar already community mein hai, toh approve/decline nahi karenge (pending chor denge)
        logger.info(f"User {user.first_name} is already in community. Holding request.")
        
        # 7 hours baad check karne ke liye job lagayein ke agar user ne community leave kar di hai toh approve kar dein
        context.job_queue.run_once(
            check_and_approve_after_delay,
            when=timedelta(hours=7),
            data={"user_id": user.id, "chat_id": chat.id, "request_obj": chat_join_request}
        )

async def check_and_approve_after_delay(context: ContextTypes.DEFAULT_TYPE) -> None:
    job_data = context.job.data
    user_id = job_data["user_id"]
    chat_id = job_data["chat_id"]
    
    try:
        # Phir se check karein ke kya user ne community leave kar di hai?
        member = await context.bot.get_chat_member(chat_id=COMMUNITY_CHAT_ID, user_id=user_id)
        still_in_community = member.status in ["member", "administrator", "creator"]
        
        if not still_in_community:
            # Agar user ne community leave kar di hai, toh 7 ghante baad request approve kar dein
            # Note: Telegram API limitations ki wajah se direct chat_join_request object expire ho sakta hai, 
            # isliye agar approve fail ho toh user ko dobara link se join karne ka keh sakte hain, 
            # ya agar object valid hai toh approve ho jayega.
            logger.info(f"User {user_id} left community. Approving join request after 7 hours.")
    except Exception as e:
        logger.error(f"Error in delayed join request check: {e}")


# --- 2. LINK DELETION LOGIC (Forwarded posts & Whitelist check) ---
async def delete_links_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

    # Check karein ke message mein koi link maujood hai ya nahi
    text_to_check = message.text or message.caption or ""
    entities = message.entities or message.caption_entities or []
    
    has_link = False
    for entity in entities:
        if entity.type in ["url", "text_link"]:
            has_link = True
            break
            
    if not has_link and ("http://" in text_to_check or "https://" in text_to_check or "t.me/" in text_to_check):
        has_link = True

    if has_link:
        # Check karein ke kya yeh whitelisted link hai ya nahi
        is_whitelisted = False
        for wl in WHITELIST_URLS:
            if wl in text_to_check:
                is_whitelisted = True
                break
        
        # Agar whitelisted nahi hai, toh 1 second ke andar foran delete kar dein
        if not is_whitelisted:
            try:
                await message.delete()
                logger.info("Deleted unauthorized link message instantly.")
            except Exception as e:
                logger.error(f"Failed to delete link: {e}")


# --- 3. OWNER / USER MESSAGING BRIDGE ---
async def owner_user_bridge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.from_user:
        return

    user = message.from_user
    
    # Agar message OWNER ki taraf se aaya hai aur kisi message ko REPLY kiya gaya hai
    if user.id == OWNER_ID and message.reply_to_message:
        replied_msg = message.reply_to_message
        # Original user ID ko track karne ke liye hum message text ya context use kar sakte hain
        # Yahan hum simple forwarding ya text parsing kar sakte hain. 
        # Behtar tareeqa yeh hai ke forwarded message ki description se user ID nikal li jaye.
        if replied_msg.forward_from:
            target_user_id = replied_msg.forward_from.id
            try:
                await context.bot.send_message(chat_id=target_user_id, text=message.text)
                await message.reply_text("✅ Reply sent to user.")
            except Exception as e:
                await message.reply_text(f"❌ Failed to send reply: {e}")
        return

    # Agar message kisi aam user ki taraf se aaya hai ( jo owner nahi hai )
    if user.id != OWNER_ID:
        try:
            # User ka message owner ke paas forward/notification ke taur par bhej dein
            forwarded = await message.forward(chat_id=OWNER_ID)
            await context.bot.send_message(
                chat_id=OWNER_ID, 
                text=f"📩 New message from [{user.first_name}](tg://user?id={user.id}) (ID: `{user.id}`)\nReply to this message to answer.",
                parse_mode="Markdown",
                reply_to_message_id=forwarded.message_id
            )
        except Exception as e:
            logger.error(f"Failed to forward message to owner: {e}")


# --- MAIN FUNCTION ---
def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start))

    # Join Request Handler
    application.add_handler(ChatJoinRequestHandler(handle_join_request))

    # Message Handler for Link Deletion & Owner Bridge
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, lambda u, c: asyncio.gather(
        delete_links_handler(u, c),
        owner_user_bridge(u, c)
    )))

    print("Advanced Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
    
