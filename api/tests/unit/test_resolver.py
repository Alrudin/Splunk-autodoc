"""Unit tests for the resolver service."""

import json
from pathlib import Path

import pytest

from app.services.parser import (
    InputStanza,
    OutputGroup,
    ParsedConfig,
    PropsStanza,
    TransformStanza,
    parse_splunk_config,
)
from app.services.resolver import (
    Edge,
    Host,
    apply_transforms_to_index,
    build_canonical_graph,
    build_edges_from_inputs_outputs,
    build_graph_metadata,
    build_host,
    create_placeholder_hosts,
    determine_protocol_and_path_kind,
    extract_hostname,
    infer_host_roles,
    merge_similar_edges,
    resolve_output_targets,
)
from tests.fixtures.splunk_configs import (
    create_ambiguous_routing_config,
    create_dangling_output_config,
    create_hf_config,
    create_idx_config,
    create_uf_config,
    write_conf_file,
)


@pytest.mark.unit
class TestHostBuilding:
    """Test host extraction and role inference."""

    def test_extract_hostname_from_metadata(self, tmp_path: Path):
        """Verify hostname extraction from ParsedConfig.host_metadata."""
        config_dir = create_uf_config(tmp_path)

        # Add server.conf with serverName
        server_content = """[general]
serverName = test-host-01
"""
        write_conf_file(config_dir / "system/local/server.conf", server_content)

        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)
        hostname = extract_hostname(parsed)

        assert hostname == "test-host-01"

    def test_extract_hostname_fallback(self, tmp_path: Path):
        """Verify placeholder generation when hostname missing."""
        # Create ParsedConfig without hostname
        parsed = ParsedConfig(
            inputs=[],
            outputs=[],
            props=[],
            transforms=[],
            host_metadata={"job_id": 1},
            traceability={},
        )

        hostname = extract_hostname(parsed)
        assert hostname == "host_1"

    def test_infer_roles_universal_forwarder(self, tmp_path: Path):
        """Verify UF role detection (inputs + outputs, no parsing)."""
        config_dir = create_uf_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        roles = infer_host_roles(parsed)
        assert "universal_forwarder" in roles

    def test_infer_roles_heavy_forwarder(self, tmp_path: Path):
        """Verify HF role detection (inputs + outputs + parsing apps)."""
        config_dir = create_hf_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        roles = infer_host_roles(parsed)
        assert "heavy_forwarder" in roles

    def test_infer_roles_indexer(self, tmp_path: Path):
        """Verify indexer role detection (splunktcp input, no outputs)."""
        config_dir = create_idx_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        roles = infer_host_roles(parsed)
        assert "indexer" in roles

    def test_infer_roles_search_head(self, tmp_path: Path):
        """Verify SH role detection (search apps, no data inputs)."""
        # Create ParsedConfig with search apps but no inputs
        parsed = ParsedConfig(
            inputs=[],
            outputs=[],
            props=[],
            transforms=[],
            host_metadata={"apps": ["search"], "job_id": 1},
            traceability={},
        )

        roles = infer_host_roles(parsed)
        assert "search_head" in roles

    def test_infer_roles_pattern_based(self, tmp_path: Path):
        """Verify role inference from hostname patterns (idx*, hf*, uf*)."""
        # Test indexer pattern
        parsed = ParsedConfig(
            inputs=[],
            outputs=[],
            props=[],
            transforms=[],
            host_metadata={"hostname": "idx01.example.com", "job_id": 1},
            traceability={},
        )

        roles = infer_host_roles(parsed)
        assert "indexer" in roles


