from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig
import os
from dotenv import load_dotenv
from app.db.base import Base

config = context.config
fileConfig(config.config_file_name)

load_dotenv()

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL not found")

config.set_main_option("sqlalchemy.url", database_url)


target_metadata = Base.metadata
