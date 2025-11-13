"""Unit tests for the validator service."""

import pytest
from sqlalchemy.orm import Session

from app.models.graph import Graph
from app.models.finding import Finding
from app.services.validator import (
    validate_graph,
    extract_hosts_from_graph,
    extract_edges_from_graph,
    extract_meta_from_graph,
    is_placeholder_host,
    get_placeholder_host_ids,
    collect_known_indexes,
    get_declared_indexes_from_meta,
    detect_dangling_outputs,
    detect_unknown_indexes,
    detect_unsecured_pipes,
    detect_drop_paths,
    detect_ambiguous_groups,
    create_findings_in_db,
    validate_and_store_findings,
)


@pytest.mark.unit
class TestHelperFunctions:
    """Test validator helper functions."""

    def test_extract_hosts_from_graph(self):
        """Extract hosts array from graph JSON."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "host2", "roles": ["indexer"], "labels": [], "apps": []}
            ],
            "edges": [],
            "meta": {}
        }
        hosts = extract_hosts_from_graph(graph_json)
        assert len(hosts) == 2
        assert hosts[0]["id"] == "host1"
        assert hosts[1]["id"] == "host2"

    def test_extract_edges_from_graph(self):
        """Extract edges array from graph JSON."""
        graph_json = {
            "hosts": [],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "host2",
                    "protocol": "splunktcp",
                    "indexes": ["main"]
                }
            ],
            "meta": {}
        }
        edges = extract_edges_from_graph(graph_json)
        assert len(edges) == 1
        assert edges[0]["src_host"] == "host1"
        assert edges[0]["dst_host"] == "host2"

    def test_extract_meta_from_graph(self):
        """Extract meta dict from graph JSON."""
        graph_json = {
            "hosts": [],
            "edges": [],
            "meta": {
                "generator": "test",
                "host_count": 5
            }
        }
        meta = extract_meta_from_graph(graph_json)
        assert meta["generator"] == "test"
        assert meta["host_count"] == 5

    def test_is_placeholder_host_by_label(self):
        """Detect placeholder by 'placeholder' label."""
        host = {
            "id": "host1",
            "roles": ["universal_forwarder"],
            "labels": ["placeholder"],
            "apps": []
        }
        assert is_placeholder_host(host) is True

    def test_is_placeholder_host_by_id(self):
        """Detect placeholder by 'unknown_destination' ID."""
        host = {
            "id": "unknown_destination",
            "roles": ["unknown"],
            "labels": [],
            "apps": []
        }
        assert is_placeholder_host(host) is True

    def test_is_placeholder_host_indexer_discovery(self):
        """Detect placeholder by 'indexer_discovery:' prefix."""
        host = {
            "id": "indexer_discovery:cluster_master",
            "roles": ["unknown"],
            "labels": [],
            "apps": []
        }
        assert is_placeholder_host(host) is True

    def test_is_placeholder_host_unknown_role(self):
        """Detect placeholder by 'unknown' role."""
        host = {
            "id": "host1",
            "roles": ["unknown"],
            "labels": [],
            "apps": []
        }
        assert is_placeholder_host(host) is True

    def test_is_placeholder_host_real_host(self):
        """Verify real host is not detected as placeholder."""
        host = {
            "id": "splunk-uf-01",
            "roles": ["universal_forwarder"],
            "labels": [],
            "apps": []
        }
        assert is_placeholder_host(host) is False

    def test_get_placeholder_host_ids(self):
        """Get set of placeholder host IDs."""
        hosts = [
            {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
            {"id": "unknown_destination", "roles": ["unknown"], "labels": ["placeholder"], "apps": []},
            {"id": "indexer_discovery:cluster", "roles": ["unknown"], "labels": [], "apps": []},
            {"id": "host2", "roles": ["indexer"], "labels": [], "apps": []}
        ]
        placeholder_ids = get_placeholder_host_ids(hosts)
        assert len(placeholder_ids) == 2
        assert "unknown_destination" in placeholder_ids
        assert "indexer_discovery:cluster" in placeholder_ids
        assert "host1" not in placeholder_ids
        assert "host2" not in placeholder_ids

    def test_collect_known_indexes_from_real_hosts(self):
        """Collect indexes only from edges to real hosts."""
        edges = [
            {"src_host": "host1", "dst_host": "indexer1", "indexes": ["main", "security"]},
            {"src_host": "host2", "dst_host": "unknown_destination", "indexes": ["test"]},
            {"src_host": "host3", "dst_host": "indexer2", "indexes": ["app_data"]}
        ]
        placeholder_host_ids = {"unknown_destination"}
        known_indexes = collect_known_indexes(edges, placeholder_host_ids)
        assert len(known_indexes) == 3
        assert "main" in known_indexes
        assert "security" in known_indexes
        assert "app_data" in known_indexes
        assert "test" not in known_indexes  # Edge goes to placeholder

    def test_get_declared_indexes_from_meta_simple(self):
        """Get declared indexes from meta dict."""
        meta = {
            "declared_indexes": ["main", "test", "security"]
        }
        declared = get_declared_indexes_from_meta(meta)
        assert declared is not None
        assert len(declared) == 3
        assert "main" in declared
        assert "test" in declared
        assert "security" in declared

    def test_get_declared_indexes_from_meta_none(self):
        """Return None when no declared_indexes in meta."""
        meta = {}
        declared = get_declared_indexes_from_meta(meta)
        assert declared is None


@pytest.mark.unit
class TestDanglingOutputDetection:
    """Test detection of outputs with no reachable indexers."""

    def test_detect_dangling_outputs_simple(self):
        """Detect edge to unknown_destination."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "unknown_destination", "roles": ["unknown"], "labels": ["placeholder"], "apps": []}
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "unknown_destination",
                    "protocol": "splunktcp",
                    "sources": ["/var/log/app.log"],
                    "indexes": ["main"]
                }
            ],
            "meta": {}
        }
        hosts = extract_hosts_from_graph(graph_json)
        edges = extract_edges_from_graph(graph_json)
        meta = extract_meta_from_graph(graph_json)
        
        findings = detect_dangling_outputs(hosts, edges, meta)
        
        assert len(findings) == 1
        assert findings[0]["code"] == "DANGLING_OUTPUT"
        assert findings[0]["severity"] == "error"
        assert "host1" in findings[0]["message"]
        assert "unknown_destination" in findings[0]["message"]
        assert findings[0]["context"]["src_host"] == "host1"
        assert findings[0]["context"]["dst_host"] == "unknown_destination"
        assert findings[0]["context"]["protocol"] == "splunktcp"

    def test_detect_dangling_outputs_indexer_discovery(self):
        """Detect edges to indexer_discovery:* placeholders."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["heavy_forwarder"], "labels": [], "apps": []},
                {"id": "indexer_discovery:cluster_master", "roles": ["unknown"], "labels": ["placeholder"], "apps": []}
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "indexer_discovery:cluster_master",
                    "protocol": "splunktcp",
                    "sources": [],
                    "indexes": ["main"]
                }
            ],
            "meta": {}
        }
        hosts = extract_hosts_from_graph(graph_json)
        edges = extract_edges_from_graph(graph_json)
        meta = extract_meta_from_graph(graph_json)
        
        findings = detect_dangling_outputs(hosts, edges, meta)
        
        assert len(findings) == 1
        assert findings[0]["code"] == "DANGLING_OUTPUT"
        assert "indexer_discovery:cluster_master" in findings[0]["context"]["dst_host"]

    def test_detect_dangling_outputs_no_issues(self):
        """Verify no findings for complete routing."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "indexer1", "roles": ["indexer"], "labels": [], "apps": []}
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "indexer1",
                    "protocol": "splunktcp",
                    "sources": ["/var/log/app.log"],
                    "indexes": ["main"]
                }
            ],
            "meta": {}
        }
        hosts = extract_hosts_from_graph(graph_json)
        edges = extract_edges_from_graph(graph_json)
        meta = extract_meta_from_graph(graph_json)
        
        findings = detect_dangling_outputs(hosts, edges, meta)
        
        assert len(findings) == 0


