"""Pydantic schemas for Upload entity."""

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.schemas.job import JobResponse
    from app.schemas.project import ProjectResponse

# Upload status enum for type safety
UploadStatus = Literal["pending", "processing", "completed", "failed"]


class UploadCreate(BaseModel):
    """
    Schema for upload creation (documentation purposes).

    Note: File upload uses multipart/form-data with UploadFile parameter.
    This schema is primarily for OpenAPI documentation completeness.
    """

    filename: str = Field(description="Original filename", examples=["splunk_etc.zip"])
    project_id: int = Field(description="Parent project ID", examples=[1])


class UploadResponse(BaseModel):
    """Response schema for Upload entity."""

    id: int = Field(description="Upload ID")
    project_id: int = Field(description="Parent project ID")
    filename: str = Field(description="Original filename")
    size: int = Field(description="File size in bytes", examples=[1048576])
    status: UploadStatus = Field(description="Upload status", examples=["pending"])
    storage_uri: str = Field(
        description="Storage path", examples=["/data/artifacts/123/upload.zip"]
    )
    created_at: datetime = Field(description="Upload timestamp")
    project: "ProjectResponse | None" = Field(None, description="Parent project")
    jobs: list["JobResponse"] | None = Field(None, description="Related jobs")

    model_config = ConfigDict(from_attributes=True)
