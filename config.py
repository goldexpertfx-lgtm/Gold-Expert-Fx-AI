import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4")

# The chat where screenshots get forwarded for manual review.
# This can be the owner's personal DM with the bot, OR a private admin group.
# Get it by messaging @userinfobot or checking bot logs (message.chat.id) once.
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./gefx_orders.db")
