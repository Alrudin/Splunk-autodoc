"""
Graph validation service for detecting configuration issues.

This module analyzes canonical graph JSON structures to detect validation issues
per spec section 4.4. The validator identifies five types of findings:

1. DANGLING_OUTPUT (error): Output target is unreachable or undefined (placeholder hosts)
2. UNKNOWN_INDEX (warning): Edge references index not declared in destination cluster
3. UNSECURED_PIPE (warning): Data connection does not use TLS encryption
4. DROP_PATH (info): Data is dropped via nullQueue (informational)
5. AMBIGUOUS_GROUP (warning): Multiple output groups without defaultGroup

The validator operates on the canonical graph JSON stored in Graph.json_blob,
which contains hosts (with labels including "placeholder"), edges (with tls,
protocol, indexes, drop_rules, confidence fields), and meta (with traceability).

Detection Logic:
- DANGLING_OUTPUT: Edges where dst_host has label "placeholder" or roles "unknown"
- UNKNOWN_INDEX: Indexes on edges not found in known index set (heuristic)
- UNSECURED_PIPE: splunktcp/http_event_collector edges with tls=False or None
- DROP_PATH: Edges with non-empty drop_rules array
- AMBIGUOUS_GROUP: Edges with confidence="derived" (set by resolver)

Integration:
- Called by job execution after resolver creates graph
- Supports re-validation via POST /graphs/{graph_id}/validate endpoint
- Deletes old findings and creates new ones on re-validation

Severity Levels:
- error: Critical issues requiring attention (DANGLING_OUTPUT)
- warning: Important issues to review (UNKNOWN_INDEX, UNSECURED_PIPE, AMBIGUOUS_GROUP)
- info: Informational notices (DROP_PATH)

References:
- Spec section 4.4: Validation rules
- api/app/models/graph.py: Graph model with json_blob
- api/app/models/finding.py: Finding model with severity/code/context
- api/app/services/resolver.py: Canonical graph structure
"""

import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.finding import Finding
from app.models.graph import Graph

logger = logging.getLogger(__name__)

# Finding codes with severity and description
FINDING_CODES = {
    "DANGLING_OUTPUT": {
        "severity": "error",
        "description": "Output target is unreachable or undefined",
    },
    "UNKNOWN_INDEX": {
        "severity": "warning",
        "description": "Edge references index not declared in destination cluster",
    },
    "UNSECURED_PIPE": {
        "severity": "warning",
        "description": "Data connection does not use TLS encryption",
    },
    "DROP_PATH": {
        "severity": "info",
        "description": "Data is dropped via nullQueue",
    },
    "AMBIGUOUS_GROUP": {
        "severity": "warning",
        "description": "Multiple output groups without defaultGroup",
    },
}

# Protocols that require TLS encryption
TLS_REQUIRED_PROTOCOLS = {"splunktcp", "http_event_collector"}


