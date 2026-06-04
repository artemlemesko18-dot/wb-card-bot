import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import admin_router, balance_router, generation_router, payments_router, start_router
from services import refresh_wb_categories_cache


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start_router)
    dp.include_router(balance_router)
    dp.include_router(payments_router)
    dp.include_router(generation_router)
    dp.include_router(admin_router)

    try:
        updated = await refresh_wb_categories_cache()
        logging.info("WB categories cache updated: %s", updated)
    except Exception as exc:
        logging.warning("WB categories cache update skipped: %s", exc)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
