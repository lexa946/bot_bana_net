from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    DOWNLOAD_FOLDER: str
    FFMPEG_PATH: str
    FFPROBE_PATH: str
    MAX_DURATION_VIDEO: int

    class Config:
        env_file = '.env'


settings = Settings()