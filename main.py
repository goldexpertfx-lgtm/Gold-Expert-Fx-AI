import asyncio
import re
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.types import ChannelParticipantsRecent

# Apni Telegram API credentials yahan dalein
API_ID = 1234567  # Apka API ID
API_HASH = "your_api_hash_here"
BOT_TOKEN = "your_bot_token_here"  # Agar userbot hai toh session string use karein ya client setup badlein

client = TelegramClient("gold_expert_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Whitelisted links jo delete nahi honi chahiye
ALLOWED_LINKS = [
    "brokeraccountguide.com",
    "goldexpertfxcommunity",
    "ri2sc_tdify5nti1",  # telegram.me/+Ri2SC_TdIFY5NTI1 ka unique part
]

# IDs configure karein
COMMUNITY_ID = -1001234567890  # Aapki Community/Group ID
PRIVATE_CHANNEL_ID = -1001987654321  # Aapka Private Channel ID
OWNER_ID = 123456789  # Aapki (Owner) Telegram User ID

# Pending requests tracking ke liye dictionary
pending_requests = {}  # {user_id: {"date": datetime, "chat_id": chat_id}}


def contains_unallowed_link(text):
  if not text:
    return False

  # URL regex pattern
  url_pattern = re.compile(r"https?://[^\s]+|www\.[^\s]+|t\.me/[^\s]+", re.IGNORECASE)
  found_urls = url_pattern.findall(text)

  if not found_urls:
    return False

  for url in found_urls:
    # Check karein kya URL allowed links mein se ek hai
    is_allowed = any(allowed in url.lower() for allowed in ALLOWED_LINKS)
    if not is_allowed:
      return True  -  # Unauthorized link mil gayi

  return False


@client.on(events.NewMessage(chats=PRIVATE_CHANNEL_ID))
async def handle_channel_messages(event):
  sender_id = event.sender_id
  message_text = event.raw_text

  # 1. Agar owner ne message bheja hai toh delete na karein
  if sender_id == OWNER_ID:
    return

  # 2. Check karein kya message mein koi unauthorized link hai (ya forward kiya gaya hai)
  has_bad_link = contains_unallowed_link(message_text)
  is_forwarded = event.message.fwd_from is not None

  if has_bad_link or is_forwarded:
    try:
      await event.delete()
      print(f"Deleted unauthorized or forwarded message from: {sender_id}")
    except Exception as e:
      print(f"Error deleting message: {e}")


@client.on(events.ChatAction)
async def handle_join_requests(event):
  # Jab koi join request bhejta hai
  if event.user_joined or event.пеending:  # Join request handling
    user_id = event.user_id
    chat_id = event.chat_id

    if chat_id == PRIVATE_CHANNEL_ID:
      # Check karein kya user Community mein already member hai ya nahi
      try:
        participant = await client.get_permissions(COMMUNITY_ID, user_id)
        is_in_community = participant and not participant.is_banned
      except Exception:
        is_in_community = False

      if is_in_community:
        # Agar user Community mein hai, toh request turant accept nahi karni
        # Ise pending dictionary mein daal kar 7 ghante ka wait karwayenge
        pending_requests[user_id] = {
            "time": datetime.now(),
            "chat_id": chat_id,
        }
        print(
            f"User {user_id} is in Community. Holding private channel request"
            " for 7 hours."
        )
        # Optional: Request ko decline ya ignore kar sakte hain taaki turant access na mile
        # await client.edit_permissions(chat_id, user_id, view_messages=False)
      else:
        # Agar user Community mein nahi hai, toh direct action ya standard flow
        pass


async def background_request_scanner():
  while True:
    await asyncio.sleep(60)  # Har 1 minute mein check karega
    now = datetime.now()

    for user_id, data in list(pending_requests.items()):
      chat_id = data["chat_id"]
      request_time = data["time"]

      # Check karein kya 7 ghante beet chuke hain
      if now - request_time >= timedelta(hours=7):
        # Dobara check karein kya user ne Community abhi bhi chhori (leave) hai ya nahi
        try:
          participant = await client.get_permissions(COMMUNITY_ID, user_id)
          is_still_in_community = participant and not participant.is_banned
        except Exception:
          is_still_in_community = False

        if not is_still_in_community:
          # 7 ghante ho gaye aur user ne community leave kar di hai, ab request approve kar dein
          try:
            # Telegram API ke zariye join request approve karein
            await client.inline_query(
                # ya appropriate approve method call karein
                ...
            )
            print(
                f"Approved join request for user {user_id} after 7 hours of"
                " leaving community."
            )
          except Exception as e:
            print(f"Failed to approve request for {user_id}: {e}")

        # List se remove kar dein
        del pending_requests[user_id]


def main():
  print("Bot is running...")
  client.loop.create_task(background_request_scanner())
  client.run_until_disconnected()


if __name__ == "__main__":
  main()
    
