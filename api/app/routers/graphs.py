"""
Graphs Router

This module provides endpoints for graph retrieval, findings, query filtering,
validation, and exports. It handles:
- Listing graphs for a project
- Retrieving single graph with canonical JSON
- Getting findings for a graph
- Querying graphs with server-side filtering (by host, index, protocol)
- Re-running validation on existing graphs
- Exporting graphs in multiple formats (DOT, JSON, PNG, PDF)

Integration:
- Uses Graph and Finding models
- Calls validator service for re-validation
- Calls export service for format conversion
- Returns FileResponse with BackgroundTasks for cleanup
"""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.finding import Finding
from app.models.graph import Graph
from app.models.project import Project
from app.schemas.finding import FindingResponse
from app.schemas.graph import GraphResponse
from app.services import export, validator

router = APIRouter(prefix="", tags=["graphs"])

logger = logging.getLogger(__name__)


@router.get("/projects/{project_id}/graphs", response_model=list[GraphResponse])
def list_graphs(project_id: int, db: Session = Depends(get_db)) -> list[Graph]:  # noqa: B008
    """
    List all graphs for a project.

    Returns graphs in descending order by creation time (newest first).
    This allows frontend to display all graph versions for a project.

    Args:
        project_id: The project ID
        db: Database session

    Returns:
        List of Graph instances

    Raises:
        HTTPException: 404 if project not found
    """
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # Query all graphs for project
    graphs = (
        db.query(Graph)
        .filter(Graph.project_id == project_id)
        .order_by(Graph.created_at.desc())
        .all()
    )

    return graphs


@router.get("/graphs/{graph_id}", response_model=GraphResponse)
def get_graph(graph_id: int, db: Session = Depends(get_db)) -> Graph:  # noqa: B008
    """
    Get a single graph by ID.

    Returns the complete graph including json_blob with canonical graph structure
    (hosts, edges, meta). Frontend uses this to render the graph visualization.

    Args:
        graph_id: The graph ID
        db: Database session

    Returns:
        Graph instance with json_blob

    Raises:
        HTTPException: 404 if graph not found
    """
    graph = db.query(Graph).filter(Graph.id == graph_id).first()
    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph {graph_id} not found",
        )

    return graph


@router.get("/graphs/{graph_id}/findings", response_model=list[FindingResponse])
def get_findings(graph_id: int, db: Session = Depends(get_db)) -> list[Finding]:  # noqa: B008
    """
    Get all findings for a graph.

    Returns findings ordered by severity (ERROR, WARNING, INFO) and code.
    Frontend displays these in a findings table with filtering.

    Args:
        graph_id: The graph ID
        db: Database session

    Returns:
        List of Finding instances

    Raises:
        HTTPException: 404 if graph not found
    """
    # Verify graph exists
    graph = db.query(Graph).filter(Graph.id == graph_id).first()
    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph {graph_id} not found",
        )

    # Query all findings for graph
    findings = (
        db.query(Finding)
        .filter(Finding.graph_id == graph_id)
        .order_by(Finding.severity, Finding.code)
        .all()
    )

    return findings


@router.get("/graphs/{graph_id}/query", response_model=GraphResponse)
def query_graph(
    graph_id: int,
    host: str | None = Query(None, description="Filter by host ID (partial match)"),
    index: str | None = Query(None, description="Filter edges by index"),
    protocol: str | None = Query(None, description="Filter edges by protocol"),
    db: Session = Depends(get_db),  # noqa: B008
) -> GraphResponse:
    """
    Query graph with server-side filtering.

    Filters the canonical graph structure based on provided query parameters:
    - host: Partial match on src_host or dst_host
    - index: Exact match on indexes array
    - protocol: Exact match on protocol field

    If no filters provided, returns full graph.
    If filters provided, returns filtered graph with only matching edges and
    referenced hosts.

    This is a convenience endpoint for large graphs; frontend can also filter
    client-side for better interactivity.

    Args:
        graph_id: The graph ID
        host: Optional host ID filter (partial match)
        index: Optional index filter
        protocol: Optional protocol filter
        db: Database session

    Returns:
        Graph instance with filtered json_blob

    Raises:
        HTTPException: 404 if graph not found
    """
    # Query graph by ID
    graph = db.query(Graph).filter(Graph.id == graph_id).first()
    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph {graph_id} not found",
        )

    # Extract canonical graph from json_blob
    graph_json = graph.json_blob

    # If no filters provided, return full graph
    if not host and not index and not protocol:
        return graph

    # Apply server-side filtering
    hosts = graph_json.get("hosts", [])
    edges = graph_json.get("edges", [])
    meta = graph_json.get("meta", {}).copy()

    # Filter edges based on all provided filters
    filtered_edges = []
    for edge in edges:
        # Check host filter (partial match on src_host or dst_host)
        if host:
            src_match = host.lower() in edge.get("src_host", "").lower()
            dst_match = host.lower() in edge.get("dst_host", "").lower()
            if not (src_match or dst_match):
                continue

        # Check index filter (exact match in indexes array)
        if index:
            if index not in edge.get("indexes", []):
                continue

        # Check protocol filter (exact match)
        if protocol:
            if edge.get("protocol") != protocol:
                continue

        # Edge matches all filters
        filtered_edges.append(edge)

    # Filter hosts to only include those referenced in filtered edges
    referenced_host_ids = set()
    for edge in filtered_edges:
        referenced_host_ids.add(edge.get("src_host"))
        referenced_host_ids.add(edge.get("dst_host"))

    filtered_hosts = [h for h in hosts if h.get("id") in referenced_host_ids]

    # Build filtered graph JSON with updated meta counts
    filtered_meta = meta.copy()
    filtered_meta["host_count"] = len(filtered_hosts)
    filtered_meta["edge_count"] = len(filtered_edges)

    filtered_graph_json = {
        "hosts": filtered_hosts,
        "edges": filtered_edges,
        "meta": filtered_meta,
    }

    # Build response payload matching GraphResponse using original graph fields
    response_payload = {
        "id": graph.id,
        "project_id": graph.project_id,
        "job_id": graph.job_id,
        "version": graph.version,
        "json_blob": filtered_graph_json,
        "meta": graph.meta,
        "created_at": graph.created_at,
    }

    return GraphResponse.model_validate(response_payload)


