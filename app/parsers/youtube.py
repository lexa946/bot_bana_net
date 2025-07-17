import asyncio
import uuid
from datetime import timedelta
from io import BytesIO
from pathlib import Path

import aiofiles
from aiogram.types import Message
from pytubefix import Stream, YouTube, StreamQuery

from app.config import settings
from app.helpers import combine_audio_and_video
# from app.models.status import VideoDownloadStatus
# from app.models.storage import DOWNLOAD_TASKS, DownloadTask
from app.parsers.base import BaseParser
from app.s3.client import s3_client


# from app.schemas.main import SVideo, SVideoFormatsResponse, SVideoDownload
# from app.utils.video_utils import save_preview_on_s3, combine_audio_and_video


class YouTubeParser(BaseParser):

    def __init__(self, url, message: Message):
        self.url = url
        self._message = message
        self._yt = YouTube(self.url)

    @staticmethod
    def _format_filter(stream: Stream):
        return (
                stream.type == "video" and
                stream.video_codec.startswith("avc1")
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
        audio_stream = await asyncio.to_thread(self._get_audio_stream, streams)
        duration = timedelta(milliseconds=int(audio_stream.durationMs)).seconds
        title = f'{self._yt.author.replace(" ", "_")}/{self._yt.title.replace(" ", "_")}.mp4'



        if await asyncio.to_thread(s3_client.file_exists, title):
            return f"{s3_client.config['endpoint_url']}/{s3_client.bucket_name}/{title}"


        video_streams = list(filter(self._format_filter, streams))

        video_stream = video_streams[0]
        for stream in video_streams:
            current_res = int(video_stream.resolution[:-1])
            next_resolution = int(stream.resolution[:-1])
            if current_res > next_resolution >= 720:
                video_stream = stream

        video_path = Path(await asyncio.to_thread(
            video_stream.download,
            output_path=download_path.as_posix(),
            filename_prefix=f"{video_uuid}_video_"
        ))

        audio_path = Path(await asyncio.to_thread(
            audio_stream.download,
            output_path=download_path.as_posix(),
            filename_prefix=f"{video_uuid}_audio_"
        ))

        out_path = video_path.with_name(video_path.stem + "_out.mp4")
        await asyncio.to_thread(combine_audio_and_video,
                                video_path.as_posix(),
                                audio_path.as_posix(),
                                out_path.as_posix()
                                )
        audio_path.unlink(missing_ok=True)
        video_path.unlink(missing_ok=True)

        async with aiofiles.open(out_path, 'rb') as f:
            content = await f.read()

        s3_url = await asyncio.to_thread(s3_client.upload_file,
            key=title,
            body=BytesIO(content),
            size=len(content),
        )
        return s3_url


