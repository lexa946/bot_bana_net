from io import BytesIO

import aiohttp

from app.config import settings


class ApiManager:
    BASE_URL = settings.PARSER_API_BASE_URL
    GET_FORMAT_URL = f"{BASE_URL}/get-formats/"
    START_DOWNLOAD_URL = f"{BASE_URL}/start-download/"
    DOWNLOAD_STATUS_URL = f"{BASE_URL}/download-status/"
    GET_VIDEO_URL = f"{BASE_URL}/get-video/"

    @classmethod
    async def _send_request(cls, method_url, type_req: str,
                            json: dict = None,
                            params: dict = None,
                            path: str = ""):
        async with aiohttp.ClientSession() as session:
            if type_req == 'GET':
                async with session.get(method_url+path, params=params) as resp:
                    resp.raise_for_status()
                    return await resp.json()
            elif type_req == 'POST':
                async with session.post(method_url+path, json=json) as resp:
                    resp.raise_for_status()
                    return await resp.json()

    @classmethod
    async def get_formats(cls, url):
        return await cls._send_request(cls.GET_FORMAT_URL, type_req='GET', params={"url": url})

    @classmethod
    async def get_status(cls, task_id):
        return await cls._send_request(cls.DOWNLOAD_STATUS_URL, type_req='GET', path=task_id)

    @classmethod
    async def start_download(cls, url, video_format_id, audio_format_id):
        return await cls._send_request(cls.START_DOWNLOAD_URL, type_req="POST", json={
            "url": url,
            "video_format_id": video_format_id,
            "audio_format_id": audio_format_id,
        })

    @classmethod
    async def get_video(cls, task_id:str):
        chunk_size = 1024*1024*10
        buffer = BytesIO()
        async with aiohttp.ClientSession() as session:
            async with session.get(cls.GET_VIDEO_URL+task_id) as resp:
                while chunk := await resp.content.read(chunk_size):
                    buffer.write(chunk)
                    if buffer.getbuffer().nbytes >= chunk_size:
                        buffer.seek(0)
                        yield buffer.getbuffer()
                        buffer = BytesIO()
        yield buffer.getbuffer()
