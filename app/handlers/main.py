import asyncio
from uuid import uuid4

from aiogram.filters import Command
from aiogram import Router

from aiogram.types import Message, CallbackQuery
from aiogram import F
from minio.datatypes import Part

from app.api import ApiManager

from app.handlers.filters import video_filter

from app.keyboards.main import yes_no_keyboard
from app.messages import AnswerMessage
from app.s3.client import s3_client, S3StreamFile

router = Router()

REMOVE_CHARS_FROM_YOUTUBE = ["#", "`", "'", '"', "@", "|", "\\", "/"]


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
    await callback.message.edit_text(AnswerMessage.PENDING)
    url = callback.message.reply_to_message.text

    video_info = await ApiManager.get_formats(url)

    if video_info['formats'][0]['filesize'] > 1024*1024*100:
        await callback.message.edit_text(AnswerMessage.TOO_MUCH_SIZE)
        return

    s3_key = "/".join(video_info['preview_url'].replace("https://", "").split("/")[2:])[:-4] + ".mp4"

    if await asyncio.to_thread(s3_client.file_exists, s3_key):
        await callback.message.edit_text(f"{s3_client.config['endpoint_url']}/{s3_client.bucket_name}/{s3_key}")
        return

    download_status = await ApiManager.start_download(
        video_info['url'],
        video_info['formats'][0]['video_format_id'],
        video_info['formats'][0]['audio_format_id'],
    )

    while download_status['status'] == "Pending":
        await asyncio.sleep(1)
        download_status = await ApiManager.get_status(download_status['task_id'])
        try:
            await callback.message.edit_text(AnswerMessage.PROGRESS_BAR.replace(
                "{download_status}",
                download_status['percent'])
            )
        except Exception as e:
            ...

    if download_status['status'] != "Completed":
        await callback.message.edit_text(AnswerMessage.ERROR)
        raise ValueError("Download Error")

    stream_file = S3StreamFile(s3_client.client, s3_client.bucket_name, s3_key)

    async for chunk in ApiManager.get_video(download_status['task_id']):
        await asyncio.to_thread(stream_file.send_chunk, chunk)
    minio_file_info = stream_file.complete()

    await callback.message.delete()
    await callback.message.answer(minio_file_info.location)
