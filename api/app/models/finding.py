"""Finding SQLAlchemy model."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.graph import Graph


class Finding(Base):
    """Finding model - validation issues discovered in graphs."""

    __tablename__ = "findings"

    # Fields
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    graph_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("graphs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    graph: Mapped["Graph"] = relationship("Graph", back_populates="findings")

    # Additional indexes
    __table_args__ = (
        Index("ix_findings_severity", "severity"),
        Index("ix_findings_code", "code"),
        Index("ix_findings_graph_severity", "graph_id", "severity"),
    )
