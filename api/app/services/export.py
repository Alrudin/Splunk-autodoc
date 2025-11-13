"""
Export Service for Graph Visualization

This module provides functionality for generating graph exports in multiple formats:
- DOT: Graphviz DOT format (plain text graph definition)
- JSON: Canonical graph structure as JSON
- PNG: Rendered graph image (requires system Graphviz)
- PDF: Rendered graph document (requires system Graphviz)

Dependencies:
    - Python graphviz package (wrapper around system Graphviz)
    - System Graphviz must be installed:
        - Debian/Ubuntu: apt-get install graphviz
        - Alpine: apk add graphviz
        - macOS: brew install graphviz

File Handling:
    - DOT and JSON exports return strings directly
    - PNG and PDF exports create temporary files that must be cleaned up by caller
    - Files are written to STORAGE_ROOT/exports/{graph_id}/

Integration:
    - Called by graphs router for export endpoints
    - Uses storage service for directory management
    - Converts canonical graph JSON to various formats per spec section 4.2
"""

import json
import logging
from pathlib import Path
from typing import Any

import graphviz  # type: ignore
from graphviz.backend import CalledProcessError, ExecutableNotFound  # type: ignore

from app.services.storage import get_exports_directory

# Supported export formats
EXPORT_FORMATS = {"dot", "json", "png", "pdf"}

# Graphviz layout engine for hierarchical graphs
LAYOUT_ENGINE = "dot"

# Graph attributes for better rendering
GRAPH_ATTRS = {
    "rankdir": "LR",  # Left to right layout
    "splines": "ortho",  # Orthogonal edges
    "nodesep": "0.5",  # Node separation
    "ranksep": "1.0",  # Rank separation
}

# Node colors by role
NODE_COLORS = {
    "universal_forwarder": "#90CAF9",  # Light blue
    "heavy_forwarder": "#81C784",  # Light green
    "indexer": "#FFB74D",  # Light orange
    "search_head": "#CE93D8",  # Light purple
    "unknown": "#E0E0E0",  # Gray
}

# Edge colors by protocol
EDGE_COLORS = {
    "splunktcp": "#1976D2",  # Blue
    "http_event_collector": "#388E3C",  # Green
    "syslog": "#F57C00",  # Orange
    "tcp": "#7B1FA2",  # Purple
    "udp": "#C2185B",  # Pink
}

# Maximum number of indexes to display in edge labels
MAX_DISPLAYED_INDEXES = 3

# Penwidth calculation constants
BASE_PENWIDTH = 1.0
WEIGHT_MULTIPLIER = 0.5
MAX_PENWIDTH = 5.0

logger = logging.getLogger(__name__)


def validate_export_format(export_format: str) -> str:
    """
    Validate that the export format is supported.

    Args:
        export_format: The export format string (case-insensitive)

    Returns:
        The validated format string in lowercase

    Raises:
        ValueError: If the format is not supported
    """
    format_lower = export_format.lower()
    if format_lower not in EXPORT_FORMATS:
        raise ValueError(
            f"Unsupported export format: {export_format}. "
            f"Supported formats: {', '.join(sorted(EXPORT_FORMATS))}"
        )
    return format_lower


