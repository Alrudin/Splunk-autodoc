"""Graph model for versioned canonical structures."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base  # type: ignore

if TYPE_CHECKING:
    from app.models.finding import Finding  # type: ignore
    from app.models.job import Job  # type: ignore
    from app.models.project import Project  # type: ignore


class Graph(Base):
    """
    Graph model representing versioned canonical graph structures.

    Attributes:
        id: Primary key
        project_id: Foreign key to project
        job_id: Foreign key to job that generated this graph
        version: Version identifier for this graph
        json_blob: Canonical graph JSON (hosts, edges, meta)
        meta: Additional metadata about the graph
        created_at: Timestamp when graph was created
        project: Related project (many-to-one)
        job: Related job (one-to-one)
        findings: Related findings (one-to-many)
    """

    __tablename__ = "graphs"

    # Allow SQLAlchemy model to be used with Pydantic
    model_config = {"from_attributes": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    version: Mapped[str] = mapped_column(String, nullable=False)
    json_blob: Mapped[dict] = mapped_column(JSON, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="graphs")
    job: Mapped["Job"] = relationship("Job", back_populates="graph")
    findings: Mapped[list["Finding"]] = relationship(
        "Finding", back_populates="graph", cascade="all, delete-orphan"
    )
