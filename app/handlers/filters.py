from aiogram.types import Message


def video_filter(message: Message):
    url = message.text
    if "youtube.com" in url or "youtu.be" in url:
        return True
    elif "instagram" in url:
        return True

    return False
