from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    DOWNLOAD_FOLDER: str
    FFMPEG_PATH: str
    MAX_DURATION_VIDEO: int

    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_ENDPOINT_URL: str
    S3_BUCKET_NAME: str

    INSTAGRAM_CSRFTOKEN: str
    INSTAGRAM_SESSIONID: str

    class Config:
        env_file = '.env'


settings = Settings()