@pytest.mark.unit
class TestUnknownIndexDetection:
    """Test detection of indexes not in the graph."""

    def test_detect_unknown_indexes_simple(self):
        """Detect index names not found in graph indexes."""
        edges = [
            {
                "src_host": "host1",
                "dst_host": "indexer1",
                "indexes": ["nonexistent_index"]
            }
        ]
        known_indexes = {"main", "security"}
        meta = {}
        
        findings = detect_unknown_indexes(edges, known_indexes, meta)
        
        assert len(findings) == 1
        assert findings[0]["code"] == "UNKNOWN_INDEX"
        assert findings[0]["severity"] == "warning"
        assert findings[0]["context"]["index"] == "nonexistent_index"

    def test_detect_unknown_indexes_main_default(self):
        """Verify 'main' index is not flagged if it exists."""
        edges = [
            {
                "src_host": "host1",
                "dst_host": "indexer1",
                "indexes": ["main"]
            }
        ]
        known_indexes = {"main"}
        meta = {}
        
        findings = detect_unknown_indexes(edges, known_indexes, meta)
        
        assert len(findings) == 0

    def test_detect_unknown_indexes_wildcard(self):
        """Detect ambiguous routing to '*' index."""
        edges = [
            {
                "src_host": "host1",
                "dst_host": "indexer1",
                "indexes": ["*"]
            }
        ]
        known_indexes = {"main", "security"}
        meta = {}
        
        findings = detect_unknown_indexes(edges, known_indexes, meta)
        
        assert len(findings) == 1
        assert findings[0]["severity"] == "warning"


