# src/models/permission.py
from sqlalchemy import Column, String, Text

from src.models.base import Base, TimestampMixin


class Permission(Base, TimestampMixin):
    """Represents a permission record that groups actions by module and description."""

    __tablename__ = "permissions"

    code = Column(String(100), primary_key=True)
    module = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
