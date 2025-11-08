"""Project model for logical containers of uploads and graphs."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.graph import Graph
    from app.models.upload import Upload


class Project(Base):
    """
    Project model representing a logical container for uploads and graphs.

    Attributes:
        id: Primary key
        name: Project name
        labels: List of labels/tags for categorization
        created_at: Timestamp when project was created
        updated_at: Timestamp when project was last updated
        uploads: Related uploads (one-to-many)
        graphs: Related graphs (one-to-many)
    """

    __tablename__ = "projects"

    # Allow SQLAlchemy model to be used with Pydantic
    model_config = {"from_attributes": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    labels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    uploads: Mapped[list["Upload"]] = relationship(
        "Upload", back_populates="project", cascade="all, delete-orphan"
    )
    graphs: Mapped[list["Graph"]] = relationship(
        "Graph", back_populates="project", cascade="all, delete-orphan"
    )
