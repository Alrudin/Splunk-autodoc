"""Pydantic schemas for Graph entity and canonical graph structure."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.schemas.finding import FindingResponse
    from app.schemas.job import JobResponse
    from app.schemas.project import ProjectResponse


class HostSchema(BaseModel):
    """
    Host schema for canonical graph structure per spec section 4.2 and 11.

    Represents a single host in the Splunk topology with its roles, labels, and apps.
    """

    id: str = Field(description="Unique host identifier", examples=["hf01"])
    roles: list[str] = Field(
        default_factory=list, description="Host roles", examples=[["heavy_forwarder"]]
    )
    labels: list[str] = Field(
        default_factory=list, description="Host labels/tags", examples=[["prod", "site=eu1"]]
    )
    apps: list[str] = Field(
        default_factory=list, description="Installed Splunk apps", examples=[["Splunk_TA_nix"]]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "hf01",
                "roles": ["heavy_forwarder"],
                "labels": ["prod", "site=eu1"],
                "apps": ["Splunk_TA_nix", "Splunk_TA_windows"],
            }
        }
    )


class EdgeSchema(BaseModel):
    """
    Edge schema for canonical graph structure per spec section 4.2 and 11.

    Represents a data flow connection between two hosts with routing details.
    """

    src_host: str = Field(description="Source host ID", examples=["uf01"])
    dst_host: str = Field(description="Destination host ID", examples=["hf01"])
    protocol: Literal["splunktcp", "http_event_collector", "syslog", "tcp", "udp"] = Field(
        description="Transport protocol"
    )
    path_kind: Literal["forwarding", "hec", "syslog", "scripted_input", "modinput"] = Field(
        description="Data path type"
    )
    sources: list[str] = Field(
        default_factory=list,
        description="Input sources",
        examples=[["monitor:///var/log/messages"]],
    )
    sourcetypes: list[str] = Field(
        default_factory=list, description="Sourcetypes", examples=[["linux:messages"]]
    )
    indexes: list[str] = Field(
        default_factory=list, description="Target indexes", examples=[["os"]]
    )
    filters: list[str] = Field(
        default_factory=list,
        description="Applied transforms",
        examples=[["TRANSFORMS:route_os"]],
    )
    drop_rules: list[str] = Field(default_factory=list, description="Drop/nullQueue rules")
    tls: bool | None = Field(None, description="TLS enabled")
    weight: int = Field(default=1, ge=1, description="Edge weight/volume indicator")
    app_contexts: list[str] = Field(default_factory=list, description="App contexts")
    confidence: Literal["explicit", "derived"] = Field(
        default="explicit", description="Confidence level"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "src_host": "uf01",
                "dst_host": "hf01",
                "protocol": "splunktcp",
                "path_kind": "forwarding",
                "sources": ["monitor:///var/log/messages"],
                "sourcetypes": ["linux:messages"],
                "indexes": ["os"],
                "filters": ["TRANSFORMS:route_os"],
                "drop_rules": [],
                "tls": True,
                "weight": 14,
                "app_contexts": ["Splunk_TA_nix"],
                "confidence": "explicit",
            }
        }
    )


class GraphMetaSchema(BaseModel):
    """
    Metadata schema for canonical graph per spec section 4.2.

    Contains generation metadata, counts, and traceability information.
    """

    generator: str = Field(
        description="Generator identifier", examples=["splunk-autodoc-v2.0"]
    )
    generated_at: datetime = Field(description="Generation timestamp")
    host_count: int = Field(description="Total number of hosts", examples=[42])
    edge_count: int = Field(description="Total number of edges", examples=[156])
    source_hosts: list[str] = Field(
        default_factory=list, description="Source host identifiers"
    )
    traceability: dict[str, Any] = Field(
        default_factory=dict, description="File:line traceability pointers"
    )


class GraphResponse(BaseModel):
    """
    Response schema for Graph entity.

    The json_blob field contains the canonical graph structure with hosts, edges, and meta.
    Structure: {"hosts": [HostSchema], "edges": [EdgeSchema], "meta": GraphMetaSchema}
    """

    id: int = Field(description="Graph ID")
    project_id: int = Field(description="Parent project ID")
    job_id: int = Field(description="Job that generated this graph")
    version: str = Field(description="Graph version identifier", examples=["1.0"])
    json_blob: dict[str, Any] = Field(
        description="Canonical graph JSON containing hosts, edges, meta"
    )
    meta: dict[str, Any] = Field(description="Additional metadata")
    created_at: datetime = Field(description="Creation timestamp")
    project: "ProjectResponse | None" = Field(None, description="Parent project")
    job: "JobResponse | None" = Field(None, description="Source job")
    findings: list["FindingResponse"] | None = Field(None, description="Validation findings")

    model_config = ConfigDict(from_attributes=True)
