"""
Splunk Configuration Resolver Service

This module transforms ParsedConfig objects (from parser.py) into canonical graph
structures following the specification in section 4.2. The resolver implements the
complete resolution algorithm:

1. Host identification: Extract hostname and infer roles from configuration patterns
2. Edge building: Match inputs to outputs to create host-to-host data flow edges
3. Props/Transforms evaluation: Apply index routing, filters, and drop rules per spec 4.3
4. Heuristics for ambiguity: Handle unknown destinations, ambiguous routing with confidence levels
5. Metadata generation: Build complete traceability and statistics
6. Serialization: Convert to canonical JSON format for Graph.json_blob storage

The resolver handles single-host configurations (one ParsedConfig = one primary host)
and generates placeholder hosts for unknown destinations. Transform evaluation is
simplified per spec assumptions (routing based on configuration presence, not runtime
regex matching on event data).

Key functions:
- build_canonical_graph(): Main entry point, returns canonical JSON dict
- resolve_and_create_graph(): Integration function with database persistence
- Helper functions for host detection, edge building, transform evaluation
"""

import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.models.graph import Graph
from app.models.job import Job
from app.services.parser import (
    InputStanza,
    OutputGroup,
    ParsedConfig,
    PropsStanza,
    TransformStanza,
)

# Constants
GENERATOR = "splunk-autodoc-v2.0"
GRAPH_VERSION = "1.0"

# Role detection patterns (keywords/patterns for inferring host roles)
ROLE_PATTERNS = {
    "universal_forwarder": [r"splunkforwarder", r"uf_", r"forwarder"],
    "heavy_forwarder": [r"heavy", r"hf_", r"Splunk_TA_", r"SA-"],
    "indexer": [r"idx", r"indexer", r"cluster_master", r"cluster_peer"],
    "search_head": [r"search", r"sh_", r"deployer"],
}

# Protocol mappings for input types
PROTOCOL_MAPPINGS = {
    "monitor": ("splunktcp", "forwarding"),
    "tcp": ("tcp", "syslog"),
    "udp": ("udp", "syslog"),
    "splunktcp": ("splunktcp", "forwarding"),
    "http": ("http_event_collector", "hec"),
    "script": ("splunktcp", "scripted_input"),
    "WinEventLog": ("splunktcp", "modinput"),
    "modular_input": ("splunktcp", "modinput"),
}

# Precedence order for props matching (lower = higher precedence)
# sourcetype < source < host per Splunk's evaluation order
PRECEDENCE_ORDER = {
    "sourcetype": 0,
    "source": 1,
    "host": 2,
}

logger = logging.getLogger(__name__)


# Internal Dataclasses for Graph Building


@dataclass
class Host:
    """
    Internal representation of a host in the graph.

    Matches the HostSchema from schemas/graph.py for type-safe construction.
    """

    id: str
    roles: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    apps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


@dataclass
class Edge:
    """
    Internal representation of an edge (data flow) in the graph.

    Matches the EdgeSchema from schemas/graph.py for type-safe construction.
    """

    src_host: str
    dst_host: str
    protocol: Literal["splunktcp", "http_event_collector", "syslog", "tcp", "udp"]
    path_kind: Literal["forwarding", "hec", "syslog", "scripted_input", "modinput"]
    sources: list[str] = field(default_factory=list)
    sourcetypes: list[str] = field(default_factory=list)
    indexes: list[str] = field(default_factory=list)
    filters: list[str] = field(default_factory=list)
    drop_rules: list[str] = field(default_factory=list)
    tls: bool | None = None
    weight: int = 1
    app_contexts: list[str] = field(default_factory=list)
    confidence: Literal["explicit", "derived"] = "explicit"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


@dataclass
class GraphMeta:
    """
    Internal representation of graph metadata.

    Matches the GraphMetaSchema from schemas/graph.py.
    """

    generator: str
    generated_at: datetime
    host_count: int
    edge_count: int
    source_hosts: list[str] = field(default_factory=list)
    traceability: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        data = asdict(self)
        # Convert datetime to ISO format string
        data["generated_at"] = self.generated_at.isoformat()
        return data


# Helper Functions


