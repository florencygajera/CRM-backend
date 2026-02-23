"""
Single source of truth for the SQLAlchemy declarative Base.

All models import Base from here.  `db/base.py` then imports every model
so that `Base.metadata` knows about all tables at create_all / migration time.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Application-wide declarative base class."""
    pass