def build_dot_from_canonical_graph(graph_json: dict[str, Any]) -> str:
    """
    Convert canonical graph JSON to Graphviz DOT format.

    The canonical graph structure (per spec 4.2) contains:
    - hosts: Array of host objects with id, roles, is_placeholder
    - edges: Array of edge objects with src_host, dst_host, protocol, indexes, etc.
    - meta: Metadata about the graph

    This function generates DOT syntax with:
    - Node styling based on role (different colors for UF, HF, IDX, SH)
    - Edge styling based on protocol (different colors)
    - TLS indicator (bold style for TLS-enabled edges)
    - Weight indicator (penwidth based on edge weight)

    Example DOT output:
        digraph G {
            rankdir=LR;
            "uf01" [label="uf01\nUF", shape=box, fillcolor="#90CAF9", style=filled];
            "hf01" [label="hf01\nHF", shape=box, fillcolor="#81C784", style=filled];
            "uf01" -> "hf01" [label="splunktcp\nmain", color="#1976D2"];
        }

    Args:
        graph_json: Canonical graph structure with hosts and edges arrays

    Returns:
        DOT format string representing the graph

    Raises:
        ValueError: If graph is empty or invalid
    """
    hosts = graph_json.get("hosts", [])
    edges = graph_json.get("edges", [])

    if not hosts and not edges:
        logger.warning("Empty graph provided for DOT export")
        # Return minimal valid DOT graph
        return "digraph G {\n    label=\"Empty Graph\";\n}\n"

    dot_lines = ["digraph G {"]

    # Add graph attributes
    for attr_key, attr_val in GRAPH_ATTRS.items():
        dot_lines.append(f'    {attr_key}="{attr_val}";')

    # Add node declarations
    for host in hosts:
        host_id = host.get("id", "unknown")
        roles = host.get("roles", [])
        is_placeholder = host.get("is_placeholder", False)

        # Determine node color based on primary role
        primary_role = roles[0] if roles else "unknown"
        color = NODE_COLORS.get(primary_role, NODE_COLORS["unknown"])

        # Build label with host ID and roles
        role_abbrev = {
            "universal_forwarder": "UF",
            "heavy_forwarder": "HF",
            "indexer": "IDX",
            "search_head": "SH",
            "unknown": "?",
        }
        role_labels = ", ".join(role_abbrev.get(r, r.upper()[:3]) for r in roles)
        label = f"{host_id}\\n{role_labels}"

        # Add placeholder indicator
        if is_placeholder:
            label += "\\n(placeholder)"

        # Node attributes with conditional style based on placeholder status
        style_value = "filled,dashed" if is_placeholder else "filled"
        node_attrs = [
            f'label="{label}"',
            "shape=box",
            f'fillcolor="{color}"',
            f'style="{style_value}"',
        ]

        dot_lines.append(f'    "{host_id}" [{", ".join(node_attrs)}];')

    # Add edge declarations
    for edge in edges:
        src = edge.get("src_host", "unknown")
        dst = edge.get("dst_host", "unknown")
        protocol = edge.get("protocol", "unknown")
        indexes = edge.get("indexes", [])
        tls_enabled = edge.get("tls", False)
        weight = edge.get("weight", 1)
        # Build label with protocol and indexes
        label_parts = [protocol]
        if indexes:
            # Limit to MAX_DISPLAYED_INDEXES for readability
            label_parts.append(", ".join(indexes[:MAX_DISPLAYED_INDEXES]))
            if len(indexes) > MAX_DISPLAYED_INDEXES:
                label_parts.append(f"(+{len(indexes) - MAX_DISPLAYED_INDEXES} more)")
        label = "\\n".join(label_parts)

        # Determine edge color based on protocol
        edge_color = EDGE_COLORS.get(protocol, "#999999")

        # Edge attributes
        edge_attrs = [
            f'label="{label}"',
            f'color="{edge_color}"',
        ]

        if tls_enabled:
            edge_attrs.append("style=bold")

        # Set penwidth based on weight (thicker for higher weight)
        # Cap at MAX_PENWIDTH
        penwidth = min(BASE_PENWIDTH + (weight - 1) * WEIGHT_MULTIPLIER, MAX_PENWIDTH)
        edge_attrs.append(f"penwidth={penwidth}")

        dot_lines.append(f'    "{src}" -> "{dst}" [{", ".join(edge_attrs)}];')

    dot_lines.append("}")

    return "\n".join(dot_lines) + "\n"


def export_as_dot(graph_json: dict[str, Any]) -> str:
    """
    Generate DOT format export (plain text graph definition).

    Args:
        graph_json: Canonical graph structure

    Returns:
        DOT format string
    """
    return build_dot_from_canonical_graph(graph_json)


def export_as_json(graph_json: dict[str, Any]) -> str:
    """
    Generate JSON format export.

    Simply serializes the canonical graph structure to pretty-printed JSON.
    This returns the graph as-is without transformation.

    Args:
        graph_json: Canonical graph structure

    Returns:
        Pretty-printed JSON string
    """
    return json.dumps(graph_json, indent=2, sort_keys=False)


