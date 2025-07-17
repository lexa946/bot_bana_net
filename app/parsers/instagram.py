import json
from io import BytesIO

import aiohttp
from aiogram.types import Message
from attr import dataclass
from bs4 import BeautifulSoup

from app.config import settings

from app.parsers.base import BaseParser
from app.s3.client import s3_client


@dataclass
class InstagramVideo:
    title: str
    content_url: str
    preview_url: str
    duration: int
    quality: str
    size: int
    author: str

    @classmethod
    def from_json(cls, json_: dict):
        items = json_['require'][0][3][0]['__bbox']['require'][0][3][1]['__bbox']['result']['data'][
            'xdt_api__v1__media__shortcode__web_info']['items']

        video_url = items[0]['video_versions'][0]['url']

        video_width = items[0]['video_versions'][0]['width']
        video_height = items[0]['video_versions'][0]['height']
        video_quality = f"{video_width}x{video_height}"

        video_preview_url = items[0]['image_versions2']['candidates'][0]['url']
        video_author = items[0]['user']['username']
        video_title = f"{items[0]['id']}_video_by_{video_author}.mp4"

        manifest_soup = BeautifulSoup(items[0]['video_dash_manifest'], features="xml")
        video_duration = int(float(manifest_soup.select_one("Period").attrs['duration'][2:-1]))

        video_size = int(
            manifest_soup.select_one("AdaptationSet[contentType='video'] Representation").attrs['FBContentLength'])
        audio_size = int(
            manifest_soup.select_one("AdaptationSet[contentType='audio'] Representation").attrs['FBContentLength'])
        full_size = video_size + audio_size

        return cls(video_title, video_url, video_preview_url, video_duration, video_quality, full_size, video_author)


class InstagramParser(BaseParser):
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 YaBrowser/25.6.0.0 Safari/537.36",
    }
    cookies = {
        "csrftoken": settings.INSTAGRAM_CSRFTOKEN,
        "sessionid": settings.INSTAGRAM_SESSIONID,
    }

    def __init__(self, url, message: Message):
        self.url = url
        self._message = message

    @staticmethod
    def _parse_video_attributes(content: str) -> InstagramVideo:
        soup = BeautifulSoup(content, features="lxml")
        json_tag = list(
            filter(lambda json_tag: ".mp4" in json_tag.text, soup.select("script[type='application/json']"))
        )[0]
        json_ = json.loads(json_tag.text)
        return InstagramVideo.from_json(json_)


    async def download(self) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url, headers=self.headers, cookies=self.cookies) as response:
                response.raise_for_status()
                response_text = await response.text()

            video = self._parse_video_attributes(response_text)
            if s3_client.file_exists(f"{video.author}/{video.title}"):
                return f"{s3_client.config['endpoint_url']}/{s3_client.bucket_name}/{video.author}/{video.title}"

            async with session.get(video.content_url, headers=self.headers, cookies=self.cookies) as response:
                response.raise_for_status()
                content = await response.content.read()
            s3_url = s3_client.upload_file(
                key=f"{video.author}/{video.title}",
                body=BytesIO(content),
                size=len(content),
            )
            return s3_url
