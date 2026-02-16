import os
from dotenv import load_dotenv
from alembic import context

config = context.config

load_dotenv()
DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/smartserve

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found")
config.set_main_option("sqlalchemy.url", DATABASE_URL)