import urllib3
from minio import Minio
from minio.datatypes import Part
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

    def file_exists(self, key):
        try:
            self.client.stat_object(self.bucket_name, key)
            return True
        except S3Error as err:
            if err.code == "NoSuchKey":
                return False
            raise err


class S3StreamFile:
    def __init__(self, client: Minio, bucket_name: str, key: str):
        self.client = client
        self.bucket_name = bucket_name
        self.key = key

        self.__part_number = 1
        self.__parts = []

        self.__upload_id = client._create_multipart_upload(
            bucket_name, key, {}
        )

    def send_chunk(self, chunk):
        etag = s3_client.client._upload_part(self.bucket_name, self.key, chunk, {}, self.__upload_id,
                                             self.__part_number)
        self.__parts.append(Part(self.__part_number, etag))
        self.__part_number += 1

    def complete(self):
        file_info = s3_client.client._complete_multipart_upload(
            self.bucket_name, self.key, self.__upload_id, self.__parts
        )
        return file_info


s3_client = S3Client(
    access_key=settings.S3_ACCESS_KEY,
    secret_key=settings.S3_SECRET_KEY,
    endpoint_url=settings.S3_ENDPOINT_URL,
    bucket_name=settings.S3_BUCKET_NAME
)
