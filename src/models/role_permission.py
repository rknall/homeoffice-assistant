# src/models/role_permission.py
from sqlalchemy import Column, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class RolePermission(Base):
    """Association table mapping roles to their granted permissions."""

    __tablename__ = "role_permissions"

    role_id = Column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_code = Column(
        ForeignKey("permissions.code", ondelete="CASCADE"), primary_key=True
    )

    __table_args__ = (PrimaryKeyConstraint("role_id", "permission_code"),)

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission")
