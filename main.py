import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from db import init_db
from payment_handlers import router

logging.basicConfig(level=logging.INFO)


async def main():
    if not BOT_TOKEN or BOT_TOKEN == "8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4":
        raise RuntimeError("Set BOT_TOKEN in your environment or config.py before running.")

    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
    