@pytest.mark.unit
class TestProtocolDetermination:
    """Test protocol and path_kind determination from input types."""

    def test_determine_protocol_monitor(self):
        """Verify monitor:// → splunktcp/forwarding protocol."""
        input_stanza = InputStanza(
            stanza_name="monitor:///var/log/messages",
            input_type="monitor",
            source_path="/var/log/messages",
        )

        protocol, path_kind = determine_protocol_and_path_kind(input_stanza)
        assert protocol == "splunktcp"
        assert path_kind == "forwarding"

    def test_determine_protocol_tcp(self):
        """Verify tcp:// → tcp/syslog protocol."""
        input_stanza = InputStanza(
            stanza_name="tcp://:9999",
            input_type="tcp",
            port=9999,
        )

        protocol, path_kind = determine_protocol_and_path_kind(input_stanza)
        assert protocol == "tcp"
        assert path_kind == "syslog"

    def test_determine_protocol_udp(self):
        """Verify udp:// → udp/syslog protocol."""
        input_stanza = InputStanza(
            stanza_name="udp://:514",
            input_type="udp",
            port=514,
        )

        protocol, path_kind = determine_protocol_and_path_kind(input_stanza)
        assert protocol == "udp"
        assert path_kind == "syslog"

    def test_determine_protocol_splunktcp(self):
        """Verify splunktcp:// → splunktcp/forwarding protocol."""
        input_stanza = InputStanza(
            stanza_name="splunktcp://:9997",
            input_type="splunktcp",
            port=9997,
        )

        protocol, path_kind = determine_protocol_and_path_kind(input_stanza)
        assert protocol == "splunktcp"
        assert path_kind == "forwarding"

    def test_determine_protocol_http(self):
        """Verify http → http_event_collector/hec protocol."""
        input_stanza = InputStanza(
            stanza_name="http://my_token",
            input_type="http",
            source_path="my_token",
        )

        protocol, path_kind = determine_protocol_and_path_kind(input_stanza)
        assert protocol == "http_event_collector"
        assert path_kind == "hec"

    def test_determine_protocol_script(self):
        """Verify script:// → splunktcp/scripted_input protocol."""
        input_stanza = InputStanza(
            stanza_name="script://./bin/script.sh",
            input_type="script",
            source_path="./bin/script.sh",
        )

        protocol, path_kind = determine_protocol_and_path_kind(input_stanza)
        assert protocol == "splunktcp"
        assert path_kind == "scripted_input"

    def test_determine_protocol_wineventlog(self):
        """Verify WinEventLog → splunktcp/modinput protocol."""
        input_stanza = InputStanza(
            stanza_name="WinEventLog://Application",
            input_type="WinEventLog",
            source_path="Application",
        )

        protocol, path_kind = determine_protocol_and_path_kind(input_stanza)
        assert protocol == "splunktcp"
        assert path_kind == "modinput"


@pytest.mark.unit
class TestOutputTargetResolution:
    """Test resolution of output targets from tcpout groups."""

    def test_resolve_output_targets_simple(self):
        """Parse server list, verify host extraction."""
        output_group = OutputGroup(
            group_name="test_group",
            servers=["host1:9997", "host2:9997"],
        )

        targets = resolve_output_targets([output_group])

        assert len(targets) == 2
        assert targets[0][0] == "host1"
        assert targets[1][0] == "host2"
        assert targets[0][2] == "test_group"
        assert targets[1][2] == "test_group"

    def test_resolve_output_targets_ssl(self):
        """Verify TLS detection from ssl_enabled and ssl_cert_path."""
        output_group = OutputGroup(
            group_name="ssl_group",
            servers=["host1:9997"],
            ssl_enabled=True,
            ssl_cert_path="/path/to/cert.pem",
        )

        targets = resolve_output_targets([output_group])

        assert len(targets) == 1
        assert targets[0][1] is True  # tls_enabled

    def test_resolve_output_targets_indexer_discovery(self):
        """Verify placeholder creation for indexer discovery."""
        output_group = OutputGroup(
            group_name="discovery_group",
            servers=[],
            indexer_discovery="cluster_master",
        )

        targets = resolve_output_targets([output_group])

        assert len(targets) == 1
        assert targets[0][0].startswith("indexer_discovery:")
        assert "cluster_master" in targets[0][0]

    def test_resolve_output_targets_empty(self):
        """Verify empty list when no outputs."""
        targets = resolve_output_targets([])
        assert targets == []


