"""Upload model for artifact records."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.project import Project


class Upload(Base):
    """
    Upload model representing uploaded artifact files.

    Attributes:
        id: Primary key
        project_id: Foreign key to project
        filename: Original filename of uploaded file
        size: File size in bytes
        status: Upload status (pending, processing, completed, failed)
        storage_uri: Path to stored file
        created_at: Timestamp when upload was created
        project: Related project (many-to-one)
        jobs: Related jobs (one-to-many)
    """

    __tablename__ = "uploads"

    # Allow SQLAlchemy model to be used with Pydantic
    model_config = {"from_attributes": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending", index=True)
    storage_uri: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="uploads")
    jobs: Mapped[list["Job"]] = relationship(
        "Job", back_populates="upload", cascade="all, delete-orphan"
    )