def infer_host_roles(parsed: ParsedConfig) -> list[str]:
    """
    Infer host roles from configuration patterns per spec section 4.3.

    Detection logic:
    - Universal Forwarder: Has inputs and outputs with forwarding, minimal apps
    - Heavy Forwarder: Has inputs, outputs, parsing apps (Splunk_TA_*, SA-*), props/transforms
    - Indexer: Has splunktcp inputs (receiving data), minimal outputs
    - Search Head: Has search apps, no data inputs

    Args:
        parsed: ParsedConfig object from parser

    Returns:
        List of detected role strings (can be multiple). Returns ["unknown"] if no clear indicators.
    """
    roles = []

    has_outputs = bool(parsed.outputs)
    has_props = bool(parsed.props)
    has_transforms = bool(parsed.transforms)

    # Get apps list from metadata
    apps = parsed.host_metadata.get("apps", [])
    app_names = [app.lower() for app in apps]

    # Check for parsing/TA apps
    has_parsing_apps = any("splunk_ta_" in app or "sa-" in app or "ta-" in app for app in app_names)

    # Check for search apps
    has_search_apps = any("search" in app for app in app_names)

    # Check input types
    has_splunktcp_input = any(
        inp.input_type == "splunktcp" for inp in parsed.inputs if not inp.disabled
    )
    has_data_inputs = any(
        inp.input_type in ("monitor", "tcp", "udp", "script", "WinEventLog")
        for inp in parsed.inputs
        if not inp.disabled
    )

    # Indexer detection: receiving splunktcp, minimal outputs
    if has_splunktcp_input and not has_outputs:
        roles.append("indexer")
    elif has_splunktcp_input and has_outputs:
        # Could be indexer with replication or HF receiving from UFs
        # Check for parsing - if has parsing, likely HF; if not, likely indexer
        if not has_parsing_apps and not has_props:
            roles.append("indexer")

    # Heavy Forwarder detection: inputs + outputs + parsing
    if has_data_inputs and has_outputs and (has_parsing_apps or has_props or has_transforms):
        roles.append("heavy_forwarder")

    # Universal Forwarder detection: inputs + outputs, minimal processing
    if (
        has_data_inputs
        and has_outputs
        and not has_parsing_apps
        and not has_props
        and not has_transforms
        and "heavy_forwarder" not in roles
    ):
        roles.append("universal_forwarder")

    # Search Head detection: search apps, no data inputs
    if has_search_apps and not has_data_inputs:
        roles.append("search_head")

    # Pattern-based detection from hostname/apps (fallback)
    hostname = parsed.host_metadata.get("hostname", "").lower()
    for role, patterns in ROLE_PATTERNS.items():
        if role not in roles:  # Don't duplicate
            if any(re.search(pattern, hostname) for pattern in patterns):
                roles.append(role)
                break
            if any(any(re.search(pattern, app) for pattern in patterns) for app in app_names):
                roles.append(role)
                break

    # Default to unknown if no clear indicators
    if not roles:
        roles.append("unknown")

    return roles


def extract_hostname(parsed: ParsedConfig) -> str:
    """
    Extract hostname from ParsedConfig.host_metadata.

    Checks for 'hostname' key from server.conf. Falls back to generating
    placeholder if not found.

    Args:
        parsed: ParsedConfig object from parser

    Returns:
        Sanitized hostname string (alphanumeric, hyphens, underscores only)
    """
    hostname = parsed.host_metadata.get("hostname", "")

    if not hostname:
        # Generate placeholder from job_id if available
        job_id = parsed.host_metadata.get("job_id", "unknown")
        hostname = f"host_{job_id}"

    # Sanitize: keep only alphanumeric, hyphens, underscores
    hostname = re.sub(r"[^a-zA-Z0-9_-]", "_", hostname)

    return hostname


def build_host(parsed: ParsedConfig) -> Host:
    """
    Create Host object from parsed configuration.

    Extracts hostname, infers roles, and pulls apps/labels from metadata.

    Args:
        parsed: ParsedConfig object from parser

    Returns:
        Host dataclass instance representing the primary host
    """
    hostname = extract_hostname(parsed)
    roles = infer_host_roles(parsed)
    apps = parsed.host_metadata.get("apps", [])

    # Generate labels from metadata (e.g., environment tags)
    labels = []
    if parsed.host_metadata.get("environment"):
        labels.append(f"env:{parsed.host_metadata['environment']}")
    if parsed.host_metadata.get("cluster"):
        labels.append(f"cluster:{parsed.host_metadata['cluster']}")

    return Host(id=hostname, roles=roles, labels=labels, apps=apps)


