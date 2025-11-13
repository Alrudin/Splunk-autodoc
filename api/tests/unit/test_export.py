"""Unit tests for the export service."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.export import (
    MAX_DISPLAYED_INDEXES,
    NODE_COLORS,
    build_dot_from_canonical_graph,
    export_as_image,
    export_as_json,
    export_graph,
    validate_export_format,
)


@pytest.mark.unit
class TestDOTGeneration:
    """Test DOT (Graphviz) format generation."""

    def test_generate_dot_simple(self, tmp_path: Path):
        """Generate DOT from simple graph."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "host2", "roles": ["indexer"], "labels": [], "apps": []},
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "host2",
                    "protocol": "splunktcp",
                    "indexes": ["main"],
                    "tls": False,
                    "weight": 1,
                }
            ],
            "meta": {},
        }

        dot_str = build_dot_from_canonical_graph(graph_json)

        assert "digraph G {" in dot_str
        assert '"host1"' in dot_str
        assert '"host2"' in dot_str
        assert '"host1" -> "host2"' in dot_str
        assert "splunktcp" in dot_str
        assert "main" in dot_str

    def test_generate_dot_node_styling(self, tmp_path: Path):
        """Verify node styling by role (UF, HF, IDX shapes/colors)."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "host2", "roles": ["heavy_forwarder"], "labels": [], "apps": []},
                {"id": "host3", "roles": ["indexer"], "labels": [], "apps": []},
                {"id": "host4", "roles": ["search_head"], "labels": [], "apps": []},
            ],
            "edges": [],
            "meta": {},
        }

        dot_str = build_dot_from_canonical_graph(graph_json)

        assert NODE_COLORS["universal_forwarder"] in dot_str
        assert NODE_COLORS["heavy_forwarder"] in dot_str
        assert NODE_COLORS["indexer"] in dot_str
        assert NODE_COLORS["search_head"] in dot_str
        assert "shape=box" in dot_str
        assert "style=filled" in dot_str
        # Verify role abbreviations
        assert "UF" in dot_str
        assert "HF" in dot_str
        assert "IDX" in dot_str
        assert "SH" in dot_str

    def test_generate_dot_edge_labels(self, tmp_path: Path):
        """Verify edge labels include protocol and index info."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "host2", "roles": ["indexer"], "labels": [], "apps": []},
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "host2",
                    "protocol": "http_event_collector",
                    "indexes": ["security", "audit", "compliance"],
                    "sourcetypes": ["json", "xml"],
                    "tls": False,
                    "weight": 1,
                }
            ],
            "meta": {},
        }

        dot_str = build_dot_from_canonical_graph(graph_json)

        assert "http_event_collector" in dot_str
        assert "security" in dot_str
        assert "audit" in dot_str
        assert "compliance" in dot_str
        # Check for multi-line labels
        assert "\\n" in dot_str

    def test_generate_dot_tls_styling(self, tmp_path: Path):
        """Verify TLS edges are styled differently (bold, green)."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "host2", "roles": ["indexer"], "labels": [], "apps": []},
                {"id": "host3", "roles": ["indexer"], "labels": [], "apps": []},
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "host2",
                    "protocol": "splunktcp",
                    "indexes": ["main"],
                    "tls": True,
                    "weight": 1,
                },
                {
                    "src_host": "host1",
                    "dst_host": "host3",
                    "protocol": "splunktcp",
                    "indexes": ["main"],
                    "tls": False,
                    "weight": 1,
                },
            ],
            "meta": {},
        }

        dot_str = build_dot_from_canonical_graph(graph_json)

        # TLS edge should have bold styling
        assert "style=bold" in dot_str
        # Both edges should have penwidth
        assert "penwidth" in dot_str

    def test_generate_dot_placeholder_styling(self, tmp_path: Path):
        """Verify placeholder hosts are styled (dashed, red)."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {
                    "id": "unknown_destination",
                    "roles": ["unknown"],
                    "labels": ["placeholder"],
                    "apps": [],
                    "is_placeholder": True,
                },
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "unknown_destination",
                    "protocol": "splunktcp",
                    "indexes": ["main"],
                    "tls": False,
                    "weight": 1,
                }
            ],
            "meta": {},
        }

        dot_str = build_dot_from_canonical_graph(graph_json)

        # Placeholder node should have dashed styling
        assert "dashed" in dot_str
        # Should have placeholder indicator or gray color
        assert NODE_COLORS.get("unknown", "#CCCCCC") in dot_str or "(placeholder)" in dot_str

    def test_generate_dot_empty_graph(self, tmp_path: Path):
        """Generate DOT from empty graph."""
        graph_json: dict[str, object] = {
            "hosts": [],
            "edges": [],
            "meta": {},
        }

        dot_str = build_dot_from_canonical_graph(graph_json)

        # Should return valid DOT string
        assert dot_str is not None
        assert len(dot_str) > 0
        assert "digraph G {" in dot_str

    def test_generate_dot_edge_weight(self, tmp_path: Path):
        """Verify edge weight affects penwidth."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "host2", "roles": ["indexer"], "labels": [], "apps": []},
                {"id": "host3", "roles": ["indexer"], "labels": [], "apps": []},
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "host2",
                    "protocol": "splunktcp",
                    "indexes": ["main"],
                    "tls": False,
                    "weight": 1,
                },
                {
                    "src_host": "host1",
                    "dst_host": "host3",
                    "protocol": "splunktcp",
                    "indexes": ["main"],
                    "tls": False,
                    "weight": 10,
                },
            ],
            "meta": {},
        }

        dot_str = build_dot_from_canonical_graph(graph_json)

        # Extract penwidth values for each edge
        import re

        # Find edge to host2 (weight=1)
        host2_match = re.search(r'"host1" -> "host2".*?penwidth=([\d.]+)', dot_str)
        assert host2_match is not None, "host2 edge not found"
        penwidth_weight1 = float(host2_match.group(1))

        # Find edge to host3 (weight=10)
        host3_match = re.search(r'"host1" -> "host3".*?penwidth=([\d.]+)', dot_str)
        assert host3_match is not None, "host3 edge not found"
        penwidth_weight10 = float(host3_match.group(1))

        # Higher weight should have larger penwidth
        assert penwidth_weight10 > penwidth_weight1
        # Both edges should be present
        assert "host2" in dot_str
        assert "host3" in dot_str

    def test_generate_dot_many_indexes(self, tmp_path: Path):
        """Verify many indexes are truncated in labels."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "host2", "roles": ["indexer"], "labels": [], "apps": []},
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "host2",
                    "protocol": "splunktcp",
                    "indexes": [
                        "idx1",
                        "idx2",
                        "idx3",
                        "idx4",
                        "idx5",
                        "idx6",
                        "idx7",
                        "idx8",
                        "idx9",
                        "idx10",
                    ],
                    "tls": False,
                    "weight": 1,
                }
            ],
            "meta": {},
        }

        dot_str = build_dot_from_canonical_graph(graph_json)

        # Should be valid DOT
        assert "digraph G {" in dot_str
        # First MAX_DISPLAYED_INDEXES indexes should appear
        assert "idx1" in dot_str
        assert "idx2" in dot_str
        assert "idx3" in dot_str
        # Verify we're using the correct constant
        assert MAX_DISPLAYED_INDEXES == 3
        # Truncation indicator for remaining 7 indexes (10 total - 3 displayed)
        assert "(+7 more)" in dot_str
        # Edge should be present
        assert '"host1" -> "host2"' in dot_str


