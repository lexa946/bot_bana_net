from aiogram.filters import Command
from aiogram import Router

from aiogram.types import Message, CallbackQuery
from aiogram import F



from app.handlers.filters import video_filter

from app.keyboards.main import yes_no_keyboard
from app.parsers import InstagramParser, YouTubeParser

router = Router()

@router.message(Command("help"))
async def help(message: Message):
    await message.answer("Если вы столкнулись с трудностями при работе с ботом, "
                         "тогда попробуйте вызвать /menu и повторить свои действия. "
                         "Если трудности повторяются тогда необходимо обратиться к @PozharAlex "
                         "и описать цикл ваших действий приводимых к ошибкам работы. "
                         "Это необходимо для дальнейшего устранения и улучшения работы бота.")


@router.message(video_filter)
async def handle_url(message: Message):
    await message.reply("Скачать видик?", reply_markup=yes_no_keyboard())


@router.callback_query(F.data == "no")
async def delete_message(callback: CallbackQuery, ):
    await callback.message.delete()


@router.callback_query(F.data.startswith("yes"))
async def download_video(callback: CallbackQuery):
    await callback.message.edit_text("Подожди ёбана...")
    url = callback.message.reply_to_message.text
    file_url = ""
    if "instagram" in url:
        file_url = await InstagramParser(url, callback.message).download()
    elif "youtube.com/shorts" in url :
        file_url = await YouTubeParser(url, callback.message).download()

    await callback.message.answer(file_url)
    await callback.message.delete()

