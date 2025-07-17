import asyncio
import uuid
from datetime import timedelta
from io import BytesIO
from pathlib import Path

import aiofiles
from aiogram.types import Message
from pytubefix import Stream, YouTube, StreamQuery

from app.config import settings

from app.parsers.base import BaseParser
from app.s3.client import s3_client


class YouTubeParser(BaseParser):

    def __init__(self, url, message: Message):
        self.url = url
        self._message = message
        self._yt = YouTube(self.url)

    @staticmethod
    def _format_filter(stream: Stream):
        return (
                stream.type == "video" and
                stream.video_codec.startswith("avc1") and
                len(stream.video_codec) > 1
        )

    @staticmethod
    def _get_audio_stream(streams: StreamQuery) -> Stream:
        main_stream = next(
            (s for s in streams if s.includes_audio_track and s.includes_video_track),
            None
        ) or streams.filter(only_audio=True).order_by('abr').first()
        return main_stream


    async def download(self):
        video_uuid = str(uuid.uuid4())
        download_path = Path(settings.DOWNLOAD_FOLDER) / self._yt.author

        streams = await asyncio.to_thread(lambda: self._yt.streams.fmt_streams)

        author = self._yt.author.replace(" ", "_")
        title = self._yt.title.replace(" ", "_")
        for char_ in ["#", "`", "'", '"']:
            author = author.replace(char_, "")
            title = title.replace(char_, "_")

        s3_key = f'{author}/{title}.mp4'

        if await asyncio.to_thread(s3_client.file_exists, title):
            return f"{s3_client.config['endpoint_url']}/{s3_client.bucket_name}/{s3_key}"


        video_stream = next(filter(self._format_filter, streams))
        duration = timedelta(milliseconds=int(video_stream.durationMs)).seconds

        video_path = Path(await asyncio.to_thread(
            video_stream.download,
            output_path=download_path.as_posix(),
            filename_prefix=f"{video_uuid}_video_"
        ))


        async with aiofiles.open(video_path, 'rb') as f:
            content = await f.read()

        s3_url = await asyncio.to_thread(s3_client.upload_file,
            key=s3_key,
            body=BytesIO(content),
            size=len(content),
        )
        video_path.unlink(missing_ok=True)
        return s3_url


