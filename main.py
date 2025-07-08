import asyncio
import logging
from app.bot import bot, dp


logging.basicConfig(level=logging.INFO)


async def bot_start():
    await dp.start_polling(bot)


if __name__ == '__main__':
    import sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(bot_start())