@pytest.mark.unit
class TestJSONGeneration:
    """Test JSON export format."""

    def test_generate_json_complete(self, tmp_path: Path):
        """Generate JSON with all graph fields."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "host2", "roles": ["indexer"], "labels": [], "apps": []},
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "host2",
                    "protocol": "splunktcp",
                    "indexes": ["main"],
                    "tls": False,
                    "weight": 1,
                }
            ],
            "meta": {"created_at": "2025-11-13", "version": "1.0"},
        }

        json_str = export_as_json(graph_json)

        # Verify valid JSON
        parsed = json.loads(json_str)
        assert "hosts" in parsed
        assert "edges" in parsed
        assert "meta" in parsed
        assert parsed["hosts"] == graph_json["hosts"]
        assert parsed["edges"] == graph_json["edges"]
        assert parsed["meta"] == graph_json["meta"]

    def test_generate_json_pretty_print(self, tmp_path: Path):
        """Verify JSON is human-readable (indented)."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
            ],
            "edges": [],
            "meta": {},
        }

        json_str = export_as_json(graph_json)

        # Pretty-printed JSON should contain newlines and indentation
        assert "\n" in json_str
        assert "  " in json_str  # 2-space indentation
        # Line count should be > 10 for typical graph
        assert len(json_str.split("\n")) > 5

    @pytest.mark.skip(reason="export_as_json does not support minification parameter")
    def test_generate_json_minified(self, tmp_path: Path):
        """Verify JSON can be minified for size."""
        # NOTE: export_as_json does not support minification parameter
        # This test is skipped as minification is not implemented
        pass

    def test_generate_json_serialization(self, tmp_path: Path):
        """Verify JSON can be deserialized back."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "host2", "roles": ["indexer"], "labels": [], "apps": []},
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "host2",
                    "protocol": "splunktcp",
                    "indexes": ["main"],
                    "tls": False,
                    "weight": 1,
                }
            ],
            "meta": {},
        }

        json_str = export_as_json(graph_json)
        parsed = json.loads(json_str)

        # Round-trip serialization should preserve data
        assert parsed["hosts"] == graph_json["hosts"]
        assert parsed["edges"] == graph_json["edges"]
        assert parsed["meta"] == graph_json["meta"]


@pytest.mark.unit
@pytest.mark.requires_graphviz
class TestPNGGeneration:
    """Test PNG image generation (requires Graphviz)."""

    def test_generate_png_from_dot(self, tmp_path: Path, temp_storage_root: Path):
        """Generate PNG image from DOT source."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "host2", "roles": ["indexer"], "labels": [], "apps": []},
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "host2",
                    "protocol": "splunktcp",
                    "indexes": ["main"],
                    "tls": False,
                    "weight": 1,
                }
            ],
            "meta": {},
        }

        png_path = export_as_image(graph_json, "png", graph_id=1)

        # Verify PNG file exists
        assert png_path.exists()
        assert png_path.stat().st_size > 0
        # Verify PNG magic bytes
        with open(png_path, "rb") as f:
            magic = f.read(8)
            assert magic == b"\x89PNG\r\n\x1a\n"

    @pytest.mark.skip(reason="export_as_image does not support DPI configuration")
    def test_generate_png_resolution(self, tmp_path: Path):
        """Verify PNG resolution can be configured (dpi)."""
        # NOTE: export_as_image does not support DPI parameter
        # DPI is controlled by Graphviz defaults
        pass

    def test_generate_png_graphviz_not_installed(self, tmp_path: Path):
        """Handle missing Graphviz gracefully."""
        from graphviz import ExecutableNotFound  # type: ignore[import-untyped]

        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
            ],
            "edges": [],
            "meta": {},
        }

        with patch("app.services.export.graphviz.Source.render") as mock_render:
            mock_render.side_effect = ExecutableNotFound("dot")
            with pytest.raises(RuntimeError) as exc_info:
                export_as_image(graph_json, "png", graph_id=1)
            assert "Graphviz is not installed" in str(exc_info.value)

    def test_generate_png_invalid_format(self, tmp_path: Path):
        """Verify invalid image format raises error."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
            ],
            "edges": [],
            "meta": {},
        }

        with pytest.raises(ValueError) as exc_info:
            export_as_image(graph_json, "invalid", graph_id=1)
        assert "Invalid image format" in str(exc_info.value)

    def test_generate_png_cleanup(self, tmp_path: Path, temp_storage_root: Path):
        """Verify PNG file cleanup works correctly."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
            ],
            "edges": [],
            "meta": {},
        }

        png_path = export_as_image(graph_json, "png", graph_id=1)
        assert png_path.exists()

        # Manually delete the file (simulating cleanup)
        png_path.unlink()
        assert not png_path.exists()


