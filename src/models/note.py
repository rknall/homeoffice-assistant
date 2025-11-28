"""Note model."""
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin
from src.models.enums import NoteType

if TYPE_CHECKING:
    from src.models.event import Event


class Note(Base, TimestampMixin):
    """Note model for event observations and report sections."""

    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    note_type: Mapped[NoteType] = mapped_column(
        Enum(NoteType),
        default=NoteType.OBSERVATION,
        nullable=False,
    )

    # Relationships
    event: Mapped["Event"] = relationship("Event", back_populates="notes")
