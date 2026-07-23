import os
import logging
import asyncio
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
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

TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "YOUR_TELEGRAM_OWNER_ID"))
COMMUNITY_CHAT_ID = os.getenv("COMMUNITY_CHAT_ID", "@GoldExpertFxCommunity")
PRIVATE_CHANNEL_ID = os.getenv("PRIVATE_CHANNEL_ID", "YOUR_PRIVATE_CHANNEL_ID")
WEBSITE_URL = "https://goldexpertfx.com/"

# Pending requests save karne ke liye file name
PENDING_FILE = "pending_requests.json"

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

# --- DATABASE / JSON FUNCTIONS FOR PERSISTENCE ---
def load_pending_requests():
    if os.path.exists(PENDING_FILE):
        try:
            with open(PENDING_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_pending_requests(data):
    try:
        with open(PENDING_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving pending requests: {e}")

# --- START COMMAND ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_text = "Join Our Channel For Daily 5-7 XAUUSD GOLD Signals 👇👇"
    keyboard = [[InlineKeyboardButton("🌐 Visit Website", url=WEBSITE_URL)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# --- 1. JOIN REQUEST APPROVAL LOGIC ---
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_join_request = update.chat_join_request
    user = chat_join_request.from_user
    chat = chat_join_request.chat

    if str(chat.id) != str(PRIVATE_CHANNEL_ID):
        return

    is_in_community = False
    try:
        member = await context.bot.get_chat_member(chat_id=COMMUNITY_CHAT_ID, user_id=user.id)
        if member.status in ["member", "administrator", "creator"]:
            is_in_community = True
    except Exception:
        is_in_community = False

    if not is_in_community:
        # Agar user community mein NAHI hai -> Turant approve kar do
        try:
            await chat_join_request.approve()
            logger.info(f"User {user.first_name} community mein nahi tha, request instantly approved.")
        except Exception as e:
            logger.error(f"Error approving request instantly: {e}")
    else:
        # Agar user community mein HAI -> Pending mein daal do
        logger.info(f"User {user.first_name} community mein hai, request pending mein chali gayi.")
        
        pending_data = load_pending_requests()
        user_key = str(user.id)
        
        if user_key not in pending_data:
            pending_data[user_key] = {
                "chat_id": chat.id,
                "user_id": user.id,
                "name": user.first_name,
                "left_timestamp": None
            }
            save_pending_requests(pending_data)

async def background_pending_checker(application: Application):
    """
    Yeh background loop check karega:
    - Agar user ne community leave kar di hai, toh 7 ghante baad request automatically approve ho jayegi.
    """
    await asyncio.sleep(15)
    while True:
        try:
            pending_data = load_pending_requests()
            if pending_data:
                updated_data = pending_data.copy()
                bot = application.bot
                current_time = datetime.now()

                for user_key, info in pending_data.items():
                    user_id = info["user_id"]
                    chat_id = info["chat_id"]
                    
                    try:
                        member = await bot.get_chat_member(chat_id=COMMUNITY_CHAT_ID, user_id=user_id)
                        still_in_community = member.status in ["member", "administrator", "creator"]
                    except Exception:
                        still_in_community = False

                    if still_in_community:
                        updated_data[user_key]["left_timestamp"] = None
                    else:
                        if updated_data[user_key]["left_timestamp"] is None:
                            updated_data[user_key]["left_timestamp"] = current_time.isoformat()
                            logger.info(f"User {user_id} ne community leave kar di. 7 ghante ka timer start!")
                        else:
                            left_time = datetime.fromisoformat(updated_data[user_key]["left_timestamp"])
                            time_diff = current_time - left_time

                            if time_diff >= timedelta(hours=7):
                                try:
                                    await bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
                                    logger.info(f"User {user_id} ko community leave kiye 7+ hours ho gaye, successfully approved!")
                                    del updated_data[user_key]
                                except Exception as e:
                                    logger.error(f"Approval error for user {user_id}: {e}")
                                    del updated_data[user_key]

                save_pending_requests(updated_data)

        except Exception as e:
            logger.error(f"Error in background pending checker loop: {e}")

        await asyncio.sleep(600)


# --- 2. AUTO DELETE TELEGRAM LINKS LOGIC ---
async def delete_links_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

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
        is_whitelisted = any(wl in text_to_check for wl in WHITELIST_URLS)
        
        if not is_whitelisted:
            try:
                await message.delete()
                logger.info("Deleted unauthorized Telegram link message immediately.")
            except Exception as e:
                logger.error(f"Failed to delete link: {e}")


# --- 3. USER SUPPORT SYSTEM (WhatsApp Style Bridge) ---
async def owner_user_bridge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.from_user:
        return

    # Channel ke messages ko ignore karein taake duplicate forward na ho
    if message.chat.type == "channel":
        return

    user = message.from_user
    
    if user.id == OWNER_ID and message.reply_to_message:
        replied_msg = message.reply_to_message
        if replied_msg.forward_from:
            target_user_id = replied_msg.forward_from.id
            try:
                await context.bot.send_message(chat_id=target_user_id, text=message.text)
                await message.reply_text("✅ Reply sent to user.")
            except Exception as e:
                await message.reply_text(f"❌ Failed to send reply: {e}")
        return

    if user.id != OWNER_ID:
        try:
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

    application.add_handler(CommandHandler("start", start))
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, lambda u, c: asyncio.gather(
        delete_links_handler(u, c),
        owner_user_bridge(u, c)
    )))

    async def post_init(app: Application):
        asyncio.create_task(background_pending_checker(app))

    application.post_init = post_init

    print("Bot is up and running successfully!")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
    