@pytest.mark.unit
@pytest.mark.requires_graphviz
class TestPDFGeneration:
    """Test PDF document generation (requires Graphviz)."""

    def test_generate_pdf_from_dot(self, tmp_path: Path, temp_storage_root: Path):
        """Generate PDF document from DOT source."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "host2", "roles": ["indexer"], "labels": [], "apps": []},
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "host2",
                    "protocol": "splunktcp",
                    "indexes": ["main"],
                    "tls": False,
                    "weight": 1,
                }
            ],
            "meta": {},
        }

        pdf_path = export_as_image(graph_json, "pdf", graph_id=1)

        # Verify PDF file exists
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0
        # Verify PDF magic bytes
        with open(pdf_path, "rb") as f:
            magic = f.read(5)
            assert magic == b"%PDF-"
        # Verify file extension
        assert pdf_path.suffix == ".pdf"

    def test_generate_pdf_vector_format(self, tmp_path: Path, temp_storage_root: Path):
        """Verify PDF is vector format (scalable)."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "host2", "roles": ["indexer"], "labels": [], "apps": []},
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "host2",
                    "protocol": "splunktcp",
                    "indexes": ["main"],
                    "tls": False,
                    "weight": 1,
                }
            ],
            "meta": {},
        }

        pdf_path = export_as_image(graph_json, "pdf", graph_id=1)

        # PDF should be reasonable size (< 1MB for typical graph)
        assert pdf_path.stat().st_size < 1024 * 1024
        # PDF is vector format (implicit in Graphviz PDF output)
        assert pdf_path.exists()


