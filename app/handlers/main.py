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
from app.s3.client import s3_client


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

    author = str(uuid4())
    title = video_info['title'].replace(" ", "_")
    for char_ in REMOVE_CHARS_FROM_YOUTUBE:
        author = author.replace(char_, "")
        title = title.replace(char_, "_")

    # s3_key = f'{author}/{title}.mp4'
    # s3_key = f'{title}.mp4'.strip("_"+"".join(REMOVE_CHARS_FROM_YOUTUBE))
    s3_key = f'{str(uuid4())}.mp4'

    if await asyncio.to_thread(s3_client.file_exists, title):
        return f"{s3_client.config['endpoint_url']}/{s3_client.bucket_name}/{s3_key}"

    download_status = await ApiManager.start_download(
        video_info['url'],
        video_info['formats'][0]['video_format_id'],
        video_info['formats'][0]['audio_format_id'],
    )
    while download_status['status'] == "Pending":
        await asyncio.sleep(1)
        download_status = await ApiManager.get_status(download_status['task_id'])
        try:
            await callback.message.edit_text(f"Скачиваю видик: {download_status['percent']} %")
        except Exception as e:
            ...

    if download_status['status'] != "Completed":
        await callback.message.edit_text(AnswerMessage.ERROR)
        raise ValueError("Download Error")

    part_number = 1
    parts = []

    upload_id = s3_client.client._create_multipart_upload(
        s3_client.bucket_name, s3_key, {}
    )

    async for chunk in ApiManager.get_video(download_status['task_id']):
        etag = await asyncio.to_thread(s3_client.client._upload_part,
            s3_client.bucket_name,
            s3_key,
            chunk,
            {},
            upload_id,
            part_number,
        )
        parts.append(Part(part_number, etag))
        part_number += 1

    minio_file_info = s3_client.client._complete_multipart_upload(
        s3_client.bucket_name,
        s3_key,
        upload_id,
        parts
    )
    await callback.message.delete()
    await callback.message.answer(minio_file_info.location)
