import uuid
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class SemanticRelationship(Base):
    __tablename__ = "semantic_relationships"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    from_key: Mapped[str] = mapped_column(String(120), nullable=False)
    from_value: Mapped[str] = mapped_column(String(400), nullable=False)
    to_key: Mapped[str] = mapped_column(String(120), nullable=False)
    to_value: Mapped[str] = mapped_column(String(400), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(200), nullable=False)  # e.g., HAS_SKILL, ASSOCIATED_WITH

    source_extraction_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("extractions.id"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