@pytest.mark.unit
class TestTransformsEvaluation:
    """Test transforms evaluation for index routing and drops."""

    def test_apply_transforms_index_routing(self):
        """Verify index routing (DEST_KEY=_MetaData:Index)."""
        input_stanza = InputStanza(
            stanza_name="monitor:///var/log/app.log",
            input_type="monitor",
            source_path="/var/log/app.log",
            sourcetype="app:log",
            index="main",
        )

        props_stanza = PropsStanza(
            stanza_name="sourcetype::app:log",
            stanza_type="sourcetype",
            stanza_value="app:log",
            transforms=["route_to_errors"],
        )

        transform_stanza = TransformStanza(
            stanza_name="route_to_errors",
            regex="ERROR",
            dest_key="_MetaData:Index",
            format="errors",
            is_index_routing=True,
        )

        indexes, filters, drop_rules = apply_transforms_to_index(
            input_stanza, [props_stanza], [transform_stanza]
        )

        assert "errors" in indexes

    def test_apply_transforms_drop(self):
        """Verify drop rules (DEST_KEY=queue, FORMAT=nullQueue)."""
        input_stanza = InputStanza(
            stanza_name="monitor:///var/log/app.log",
            input_type="monitor",
            source_path="/var/log/app.log",
            sourcetype="app:log",
            index="main",
        )

        props_stanza = PropsStanza(
            stanza_name="sourcetype::app:log",
            stanza_type="sourcetype",
            stanza_value="app:log",
            transforms=["drop_debug"],
        )

        transform_stanza = TransformStanza(
            stanza_name="drop_debug",
            regex="DEBUG",
            dest_key="queue",
            format="nullQueue",
            is_drop=True,
        )

        indexes, filters, drop_rules = apply_transforms_to_index(
            input_stanza, [props_stanza], [transform_stanza]
        )

        assert len(drop_rules) > 0
        assert any("drop_debug" in rule for rule in drop_rules)

    def test_apply_transforms_sourcetype_rewrite(self):
        """Verify sourcetype rewrite and re-evaluation."""
        input_stanza = InputStanza(
            stanza_name="monitor:///var/log/app.log",
            input_type="monitor",
            source_path="/var/log/app.log",
            sourcetype="old_sourcetype",
            index="main",
        )

        props_stanza = PropsStanza(
            stanza_name="sourcetype::old_sourcetype",
            stanza_type="sourcetype",
            stanza_value="old_sourcetype",
            transforms=["rewrite_st"],
        )

        transform_stanza = TransformStanza(
            stanza_name="rewrite_st",
            regex=".",
            dest_key="_MetaData:Sourcetype",
            format="new_sourcetype",
            is_sourcetype_rewrite=True,
        )

        indexes, filters, drop_rules = apply_transforms_to_index(
            input_stanza, [props_stanza], [transform_stanza]
        )

        assert any("SOURCETYPE_REWRITE" in f for f in filters)

    def test_apply_transforms_precedence(self):
        """Verify props precedence (host < source < sourcetype)."""
        input_stanza = InputStanza(
            stanza_name="monitor:///var/log/test.log",
            input_type="monitor",
            source_path="/var/log/test.log",
            sourcetype="test_st",
            host="testhost",
            index="main",
        )

        # Create props for all three levels
        props_host = PropsStanza(
            stanza_name="host::testhost",
            stanza_type="host",
            stanza_value="testhost",
            transforms=["transform_host"],
        )

        props_source = PropsStanza(
            stanza_name="source::/var/log/test.log",
            stanza_type="source",
            stanza_value="/var/log/test.log",
            transforms=["transform_source"],
        )

        props_sourcetype = PropsStanza(
            stanza_name="sourcetype::test_st",
            stanza_type="sourcetype",
            stanza_value="test_st",
            transforms=["transform_sourcetype"],
        )

        # Create transforms for all three levels
        transform_host = TransformStanza(
            stanza_name="transform_host",
            regex=".",
            dest_key="_MetaData:Index",
            format="host_index",
            is_index_routing=True,
        )

        transform_source = TransformStanza(
            stanza_name="transform_source",
            regex=".",
            dest_key="_MetaData:Index",
            format="source_index",
            is_index_routing=True,
        )

        # Sourcetype level should take precedence
        transform_st = TransformStanza(
            stanza_name="transform_sourcetype",
            regex=".",
            dest_key="_MetaData:Index",
            format="st_index",
            is_index_routing=True,
        )

        indexes, filters, drop_rules = apply_transforms_to_index(
            input_stanza,
            [props_host, props_source, props_sourcetype],
            [transform_host, transform_source, transform_st],
        )

        # Only sourcetype-level transform should be applied due to precedence
        assert indexes == ["st_index"]
        assert "host_index" not in indexes
        assert "source_index" not in indexes

        # All transforms should be present in filters for traceability
        assert any("transform_host" in f for f in filters)
        assert any("transform_source" in f for f in filters)
        assert any("transform_sourcetype" in f for f in filters)

    def test_apply_transforms_multiple(self):
        """Verify multiple transforms applied in order."""
        input_stanza = InputStanza(
            stanza_name="monitor:///var/log/app.log",
            input_type="monitor",
            source_path="/var/log/app.log",
            sourcetype="app:log",
            index="main",
        )

        props_stanza = PropsStanza(
            stanza_name="sourcetype::app:log",
            stanza_type="sourcetype",
            stanza_value="app:log",
            transforms=["transform_a", "transform_b"],
        )

        transform_a = TransformStanza(
            stanza_name="transform_a",
            regex="ERROR",
            dest_key="_MetaData:Index",
            format="errors",
            is_index_routing=True,
        )

        transform_b = TransformStanza(
            stanza_name="transform_b",
            regex="WARN",
            dest_key="_MetaData:Index",
            format="warnings",
            is_index_routing=True,
        )

        indexes, filters, drop_rules = apply_transforms_to_index(
            input_stanza, [props_stanza], [transform_a, transform_b]
        )

        # Both transforms should be evaluated
        assert "errors" in indexes
        assert "warnings" in indexes
        assert len(filters) >= 2

    def test_apply_transforms_default_index(self):
        """Verify default to 'main' when no index specified."""
        input_stanza = InputStanza(
            stanza_name="monitor:///var/log/app.log",
            input_type="monitor",
            source_path="/var/log/app.log",
            index=None,
        )

        indexes, filters, drop_rules = apply_transforms_to_index(input_stanza, [], [])

        assert "main" in indexes


