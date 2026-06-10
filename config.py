from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    bot_token: str
    database_url: str


def load_config() -> Config:
    bot_token = getenv("BOT_TOKEN")
    database_url = getenv("DATABASE_URL")

    if not bot_token:
        raise ValueError("Не указан токен бота в файле .env")

    if not database_url:
        raise ValueError("Не указан DATABASE_URL в файле .env")

    return Config(
        bot_token=bot_token,
        database_url=database_url,
    )