def determine_protocol_and_path_kind(
    input_stanza: InputStanza,
) -> tuple[str, Literal["forwarding", "hec", "syslog", "scripted_input", "modinput"]]:
    """
    Map input type to protocol and path_kind per spec section 11.

    Protocol indicates the transport mechanism. Path_kind indicates the data flow category.
    Note: Protocol depends on how data is forwarded, not just the input type.

    Args:
        input_stanza: InputStanza object with input_type field

    Returns:
        Tuple of (protocol, path_kind) strings where path_kind is a Literal type
    """
    input_type = input_stanza.input_type.lower()

    # Check direct mappings
    for key, (protocol, path_kind) in PROTOCOL_MAPPINGS.items():
        if input_type.startswith(key.lower()):
            return (protocol, path_kind)  # type: ignore

    # Default fallback: assume forwarded via splunktcp
    logger.warning(
        f"Unknown input type '{input_type}' for stanza '{input_stanza.stanza_name}'. "
        f"Defaulting to splunktcp/forwarding"
    )
    return ("splunktcp", "forwarding")


def resolve_output_targets(
    output_groups: list[OutputGroup],
) -> list[tuple[str, bool, str]]:
    """
    Resolve output target hosts from OutputGroup configurations.

    Parses server lists, extracts hostnames, determines SSL/TLS settings.
    Handles indexer discovery by creating placeholder targets.

    Args:
        output_groups: List of OutputGroup objects from parsed config

    Returns:
        List of tuples: (target_host, tls_enabled, group_name)
        Returns empty list if no outputs configured (will trigger DANGLING_OUTPUT finding)
    """
    targets = []

    for group in output_groups:

        # Handle indexer discovery
        if group.indexer_discovery:
            target_host = f"indexer_discovery:{group.indexer_discovery}"
            tls_enabled = bool(group.ssl_enabled) or bool(group.ssl_cert_path)
            targets.append((target_host, tls_enabled, group.group_name))
            continue

        # Parse server list
        for server in group.servers:
            # Server format: "host:port" or just "host"
            host_part = server.split(":")[0].strip()

            if not host_part:
                logger.warning(
                    f"Empty host in server '{server}' for output group '{group.group_name}'"
                )
                continue

            # Determine TLS from ssl_enabled or presence of ssl_cert_path
            # ssl_enabled can be None, True, or False
            tls_enabled = bool(group.ssl_enabled) or bool(group.ssl_cert_path)

            targets.append((host_part, tls_enabled, group.group_name))

    return targets


