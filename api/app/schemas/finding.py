"""Pydantic schemas for Finding entity."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.schemas.graph import GraphResponse

# Finding severity enum per spec section 4.4
FindingSeverity = Literal["error", "warning", "info"]

# Known finding codes per spec section 4.4
FindingCode = Literal[
    "DANGLING_OUTPUT", "UNKNOWN_INDEX", "UNSECURED_PIPE", "DROP_PATH", "AMBIGUOUS_GROUP"
]


class FindingResponse(BaseModel):
    """
    Response schema for Finding entity.

    Findings represent validation issues discovered during graph analysis.

    Example:
        {
            "id": 1,
            "graph_id": 5,
            "severity": "warning",
            "code": "UNSECURED_PIPE",
            "message": "Splunktcp connection from uf01 to hf01 does not use TLS",
            "context": {
                "src_host": "uf01",
                "dst_host": "hf01",
                "protocol": "splunktcp",
                "file": "outputs.conf",
                "line": 42
            },
            "created_at": "2025-11-08T10:30:00Z"
        }

    Context Structure:
        The context field typically contains:
        - src_host, dst_host: affected hosts
        - protocol, index, sourcetype: affected data flow attributes
        - file, line: traceability to source configuration file
        - app: app context where issue was found
        - group: output group name (for AMBIGUOUS_GROUP)
        - Any other relevant metadata for troubleshooting
    """

    id: int = Field(description="Finding ID")
    graph_id: int = Field(description="Parent graph ID")
    severity: FindingSeverity = Field(description="Finding severity level", examples=["warning"])
    code: FindingCode = Field(description="Finding type code", examples=["UNSECURED_PIPE"])
    message: str = Field(
        description="Human-readable description",
        examples=["Splunktcp connection from uf01 to hf01 does not use TLS"],
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (file, line, affected components)",
        examples=[
            {
                "src_host": "uf01",
                "dst_host": "hf01",
                "protocol": "splunktcp",
                "file": "outputs.conf",
                "line": 42,
            }
        ],
    )
    created_at: datetime = Field(description="Finding creation timestamp")
    graph: "GraphResponse | None" = Field(None, description="Parent graph")

    model_config = ConfigDict(from_attributes=True)
