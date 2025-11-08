"""Graph SQLAlchemy model."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.finding import Finding
    from app.models.job import Job
    from app.models.project import Project


class Graph(Base):
    """Graph model - generated flow graph."""

    __tablename__ = "graphs"

    # Fields
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    json_blob: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="graphs")
    job: Mapped["Job | None"] = relationship("Job", back_populates="graph")
    findings: Mapped[list["Finding"]] = relationship(
        "Finding", back_populates="graph", cascade="all, delete-orphan"
    )

    # Additional indexes and constraints
    __table_args__ = (
        Index("ix_graphs_created_at", "created_at"),
        UniqueConstraint("project_id", "version", name="uq_graphs_project_version"),
        Index("ix_graphs_project_version", "project_id", "version"),
    )