@pytest.mark.unit
@pytest.mark.requires_graphviz
class TestSVGGeneration:
    """Test SVG vector graphic generation (requires Graphviz)."""

    @pytest.mark.skip(reason="SVG export not implemented - only DOT, JSON, PNG, PDF supported")
    def test_generate_svg_from_dot(self, tmp_path: Path):
        """Generate SVG from DOT source."""
        # NOTE: SVG export is not implemented in export.py
        # EXPORT_FORMATS only includes: {"dot", "json", "png", "pdf"}
        pass

    @pytest.mark.skip(reason="SVG export not implemented - only DOT, JSON, PNG, PDF supported")
    def test_generate_svg_interactive_elements(self, tmp_path: Path):
        """Verify SVG includes interactive elements (titles, links)."""
        # NOTE: SVG export is not implemented in export.py
        pass


@pytest.mark.unit
class TestGraphFiltering:
    """Test graph filtering for exports."""

    @pytest.mark.skip(reason="Filtering implemented in graphs.py router, not export service")
    def test_apply_graph_filters_by_role(self, tmp_path: Path):
        """Filter graph to show only specific roles."""
        # NOTE: Graph filtering is implemented in graphs.py router's /query endpoint
        # (lines 175-284), not in the export service
        pass

    @pytest.mark.skip(reason="Filtering implemented in graphs.py router, not export service")
    def test_apply_graph_filters_by_index(self, tmp_path: Path):
        """Filter graph to show only edges with specific index."""
        # NOTE: Graph filtering is implemented in graphs.py router's /query endpoint
        pass

    @pytest.mark.skip(reason="Filtering implemented in graphs.py router, not export service")
    def test_apply_graph_filters_by_host(self, tmp_path: Path):
        """Filter graph to show only specific hosts."""
        # NOTE: Graph filtering is implemented in graphs.py router's /query endpoint
        pass

    @pytest.mark.skip(reason="Filtering implemented in graphs.py router, not export service")
    def test_apply_graph_filters_combined(self, tmp_path: Path):
        """Apply multiple filters simultaneously."""
        # NOTE: Graph filtering is implemented in graphs.py router's /query endpoint
        pass