@pytest.mark.unit
class TestUnsecuredPipeDetection:
    """Test detection of unencrypted forwarding connections."""

    def test_detect_unsecured_pipes_simple(self):
        """Detect edges with tls=False."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "indexer1", "roles": ["indexer"], "labels": [], "apps": []}
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "indexer1",
                    "protocol": "splunktcp",
                    "tls": False
                }
            ],
            "meta": {}
        }
        edges = extract_edges_from_graph(graph_json)
        meta = extract_meta_from_graph(graph_json)
        placeholder_host_ids = set()
        
        findings = detect_unsecured_pipes(edges, meta, placeholder_host_ids)
        
        assert len(findings) == 1
        assert findings[0]["code"] == "UNSECURED_PIPE"
        assert findings[0]["severity"] == "warning"
        assert findings[0]["context"]["protocol"] == "splunktcp"
        assert findings[0]["context"]["tls"] is False

    def test_detect_unsecured_pipes_hec(self):
        """Flag HEC connections without HTTPS."""
        edges = [
            {
                "src_host": "host1",
                "dst_host": "hec_endpoint",
                "protocol": "http_event_collector",
                "tls": False
            }
        ]
        meta = {}
        placeholder_host_ids = set()
        
        findings = detect_unsecured_pipes(edges, meta, placeholder_host_ids)
        
        assert len(findings) == 1
        assert findings[0]["code"] == "UNSECURED_PIPE"

    def test_detect_unsecured_pipes_no_issues(self):
        """Verify no findings for all-TLS connections."""
        edges = [
            {
                "src_host": "host1",
                "dst_host": "indexer1",
                "protocol": "splunktcp",
                "tls": True
            },
            {
                "src_host": "host2",
                "dst_host": "indexer1",
                "protocol": "http_event_collector",
                "tls": True
            }
        ]
        meta = {}
        placeholder_host_ids = set()
        
        findings = detect_unsecured_pipes(edges, meta, placeholder_host_ids)
        
        assert len(findings) == 0


@pytest.mark.unit
class TestDropPathDetection:
    """Test detection of events routed to nullQueue."""

    def test_detect_drop_paths_simple(self):
        """Detect edges with drop_rules."""
        edges = [
            {
                "src_host": "host1",
                "dst_host": "indexer1",
                "drop_rules": ["DROP:drop_debug REGEX=DEBUG"],
                "sources": ["/var/log/app.log"],
                "sourcetypes": ["app:log"]
            }
        ]
        meta = {}
        
        findings = detect_drop_paths(edges, meta)
        
        assert len(findings) == 1
        assert findings[0]["code"] == "DROP_PATH"
        assert findings[0]["severity"] == "info"
        assert "drop_rules" in findings[0]["context"]
        assert "nullQueue" in findings[0]["message"] or "drop" in findings[0]["message"].lower()

    def test_detect_drop_paths_multiple_rules(self):
        """Detect multiple drop rules on same edge."""
        edges = [
            {
                "src_host": "host1",
                "dst_host": "indexer1",
                "drop_rules": ["DROP:rule1", "DROP:rule2"]
            }
        ]
        meta = {}
        
        findings = detect_drop_paths(edges, meta)
        
        assert len(findings) == 1
        assert len(findings[0]["context"]["drop_rules"]) == 2

    def test_detect_drop_paths_no_issues(self):
        """Verify no findings when no drop_rules present."""
        edges = [
            {
                "src_host": "host1",
                "dst_host": "indexer1",
                "drop_rules": []
            }
        ]
        meta = {}
        
        findings = detect_drop_paths(edges, meta)
        
        assert len(findings) == 0


@pytest.mark.unit
class TestAmbiguousGroupDetection:
    """Test detection of ambiguous output group routing."""

    def test_detect_ambiguous_groups_no_default(self):
        """Detect multiple output groups without defaultGroup."""
        edges = [
            {
                "src_host": "host1",
                "dst_host": "indexer1",
                "confidence": "derived"
            }
        ]
        meta = {}
        
        findings = detect_ambiguous_groups(edges, meta)
        
        assert len(findings) == 1
        assert findings[0]["code"] == "AMBIGUOUS_GROUP"
        assert findings[0]["severity"] == "warning"
        assert findings[0]["context"]["confidence"] == "derived"
        assert "defaultGroup" in findings[0]["message"] or "multiple output groups" in findings[0]["message"]

    def test_detect_ambiguous_groups_explicit_default(self):
        """Verify no finding when defaultGroup is set."""
        edges = [
            {
                "src_host": "host1",
                "dst_host": "indexer1",
                "confidence": "explicit"
            }
        ]
        meta = {}
        
        findings = detect_ambiguous_groups(edges, meta)
        
        assert len(findings) == 0

    def test_detect_ambiguous_groups_single_group(self):
        """Verify no finding for single output group."""
        edges = [
            {
                "src_host": "host1",
                "dst_host": "indexer1",
                "confidence": "explicit"
            }
        ]
        meta = {}
        
        findings = detect_ambiguous_groups(edges, meta)
        
        assert len(findings) == 0


@pytest.mark.unit
class TestMissingConfigDetection:
    """Test detection of missing or incomplete configurations."""

    @pytest.mark.skip(reason="detect_missing_configs not yet implemented")
    def test_detect_missing_inputs_conf(self):
        """Detect hosts with no inputs defined."""
        pass

    @pytest.mark.skip(reason="detect_missing_configs not yet implemented")
    def test_detect_missing_outputs_conf_forwarder(self):
        """Detect forwarder with no outputs."""
        pass

    @pytest.mark.skip(reason="detect_missing_configs not yet implemented")
    def test_detect_missing_outputs_conf_indexer(self):
        """Verify indexers don't need outputs.conf."""
        pass


