import asyncio
import logging

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN, OWNER_ID, ADMIN_CHAT_ID
from db import init_db
from storage import storage
import admin_handlers
import customer_handlers

logging.basicConfig(level=logging.INFO)


async def main():
    if not BOT_TOKEN or BOT_TOKEN == "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4":
        raise RuntimeError("Set BOT_TOKEN before running.")
    if not OWNER_ID:
        raise RuntimeError("Set OWNER_ID (your Telegram user id) before running.")
    if not ADMIN_CHAT_ID:
        raise RuntimeError("Set ADMIN_CHAT_ID before running.")

    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=storage)

    # Order matters: admin_handlers' specific filters (reply-to-forward,
    # oa: callbacks, owner commands) must get first look before
    # customer_handlers' catch-all private-message relay.
    dp.include_router(admin_handlers.router)
    dp.include_router(customer_handlers.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