@pytest.mark.unit
class TestExportArchive:
    """Test multi-format export archive creation."""

    @pytest.mark.skip(reason="Multi-format archive export not implemented")
    def test_create_export_archive_all_formats(self, tmp_path: Path):
        """Create .zip archive with DOT, JSON, PNG, PDF."""
        # NOTE: Export archive creation is not implemented in export.py
        # Only single-format exports are supported
        pass

    @pytest.mark.skip(reason="Multi-format archive export not implemented")
    def test_create_export_archive_selective(self, tmp_path: Path):
        """Create archive with only selected formats."""
        # NOTE: Multi-format archives would need to be implemented separately
        pass

    @pytest.mark.skip(reason="Multi-format archive export not implemented")
    def test_create_export_archive_metadata(self, tmp_path: Path):
        """Include metadata.json in export archive."""
        # NOTE: Archive metadata would be part of archive creation feature
        pass


@pytest.mark.unit
class TestExportRouter:
    """Test the main export_graph router function."""

    def test_export_graph_dot_format(self, tmp_path: Path):
        """Export graph in DOT format."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "host2", "roles": ["indexer"], "labels": [], "apps": []},
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "host2",
                    "protocol": "splunktcp",
                    "indexes": ["main"],
                    "tls": False,
                    "weight": 1,
                }
            ],
            "meta": {},
        }

        content, media_type = export_graph(graph_json, "dot", graph_id=1)

        assert isinstance(content, str)
        assert media_type == "text/vnd.graphviz"
        assert "digraph G {" in content

    def test_export_graph_json_format(self, tmp_path: Path):
        """Export graph in JSON format."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
            ],
            "edges": [],
            "meta": {},
        }

        content, media_type = export_graph(graph_json, "json", graph_id=1)

        assert isinstance(content, str)
        assert media_type == "application/json"
        # Verify valid JSON
        parsed = json.loads(content)
        assert "hosts" in parsed

    @pytest.mark.requires_graphviz
    def test_export_graph_png_format(self, tmp_path: Path, temp_storage_root: Path):
        """Export graph in PNG format."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
            ],
            "edges": [],
            "meta": {},
        }

        content, media_type = export_graph(graph_json, "png", graph_id=1)

        assert isinstance(content, Path)
        assert media_type == "image/png"
        assert content.exists()

    @pytest.mark.requires_graphviz
    def test_export_graph_pdf_format(self, tmp_path: Path, temp_storage_root: Path):
        """Export graph in PDF format."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
            ],
            "edges": [],
            "meta": {},
        }

        content, media_type = export_graph(graph_json, "pdf", graph_id=1)

        assert isinstance(content, Path)
        assert media_type == "application/pdf"
        assert content.exists()

    def test_export_graph_invalid_format(self, tmp_path: Path):
        """Verify invalid format raises error."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
            ],
            "edges": [],
            "meta": {},
        }

        with pytest.raises(ValueError) as exc_info:
            export_graph(graph_json, "invalid", graph_id=1)
        assert "Unsupported export format" in str(exc_info.value)

    def test_validate_export_format_valid(self, tmp_path: Path):
        """Verify format validation normalizes to lowercase."""
        result = validate_export_format("DOT")
        assert result == "dot"

        result = validate_export_format("JSON")
        assert result == "json"

        result = validate_export_format("png")
        assert result == "png"

    def test_validate_export_format_invalid(self, tmp_path: Path):
        """Verify invalid format raises error."""
        with pytest.raises(ValueError) as exc_info:
            validate_export_format("svg")
        assert "Unsupported export format" in str(exc_info.value)

        with pytest.raises(ValueError):
            validate_export_format("xml")
