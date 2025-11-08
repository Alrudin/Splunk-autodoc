"""Finding model for validation issues."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base  # type: ignore

if TYPE_CHECKING:
    from app.models.graph import Graph  # type: ignore


class Finding(Base):
    """
    Finding model representing validation issues linked to a graph.

    Attributes:
        id: Primary key
        graph_id: Foreign key to graph
        severity: Finding severity (error, warning, info)
        code: Finding type code (e.g., DANGLING_OUTPUT, UNKNOWN_INDEX)
        message: Human-readable description of the finding
        context: Additional context (file, line, affected components)
        created_at: Timestamp when finding was created
        graph: Related graph (many-to-one)
    """

    __tablename__ = "findings"

    # Allow SQLAlchemy model to be used with Pydantic
    model_config = {"from_attributes": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    graph_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("graphs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(String, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    graph: Mapped["Graph"] = relationship("Graph", back_populates="findings")
