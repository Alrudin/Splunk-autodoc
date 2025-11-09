"""Pydantic schemas for Job entity."""

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.schemas.graph import GraphResponse
    from app.schemas.upload import UploadResponse

# Job status enum for strict validation per spec section 4.5
JobStatus = Literal["pending", "running", "completed", "failed"]


class JobCreate(BaseModel):
    """
    Schema for job creation.

    Note: Job creation requires only upload_id from URL path.
    No request body fields are required.
    """

    pass


class JobResponse(BaseModel):
    """Response schema for Job entity."""

    id: int = Field(description="Job ID")
    upload_id: int = Field(description="Parent upload ID")
    status: JobStatus = Field(description="Job execution status", examples=["pending"])
    log: str | None = Field(None, description="Execution logs, errors, warnings")
    started_at: datetime | None = Field(None, description="Job start timestamp")
    finished_at: datetime | None = Field(None, description="Job completion timestamp")
    created_at: datetime = Field(description="Job creation timestamp")
    upload: "UploadResponse | None" = Field(
        None, description="Related upload"
    )  # Typically loaded via lazy="selectin"
    graph: "GraphResponse | None" = Field(None, description="Generated graph if completed")

    model_config = ConfigDict(from_attributes=True)
