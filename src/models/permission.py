# src/models/permission.py
from sqlalchemy import Column, String, Text

from src.models.base import Base, TimestampMixin


class Permission(Base, TimestampMixin):
    """Represents a permission record that groups actions by module and description.

    Permissions can be either core (built-in to the application) or plugin-provided.
    Plugin-provided permissions have a non-null plugin_id.
    """

    __tablename__ = "permissions"

    code = Column(String(100), primary_key=True)
    module = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    # NULL = core permission, non-NULL = plugin-provided permission
    plugin_id = Column(String(100), nullable=True, index=True)

    @property
    def is_plugin_provided(self) -> bool:
        """Check if this permission is provided by a plugin."""
        return self.plugin_id is not None
