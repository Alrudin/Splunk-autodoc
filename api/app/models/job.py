"""Job model for parse/resolve requests."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.graph import Graph
    from app.models.upload import Upload


class Job(Base):
    """
    Job model representing parse/resolve processing requests.

    Attributes:
        id: Primary key
        upload_id: Foreign key to upload
        status: Job status (pending, running, completed, failed)
        log: Execution logs, errors, warnings
        started_at: Timestamp when job started processing
        finished_at: Timestamp when job finished processing
        created_at: Timestamp when job was created
        upload: Related upload (many-to-one)
        graph: Related graph if completed (one-to-one)
    """

    __tablename__ = "jobs"

    # Allow SQLAlchemy model to be used with Pydantic
    model_config = {"from_attributes": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    upload_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending", index=True)
    log: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    # Changed from lazy="selectin" to default lazy loading to avoid automatic loading of nested relationships
    upload: Mapped["Upload"] = relationship("Upload", back_populates="jobs")
    graph: Mapped["Graph | None"] = relationship(
        "Graph", back_populates="job", uselist=False, cascade="all, delete-orphan"
    )
