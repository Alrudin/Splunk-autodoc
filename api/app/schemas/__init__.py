"""Pydantic schemas for API request/response validation."""

from app.schemas.finding import FindingResponse, FindingSeverity
from app.schemas.graph import EdgeSchema, GraphMetaSchema, GraphResponse, HostSchema
from app.schemas.job import JobCreate, JobResponse, JobStatus
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.schemas.upload import UploadCreate, UploadResponse, UploadStatus

# Rebuild models to resolve forward references from TYPE_CHECKING
ProjectResponse.model_rebuild()
UploadResponse.model_rebuild()
GraphResponse.model_rebuild()
JobResponse.model_rebuild()
FindingResponse.model_rebuild()

__all__ = [
    # Project schemas
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    # Upload schemas
    "UploadCreate",
    "UploadResponse",
    "UploadStatus",
    # Job schemas
    "JobCreate",
    "JobResponse",
    "JobStatus",
    # Graph schemas
    "GraphResponse",
    "HostSchema",
    "EdgeSchema",
    "GraphMetaSchema",
    # Finding schemas
    "FindingResponse",
    "FindingSeverity",
]