def export_as_image(graph_json: dict[str, Any], export_format: str, graph_id: int) -> Path:
    """
    Generate PNG or PDF format export using Graphviz rendering.

    This function:
    1. Builds DOT string from canonical graph
    2. Creates Graphviz Source object
    3. Renders to PNG or PDF file
    4. Returns path to rendered file (caller must clean up)

    System Graphviz must be installed:
    - Debian/Ubuntu: apt-get install graphviz
    - Alpine: apk add graphviz
    - macOS: brew install graphviz

    Args:
        graph_json: Canonical graph structure
        export_format: Output format ("png" or "pdf")
        graph_id: Graph ID for filename

    Returns:
        Path to rendered file

    Raises:
        ValueError: If export_format is not "png" or "pdf"
        RuntimeError: If Graphviz is not installed or rendering fails
        OSError: If file I/O errors occur
    """
    if export_format not in {"png", "pdf"}:
        raise ValueError(f"Invalid image format: {export_format}. Must be 'png' or 'pdf'.")

    logger.info(f"Rendering graph {graph_id} to {export_format.upper()} format")

    try:
        # Build DOT string
        dot_string = build_dot_from_canonical_graph(graph_json)

        # Create Graphviz Source object
        source = graphviz.Source(dot_string, format=export_format)

        # Get exports directory
        exports_dir = get_exports_directory()

        # Create graph-specific subdirectory
        graph_export_dir = exports_dir / str(graph_id)
        graph_export_dir.mkdir(parents=True, exist_ok=True)

        # Generate output filename
        output_name = f"graph_{graph_id}"

        # Render to file (cleanup=True removes intermediate .dot file)
        source.render(
            filename=output_name,
            directory=str(graph_export_dir),
            format=export_format,
            cleanup=True,
        )

        # Return path to rendered file
        output_path = graph_export_dir / f"{output_name}.{export_format}"

        if not output_path.exists():
            raise RuntimeError(f"Rendering succeeded but output file not found: {output_path}")

        file_size = output_path.stat().st_size
        logger.info(f"Rendered graph {graph_id} to {export_format.upper()}: {file_size} bytes")

        return output_path

    except ExecutableNotFound as e:
        logger.error(f"Graphviz not found: {e}")
        raise RuntimeError(
            "Graphviz is not installed. Please install system Graphviz: "
            "apt-get install graphviz (Debian/Ubuntu) or "
            "apk add graphviz (Alpine) or "
            "brew install graphviz (macOS)"
        ) from e

    except CalledProcessError as e:
        logger.error(f"Graphviz rendering failed: {e}")
        logger.debug(f"DOT content:\n{dot_string}")
        raise RuntimeError(f"Graphviz rendering failed: {e}") from e

    except OSError as e:
        logger.error(f"File I/O error during export: {e}")
        raise


def export_graph(
    graph_json: dict[str, Any], export_format: str, graph_id: int
) -> tuple[str | Path, str]:
    """
    Main export function that routes to appropriate format handler.

    This function validates the format and delegates to the appropriate
    export handler. It returns a tuple of (content_or_path, media_type):
    - For DOT/JSON: content is string
    - For PNG/PDF: content is Path to file (caller must clean up)

    Args:
        graph_json: Canonical graph structure
        export_format: Export format (dot, json, png, pdf)
        graph_id: Graph ID for filename/logging

    Returns:
        Tuple of (content_or_path, media_type):
        - content_or_path: String content or Path to file
        - media_type: MIME type for HTTP response

    Raises:
        ValueError: If export_format is invalid or graph is empty
        RuntimeError: If Graphviz is not installed or rendering fails
        OSError: If file I/O errors occur
    """
    # Validate format
    format_lower = validate_export_format(export_format)

    # Route to appropriate handler
    if format_lower == "dot":
        content = export_as_dot(graph_json)
        return (content, "text/vnd.graphviz")

    elif format_lower == "json":
        content = export_as_json(graph_json)
        return (content, "application/json")

    elif format_lower == "png":
        file_path = export_as_image(graph_json, "png", graph_id)
        return (file_path, "image/png")

    elif format_lower == "pdf":
        file_path = export_as_image(graph_json, "pdf", graph_id)
        return (file_path, "application/pdf")

    else:
        # Should never reach here due to validate_export_format
        raise ValueError(f"Unsupported format: {export_format}")