def apply_transforms_to_index(
    input_stanza: InputStanza,
    props: list[PropsStanza],
    transforms: list[TransformStanza],
) -> tuple[list[str], list[str], list[str]]:
    """
    Apply props/transforms logic to determine final indexes, filters, and drops per spec 4.3.

    Evaluation logic:
    1. Start with input's default index (or "main")
    2. Find matching props by sourcetype, source, host (precedence: host < source < sourcetype)
    3. For each matching props, evaluate TRANSFORMS-* in order
    4. Apply index routing (DEST_KEY=_MetaData:Index)
    5. Apply drops (DEST_KEY=queue, FORMAT=nullQueue)
    6. Handle sourcetype rewrites and re-evaluate props if sourcetype changes
    7. Track filters and drop rules for traceability

    Note: This is simplified evaluation without regex matching on event data (per spec assumption).

    Args:
        input_stanza: InputStanza with source, sourcetype, index
        props: List of PropsStanza objects
        transforms: List of TransformStanza objects

    Returns:
        Tuple of (final_indexes, filters_applied, drop_rules)
    """
    # Start with input's default index
    current_indexes = [input_stanza.index] if input_stanza.index else ["main"]
    filters_applied = []
    drop_rules = []

    # Track current sourcetype for rewrites
    current_sourcetype = input_stanza.sourcetype

    # Track which props we've already processed to avoid infinite loops
    processed_props = set()

    # Iteratively find and apply props/transforms until no more sourcetype changes
    max_iterations = 10  # Prevent infinite loops
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        # Find matching props stanzas based on current sourcetype
        matching_props = []

        for prop in props:
            # Skip already processed props to avoid loops
            prop_key = (prop.stanza_type, prop.stanza_value, current_sourcetype)
            if prop_key in processed_props:
                continue

            # Match by stanza_type and stanza_value
            if prop.stanza_type == "sourcetype" and prop.stanza_value == current_sourcetype:
                matching_props.append(("sourcetype", prop))
            # Match by source (with wildcard support - simplified)
            elif prop.stanza_type == "source" and input_stanza.source_path:
                if prop.stanza_value == input_stanza.source_path:
                    matching_props.append(("source", prop))
                elif prop.stanza_value.endswith("*"):
                    prefix = prop.stanza_value[:-1]
                    if input_stanza.source_path.startswith(prefix):
                        matching_props.append(("source", prop))
            # Match by host
            elif prop.stanza_type == "host" and prop.stanza_value == input_stanza.host:
                matching_props.append(("host", prop))

        # If no new matching props, we're done
        if not matching_props:
            break

        # Sort by precedence: host < source < sourcetype (higher number = higher precedence)
        matching_props.sort(key=lambda x: PRECEDENCE_ORDER.get(x[0], 0), reverse=True)

        sourcetype_changed = False

        # Apply transforms from matching props
        for _match_type, prop in matching_props:
            # Mark this prop as processed
            prop_key = (prop.stanza_type, prop.stanza_value, current_sourcetype)
            processed_props.add(prop_key)

            # Evaluate each transform reference in order
            transform_refs = prop.transforms or []

            for transform_ref in transform_refs:
                # Look up transform by name (stanza_name, not transform_name)
                transform = next(
                    (t for t in transforms if t.stanza_name == transform_ref),
                    None,
                )

                if not transform:
                    logger.warning(
                        f"Transform '{transform_ref}' referenced in props but not found "
                        f"in transforms.conf"
                    )
                    continue

                # Apply index routing
                if transform.is_index_routing:
                    if transform.format:
                        current_indexes.append(transform.format)
                        filters_applied.append(f"TRANSFORMS:{transform_ref}")
                    else:
                        logger.warning(
                            f"Transform '{transform_ref}' is index routing but has no FORMAT "
                            f"value"
                        )

                # Apply drops
                if transform.is_drop:
                    drop_rules.append(f"DROP:{transform_ref}")
                    current_indexes = []  # Clear indexes - data is dropped

                # Track sourcetype rewrites (affects subsequent matching)
                if transform.is_sourcetype_rewrite:
                    if transform.format:
                        # Update current sourcetype and flag for re-evaluation
                        new_sourcetype = transform.format
                        filters_applied.append(f"SOURCETYPE_REWRITE:{transform_ref}")
                        if new_sourcetype != current_sourcetype:
                            current_sourcetype = new_sourcetype
                            sourcetype_changed = True
                    else:
                        logger.warning(
                            f"Transform '{transform_ref}' is sourcetype rewrite but has no "
                            f"FORMAT value"
                        )

        # If sourcetype changed, continue to next iteration to re-evaluate props
        if not sourcetype_changed:
            break

    if iteration >= max_iterations:
        logger.warning(
            f"Max iterations ({max_iterations}) reached in apply_transforms_to_index for "
            f"input '{input_stanza.stanza_name}'. Possible circular sourcetype rewrite."
        )

    return (current_indexes, filters_applied, drop_rules)