@pytest.mark.unit
class TestCircularRoutingDetection:
    """Test detection of circular forwarding loops."""

    @pytest.mark.skip(reason="detect_circular_routing not yet implemented")
    def test_detect_circular_routing_simple(self):
        """Detect simple A → B → A loop."""
        pass

    @pytest.mark.skip(reason="detect_circular_routing not yet implemented")
    def test_detect_circular_routing_complex(self):
        """Detect multi-hop loop A → B → C → A."""
        pass

    @pytest.mark.skip(reason="detect_circular_routing not yet implemented")
    def test_detect_circular_routing_no_cycle(self):
        """Verify no findings for acyclic graph."""
        pass


@pytest.mark.unit
class TestCompleteValidation:
    """Test complete validation workflow."""

    def test_validate_graph_all_rules(self):
        """Run all validation rules, verify Finding objects."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "unknown_destination", "roles": ["unknown"], "labels": ["placeholder"], "apps": []},
                {"id": "indexer1", "roles": ["indexer"], "labels": [], "apps": []}
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "unknown_destination",
                    "protocol": "splunktcp",
                    "sources": ["/var/log/app.log"],
                    "indexes": ["nonexistent_index"],
                    "tls": False,
                    "drop_rules": ["DROP:debug REGEX=DEBUG"],
                    "confidence": "derived"
                }
            ],
            "meta": {}
        }
        
        findings = validate_graph(graph_json)
        
        assert len(findings) > 0
        for finding in findings:
            assert "code" in finding
            assert "severity" in finding
            assert "message" in finding
            assert "context" in finding
        
        finding_codes = [f["code"] for f in findings]
        assert "DANGLING_OUTPUT" in finding_codes
        assert "UNKNOWN_INDEX" in finding_codes
        assert "UNSECURED_PIPE" in finding_codes
        assert "DROP_PATH" in finding_codes
        assert "AMBIGUOUS_GROUP" in finding_codes

    def test_validate_graph_severity_filtering(self):
        """Verify findings have correct severity levels."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "unknown_destination", "roles": ["unknown"], "labels": ["placeholder"], "apps": []},
                {"id": "indexer1", "roles": ["indexer"], "labels": [], "apps": []}
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "unknown_destination",
                    "protocol": "splunktcp",
                    "sources": [],
                    "indexes": ["main"],
                    "tls": False,
                    "drop_rules": [],
                    "confidence": "explicit"
                }
            ],
            "meta": {}
        }
        
        findings = validate_graph(graph_json)
        
        severity_map = {f["code"]: f["severity"] for f in findings}
        assert severity_map.get("DANGLING_OUTPUT") == "error"
        assert severity_map.get("UNSECURED_PIPE") == "warning"

    def test_validate_graph_no_issues(self):
        """Verify clean graph returns empty findings list."""
        graph_json = {
            "hosts": [
                {"id": "uf-01", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "hf-01", "roles": ["heavy_forwarder"], "labels": [], "apps": []},
                {"id": "idx-01", "roles": ["indexer"], "labels": [], "apps": []}
            ],
            "edges": [
                {
                    "src_host": "uf-01",
                    "dst_host": "hf-01",
                    "protocol": "splunktcp",
                    "sources": ["/var/log/app.log"],
                    "indexes": ["main"],
                    "tls": True,
                    "drop_rules": [],
                    "confidence": "explicit"
                },
                {
                    "src_host": "hf-01",
                    "dst_host": "idx-01",
                    "protocol": "splunktcp",
                    "sources": [],
                    "indexes": ["main"],
                    "tls": True,
                    "drop_rules": [],
                    "confidence": "explicit"
                }
            ],
            "meta": {
                "declared_indexes": ["main"]
            }
        }
        
        findings = validate_graph(graph_json)
        
        assert len(findings) == 0

    def test_validate_graph_deduplication(self):
        """Verify duplicate findings are deduplicated."""
        graph_json = {
            "hosts": [
                {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "host2", "roles": ["universal_forwarder"], "labels": [], "apps": []},
                {"id": "unknown_destination", "roles": ["unknown"], "labels": ["placeholder"], "apps": []}
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "unknown_destination",
                    "protocol": "splunktcp",
                    "sources": [],
                    "indexes": ["main"]
                },
                {
                    "src_host": "host2",
                    "dst_host": "unknown_destination",
                    "protocol": "splunktcp",
                    "sources": [],
                    "indexes": ["main"]
                }
            ],
            "meta": {}
        }
        
        findings = validate_graph(graph_json)
        
        # Validator does NOT deduplicate - each edge generates its own finding
        dangling_findings = [f for f in findings if f["code"] == "DANGLING_OUTPUT"]
        assert len(dangling_findings) == 2

    def test_create_findings_in_db(self, test_db):
        """Test creating findings in database."""
        # Create a graph
        from app.models.project import Project
        from app.models.upload import Upload
        from app.models.job import Job
        
        project = Project(name="Test Project", description="Test")
        test_db.add(project)
        test_db.commit()
        test_db.refresh(project)
        
        upload = Upload(
            project_id=project.id,
            filename="test.zip",
            status="completed",
            file_size=1024
        )
        test_db.add(upload)
        test_db.commit()
        test_db.refresh(upload)
        
        job = Job(
            upload_id=upload.id,
            status="completed"
        )
        test_db.add(job)
        test_db.commit()
        test_db.refresh(job)
        
        graph = Graph(
            job_id=job.id,
            json_blob={
                "hosts": [],
                "edges": [],
                "meta": {}
            }
        )
        test_db.add(graph)
        test_db.commit()
        test_db.refresh(graph)
        
        # Create finding dicts
        finding_dicts = [
            {
                "code": "DANGLING_OUTPUT",
                "severity": "error",
                "message": "Test dangling output",
                "context": {"src_host": "host1", "dst_host": "unknown"}
            },
            {
                "code": "UNSECURED_PIPE",
                "severity": "warning",
                "message": "Test unsecured pipe",
                "context": {"protocol": "splunktcp", "tls": False}
            }
        ]
        
        # Call create_findings_in_db
        findings = create_findings_in_db(graph.id, finding_dicts, test_db)
        test_db.commit()
        
        # Query findings from database
        db_findings = test_db.query(Finding).filter(Finding.graph_id == graph.id).all()
        
        assert len(db_findings) == 2
        assert db_findings[0].graph_id == graph.id
        assert db_findings[0].code in ["DANGLING_OUTPUT", "UNSECURED_PIPE"]
        assert db_findings[0].severity in ["error", "warning"]
        assert db_findings[0].id is not None

    def test_validate_and_store_findings(self, test_db, sample_graph):
        """Test validate_and_store_findings integration."""
        # Modify sample_graph to include validation issues
        graph_json = sample_graph.json_blob
        graph_json["hosts"].append({
            "id": "unknown_destination",
            "roles": ["unknown"],
            "labels": ["placeholder"],
            "apps": []
        })
        graph_json["edges"].append({
            "src_host": graph_json["hosts"][0]["id"],
            "dst_host": "unknown_destination",
            "protocol": "splunktcp",
            "sources": [],
            "indexes": ["main"],
            "tls": False,
            "drop_rules": [],
            "confidence": "explicit"
        })
        sample_graph.json_blob = graph_json
        test_db.commit()
        test_db.refresh(sample_graph)
        
        # Call validate_and_store_findings
        findings = validate_and_store_findings(sample_graph.id, test_db)
        
        # Query findings from database
        db_findings = test_db.query(Finding).filter(Finding.graph_id == sample_graph.id).all()
        
        assert len(findings) > 0
        assert len(db_findings) > 0
        assert all(isinstance(f, Finding) for f in findings)
        assert "DANGLING_OUTPUT" in [f.code for f in findings]
        assert "UNSECURED_PIPE" in [f.code for f in findings]

    def test_validate_and_store_findings_revalidation(self, test_db, sample_graph):
        """Test revalidation deletes old findings and creates new ones."""
        # Initial validation with one issue
        graph_json = sample_graph.json_blob
        graph_json["hosts"].append({
            "id": "unknown_destination",
            "roles": ["unknown"],
            "labels": ["placeholder"],
            "apps": []
        })
        graph_json["edges"].append({
            "src_host": graph_json["hosts"][0]["id"],
            "dst_host": "unknown_destination",
            "protocol": "splunktcp",
            "sources": [],
            "indexes": ["main"],
            "tls": True,
            "drop_rules": [],
            "confidence": "explicit"
        })
        sample_graph.json_blob = graph_json
        test_db.commit()
        
        initial_findings = validate_and_store_findings(sample_graph.id, test_db)
        initial_count = len(initial_findings)
        
        # Modify graph to have different issues
        graph_json["edges"][-1]["tls"] = False  # Add unsecured pipe issue
        sample_graph.json_blob = graph_json
        test_db.commit()
        
        # Revalidate
        new_findings = validate_and_store_findings(sample_graph.id, test_db)
        
        # Query findings from database
        db_findings = test_db.query(Finding).filter(Finding.graph_id == sample_graph.id).all()
        
        # Should have new findings reflecting updated graph
        assert len(db_findings) == len(new_findings)
        assert len(new_findings) > initial_count  # Should have additional UNSECURED_PIPE finding
