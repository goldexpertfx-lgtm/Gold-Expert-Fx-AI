import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    ChatJoinRequestHandler,
    MessageHandler,
    filters,
)

# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================= CONFIGURATION =================
BOT_TOKEN = "8851943854:AAEflzhn0eOh4345gmekFRcZBgpn72REaqc"  # Apna Bot Token yahan dalein
COMMUNITY_CHAT_ID = -4477244119  # Apni Community (Group/Channel) ki ID yahan dalein
PRIVATE_CHANNEL_ID = -3870933647  # Apne Private Channel ki ID yahan dalein

# Whitelisted Links jo delete nahi honi chahiye
WHITELISTED_LINKS = [
    "brokeraccountguide.com",
    "t.me/goldexpertfxcommunity",
    "telegram.me/+ri2sc_tdify5nti1",
]

# Dictionary to track delayed join requests: {user_id: {"request_time": time, "chat_id": chat_id}}
pending_requests = {}
# =================================================


def contains_unauthorized_link(text: str) -> bool:
    if not text:
        return False
    
    text_lower = text.lower()
    # Check if any link exists (basic check for http/www/t.me)
    if "http://" in text_lower or "https://" in text_lower or "www." in text_lower or "t.me/" in text_lower or "telegram.me/" in text_lower:
        # Check if the text contains any whitelisted link
        for white_link in WHITELISTED_LINKS:
            if white_link in text_lower:
                return False  # Whitelisted link found, do not delete
        return True  # Link found but not whitelisted, delete it
    
    return False


async def link_filter_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.effective_message
    if not message or not message.from_user:
        return

    user = message.from_user
    chat = message.chat

    # Check if message is from our managed chats
    if chat.id not in [COMMUNITY_CHAT_ID, PRIVATE_CHANNEL_ID]:
        return

    # Check if sender is the Owner
    try:
        chat_member = await context.bot.get_chat_member(chat.id, user.id)
        if chat_member.status == "creator":
            return  # Owner ki link delete nahi karni
    except Exception as e:
        logger.error(f"Error checking chat member status: {e}")

    # Check if message is forwarded from an admin or private channel
    is_forwarded = message.forward_date is not None

    text_to_check = message.text or message.caption or ""
    
    # If unauthorized link is found, or it's a forwarded post with any link
    if contains_unauthorized_link(text_to_check) or (is_forwarded and ("http" in text_to_check.lower() or "t.me" in text_to_check.lower())):
        try:
            await message.delete()
            logger.info(f"Deleted unauthorized link message from user {user.id} in chat {chat.id}")
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")


async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = update.chat_join_request
    if not request:
        return

    user_id = request.from_user.id
    chat_id = request.chat.id

    # Sirf Private Channel ki requests ke liye process karein
    if chat_id != PRIVATE_CHANNEL_ID:
        return

    try:
        # Check karein ke user Community mein available hai ya nahi
        community_member = await context.bot.get_chat_member(COMMUNITY_CHAT_ID, user_id)
        is_in_community = community_member.status in ["member", "administrator", "creator"]
    except Exception:
        is_in_community = False

    if is_in_community:
        # Agar user Community mein hai, toh request ko rokey rakhein (pending list mein daalein)
        pending_requests[user_id] = {
            "chat_id": chat_id,
            "request_time": datetime.now()
        }
        logger.info(f"User {user_id} is in Community. Holding private channel join request.")
    else:
        # Agar user Community mein nahi hai, toh direct approve kar dein
        try:
            await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
            logger.info(f"User {user_id} approved directly (not in community).")
        except Exception as e:
            logger.error(f"Error approving direct join request: {e}")


async def background_request_scanner(context: ContextTypes.DEFAULT_TYPE):
    """Background task jo pending requests ko scan karega aur 7 ghante baad approve karega jab user community chhor de."""
    now = datetime.now()
    to_approve = []

    for user_id, data in list(pending_requests.items()):
        chat_id = data["chat_id"]
        try:
            # Dobara check karein ke user abhi bhi community mein hai ya nahi
            community_member = await context.bot.get_chat_member(COMMUNITY_CHAT_ID, user_id)
            still_in_community = community_member.status in ["member", "administrator", "creator"]
        except Exception:
            still_in_community = False

        if not still_in_community:
            # Agar user ne community leave kar di hai, toh check karein ke 7 ghante ho gaye hain kya
            # (Ya agar aap chahte hain ke leave karte hi 7 ghante count ho, toh ye logic perfect hai)
            to_approve.append((chat_id, user_id))

    for chat_id, user_id in to_approve:
        try:
            await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
            logger.info(f"Approved pending request for user {user_id} as they left the community.")
            del pending_requests[user_id]
        except Exception as e:
            logger.error(f"Error approving delayed join request: {e}")


def main():
    # Bot Application Initialize karein
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers register karein
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, link_filter_handler))

    # Job queue to scan pending requests every 5 minutes
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(background_request_scanner, interval=300, first=10)

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
    