def build_edges_from_inputs_outputs(parsed: ParsedConfig, src_host: Host) -> list[Edge]:
    """
    Build edges by matching inputs to outputs per spec section 4.3.

    For each input:
    1. Determine protocol and path_kind
    2. Apply transforms to get indexes, filters, drops
    3. Resolve output targets
    4. Create Edge for each target

    Special cases:
    - No outputs → create edge to "unknown_destination" with confidence="derived"
    - Multiple output groups without defaultGroup → mark confidence="derived"
    - Indexer discovery → create edge to placeholder "indexer_discovery:{name}"

    Args:
        parsed: ParsedConfig with inputs, outputs, props, transforms
        src_host: Host object representing the source host

    Returns:
        List of Edge objects representing data flows
    """
    edges = []

    # Resolve output targets once
    output_targets = resolve_output_targets(parsed.outputs)

    # Check for ambiguous routing (OutputGroup.default_group is optional, so use getattr)
    # If OutputGroup always has 'default_group', use direct access: any(group.default_group for
    # group in parsed.outputs)
    has_default_group = any(getattr(group, "default_group", False) for group in parsed.outputs)
    is_ambiguous_routing = len(parsed.outputs) > 1 and not has_default_group

    for input_stanza in parsed.inputs:
        if input_stanza.disabled:
            continue

        # Determine path_kind from input type
        _, path_kind = determine_protocol_and_path_kind(input_stanza)

        # Apply transforms to get indexes, filters, drops
        final_indexes, filters_applied, drop_rules = apply_transforms_to_index(
            input_stanza, parsed.props, parsed.transforms
        )

        # Build sources, sourcetypes lists
        sources = [input_stanza.stanza_name] if input_stanza.stanza_name else []
        sourcetypes = [input_stanza.sourcetype] if input_stanza.sourcetype else []
        app_contexts = [input_stanza.source_app] if input_stanza.source_app else []

        # Handle case: no outputs configured
        if not output_targets:
            edge = Edge(
                src_host=src_host.id,
                dst_host="unknown_destination",
                protocol="splunktcp",  # Unknown destination, assume splunktcp
                path_kind=path_kind,
                sources=sources,
                sourcetypes=sourcetypes,
                indexes=final_indexes,
                filters=filters_applied,
                drop_rules=drop_rules,
                tls=None,  # Unknown when no outputs configured
                weight=1,
                app_contexts=app_contexts,
                confidence="derived",
            )
            edges.append(edge)
            continue

        # Create edge for each output target
        # Protocol is splunktcp when forwarding via outputs (tcpout)
        for target_host, tls_enabled, _group_name in output_targets:
            confidence: Literal["explicit", "derived"] = (
                "derived" if is_ambiguous_routing else "explicit"
            )

            edge = Edge(
                src_host=src_host.id,
                dst_host=target_host,
                protocol="splunktcp",  # Forwarding via outputs uses splunktcp
                path_kind=path_kind,
                sources=sources,
                sourcetypes=sourcetypes,
                indexes=final_indexes,
                filters=filters_applied,
                drop_rules=drop_rules,
                tls=tls_enabled,
                weight=1,
                app_contexts=app_contexts,
                confidence=confidence,
            )
            edges.append(edge)

    return edges


def merge_similar_edges(edges: list[Edge]) -> list[Edge]:
    """
    Merge edges with same src_host, dst_host, protocol, path_kind to reduce graph complexity.

    - Use least confident value (prefer "derived" over "explicit"; "derived" is lower confidence)
    - Combine sources, sourcetypes, indexes, filters, drop_rules, app_contexts (deduplicate)
    - Use least restrictive TLS setting (False if any edge has tls=False)
    - Sum weights
    - Use lowest confidence ("derived" < "explicit")

    This optimization reduces edge count for large deployments.

    Args:
        edges: List of Edge objects

    Returns:
        List of merged Edge objects
    """
    # Group edges by (src_host, dst_host, protocol, path_kind)
    edge_groups: dict[tuple[str, str, str, str], list[Edge]] = {}

    for edge in edges:
        key = (edge.src_host, edge.dst_host, edge.protocol, edge.path_kind)
        if key not in edge_groups:
            edge_groups[key] = []
        edge_groups[key].append(edge)

    # Merge each group
    merged_edges = []

    for (src, dst, proto, path_kind), group in edge_groups.items():
        if len(group) == 1:
            # No merging needed
            merged_edges.append(group[0])
            continue

        # Merge multiple edges
        merged = Edge(
            src_host=src,
            dst_host=dst,
            protocol=proto,  # type: ignore
            path_kind=path_kind,  # type: ignore
            sources=[],
            sourcetypes=[],
            indexes=[],
            filters=[],
            drop_rules=[],
            tls=None,  # Start with None, set to False if any False, True if all True
            weight=0,
            app_contexts=[],
            confidence="explicit",  # Start with explicit, will be downgraded if any derived
        )

        # Combine fields
        sources_set = set()
        sourcetypes_set = set()
        indexes_set = set()
        filters_list = []
        drop_rules_set = set()
        app_contexts_set = set()
        tls_values = []

        for edge in group:
            sources_set.update(edge.sources)
            sourcetypes_set.update(edge.sourcetypes)
            indexes_set.update(edge.indexes)
            filters_list.extend(edge.filters)  # Preserve order
            drop_rules_set.update(edge.drop_rules)
            app_contexts_set.update(edge.app_contexts)

            # Track TLS values for proper merging
            if edge.tls is not None:
                tls_values.append(edge.tls)

            # Sum weights
            merged.weight += edge.weight

            # Lowest confidence
            if edge.confidence == "derived":
                merged.confidence = "derived"

        # Determine merged TLS: False if any False, True if all True, None if mixed True/False or
        # all None
        if tls_values:
            if any(tls is False for tls in tls_values):
                merged.tls = False
            elif all(tls is True for tls in tls_values):
                merged.tls = True
            else:
                merged.tls = None  # Mixed True/False or all None

        # Deduplicate filters while preserving order
        seen_filters = set()
        merged.filters = []
        for f in filters_list:
            if f not in seen_filters:
                merged.filters.append(f)
                seen_filters.add(f)

        merged.sources = sorted(sources_set)
        merged.sourcetypes = sorted(sourcetypes_set)
        merged.indexes = sorted(indexes_set)
        merged.drop_rules = sorted(drop_rules_set)
        merged.app_contexts = sorted(app_contexts_set)

        merged_edges.append(merged)

    return merged_edges


