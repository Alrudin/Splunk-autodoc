"""Pydantic schemas for Project entity."""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.schemas.graph import GraphResponse
    from app.schemas.upload import UploadResponse


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""

    name: str = Field(
        min_length=1,
        max_length=255,
        description="Project name",
        examples=["Production Deployment"],
    )
    labels: list[str] = Field(
        default_factory=list,
        description="List of labels/tags for categorization",
        examples=[["prod", "us-east-1"]],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Production Deployment",
                "labels": ["prod", "us-east-1", "v2.0"],
            }
        }
    )


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: str | None = Field(None, min_length=1, max_length=255, description="Updated project name")
    labels: list[str] | None = Field(None, description="Updated labels list")


class ProjectResponse(BaseModel):
    """Response schema for Project entity."""

    id: int = Field(description="Project ID")
    name: str = Field(description="Project name")
    labels: list[str] = Field(description="Project labels")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    uploads: list["UploadResponse"] | None = Field(None, description="Related uploads")
    graphs: list["GraphResponse"] | None = Field(None, description="Related graphs")

    model_config = ConfigDict(from_attributes=True)
