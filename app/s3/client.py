from typing import BinaryIO

import urllib3
from minio import Minio
from minio.error import S3Error

from app.config import settings


class S3Client:
    def __init__(self, access_key: str, secret_key: str, endpoint_url: str, bucket_name: str):
        self.config = {
            "access_key": access_key,
            "secret_key": secret_key,
            "endpoint_url": endpoint_url,
        }
        self.bucket_name = bucket_name
        self.client = Minio(
            endpoint_url.replace("http://", "").replace("https://", ""),
            access_key=access_key,
            secret_key=secret_key,
            secure=True,
            http_client=urllib3.PoolManager(cert_reqs='CERT_NONE')
        )


        # Создаем бакет, если его нет
        if not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)

    async def upload_video(self, task_id: str, object_name: str):
        upload_id = None
        parts = []
        current_part = b""
        part_number = 1

        try:
            # 1. Инициируем Multipart Upload
            upload_id = self.client._create_multipart_upload(
                self.bucket_name, object_name
            )

            # 2. Получаем потоковые данные и накапливаем чанки
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://example.com/video/{task_id}") as resp:
                    async for chunk in resp.content.iter_chunked(1024 * 8):  # Чанки по 8 КБ
                        current_part += chunk

                        # Если накопили достаточно данных для части (5 МБ) → загружаем
                        if len(current_part) >= self.part_size:
                            etag = self.client._upload_part(
                                self.bucket_name,
                                object_name,
                                upload_id,
                                part_number,
                                current_part
                            )
                            parts.append({"PartNumber": part_number, "ETag": etag})
                            part_number += 1
                            current_part = b""  # Сбрасываем буфер

            # 3. Загружаем последнюю часть (если остались данные)
            if current_part:
                etag = self.client._upload_part(
                    self.bucket_name,
                    object_name,
                    upload_id,
                    part_number,
                    current_part
                )
                parts.append({"PartNumber": part_number, "ETag": etag})

            # 4. Завершаем загрузку
            self.client._complete_multipart_upload(
                self.bucket_name,
                object_name,
                upload_id,
                parts
            )
            print(f"Видео {object_name} успешно загружено!")

        except Exception as e:
            # Отменяем загрузку в случае ошибки
            if upload_id:
                self.client._abort_multipart_upload(
                    self.bucket_name, object_name, upload_id
                )
            raise e

    def upload_file(self, key: str, body: BinaryIO, size:int) -> str:
        """Загружает файл в Minio и возвращает его URL"""
        try:
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=key,
                data=body,
                length=size,
            )
            return f"{self.config['endpoint_url']}/{self.bucket_name}/{key}"
        except S3Error as err:
            print(f"Ошибка при загрузке файла: {err}")
            return None

    def get_file(self, key):
        """Получает файл из Minio"""
        try:
            response = self.client.get_object(self.bucket_name, key)
            return response.read()  # Читаем содержимое файла
        except S3Error as err:
            print(f"Ошибка при получении файла: {err}")
            return None

    def file_exists(self, key):
        try:
            self.client.stat_object(self.bucket_name, key)
            return True
        except S3Error as err:
            if err.code == "NoSuchKey":
                return False
            raise err


s3_client = S3Client(
    access_key=settings.S3_ACCESS_KEY,
    secret_key=settings.S3_SECRET_KEY,
    endpoint_url=settings.S3_ENDPOINT_URL,
    bucket_name=settings.S3_BUCKET_NAME
)