def create_placeholder_hosts(edges: list[Edge], known_hosts: set[str]) -> list[Host]:
    """
    Create placeholder Host objects for unknown destinations referenced in edges.

    Scans all edges for dst_host values not in known_hosts. Creates Host objects
    with inferred roles based on naming patterns.

    Special handling:
    - "unknown_destination" → roles=["unknown"]
    - "indexer_discovery:*" → roles=["indexer"], labels=["indexer_discovery"]
    - Hosts matching "idx*", "indexer*" → roles=["indexer"]
    - Hosts matching "hf*", "heavy*" → roles=["heavy_forwarder"]

    These will trigger DANGLING_OUTPUT findings in validator (next phase).

    Args:
        edges: List of Edge objects
        known_hosts: Set of known host IDs

    Returns:
        List of placeholder Host objects
    """
    unknown_hosts = set()

    # Collect unknown destinations
    for edge in edges:
        if edge.dst_host not in known_hosts:
            unknown_hosts.add(edge.dst_host)

    placeholder_hosts = []

    for host_id in unknown_hosts:
        roles = ["unknown"]
        labels = ["placeholder"]

        # Infer roles from host naming patterns
        host_lower = host_id.lower()

        if host_id == "unknown_destination":
            roles = ["unknown"]
        elif host_id.startswith("indexer_discovery:"):
            roles = ["indexer"]
            labels = ["indexer_discovery", "placeholder"]
        elif "idx" in host_lower or "indexer" in host_lower:
            roles = ["indexer"]
        elif "hf" in host_lower or "heavy" in host_lower:
            roles = ["heavy_forwarder"]
        elif "uf" in host_lower or "forwarder" in host_lower:
            roles = ["universal_forwarder"]
        elif "search" in host_lower or "sh" in host_lower:
            roles = ["search_head"]

        placeholder = Host(id=host_id, roles=roles, labels=labels, apps=[])
        placeholder_hosts.append(placeholder)

    return placeholder_hosts


def build_graph_metadata(parsed: ParsedConfig, hosts: list[Host], edges: list[Edge]) -> GraphMeta:
    """
    Build graph metadata per spec section 4.2.

    Includes generator info, timestamps, counts, source hosts, and traceability
    from the parser.

    Args:
        parsed: ParsedConfig with traceability
        hosts: List of Host objects
        edges: List of Edge objects

    Returns:
        GraphMeta dataclass instance
    """
    meta = GraphMeta(
        generator=GENERATOR,
        generated_at=datetime.now(UTC),
        host_count=len(hosts),
        edge_count=len(edges),
        source_hosts=[h.id for h in hosts if "placeholder" not in h.labels],
        traceability=parsed.traceability,
    )

    # Add additional metadata to traceability
    if "resolver" not in meta.traceability:
        meta.traceability["resolver"] = {}

    meta.traceability["resolver"]["input_counts"] = {}
    for inp in parsed.inputs:
        inp_type = inp.input_type
        meta.traceability["resolver"]["input_counts"][inp_type] = (
            meta.traceability["resolver"]["input_counts"].get(inp_type, 0) + 1
        )

    meta.traceability["resolver"]["output_group_count"] = len(parsed.outputs)
    meta.traceability["resolver"]["props_count"] = len(parsed.props)
    meta.traceability["resolver"]["transforms_count"] = len(parsed.transforms)
    meta.traceability["resolver"]["apps_found"] = parsed.host_metadata.get("apps", [])

    return meta


