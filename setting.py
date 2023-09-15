from pydantic import BaseSettings
import os
from dotenv import load_dotenv

load_dotenv(verbose=True)


class Setting(BaseSettings):
    ROOT_DIR = os.path.abspath(os.path.join(
        os.path.dirname(__file__)
    ))

    VBPl_BASE_URL: str = os.getenv('VBPL_BASE_URL')
    ANLE_BASE_URL: str = os.getenv('ANLE_BASE_URL')
    SQLALCHEMY_DATABASE_URI: str = os.getenv('SQLALCHEMY_DATABASE_URI')


setting = Setting()