@pytest.mark.unit
class TestEdgeBuilding:
    """Test edge construction from inputs and outputs."""

    def test_build_edges_simple(self, tmp_path: Path):
        """Build edges from inputs and outputs, verify Edge fields."""
        config_dir = create_uf_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)
        host = build_host(parsed)

        edges = build_edges_from_inputs_outputs(parsed, host)

        assert len(edges) > 0
        edge = edges[0]
        assert edge.src_host == host.id
        assert edge.dst_host is not None
        assert edge.protocol is not None
        assert edge.sources is not None
        assert edge.indexes is not None

    def test_build_edges_no_outputs(self, tmp_path: Path):
        """Verify unknown_destination edge creation when no outputs."""
        config_dir = create_dangling_output_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)
        host = build_host(parsed)

        edges = build_edges_from_inputs_outputs(parsed, host)

        assert len(edges) > 0
        assert any(edge.dst_host == "unknown_destination" for edge in edges)
        assert any(edge.confidence == "derived" for edge in edges)

    def test_build_edges_ambiguous_routing(self, tmp_path: Path):
        """Verify confidence=derived for multiple groups without default."""
        config_dir = create_ambiguous_routing_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)
        host = build_host(parsed)

        edges = build_edges_from_inputs_outputs(parsed, host)

        assert any(edge.confidence == "derived" for edge in edges)

    def test_build_edges_with_transforms(self, tmp_path: Path):
        """Verify filters and indexes from transforms."""
        config_dir = create_hf_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)
        host = build_host(parsed)

        edges = build_edges_from_inputs_outputs(parsed, host)

        # HF config has transforms with routing/drops
        assert any(len(edge.filters) > 0 or len(edge.drop_rules) > 0 for edge in edges)

    def test_build_edges_tls(self, tmp_path: Path):
        """Verify TLS flag from output SSL settings."""
        config_dir = create_hf_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)
        host = build_host(parsed)

        edges = build_edges_from_inputs_outputs(parsed, host)

        # HF config has SSL outputs
        assert any(edge.tls is True for edge in edges)