# Main Resolution Functions


def build_canonical_graph(parsed: ParsedConfig) -> dict[str, Any]:
    """
    Main entry point for graph resolution.

    Transforms ParsedConfig into canonical graph JSON structure per spec section 4.2.

    Algorithm:
    1. Build primary host from parsed config
    2. Build edges from inputs and outputs
    3. Merge similar edges to optimize graph
    4. Create placeholder hosts for unknown destinations
    5. Build graph metadata
    6. Serialize to canonical JSON structure

    Args:
        parsed: ParsedConfig object from parser service

    Returns:
        Dict with structure: {"hosts": [...], "edges": [...], "meta": {...}}
        Ready for Graph.json_blob storage

    Raises:
        ValueError: If ParsedConfig is empty (no inputs, no outputs, no host)
    """
    logger.info("Starting graph resolution")

    # Validate ParsedConfig
    if not parsed.inputs and not parsed.outputs:
        logger.error("Empty ParsedConfig: no inputs or outputs found")
        raise ValueError("ParsedConfig must have at least one input or output")

    # Build primary host
    logger.debug("Building primary host")
    host = build_host(parsed)
    logger.info(f"Primary host: {host.id} with roles {host.roles}")

    # Build edges from inputs and outputs
    logger.debug("Building edges from inputs and outputs")
    edges = build_edges_from_inputs_outputs(parsed, host)
    logger.info(f"Built {len(edges)} initial edges")

    # Merge similar edges to optimize graph
    logger.debug("Merging similar edges")
    edges = merge_similar_edges(edges)
    logger.info(f"After merging: {len(edges)} edges")

    # Create placeholder hosts for unknown destinations
    logger.debug("Creating placeholder hosts")
    known_hosts = {host.id}
    placeholder_hosts = create_placeholder_hosts(edges, known_hosts)
    logger.info(f"Created {len(placeholder_hosts)} placeholder hosts")

    all_hosts = [host] + placeholder_hosts

    # Build graph metadata
    logger.debug("Building graph metadata")
    meta = build_graph_metadata(parsed, all_hosts, edges)

    # Serialize to canonical JSON structure
    logger.debug("Serializing to canonical JSON")
    canonical_json = {
        "hosts": [h.to_dict() for h in all_hosts],
        "edges": [e.to_dict() for e in edges],
        "meta": meta.to_dict(),
    }

    logger.info(
        f"Graph resolution complete: {len(all_hosts)} hosts, {len(edges)} edges, "
        f"{len(placeholder_hosts)} placeholders"
    )

    return canonical_json


def resolve_and_create_graph(job_id: int, parsed: ParsedConfig, db_session: Session) -> Graph:
    """
    Integration function that combines resolution with database persistence.

    Calls build_canonical_graph() to get canonical JSON, then creates Graph record
    in the database linked to the job.

    This function will be called by job execution logic (future implementation).

    Args:
        job_id: Job ID for the parse job
        parsed: ParsedConfig object from parser
        db_session: SQLAlchemy session for database operations

    Returns:
        Graph instance with ID assigned

    Raises:
        ValueError: If ParsedConfig is invalid
        SQLAlchemyError: If database operation fails
    """
    logger.info(f"Resolving and creating graph for job_id={job_id}")

    try:
        # Build canonical graph
        canonical_json = build_canonical_graph(parsed)

        # Query Job to get project_id via upload relationship
        job = db_session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job with id={job_id} not found")

        # Create Graph record (upload relationship is loaded with lazy="selectin")
        graph = Graph(
            project_id=job.upload.project_id,
            job_id=job_id,
            version=GRAPH_VERSION,
            json_blob=canonical_json,
            meta={},  # Can store resolver-specific metadata here
        )

        db_session.add(graph)
        db_session.commit()
        db_session.refresh(graph)

        logger.info(f"Created graph with id={graph.id} for job_id={job_id}")
        return graph

    except Exception as e:
        logger.error(f"Error resolving and creating graph for job_id={job_id}: {e}")
        db_session.rollback()
        raise
