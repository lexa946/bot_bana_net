import platform
import subprocess


from app.config import settings

if platform.system() == 'Windows':
    FFMPEG = settings.FFMPEG_PATH
else:
    FFMPEG = "ffmpeg"

def combine_audio_and_video(video_path, audio_path, output_path):
    """
    Накладывает аудио на видео.

    Args:
        video_path (str): Путь к исходному видеофайлу.
        audio_path (str): Путь к аудиофайлу, который нужно наложить.
        output_path (str): Путь для сохранения результирующего видеофайла.
    """
    subprocess.run([
        FFMPEG,
        "-i", video_path,  # видео без звука
        "-i", audio_path,  # источник звука
        "-c:v", "copy",  # копируем видео как есть
        "-c:a", "copy",  # копируем аудио как есть (или "aac" для пережатия)
        "-map", "0:v:0",  # берём видео из первого файла
        "-map", "1:a:0",  # берём аудио из второго
        "-shortest",  # обрезаем по короткому
        "-y",  # перезапись без подтверждения
        output_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
