import asyncio

import platform

from pathlib import Path

import yt_dlp
from aiogram.filters import Command
from aiogram import Router

from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram import F

from app.config import settings
from app.helpers import progress_hook_factory, compress_video, get_video_info
from app.keyboards.main import yes_no_keyboard

router = Router()

download_tasks = {}


@router.message(Command("help"))
async def help(message: Message):
    await message.answer("Если вы столкнулись с трудностями при работе с ботом, "
                         "тогда попробуйте вызвать /menu и повторить свои действия. "
                         "Если трудности повторяются тогда необходимо обратиться к @PozharAlex "
                         "и описать цикл ваших действий приводимых к ошибкам работы. "
                         "Это необходимо для дальнейшего устранения и улучшения работы бота.")


@router.message(F.text.startswith("https://"))
async def handle_url(message: Message):
    await message.reply("Скачать видик?", reply_markup=yes_no_keyboard())


@router.callback_query(F.data == "no")
async def delete_message(callback: CallbackQuery, ):
    await callback.message.delete()


@router.callback_query(F.data.startswith("yes"))
async def download_video(callback: CallbackQuery):
    try:
        url = callback.message.reply_to_message.text
        loop = asyncio.get_running_loop()

        await callback.message.edit_text("⏳ Проверка видео...")

        info = await get_video_info(url, loop)
        duration = info.get("duration", 0)

        if duration > settings.MAX_DURATION_VIDEO:
            await callback.message.edit_text(f"❌ Видео длится больше {round(settings.MAX_DURATION_VIDEO / 60)}"
                                             f" минут и не может быть скачано.")
            return

        ydl_opts = {
            'concurrent_fragments': 16,
            'outtmpl': f"{settings.DOWNLOAD_FOLDER}/"
                       f"%(uploader)s/"
                       f"%(upload_date>%Y-%m-%d)s_%(uploader)s#%(title)s.%(ext)s",

            'merge_output_format': 'mp4',
            'nocheckcertificate': True,
            'throttled_rate': '500K',
            'socket_timeout': 30,

        }
        if "youtube" in url and "shorts" not in url:
            ydl_opts['format'] = 'best[height<=720]/best[height<=720]'

        hook = progress_hook_factory(callback, loop)
        ydl_opts['progress_hooks'] = [hook]

        if platform.system() == 'Windows':
            ydl_opts['ffmpeg_location'] = settings.FFMPEG_PATH

        await callback.message.edit_text("Подготовка...")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            def download():
                return ydl.extract_info(url, download=True)

            info = await loop.run_in_executor(None, download)
            filename = Path(ydl.prepare_filename(info))


        if filename.stat().st_size > 50 * 1024 * 1024:
            await callback.message.edit_text("Видео слишком большое (>50МБ). Сжимаю...")
            filename_compressed = filename.with_name(filename.stem + "_compressed.mp4")

            await asyncio.to_thread(compress_video, str(filename), str(filename_compressed), target_size_mb=50)

            if filename_compressed.stat().st_size <= 50 * 1024 * 1024:
                filename = filename_compressed
            else:
                filename_compressed.unlink()
                await callback.message.edit_text("Даже после сжатия видео больше 50МБ 😢")
                return

        await callback.message.edit_text("✅ Подготовка завершена, отправляю в телегу...")
        video = FSInputFile(filename)
        await callback.message.answer_video(video, supports_streaming=True, )
        await callback.message.delete()
        filename.unlink()

    except Exception as ex:
        await callback.message.edit_text("Не могу 🥲 " + str(ex))