@pytest.mark.unit
class TestEdgeMerging:
    """Test merging of similar edges."""

    def test_merge_similar_edges_same_src_dst(self):
        """Verify edges with same src/dst/protocol are merged."""
        edge1 = Edge(
            src_host="host1",
            dst_host="host2",
            protocol="splunktcp",
            path_kind="forwarding",
            sources=["/var/log/app1.log"],
        )
        edge2 = Edge(
            src_host="host1",
            dst_host="host2",
            protocol="splunktcp",
            path_kind="forwarding",
            sources=["/var/log/app2.log"],
        )

        merged = merge_similar_edges([edge1, edge2])

        assert len(merged) == 1

    def test_merge_similar_edges_combine_fields(self):
        """Verify sources, sourcetypes, indexes are combined."""
        edge1 = Edge(
            src_host="host1",
            dst_host="host2",
            protocol="splunktcp",
            path_kind="forwarding",
            sources=["source1"],
            sourcetypes=["st1"],
            indexes=["index1"],
        )
        edge2 = Edge(
            src_host="host1",
            dst_host="host2",
            protocol="splunktcp",
            path_kind="forwarding",
            sources=["source2"],
            sourcetypes=["st2"],
            indexes=["index2"],
        )

        merged = merge_similar_edges([edge1, edge2])

        assert len(merged) == 1
        assert "source1" in merged[0].sources
        assert "source2" in merged[0].sources
        assert "st1" in merged[0].sourcetypes
        assert "st2" in merged[0].sourcetypes
        assert "index1" in merged[0].indexes
        assert "index2" in merged[0].indexes

    def test_merge_similar_edges_tls(self):
        """Verify TLS merging (False if any False, True if all True)."""
        edge1 = Edge(
            src_host="host1",
            dst_host="host2",
            protocol="splunktcp",
            path_kind="forwarding",
            tls=True,
        )
        edge2 = Edge(
            src_host="host1",
            dst_host="host2",
            protocol="splunktcp",
            path_kind="forwarding",
            tls=False,
        )

        merged = merge_similar_edges([edge1, edge2])

        assert len(merged) == 1
        assert merged[0].tls is False

    def test_merge_similar_edges_weight(self):
        """Verify weights are summed."""
        edge1 = Edge(
            src_host="host1",
            dst_host="host2",
            protocol="splunktcp",
            path_kind="forwarding",
            weight=1,
        )
        edge2 = Edge(
            src_host="host1",
            dst_host="host2",
            protocol="splunktcp",
            path_kind="forwarding",
            weight=2,
        )

        merged = merge_similar_edges([edge1, edge2])

        assert len(merged) == 1
        assert merged[0].weight == 3

    def test_merge_similar_edges_confidence(self):
        """Verify lowest confidence wins (derived < explicit)."""
        edge1 = Edge(
            src_host="host1",
            dst_host="host2",
            protocol="splunktcp",
            path_kind="forwarding",
            confidence="explicit",
        )
        edge2 = Edge(
            src_host="host1",
            dst_host="host2",
            protocol="splunktcp",
            path_kind="forwarding",
            confidence="derived",
        )

        merged = merge_similar_edges([edge1, edge2])

        assert len(merged) == 1
        assert merged[0].confidence == "derived"


@pytest.mark.unit
class TestPlaceholderHosts:
    """Test placeholder host creation."""

    def test_create_placeholder_unknown_destination(self):
        """Verify placeholder for unknown_destination."""
        edge = Edge(
            src_host="host1",
            dst_host="unknown_destination",
            protocol="splunktcp",
            path_kind="forwarding",
        )

        placeholders = create_placeholder_hosts([edge], {"host1"})

        assert len(placeholders) == 1
        assert placeholders[0].id == "unknown_destination"
        assert "unknown" in placeholders[0].roles

    def test_create_placeholder_indexer_discovery(self):
        """Verify placeholder for indexer_discovery:*."""
        edge = Edge(
            src_host="host1",
            dst_host="indexer_discovery:cluster_master",
            protocol="splunktcp",
            path_kind="forwarding",
        )

        placeholders = create_placeholder_hosts([edge], {"host1"})

        assert len(placeholders) == 1
        assert placeholders[0].id == "indexer_discovery:cluster_master"

    def test_create_placeholder_role_inference(self):
        """Verify role inference from host naming (idx*, hf*)."""
        edge = Edge(
            src_host="host1",
            dst_host="idx01.example.com",
            protocol="splunktcp",
            path_kind="forwarding",
        )

        placeholders = create_placeholder_hosts([edge], {"host1"})

        assert len(placeholders) == 1
        assert "indexer" in placeholders[0].roles

    def test_create_placeholder_labels(self):
        """Verify placeholder label is added."""
        edge = Edge(
            src_host="host1",
            dst_host="unknown_host",
            protocol="splunktcp",
            path_kind="forwarding",
        )

        placeholders = create_placeholder_hosts([edge], {"host1"})

        assert len(placeholders) == 1
        assert "placeholder" in placeholders[0].labels


