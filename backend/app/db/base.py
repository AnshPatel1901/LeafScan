"""
Shared declarative base for all SQLAlchemy models.
Import `Base` in every model file.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Application-wide SQLAlchemy declarative base."""
    pass