@router.post("/graphs/{graph_id}/validate", response_model=list[FindingResponse])
def validate_graph(graph_id: int, db: Session = Depends(get_db)) -> list[Finding]:  # noqa: B008
    """
    Re-run validation on an existing graph.

    Deletes old findings and runs validation rules again. This is useful when:
    - Validation rules have been updated
    - User wants to refresh findings after manual review
    - Debugging validation logic

    Calls validator.validate_and_store_findings() which:
    1. Extracts hosts and edges from graph json_blob
    2. Runs all detection rules (DANGLING_OUTPUT, UNKNOWN_INDEX, etc.)
    3. Deletes old findings for this graph
    4. Creates new findings
    5. Returns list of Finding instances

    Args:
        graph_id: The graph ID
        db: Database session

    Returns:
        List of Finding instances (newly created)

    Raises:
        HTTPException: 404 if graph not found
        HTTPException: 500 if validation fails
    """
    # Verify graph exists
    graph = db.query(Graph).filter(Graph.id == graph_id).first()
    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph {graph_id} not found",
        )

    try:
        # Call validator service
        findings = validator.validate_and_store_findings(graph_id, db)

        logger.info(f"Re-validated graph {graph_id}: {len(findings)} findings")

        return findings

    except Exception as e:
        logger.error(f"Validation failed for graph {graph_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}",
        ) from e


@router.get("/graphs/{graph_id}/exports", response_model=None)
def export_graph_endpoint(
    graph_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),  # noqa: B008
    format: str = Query(..., description="Export format: dot, json, png, pdf"),
) -> Response | FileResponse:
    """
    Export graph in specified format.

    Supported formats:
    - dot: Graphviz DOT format (plain text graph definition)
    - json: Canonical graph structure as JSON
    - png: Rendered graph image (requires system Graphviz)
    - pdf: Rendered graph document (requires system Graphviz)

    For DOT/JSON formats, returns string content directly.
    For PNG/PDF formats, generates file and streams with FileResponse.
    Temporary files are cleaned up automatically via BackgroundTasks.

    System Graphviz must be installed for PNG/PDF exports:
    - Debian/Ubuntu: apt-get install graphviz
    - Alpine: apk add graphviz
    - macOS: brew install graphviz

    Args:
        graph_id: The graph ID
        format: Export format (dot, json, png, pdf)
        background_tasks: FastAPI background tasks for cleanup
        db: Database session

    Returns:
        Response (for DOT/JSON) or FileResponse (for PNG/PDF)

    Raises:
        HTTPException: 404 if graph not found
        HTTPException: 400 if format is invalid or graph is empty
        HTTPException: 500 if Graphviz error or I/O error
    """
    # Query graph by ID
    graph = db.query(Graph).filter(Graph.id == graph_id).first()
    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph {graph_id} not found",
        )

    try:
        # Validate format
        export.validate_export_format(format)

        # Extract canonical graph from json_blob
        graph_json = graph.json_blob

        # Call export service
        content_or_path, media_type = export.export_graph(graph_json, format, graph_id)

        # Handle response based on format
        if isinstance(content_or_path, str):
            # DOT or JSON: return string content directly
            return Response(
                content=content_or_path,
                media_type=media_type,
                headers={
                    "Content-Disposition": f'attachment; filename="graph_{graph_id}.{format}"'
                },
            )
        elif isinstance(content_or_path, Path):
            # PNG or PDF: stream file and clean up after
            file_path = content_or_path

            # Add background task to delete file after response
            def safe_unlink(path: str):
                try:
                    os.unlink(path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file {path}: {e}")

            background_tasks.add_task(safe_unlink, str(file_path))

            return FileResponse(
                path=str(file_path),
                media_type=media_type,
                filename=f"graph_{graph_id}.{format}",
                background=background_tasks,
            )
        else:
            raise RuntimeError(f"Unexpected export result type: {type(content_or_path)}")

    except ValueError as e:
        # Invalid format or empty graph
        logger.warning(f"Export validation error for graph {graph_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except RuntimeError as e:
        # Graphviz error
        logger.error(f"Export runtime error for graph {graph_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e

    except OSError as e:
        # File I/O error
        logger.error(f"Export I/O error for graph {graph_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File I/O error: {str(e)}",
        ) from e

    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected export error for graph {graph_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        ) from e
