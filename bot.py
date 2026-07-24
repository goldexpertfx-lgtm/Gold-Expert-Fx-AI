import asyncio
import logging
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Configure logging
logging.basicConfig(level=logging.INFO)

# --- CONFIGURATION ---
API_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace with your Telegram Bot Token
OWNER_ID = 7415265825  # Owner Telegram User ID

COMMUNITY_USERNAME = "GoldExpertFxCommunity"  # Without @ or full link depending on checks
COMMUNITY_ID_OR_USERNAME = "@GoldExpertFxCommunity"
PRIVATE_CHANNEL_LINK = "https://telegram.me/+Ri2SC_TdIFY5NTI1"

WHITESLISTED_DOMAINS = [
    "t.me/GoldExpertFxCommunity",
    "goldexpertfx.com",
    "brokeraccountguide.com",
    "t.me/AnasAkram",
    "https://telegram.me/+Ri2SC_TdIFY5NTI1",
]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()

# In-memory storage for tracking pending approvals after leaving (In production, use a database like SQLite/PostgreSQL)
pending_leave_cache = {}  # {user_id: target_chat_id}


# Helper: Check if user is a member of the community
async def is_user_in_community(user_id: int) -> bool:
  try:
    member = await bot.get_chat_member(
        chat_id=COMMUNITY_ID_OR_USERNAME, user_id=user_id
    )
    if member.status in ["member", "administrator", "creator"]:
      return True
  except Exception as e:
    logging.error(f"Error checking community membership: {e}")
  return False


# 1. JOIN REQUEST HANDLER
@router.chat_join_request()
async def handle_join_request(
    join_request: types.ChatJoinRequest,
):
  user_id = join_request.from_user.id
  chat_id = join_request.chat.id

  # Check if user is in community
  in_community = await is_user_in_community(user_id)

  if in_community:
    # Keep pending indefinitely. Store for delayed approval when they leave.
    pending_leave_cache[user_id] = chat_id
    return  # Do nothing, let it stay pending
  else:
    # If not in community or brand new, approve instantly (1 second delay simulated or direct)
    await asyncio.sleep(1)
    try:
      await bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
    except Exception as e:
      logging.error(f"Failed to approve request: {e}")


# Background task to monitor user leaving community and trigger 5-7 hour delay approval
async def monitor_community_leaves():
  while True:
    await asyncio.sleep(600)  # Check every 10 minutes
    for user_id, chat_id in list(pending_leave_cache.items()):
      still_in = await is_user_in_community(user_id)
      if not still_in:
        # User left the community! Trigger 5-7 hours delay (e.g., 6 hours = 21600 seconds)
        asyncio.create_task(delayed_approval(user_id, chat_id, delay=21600))
        pending_leave_cache.pop(user_id, None)


async def delayed_approval(user_id: int, chat_id: int, delay: int):
  await asyncio.sleep(delay)
  try:
    await bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
  except Exception as e:
    logging.error(f"Failed delayed approval for {user_id}: {e}")


# 2. LINK MODERATION FILTER
@router.message(
    F.text
    | F.caption
    & (
        F.chat.type.in_(["supergroup", "group", "channel"])
    )
)
async def moderate_links(message: types.Message):
  # Skip if sender is the owner
  if message.from_user and message.from_user.id == OWNER_ID:
    return

  text = message.text or message.caption or ""
  urls = re.findall(r"(https?://\S+|t\.me/\S+)", text)

  if urls:
    is_whitelisted = False
    for url in urls:
      if any(domain in url for domain in WHITESLISTED_DOMAINS):
        is_whitelisted = True
        break

    if not is_whitelisted:
      try:
        await message.delete()
      except Exception as e:
        logging.error(f"Failed to delete unauthorized link: {e}")


# 3. WELCOME & AI BOT INTERACTION (PRIVATE CHAT)
@router.message(CommandStart())
async def cmd_start(message: types.Message):
  if message.chat.type != "private":
    return

  welcome_text = (
      "Welcome to Gold Expert Fx!\n\n"
      "I am the Gold Expert Fx AI. Feel free to ask any questions related to Gold Expert Fx, and you will get your answers in English.\n\n"
      "Explore our resources below:"
  )

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="🌐 Visit Website", url="https://goldexpertfx.com/"
              )
          ],
          [
              InlineKeyboardButton(
                  text="👥 Community",
                  url="https://t.me/GoldExpertFxCommunity",
              )
          ],
          [
              InlineKeyboardButton(
                  text="🔒 Private Channel", url=PRIVATE_CHANNEL_LINK
              )
          ],
      ]
  )

  await message.answer(welcome_text, reply_markup=keyboard)


# Forward user messages to Owner in Private Chat
@router.message(F.chat.type == "private")
async def forward_to_owner(message: types.Message):
  if message.from_user.id == OWNER_ID:
    # If owner is replying to a forwarded message
    if message.reply_to_message and message.reply_to_message.forward_from:
      target_user_id = message.reply_to_message.forward_from.id
      try:
        await bot.send_message(
            chat_id=target_user_id,
            text=f"**Owner Reply:**\n{message.text}",
            parse_mode="Markdown",
        )
        await message.reply("✅ Reply sent to user.")
      except Exception as e:
        await message.reply(f"❌ Failed to send reply: {e}")
    return

  # Forward user message to Owner
  try:
    forwarded = await message.forward(chat_id=OWNER_ID)
    await bot.send_message(
        chat_id=OWNER_ID,
        text=(
            f"📩 **New Message from User:**\nName: {message.from_user.full_name}\nID:"
            f" `{message.from_user.id}`"
        ),
        parse_mode="Markdown",
    )
  except Exception as e:
    logging.error(f"Failed to forward message to owner: {e}")


# 4. SECURITY & BAN PROTECTION (Anti-Report / Anti-Attack)
@router.message(
    F.successful_payment
    | F.new_chat_members
    | F.left_chat_member
    | F.pinned_message
)
async def security_monitor(message: types.Message):
  # Placeholder for security hooks if suspicious mass-reporting patterns or abuse occurs
  pass


async def main():
  dp.include_router(router)
  asyncio.create_task(monitor_community_leaves())
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
    
