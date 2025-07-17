from aiogram.types import Message


def video_filter(message: Message):
    url = message.text
    if not url.startswith("https://"):
        return False

    if "youtube.com/shorts" in url:
        return True
    elif "instagram" in url:
        return True

    return False