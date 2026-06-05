import json
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Импорты из вашего проекта (те же, что в bot.py)
from config import BOT_TOKEN
from handlers import admin_router, balance_router, generation_router, payments_router, start_router
from services import refresh_wb_categories_cache

# Настройка логирования (логи будут видны в консоли Cloudflare)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Подключаем роутеры (как в вашем bot.py)
dp.include_router(start_router)
dp.include_router(balance_router)
dp.include_router(payments_router)
dp.include_router(generation_router)
dp.include_router(admin_router)

# Флаг, чтобы обновить кэш категорий только один раз (при первом запросе)
cache_updated = False

async def update_categories_cache():
    """Обновляет кэш категорий WB (вызывается один раз при старте)"""
    global cache_updated
    if not cache_updated:
        try:
            updated = await refresh_wb_categories_cache()
            logger.info(f"WB categories cache updated: {updated}")
        except Exception as exc:
            logger.warning(f"WB categories cache update skipped: {exc}")
        cache_updated = True

async def handle_telegram_request(request):
    """Принимает JSON от Telegram, превращает в Update и отдаёт боту"""
    try:
        # Обновляем кэш при первом обращении (если нужно)
        await update_categories_cache()
        
        # Получаем тело запроса
        body = await request.json()
        # Преобразуем в объект Update aiogram
        update = Update(**body)
        # Передаём боту
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        logger.exception("Ошибка при обработке запроса")
        return {"ok": False, "error": str(e)}

async def fetch(request):
    """Точка входа для Cloudflare Worker"""
    # Обрабатываем только POST-запросы на путь /webhook
    if request.method == "POST" and request.url.path == "/webhook":
        result = await handle_telegram_request(request)
        return Response.json(result)
    else:
        # Для GET-запросов просто говорим, что бот жив
        return Response.json({"status": "Bot is running"}, status=200)

# Вспомогательный класс для формирования ответов
class Response:
    @staticmethod
    def json(data, status=200):
        return {
            "statusCode": status,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(data)
        }

# ========== НИЖЕ ДОБАВЛЕННЫЙ БЛОК ДЛЯ ЗАПУСКА НА RENDER ==========
if __name__ == "__main__":
    import asyncio

    async def start_polling():
        # Однократно обновляем кэш (флаг cache_updated уже есть)
        await update_categories_cache()
        # Запускаем long polling
        await dp.start_polling(bot)

    asyncio.run(start_polling())
