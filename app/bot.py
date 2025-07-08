from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage


from app.config import settings
from app.handlers.main import router as main_router



bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode='HTML'),
    session=AiohttpSession(timeout=120),
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

dp.include_router(main_router)