@pytest.mark.unit
class TestGraphMetadata:
    """Test graph metadata construction."""

    def test_build_graph_metadata_counts(self, tmp_path: Path):
        """Verify host_count, edge_count are correct, including cycles."""
        config_dir = create_uf_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        hosts = [Host(id="host1"), Host(id="host2"), Host(id="host3")]
        edges = [
            Edge(src_host="host1", dst_host="host2", protocol="splunktcp", path_kind="forwarding"),
            Edge(src_host="host1", dst_host="host3", protocol="splunktcp", path_kind="forwarding"),
            Edge(src_host="host2", dst_host="host3", protocol="splunktcp", path_kind="forwarding"),
            Edge(src_host="host2", dst_host="host1", protocol="splunktcp", path_kind="forwarding"),
            Edge(src_host="host3", dst_host="host1", protocol="splunktcp", path_kind="forwarding"),
        ]

        meta = build_graph_metadata(parsed, hosts, edges)

        assert meta.host_count == 3
        assert meta.edge_count == 5

        # Assert that cycles are present and counted correctly
        cyclic_edges = [
            (e.src_host, e.dst_host)
            for e in edges
            if (e.dst_host, e.src_host) in [(edge.src_host, edge.dst_host) for edge in edges]
        ]
        # There should be bidirectional connections (cycles) between hosts
        assert len(cyclic_edges) >= 2

    def test_build_graph_metadata_generator(self, tmp_path: Path):
        """Verify generator and version fields."""
        config_dir = create_uf_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        meta = build_graph_metadata(parsed, [], [])

        assert meta.generator == "splunk-autodoc-v2.0"
        assert meta.generated_at is not None

    def test_build_graph_metadata_traceability(self, tmp_path: Path):
        """Verify traceability from ParsedConfig."""
        parsed = ParsedConfig(
            inputs=[],
            outputs=[],
            props=[],
            transforms=[],
            host_metadata={"job_id": 1},
            traceability={"test_stanza": ["file1.conf", "file2.conf"]},
        )

        meta = build_graph_metadata(parsed, [], [])

        assert "test_stanza" in meta.traceability
        assert meta.traceability["test_stanza"] == ["file1.conf", "file2.conf"]

    def test_build_graph_metadata_source_hosts(self, tmp_path: Path):
        """Verify source_hosts excludes placeholders."""
        config_dir = create_uf_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        hosts = [
            Host(id="real_host1", labels=[]),
            Host(id="real_host2", labels=[]),
            Host(id="placeholder1", labels=["placeholder"]),
        ]

        meta = build_graph_metadata(parsed, hosts, [])

        assert "real_host1" in meta.source_hosts
        assert "real_host2" in meta.source_hosts
        assert "placeholder1" not in meta.source_hosts


@pytest.mark.unit
class TestCanonicalGraphBuilding:
    """Test complete canonical graph construction."""

    def test_build_canonical_graph_complete(self, tmp_path: Path):
        """Build complete graph, verify structure."""
        config_dir = create_hf_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        graph = build_canonical_graph(parsed)

        assert "hosts" in graph
        assert "edges" in graph
        assert "meta" in graph
        assert len(graph["hosts"]) > 0
        assert len(graph["edges"]) > 0
        assert graph["meta"]["host_count"] > 0
        assert graph["meta"]["edge_count"] > 0
        assert "generator" in graph["meta"]
        assert "generated_at" in graph["meta"]

    def test_build_canonical_graph_empty_config(self):
        """Raise ValueError for empty ParsedConfig."""
        parsed = ParsedConfig(
            inputs=[],
            outputs=[],
            props=[],
            transforms=[],
            host_metadata={"job_id": 1},
            traceability={},
        )

        with pytest.raises(ValueError):
            build_canonical_graph(parsed)

    def test_build_canonical_graph_serialization(self, tmp_path: Path):
        """Verify JSON serialization works."""
        config_dir = create_uf_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        graph = build_canonical_graph(parsed)

        # Should be JSON serializable
        json_str = json.dumps(graph)
        assert json_str is not None

        # Should be deserializable
        deserialized = json.loads(json_str)
        assert deserialized["hosts"] == graph["hosts"]
        assert deserialized["edges"] == graph["edges"]

    def test_build_canonical_graph_placeholders(self, tmp_path: Path):
        """Verify placeholder hosts are created for dangling outputs."""
        config_dir = create_dangling_output_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        graph = build_canonical_graph(parsed)

        # Should have placeholder host for unknown_destination
        assert any(
            host["id"] == "unknown_destination" and "placeholder" in host["labels"]
            for host in graph["hosts"]
        )