def extract_hosts_from_graph(graph_json: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract hosts array from canonical graph JSON.

    Args:
        graph_json: Canonical graph JSON structure

    Returns:
        List of host dicts, or empty list if not found

    Example:
        >>> hosts = extract_hosts_from_graph({"hosts": [{"id": "host1", ...}], ...})
        >>> len(hosts) > 0
        True
    """
    if "hosts" not in graph_json:
        logger.warning("Graph JSON missing 'hosts' key")
        return []

    hosts = graph_json["hosts"]
    if not isinstance(hosts, list):
        logger.warning("Graph JSON 'hosts' is not a list")
        return []

    return hosts


def extract_edges_from_graph(graph_json: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract edges array from canonical graph JSON.

    Args:
        graph_json: Canonical graph JSON structure

    Returns:
        List of edge dicts, or empty list if not found

    Example:
        >>> edges = extract_edges_from_graph({"edges": [{"src_host": "h1", ...}], ...})
        >>> len(edges) > 0
        True
    """
    if "edges" not in graph_json:
        logger.warning("Graph JSON missing 'edges' key")
        return []

    edges = graph_json["edges"]
    if not isinstance(edges, list):
        logger.warning("Graph JSON 'edges' is not a list")
        return []

    return edges


def extract_meta_from_graph(graph_json: dict[str, Any]) -> dict[str, Any]:
    """
    Extract meta dict from canonical graph JSON.

    Used for traceability information in finding context.

    Args:
        graph_json: Canonical graph JSON structure

    Returns:
        Meta dict, or empty dict if not found

    Example:
        >>> meta = extract_meta_from_graph({"meta": {"version": "1.0", ...}})
        >>> "version" in meta
        True
    """
    if "meta" not in graph_json:
        logger.warning("Graph JSON missing 'meta' key")
        return {}

    meta = graph_json["meta"]
    if not isinstance(meta, dict):
        logger.warning("Graph JSON 'meta' is not a dict")
        return {}

    return meta


def is_placeholder_host(host: dict[str, Any]) -> bool:
    """
    Check if a host is a placeholder (unknown destination).

    Placeholder hosts indicate DANGLING_OUTPUT issues - they represent
    unreachable or undefined output targets created by the resolver.

    Detection criteria:
    - Has "placeholder" in labels array
    - Has id "unknown_destination"
    - Has id starting with "indexer_discovery:"
    - Has "unknown" in roles array

    Args:
        host: Host dict from canonical graph

    Returns:
        True if host is a placeholder, False otherwise

    Example:
        >>> is_placeholder_host({"id": "h1", "labels": ["placeholder"]})
        True
        >>> is_placeholder_host({"id": "indexer_discovery:prod", "labels": []})
        True
        >>> is_placeholder_host({"id": "h1", "roles": ["unknown"]})
        True
        >>> is_placeholder_host({"id": "h1", "labels": ["indexer"]})
        False
    """
    # Check for placeholder label
    if "placeholder" in host.get("labels", []):
        return True

    # Check for unknown destination ID
    host_id = host.get("id", "")
    if host_id == "unknown_destination":
        return True

    # Check for indexer discovery placeholder
    if host_id.startswith("indexer_discovery:"):
        return True

    # Check for unknown role
    if "unknown" in host.get("roles", []):
        return True

    return False


def get_placeholder_host_ids(hosts: list[dict[str, Any]]) -> set[str]:
    """
    Get set of placeholder host IDs from hosts list.

    Used for DANGLING_OUTPUT detection - identifies which hosts are
    unreachable or undefined destinations.

    Args:
        hosts: List of host dicts from canonical graph

    Returns:
        Set of host ID strings for placeholder hosts

    Example:
        >>> hosts = [
        ...     {"id": "h1", "labels": ["indexer"]},
        ...     {"id": "h2", "labels": ["placeholder"]},
        ...     {"id": "unknown_destination", "labels": []},
        ... ]
        >>> placeholder_ids = get_placeholder_host_ids(hosts)
        >>> "h2" in placeholder_ids
        True
        >>> "unknown_destination" in placeholder_ids
        True
        >>> "h1" in placeholder_ids
        False
    """
    placeholder_ids = set()
    for host in hosts:
        if is_placeholder_host(host):
            host_id = host.get("id")
            if host_id:
                placeholder_ids.add(host_id)
    return placeholder_ids


def collect_known_indexes(
    edges: list[dict[str, Any]], placeholder_host_ids: set[str]
) -> set[str]:
    """
    Collect indexes that are considered "known" (valid).

    Heuristic approach per spec assumption: indexes are considered known if they
    appear on edges to real (non-placeholder) destinations. This assumes that if
    data flows to a real host with an index, that index exists.

    Args:
        edges: List of edge dicts from canonical graph
        placeholder_host_ids: Set of placeholder host IDs (from get_placeholder_host_ids)

    Returns:
        Set of known index names

    Example:
        >>> edges = [
        ...     {"src_host": "h1", "dst_host": "h2", "indexes": ["main", "test"]},
        ...     {"src_host": "h1", "dst_host": "placeholder_h3", "indexes": ["unknown_idx"]},
        ... ]
        >>> placeholder_ids = {"placeholder_h3"}
        >>> known = collect_known_indexes(edges, placeholder_ids)
        >>> "main" in known and "test" in known
        True
        >>> "unknown_idx" in known
        False
    """
    known_indexes = set()
    for edge in edges:
        dst_host = edge.get("dst_host")
        # Only collect indexes from edges to real (non-placeholder) hosts
        if dst_host and dst_host not in placeholder_host_ids:
            indexes = edge.get("indexes", [])
            if isinstance(indexes, list):
                known_indexes.update(indexes)
    return known_indexes


def detect_dangling_outputs(
    hosts: list[dict[str, Any]], edges: list[dict[str, Any]], meta: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Detect DANGLING_OUTPUT findings: edges to placeholder/unknown hosts.

    Each edge to a placeholder host generates one error-level finding, indicating
    that the output target is unreachable or undefined.

    Args:
        hosts: List of host dicts from canonical graph
        edges: List of edge dicts from canonical graph
        meta: Meta dict with traceability information

    Returns:
        List of finding dicts with code, severity, message, context

    Example:
        >>> hosts = [{"id": "h1"}, {"id": "placeholder_h2", "labels": ["placeholder"]}]
        >>> edges = [{"src_host": "h1", "dst_host": "placeholder_h2", "protocol": "splunktcp"}]
        >>> findings = detect_dangling_outputs(hosts, edges, {})
        >>> len(findings)
        1
        >>> findings[0]["code"]
        'DANGLING_OUTPUT'
        >>> findings[0]["severity"]
        'error'
    """
    findings = []
    placeholder_host_ids = get_placeholder_host_ids(hosts)

    for edge in edges:
        dst_host = edge.get("dst_host")
        if dst_host and dst_host in placeholder_host_ids:
            src_host = edge.get("src_host", "unknown")
            context: dict[str, Any] = {
                "src_host": src_host,
                "dst_host": dst_host,
                "protocol": edge.get("protocol"),
                "sources": edge.get("sources", []),
                "indexes": edge.get("indexes", []),
            }
            # Add traceability from meta if available
            if meta:
                context["meta"] = meta

            finding = {
                "code": "DANGLING_OUTPUT",
                "severity": "error",
                "message": (
                    f"Output from {src_host} to {dst_host} is dangling "
                    f"(destination unreachable or undefined)"
                ),
                "context": context,
            }
            findings.append(finding)

    logger.debug(f"Detected {len(findings)} DANGLING_OUTPUT findings")
    return findings


def detect_unknown_indexes(
    edges: list[dict[str, Any]], known_indexes: set[str], meta: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Detect UNKNOWN_INDEX findings: edges with indexes not in known set.

    One finding is generated per unknown index per edge. Indexes are considered
    unknown if they don't appear on edges to real (non-placeholder) destinations.

    Args:
        edges: List of edge dicts from canonical graph
        known_indexes: Set of known index names (from collect_known_indexes)
        meta: Meta dict with traceability information

    Returns:
        List of finding dicts with code, severity, message, context

    Example:
        >>> edges = [
        ...     {"src_host": "h1", "dst_host": "h2", "indexes": ["main", "unknown_idx"]},
        ... ]
        >>> known = {"main"}
        >>> findings = detect_unknown_indexes(edges, known, {})
        >>> len(findings)
        1
        >>> findings[0]["context"]["index"]
        'unknown_idx'
    """
    findings = []

    for edge in edges:
        src_host = edge.get("src_host", "unknown")
        dst_host = edge.get("dst_host", "unknown")
        indexes = edge.get("indexes", [])

        for index in indexes:
            if index not in known_indexes:
                context: dict[str, Any] = {
                    "src_host": src_host,
                    "dst_host": dst_host,
                    "index": index,
                    "protocol": edge.get("protocol"),
                    "sourcetypes": edge.get("sourcetypes", []),
                }
                # Add traceability from meta if available
                if meta:
                    context["meta"] = meta

                finding = {
                    "code": "UNKNOWN_INDEX",
                    "severity": "warning",
                    "message": (
                        f"Edge from {src_host} to {dst_host} references "
                        f"unknown index '{index}'"
                    ),
                    "context": context,
                }
                findings.append(finding)

    logger.debug(f"Detected {len(findings)} UNKNOWN_INDEX findings")
    return findings


def detect_unsecured_pipes(
    edges: list[dict[str, Any]], meta: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Detect UNSECURED_PIPE findings: splunktcp/http connections without TLS.

    Checks edges with protocols in TLS_REQUIRED_PROTOCOLS. A finding is generated
    if tls=False or tls=None (unknown TLS state is treated as insecure).

    Args:
        edges: List of edge dicts from canonical graph
        meta: Meta dict with traceability information

    Returns:
        List of finding dicts with code, severity, message, context

    Example:
        >>> edges = [
        ...     {"src_host": "h1", "dst_host": "h2", "protocol": "splunktcp", "tls": False},
        ...     {"src_host": "h1", "dst_host": "h3", "protocol": "splunktcp", "tls": True},
        ... ]
        >>> findings = detect_unsecured_pipes(edges, {})
        >>> len(findings)
        1
        >>> findings[0]["context"]["protocol"]
        'splunktcp'
    """
    findings = []

    for edge in edges:
        protocol = edge.get("protocol")
        if protocol in TLS_REQUIRED_PROTOCOLS:
            tls = edge.get("tls")
            # tls=None is treated as unsecured (unknown = assume insecure)
            if tls is False or tls is None:
                src_host = edge.get("src_host", "unknown")
                dst_host = edge.get("dst_host", "unknown")
                context: dict[str, Any] = {
                    "src_host": src_host,
                    "dst_host": dst_host,
                    "protocol": protocol,
                    "tls": tls,
                    "sources": edge.get("sources", []),
                }
                # Add traceability from meta if available
                if meta:
                    context["meta"] = meta

                finding = {
                    "code": "UNSECURED_PIPE",
                    "severity": "warning",
                    "message": (
                        f"{protocol} connection from {src_host} to {dst_host} "
                        f"does not use TLS"
                    ),
                    "context": context,
                }
                findings.append(finding)

    logger.debug(f"Detected {len(findings)} UNSECURED_PIPE findings")
    return findings


def detect_drop_paths(
    edges: list[dict[str, Any]], meta: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Detect DROP_PATH findings: edges with nullQueue drop rules.

    This is informational (severity="info") as drops may be intentional for
    filtering unwanted data.

    Args:
        edges: List of edge dicts from canonical graph
        meta: Meta dict with traceability information

    Returns:
        List of finding dicts with code, severity, message, context

    Example:
        >>> edges = [
        ...     {"src_host": "h1", "dst_host": "h2", "drop_rules": ["TRANSFORM-drop_noise"]},
        ... ]
        >>> findings = detect_drop_paths(edges, {})
        >>> len(findings)
        1
        >>> findings[0]["severity"]
        'info'
    """
    findings = []

    for edge in edges:
        drop_rules = edge.get("drop_rules", [])
        if drop_rules:  # Non-empty list
            src_host = edge.get("src_host", "unknown")
            dst_host = edge.get("dst_host", "unknown")
            drop_rules_str = ", ".join(drop_rules)
            context: dict[str, Any] = {
                "src_host": src_host,
                "dst_host": dst_host,
                "drop_rules": drop_rules,
                "sources": edge.get("sources", []),
                "sourcetypes": edge.get("sourcetypes", []),
                "filters": edge.get("filters", []),
            }
            # Add traceability from meta if available
            if meta:
                context["meta"] = meta

            finding = {
                "code": "DROP_PATH",
                "severity": "info",
                "message": (
                    f"Data from {src_host} is dropped via nullQueue: "
                    f"{drop_rules_str}"
                ),
                "context": context,
            }
            findings.append(finding)

    logger.debug(f"Detected {len(findings)} DROP_PATH findings")
    return findings


def detect_ambiguous_groups(
    edges: list[dict[str, Any]], meta: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Detect AMBIGUOUS_GROUP findings: edges with confidence="derived".

    The resolver sets confidence="derived" when multiple output groups exist
    without a defaultGroup setting. This indicates ambiguous routing logic.

    Args:
        edges: List of edge dicts from canonical graph
        meta: Meta dict with traceability information

    Returns:
        List of finding dicts with code, severity, message, context

    Example:
        >>> edges = [
        ...     {"src_host": "h1", "dst_host": "h2", "confidence": "derived"},
        ... ]
        >>> findings = detect_ambiguous_groups(edges, {})
        >>> len(findings)
        1
        >>> findings[0]["code"]
        'AMBIGUOUS_GROUP'
    """
    findings = []

    for edge in edges:
        confidence = edge.get("confidence")
        if confidence == "derived":
            src_host = edge.get("src_host", "unknown")
            dst_host = edge.get("dst_host", "unknown")
            context: dict[str, Any] = {
                "src_host": src_host,
                "dst_host": dst_host,
                "protocol": edge.get("protocol"),
                "confidence": confidence,
                "sources": edge.get("sources", []),
            }
            # Add traceability from meta if available
            if meta:
                context["meta"] = meta

            finding = {
                "code": "AMBIGUOUS_GROUP",
                "severity": "warning",
                "message": (
                    f"Ambiguous routing from {src_host} to {dst_host}: "
                    f"multiple output groups without defaultGroup"
                ),
                "context": context,
            }
            findings.append(finding)

    logger.debug(f"Detected {len(findings)} AMBIGUOUS_GROUP findings")
    return findings


def validate_graph(graph_json: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Main validation function that runs all detection rules.

    Analyzes the canonical graph structure and returns a list of finding dicts
    (not yet persisted to database). Use create_findings_in_db to persist.

    Args:
        graph_json: Canonical graph JSON from Graph.json_blob

    Returns:
        List of finding dicts with code, severity, message, context

    Raises:
        ValueError: If graph_json structure is invalid

    Example:
        >>> graph_json = {
        ...     "hosts": [{"id": "h1"}, {"id": "h2", "labels": ["placeholder"]}],
        ...     "edges": [{
        ...         "src_host": "h1", "dst_host": "h2",
        ...         "protocol": "splunktcp", "tls": False
        ...     }],
        ...     "meta": {"version": "1.0"}
        ... }
        >>> findings = validate_graph(graph_json)
        >>> len(findings) > 0
        True
    """
    # Extract graph components
    hosts = extract_hosts_from_graph(graph_json)
    edges = extract_edges_from_graph(graph_json)
    meta = extract_meta_from_graph(graph_json)

    if not hosts and not edges:
        logger.warning("Empty graph: no hosts or edges")
        return []

    # Get placeholder host IDs
    placeholder_host_ids = get_placeholder_host_ids(hosts)
    logger.debug(f"Found {len(placeholder_host_ids)} placeholder hosts")

    # Collect known indexes
    known_indexes = collect_known_indexes(edges, placeholder_host_ids)
    logger.debug(f"Found {len(known_indexes)} known indexes")

    # Run all detection functions
    dangling_findings = detect_dangling_outputs(hosts, edges, meta)
    unknown_index_findings = detect_unknown_indexes(edges, known_indexes, meta)
    unsecured_findings = detect_unsecured_pipes(edges, meta)
    drop_findings = detect_drop_paths(edges, meta)
    ambiguous_findings = detect_ambiguous_groups(edges, meta)

    # Combine all findings
    all_findings = (
        dangling_findings
        + unknown_index_findings
        + unsecured_findings
        + drop_findings
        + ambiguous_findings
    )

    # Log summary
    logger.info(
        f"Validation complete: {len(all_findings)} findings "
        f"(DANGLING_OUTPUT: {len(dangling_findings)}, "
        f"UNKNOWN_INDEX: {len(unknown_index_findings)}, "
        f"UNSECURED_PIPE: {len(unsecured_findings)}, "
        f"DROP_PATH: {len(drop_findings)}, "
        f"AMBIGUOUS_GROUP: {len(ambiguous_findings)})"
    )

    return all_findings


def create_findings_in_db(
    graph_id: int, finding_dicts: list[dict[str, Any]], db_session: Session
) -> list[Finding]:
    """
    Create Finding records in database from finding dicts.

    All findings are created in a single transaction. If any error occurs,
    the transaction is rolled back and the exception is re-raised.

    Args:
        graph_id: ID of the graph these findings belong to
        finding_dicts: List of finding dicts from validate_graph
        db_session: SQLAlchemy database session

    Returns:
        List of Finding instances with IDs populated

    Raises:
        SQLAlchemyError: If database operation fails

    Example:
        >>> # Assuming db_session and finding_dicts are available
        >>> findings = create_findings_in_db(1, finding_dicts, db_session)
        >>> all(f.id is not None for f in findings)
        True
    """
    try:
        findings = []
        for finding_dict in finding_dicts:
            finding = Finding(
                graph_id=graph_id,
                severity=finding_dict["severity"],
                code=finding_dict["code"],
                message=finding_dict["message"],
                context=finding_dict["context"],
            )
            db_session.add(finding)
            findings.append(finding)

        # Commit all findings in single transaction
        db_session.commit()

        # Refresh to get IDs
        for finding in findings:
            db_session.refresh(finding)

        logger.info(f"Created {len(findings)} findings for graph_id={graph_id}")
        return findings

    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error(f"Failed to create findings for graph_id={graph_id}: {e}")
        raise


def validate_and_store_findings(graph_id: int, db_session: Session) -> list[Finding]:
    """
    Main entry point for validation with database persistence.

    Queries the graph, runs validation, deletes old findings (if re-validation),
    and creates new findings in the database.

    This function is called by:
    - Job execution after graph creation (future implementation)
    - POST /graphs/{graph_id}/validate endpoint (subsequent phase)

    Args:
        graph_id: ID of the graph to validate
        db_session: SQLAlchemy database session

    Returns:
        List of Finding instances

    Raises:
        ValueError: If graph not found or invalid JSON structure
        SQLAlchemyError: If database operation fails

    Example:
        >>> # Assuming db_session is available
        >>> findings = validate_and_store_findings(1, db_session)
        >>> len(findings) >= 0
        True
    """
    # Query Graph by graph_id
    graph = db_session.query(Graph).filter(Graph.id == graph_id).first()
    if not graph:
        raise ValueError(f"Graph with id={graph_id} not found")

    # Extract graph_json from graph.json_blob
    graph_json = graph.json_blob
    if not isinstance(graph_json, dict):
        raise ValueError(f"Graph id={graph_id} has invalid json_blob (not a dict)")

    # Run validation
    finding_dicts = validate_graph(graph_json)

    # Delete existing findings for this graph (re-validation scenario)
    try:
        deleted_count = (
            db_session.query(Finding).filter(Finding.graph_id == graph_id).delete()
        )
        db_session.commit()
        if deleted_count > 0:
            logger.info(
                f"Deleted {deleted_count} existing findings for graph_id={graph_id} (re-validation)"
            )
    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error(f"Failed to delete existing findings for graph_id={graph_id}: {e}")
        raise

    # Create new findings
    findings = create_findings_in_db(graph_id, finding_dicts, db_session)

    logger.info(
        f"Validation complete for graph_id={graph_id}: {len(findings)} findings created"
    )
    return findings


def validate_graph_after_creation(graph: Graph, db_session: Session) -> list[Finding]:
    """
    Convenience function for job execution flow.

    This will be called by job execution logic after resolver creates graph,
    enabling inline validation during job processing.

    Args:
        graph: Graph instance (must have id populated)
        db_session: SQLAlchemy database session

    Returns:
        List of Finding instances

    Raises:
        ValueError: If graph or graph.id is None
        SQLAlchemyError: If database operation fails

    Example:
        >>> # Assuming db_session and graph are available
        >>> findings = validate_graph_after_creation(graph, db_session)
        >>> len(findings) >= 0
        True
    """
    if not graph or not graph.id:
        raise ValueError("Graph instance must have id populated")

    return validate_and_store_findings(graph.id, db_session)
