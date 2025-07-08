import asyncio
import json
import subprocess
import time

import platform

from yt_dlp import YoutubeDL

from app.config import settings

async def get_video_info(url: str, loop):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'nocheckcertificate': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        return await asyncio.to_thread(ydl.extract_info, url, download=False)


def get_video_duration(path):
    cmd = [
        settings.FFPROBE_PATH,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    info = json.loads(result.stdout)
    duration = float(info['format']['duration'])
    return duration


def compress_video(input_path: str, output_path: str, target_size_mb: int = 25):
    duration = get_video_duration(input_path)

    target_bitrate = (target_size_mb * 8192) / duration

    command = [
        settings.FFMPEG_PATH,
        "-i", input_path,
        "-c:v", "libx264",
        "-b:v", f"{int(target_bitrate)}k",
        "-pass", "1",
        "-an",
        "-f", "mp4",
        "/dev/null" if platform.system() != "Windows" else "NUL"
    ]
    # result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(command)

    command = [
        settings.FFMPEG_PATH,
        "-i", input_path,
        "-c:v", "libx264",
        "-b:v", f"{int(target_bitrate)}k",
        "-pass", "2",
        "-c:a", "aac",
        "-b:a", "128k",
        output_path
    ]
    subprocess.run(command)
    # result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # print()

def render_bar(percent_str: str) -> str:

    try:
        percent = float(percent_str.replace('%', '').strip())
    except:
        percent = 0

    total_blocks = 12  # длина бара: 12 символов
    filled_blocks = int(percent / (100 / total_blocks))
    empty_blocks = total_blocks - filled_blocks

    bar = '█' * filled_blocks + '░' * empty_blocks
    return f"[{bar}]"

def progress_hook_factory(callback, loop):
    last_update = 0

    async def update_progress(text):
        try:
            await callback.message.edit_text(text)
        except:
            pass  # Игнорировать ошибку, если Telegram не даёт редактировать часто

    def progress_hook(d):
        nonlocal last_update

        now = time.time()
        if now - last_update < 5:  # если прошло меньше 5 секунд — не обновляем
            return
        last_update = now

        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '').strip()
            speed = d.get('_speed_str', '').strip()
            eta = d.get('_eta_str', '').strip()


            bar = render_bar(percent)
            asyncio.run_coroutine_threadsafe(update_progress(f"📥 Скачивание...\n{bar} {percent} ({speed}, ETA: {eta})"), loop)

    return progress_hook