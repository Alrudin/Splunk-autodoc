"""Project SQLAlchemy model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.graph import Graph
    from app.models.upload import Upload


class Project(Base):
    """Project model - container for uploads and graphs."""

    __tablename__ = "projects"

    # Fields
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    labels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    uploads: Mapped[list["Upload"]] = relationship(
        "Upload", back_populates="project", cascade="all, delete-orphan"
    )
    graphs: Mapped[list["Graph"]] = relationship(
        "Graph", back_populates="project", cascade="all, delete-orphan"
    )

    # Additional indexes
    __table_args__ = (
        Index("ix_projects_created_at", "created_at"),
    )
