"""Splunk Configuration Parser Service.

This module parses Splunk configuration files (inputs.conf, outputs.conf, props.conf,
transforms.conf) from extracted snapshots and applies Splunk's configuration precedence
rules to produce a merged, canonical view of the configuration.

Precedence Rules (lowest to highest):
    - system/default
    - system/local
    - apps/*/default
    - apps/*/local

Later layers override earlier layers for the same stanza and key. This matches Splunk's
runtime configuration precedence.

Supported Configuration Files:
    - inputs.conf: Data inputs (monitor://, tcp://, udp://, splunktcp://, http, script://)
    - outputs.conf: Output groups (tcpout, SSL/TLS, indexer discovery)
    - props.conf: Parsing configurations (TRANSFORMS-*, LINE_BREAKER, TIME_FORMAT)
    - transforms.conf: Field extractions, routing rules, event rewriting

Security:
    Sensitive configuration values (pass4SymmKey, sslPassword, tokens) are redacted
    and replaced with "<REDACTED>" per spec section 8.

Usage:
    parsed = parse_splunk_config(job_id)
    # Returns ParsedConfig with inputs, outputs, props, transforms, metadata
"""

import configparser
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.services.storage import get_work_directory

logger = logging.getLogger(__name__)

# Precedence layers from lowest to highest priority
PRECEDENCE_LAYERS = [
    ("system", "default"),
    ("system", "local"),
    ("apps", "default"),
    ("apps", "local"),
]

# Sensitive keys to redact (case-insensitive matching)
SENSITIVE_KEYS = {"pass4symmkey", "sslpassword", "password", "token", "secret"}

# Configuration file names
CONF_FILES = ["inputs.conf", "outputs.conf", "props.conf", "transforms.conf"]


@dataclass
class InputStanza:
    """Represents a parsed input stanza from inputs.conf.

    Examples:
        [monitor:///var/log/messages]
        [tcp://:9999]
        [splunktcp://:9997]
        [http://my_hec_token]
    """

    stanza_name: str
    input_type: str  # "monitor", "tcp", "udp", "splunktcp", "http", "script", etc.
    source_path: str | None = None
    port: int | None = None
    sourcetype: str | None = None
    index: str | None = None
    host: str | None = None
    disabled: bool = False
    options: dict[str, str] = field(default_factory=dict)
    source_file: str = ""  # Highest-precedence source file
    source_app: str | None = None  # Highest-precedence source app
    source_files: list[str] = field(default_factory=list)  # All contributing source files
    source_apps: list[str | None] = field(default_factory=list)  # All contributing source apps


@dataclass
class OutputGroup:
    """Represents a parsed tcpout group from outputs.conf.

    Examples:
        [tcpout:idxGrp1]
        server = idx1.example.com:9997, idx2.example.com:9997
        compressed = true
    """

    group_name: str
    servers: list[str] = field(default_factory=list)
    default_group: bool = False
    ssl_enabled: bool | None = None
    ssl_cert_path: str | None = None
    compressed: bool | None = None
    use_ack: bool | None = None
    indexer_discovery: str | None = None
    options: dict[str, Any] = field(default_factory=dict)
    source_file: str = ""  # Highest-precedence source file
    source_app: str | None = None  # Highest-precedence source app
    source_files: list[str] = field(default_factory=list)  # All contributing source files
    source_apps: list[str | None] = field(default_factory=list)  # All contributing source apps


@dataclass
class PropsStanza:
    """Represents a parsed props stanza from props.conf.

    Examples:
        [sourcetype::apache:access]
        [source::/var/log/apache/*.log]
        [host::webserver*]
    """

    stanza_name: str
    stanza_type: str  # "sourcetype", "source", "host", "default"
    stanza_value: str
    transforms: list[str] = field(default_factory=list)
    line_breaker: str | None = None
    time_format: str | None = None
    truncate: int | None = None
    options: dict[str, str] = field(default_factory=dict)
    source_file: str = ""  # Highest-precedence source file
    source_app: str | None = None  # Highest-precedence source app
    source_files: list[str] = field(default_factory=list)  # All contributing source files
    source_apps: list[str | None] = field(default_factory=list)  # All contributing source apps


@dataclass
class TransformStanza:
    """Represents a parsed transform stanza from transforms.conf.

    Examples:
        [route_to_web_index]
        REGEX = webserver
        DEST_KEY = _MetaData:Index
        FORMAT = web_index
    """

    stanza_name: str
    regex: str | None = None
    format: str | None = None
    dest_key: str | None = None
    source_key: str | None = None
    lookup_name: str | None = None
    filename: str | None = None
    is_drop: bool = False  # Convenience: True if routing to nullQueue
    is_index_routing: bool = False  # Convenience: True if DEST_KEY = _MetaData:Index
    is_sourcetype_rewrite: bool = False  # Convenience: True if DEST_KEY = _MetaData:Sourcetype
    is_host_rewrite: bool = False  # Convenience: True if DEST_KEY = _MetaData:Host
    options: dict[str, str] = field(default_factory=dict)
    source_file: str = ""  # Highest-precedence source file
    source_app: str | None = None  # Highest-precedence source app
    source_files: list[str] = field(default_factory=list)  # All contributing source files
    source_apps: list[str | None] = field(default_factory=list)  # All contributing source apps


@dataclass
class ParsedConfig:
    """Top-level container for all parsed Splunk configurations.

    Contains all inputs, outputs, props, transforms with precedence applied,
    plus metadata and traceability information for debugging.
    """

    inputs: list[InputStanza] = field(default_factory=list)
    outputs: list[OutputGroup] = field(default_factory=list)
    props: list[PropsStanza] = field(default_factory=list)
    transforms: list[TransformStanza] = field(default_factory=list)
    host_metadata: dict[str, Any] = field(default_factory=dict)
    traceability: dict[str, list[str]] = field(default_factory=dict)


def create_case_sensitive_parser() -> configparser.ConfigParser:
    """Create a ConfigParser with case-sensitive key preservation.

    Splunk configuration keys are case-sensitive (e.g., TRANSFORMS-routing vs
    transforms-routing are different). Python's default ConfigParser lowercases
    all keys, so we override optionxform to preserve original casing.

    Returns:
        ConfigParser instance configured for case-sensitive parsing.
    """
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str  # type: ignore  # Preserve key casing
    return parser


def redact_sensitive_value(key: str, value: str) -> str:
    """Redact sensitive configuration values for security.

    Checks if the key matches known sensitive patterns (passwords, tokens, secrets)
    and replaces the actual value with "<REDACTED>" per spec section 8.

    Args:
        key: Configuration key name.
        value: Configuration value to potentially redact.

    Returns:
        Original value if not sensitive, "<REDACTED>" otherwise.
    """
    if key.lower() in SENSITIVE_KEYS:
        return "<REDACTED>"
    return value


def find_conf_files(work_dir: Path, conf_name: str) -> list[tuple[Path, str, str | None]]:
    """Find all instances of a configuration file across precedence layers.

    Searches for conf_name in:
        - system/default/{conf_name}
        - system/local/{conf_name}
        - apps/*/default/{conf_name}
        - apps/*/local/{conf_name}

    Args:
        work_dir: Root directory of extracted Splunk configuration.
        conf_name: Name of configuration file (e.g., "inputs.conf").

    Returns:
        List of tuples (file_path, layer_type, app_name) sorted by precedence.
        layer_type is "system/default", "system/local", "app/default", or "app/local".
        app_name is None for system layers, app directory name for app layers.
    """
    found_files: list[tuple[Path, str, str | None]] = []

    # System layers
    for scope, level in [("system", "default"), ("system", "local")]:
        path = work_dir / scope / level / conf_name
        if path.exists():
            layer_type = f"{scope}/{level}"
            found_files.append((path, layer_type, None))

    # App layers
    apps_dir = work_dir / "apps"
    if apps_dir.exists():
        for app_dir in sorted(apps_dir.iterdir()):
            if not app_dir.is_dir():
                continue
            app_name = app_dir.name
            for level in ["default", "local"]:
                path = app_dir / level / conf_name
                if path.exists():
                    layer_type = f"app/{level}"
                    found_files.append((path, layer_type, app_name))

    # Sort by precedence order
    def precedence_key(item: tuple[Path, str, str | None]) -> int:
        _, layer_type, _ = item
        precedence_order = {
            "system/default": 0,
            "system/local": 1,
            "app/default": 2,
            "app/local": 3,
        }
        return precedence_order.get(layer_type, 999)

    found_files.sort(key=precedence_key)
    return found_files


def parse_conf_file(file_path: Path) -> configparser.ConfigParser:
    """Parse a Splunk configuration file using case-sensitive ConfigParser.

    Args:
        file_path: Path to the .conf file.

    Returns:
        Parsed ConfigParser object. Returns empty parser on parse errors.
    """
    parser = create_case_sensitive_parser()
    try:
        parser.read(file_path, encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to parse {file_path}: {e}")
    return parser


def merge_conf_layers(
    conf_files: list[tuple[Path, str, str | None]], conf_type: str, work_dir: Path
) -> dict[str, dict[str, Any]]:
    """Merge multiple configuration file layers according to precedence rules.

    Later layers override earlier layers for the same stanza and key. Tracks source
    metadata (_source_file, _source_files, _source_app, _source_apps) for traceability.

    Args:
        conf_files: List of (file_path, layer_type, app_name) tuples in precedence order.
        conf_type: Configuration type for logging (e.g., "inputs.conf").
        work_dir: Root directory of extracted Splunk configuration for relative path computation.

    Returns:
        Dict mapping stanza names to merged key-value dicts with metadata:
        {stanza_name: {key: value, '_source_file': path, '_source_files': [paths],
                       '_source_app': app_name, '_source_apps': [apps]}}
    """
    merged: dict[str, dict[str, Any]] = {}

    for file_path, layer_type, app_name in conf_files:
        parser = parse_conf_file(file_path)
        logger.debug(f"Merging {conf_type} from {layer_type}: {file_path}")

        for section in parser.sections():
            if section not in merged:
                merged[section] = {}
                merged[section]["_source_files"] = []
                merged[section]["_source_apps"] = []

            # Merge all key-value pairs, later layers override
            for key, value in parser.items(section):
                redacted_value = redact_sensitive_value(key, value)
                merged[section][key] = redacted_value

            # Accumulate source file and app metadata
            relative_path = str(file_path.relative_to(work_dir))
            merged[section]["_source_files"].append(relative_path)
            merged[section]["_source_apps"].append(app_name)

            # Keep highest-precedence (latest) source file and app for convenience
            merged[section]["_source_file"] = relative_path
            merged[section]["_source_app"] = app_name

    return merged


def parse_inputs_conf(work_dir: Path) -> list[InputStanza]:
    """Parse all inputs.conf files and return merged input stanzas.

    Extracts input type, source paths, ports, and common settings (sourcetype, index,
    host, disabled) from stanza names and key-value pairs.

    Args:
        work_dir: Root directory of extracted Splunk configuration.

    Returns:
        List of InputStanza objects with precedence applied.
    """
    conf_files = find_conf_files(work_dir, "inputs.conf")
    if not conf_files:
        logger.info("No inputs.conf files found")
        return []

    merged = merge_conf_layers(conf_files, "inputs.conf", work_dir)
    inputs: list[InputStanza] = []

    # Regex patterns for input type extraction
    monitor_pattern = re.compile(r"^monitor://(.+)$")
    tcp_pattern = re.compile(r"^tcp://(?:[^:]*:)?(\d+)$")
    udp_pattern = re.compile(r"^udp://(?:[^:]*:)?(\d+)$")
    splunktcp_pattern = re.compile(r"^splunktcp://(?:[^:]*:)?(\d+)$")
    http_pattern = re.compile(r"^http(?:://(.+))?$")
    script_pattern = re.compile(r"^script://(.+)$")
    wineventlog_pattern = re.compile(r"^WinEventLog://(.+)$", re.IGNORECASE)

    for stanza_name, stanza_data in merged.items():
        input_type = "modular"  # Default for unknown types
        source_path: str | None = None
        port: int | None = None

        # Extract input type and parameters from stanza name
        if match := monitor_pattern.match(stanza_name):
            input_type = "monitor"
            source_path = match.group(1)
        elif match := tcp_pattern.match(stanza_name):
            input_type = "tcp"
            port = int(match.group(1))
        elif match := udp_pattern.match(stanza_name):
            input_type = "udp"
            port = int(match.group(1))
        elif match := splunktcp_pattern.match(stanza_name):
            input_type = "splunktcp"
            port = int(match.group(1))
        elif match := http_pattern.match(stanza_name):
            input_type = "http"
            source_path = match.group(1)  # HEC token name
        elif match := script_pattern.match(stanza_name):
            input_type = "script"
            source_path = match.group(1)
        elif match := wineventlog_pattern.match(stanza_name):
            input_type = "WinEventLog"
            source_path = match.group(1)

        # Extract common settings
        sourcetype = stanza_data.get("sourcetype")
        index = stanza_data.get("index")
        host = stanza_data.get("host")
        disabled_value = stanza_data.get("disabled", "false").lower()
        disabled = disabled_value in ("1", "true", "yes")

        # Extract source file and app metadata
        source_file = stanza_data.get("_source_file", "")
        source_app = stanza_data.get("_source_app")
        source_files = stanza_data.get("_source_files", [])
        source_apps = stanza_data.get("_source_apps", [])

        # Store remaining options (exclude metadata keys)
        options = {
            k: v
            for k, v in stanza_data.items()
            if k
            not in {
                "sourcetype",
                "index",
                "host",
                "disabled",
                "_source_file",
                "_source_files",
                "_source_app",
                "_source_apps",
            }
        }

        inputs.append(
            InputStanza(
                stanza_name=stanza_name,
                input_type=input_type,
                source_path=source_path,
                port=port,
                sourcetype=sourcetype,
                index=index,
                host=host,
                disabled=disabled,
                options=options,
                source_file=source_file,
                source_app=source_app,
                source_files=source_files,
                source_apps=source_apps,
            )
        )

    logger.info(f"Parsed {len(inputs)} input stanzas from inputs.conf")
    return inputs


def parse_outputs_conf(work_dir: Path) -> list[OutputGroup]:
    """Parse all outputs.conf files and return merged output groups.

    Extracts tcpout groups, servers, SSL/TLS settings, and identifies the default group.

    Args:
        work_dir: Root directory of extracted Splunk configuration.

    Returns:
        List of OutputGroup objects with precedence applied.
    """
    conf_files = find_conf_files(work_dir, "outputs.conf")
    if not conf_files:
        logger.info("No outputs.conf files found")
        return []

    merged = merge_conf_layers(conf_files, "outputs.conf", work_dir)
    outputs: list[OutputGroup] = []

    # Find default group from [tcpout] section
    default_group_name: str | None = None
    if "tcpout" in merged:
        default_group_name = merged["tcpout"].get("defaultGroup")

    # Parse indexer_discovery stanzas first to build discovery mapping
    indexer_discovery_map: dict[str, dict[str, Any]] = {}
    indexer_discovery_pattern = re.compile(r"^indexer_discovery:(.+)$")
    for stanza_name, stanza_data in merged.items():
        if match := indexer_discovery_pattern.match(stanza_name):
            discovery_name = match.group(1)
            # Extract key indexer discovery settings
            indexer_discovery_map[discovery_name] = {
                "master_uri": (
                    stanza_data.get("master_uri")
                    if stanza_data.get("master_uri") is not None
                    else stanza_data.get("masterUri")
                ),
                "pass4SymmKey": (
                    stanza_data.get("pass4SymmKey")
                    if stanza_data.get("pass4SymmKey") is not None
                    else stanza_data.get("pass4symmkey")
                ),
                "sslCertPath": (
                    stanza_data.get("sslCertPath")
                    if stanza_data.get("sslCertPath") is not None
                    else stanza_data.get("sslcertpath")
                ),
                "sslPassword": (
                    stanza_data.get("sslPassword")
                    if stanza_data.get("sslPassword") is not None
                    else stanza_data.get("sslpassword")
                ),
                "sslVerifyServerCert": (
                    stanza_data.get("sslVerifyServerCert")
                    if stanza_data.get("sslVerifyServerCert") is not None
                    else stanza_data.get("sslverifyservercert")
                ),
                "source_file": stanza_data.get("_source_file", ""),
            }

    # Parse tcpout groups
    tcpout_pattern = re.compile(r"^tcpout:(.+)$")
    for stanza_name, stanza_data in merged.items():
        if match := tcpout_pattern.match(stanza_name):
            group_name = match.group(1)

            # Parse server list (comma-separated host:port)
            servers_str = stanza_data.get("server", "")
            servers = [s.strip() for s in servers_str.split(",") if s.strip()]

            # Check if this is the default group
            is_default = group_name == default_group_name

            # Extract SSL/TLS settings
            ssl_cert_path = stanza_data.get("sslCertPath")
            client_cert = stanza_data.get("clientCert")
            ssl_root_ca_path = stanza_data.get("sslRootCAPath")
            use_ssl_str = stanza_data.get("useSSL")
            ssl_verify_server_cert = stanza_data.get("sslVerifyServerCert")

            # Normalize useSSL to boolean
            use_ssl_bool = None
            if use_ssl_str is not None:
                use_ssl_bool = use_ssl_str.lower() in ("1", "true", "yes")

            # Determine if SSL/TLS is enabled
            ssl_enabled = None
            if any((ssl_cert_path, client_cert, ssl_root_ca_path)):
                ssl_enabled = True
            elif use_ssl_bool is True:
                ssl_enabled = True
            elif use_ssl_bool is False:
                ssl_enabled = False

            # Extract compression and acknowledgment settings
            compressed_str = stanza_data.get("compressed")
            compressed = None
            if compressed_str is not None:
                compressed = compressed_str.lower() in ("1", "true", "yes")

            use_ack_str = stanza_data.get("useACK")
            use_ack = None
            if use_ack_str is not None:
                use_ack = use_ack_str.lower() in ("1", "true", "yes")

            # Extract indexer discovery
            indexer_discovery = stanza_data.get("indexerDiscovery")

            # Extract source file and app metadata
            source_file = stanza_data.get("_source_file", "")
            source_app = stanza_data.get("_source_app")
            source_files = stanza_data.get("_source_files", [])
            source_apps = stanza_data.get("_source_apps", [])

            # Store remaining options
            options = {
                k: v
                for k, v in stanza_data.items()
                if k
                not in {
                    "server",
                    "sslCertPath",
                    "clientCert",
                    "sslRootCAPath",
                    "useSSL",
                    "compressed",
                    "useACK",
                    "indexerDiscovery",
                    "_source_file",
                    "_source_files",
                    "_source_app",
                    "_source_apps",
                }
            }

            # Keep sslVerifyServerCert in options for separate tracking
            if ssl_verify_server_cert is not None:
                options["sslVerifyServerCert"] = ssl_verify_server_cert

            # Attach indexer discovery details if referenced
            if indexer_discovery and indexer_discovery in indexer_discovery_map:
                discovery_details = indexer_discovery_map[indexer_discovery]
                options["indexer_discovery_details"] = discovery_details

            outputs.append(
                OutputGroup(
                    group_name=group_name,
                    servers=servers,
                    default_group=is_default,
                    ssl_enabled=ssl_enabled,
                    ssl_cert_path=ssl_cert_path,
                    compressed=compressed,
                    use_ack=use_ack,
                    indexer_discovery=indexer_discovery,
                    options=options,
                    source_file=source_file,
                    source_app=source_app,
                    source_files=source_files,
                    source_apps=source_apps,
                )
            )

    # Parse tcpout-server stanzas for per-server overrides
    tcpout_server_pattern = re.compile(r"^tcpout-server://(.+)$")
    server_overrides: dict[str, dict[str, Any]] = {}
    for stanza_name, stanza_data in merged.items():
        if match := tcpout_server_pattern.match(stanza_name):
            server_endpoint = match.group(1)
            # Extract all settings except metadata
            server_settings = {k: v for k, v in stanza_data.items() if not k.startswith("_source")}
            server_overrides[server_endpoint] = server_settings

    # Merge per-server overrides into OutputGroups
    for output_group in outputs:
        per_server_options: dict[str, dict[str, Any]] = {}
        for server in output_group.servers:
            if server in server_overrides:
                per_server_options[server] = server_overrides[server]
        if per_server_options:
            output_group.options["per_server_options"] = per_server_options

    logger.info(f"Parsed {len(outputs)} output groups from outputs.conf")
    return outputs


def parse_props_conf(work_dir: Path) -> list[PropsStanza]:
    """Parse all props.conf files and return merged props stanzas.

    Extracts stanza types (sourcetype, source, host), TRANSFORMS-* references, and
    parsing settings like LINE_BREAKER and TIME_FORMAT.

    Args:
        work_dir: Root directory of extracted Splunk configuration.

    Returns:
        List of PropsStanza objects with precedence applied.
    """
    conf_files = find_conf_files(work_dir, "props.conf")
    if not conf_files:
        logger.info("No props.conf files found")
        return []

    merged = merge_conf_layers(conf_files, "props.conf", work_dir)
    props: list[PropsStanza] = []

    # Regex patterns for stanza type extraction
    sourcetype_pattern = re.compile(r"^sourcetype::(.+)$")
    source_pattern = re.compile(r"^source::(.+)$")
    host_pattern = re.compile(r"^host::(.+)$")

    for stanza_name, stanza_data in merged.items():
        stanza_type = "sourcetype"  # Default for plain stanzas
        stanza_value = stanza_name

        # Determine stanza type and extract value
        if stanza_name == "default":
            stanza_type = "default"
            stanza_value = "default"
        elif match := sourcetype_pattern.match(stanza_name):
            stanza_type = "sourcetype"
            stanza_value = match.group(1)
        elif match := source_pattern.match(stanza_name):
            stanza_type = "source"
            stanza_value = match.group(1)
        elif match := host_pattern.match(stanza_name):
            stanza_type = "host"
            stanza_value = match.group(1)

        # Extract TRANSFORMS-* keys (preserve order)
        transforms: list[str] = []
        transforms_pattern = re.compile(r"^TRANSFORMS-(.+)$", re.IGNORECASE)
        for key, value in stanza_data.items():
            if transforms_pattern.match(key):
                # Value can be comma-separated list of transform names
                transform_names = [t.strip() for t in value.split(",") if t.strip()]
                transforms.extend(transform_names)

        # Extract common parsing settings
        line_breaker = stanza_data.get("LINE_BREAKER")
        time_format = stanza_data.get("TIME_FORMAT")
        truncate_str = stanza_data.get("TRUNCATE")
        try:
            truncate = int(truncate_str) if truncate_str is not None else None
        except (ValueError, TypeError):
            truncate = None

        # Extract source file and app metadata
        source_file = stanza_data.get("_source_file", "")
        source_app = stanza_data.get("_source_app")
        source_files = stanza_data.get("_source_files", [])
        source_apps = stanza_data.get("_source_apps", [])

        # Store remaining options (REPORT-*, EXTRACT-*, EVAL-*, LOOKUP-*, etc.)
        options = {
            k: v
            for k, v in stanza_data.items()
            if k
            not in {
                "LINE_BREAKER",
                "TIME_FORMAT",
                "TRUNCATE",
                "_source_file",
                "_source_files",
                "_source_app",
                "_source_apps",
            }
            and not transforms_pattern.match(k)
        }

        props.append(
            PropsStanza(
                stanza_name=stanza_name,
                stanza_type=stanza_type,
                stanza_value=stanza_value,
                transforms=transforms,
                line_breaker=line_breaker,
                time_format=time_format,
                truncate=truncate,
                options=options,
                source_file=source_file,
                source_app=source_app,
                source_files=source_files,
                source_apps=source_apps,
            )
        )

    logger.info(f"Parsed {len(props)} props stanzas from props.conf")
    return props


def parse_transforms_conf(work_dir: Path) -> list[TransformStanza]:
    """Parse all transforms.conf files and return merged transform stanzas.

    Extracts REGEX, FORMAT, DEST_KEY, SOURCE_KEY for routing and rewriting rules,
    plus lookup definitions.

    Args:
        work_dir: Root directory of extracted Splunk configuration.

    Returns:
        List of TransformStanza objects with precedence applied.
    """
    conf_files = find_conf_files(work_dir, "transforms.conf")
    if not conf_files:
        logger.info("No transforms.conf files found")
        return []

    merged = merge_conf_layers(conf_files, "transforms.conf", work_dir)
    transforms: list[TransformStanza] = []

    for stanza_name, stanza_data in merged.items():
        # Extract key transform fields
        regex = stanza_data.get("REGEX")
        format_str = stanza_data.get("FORMAT")
        dest_key = stanza_data.get("DEST_KEY")
        source_key = stanza_data.get("SOURCE_KEY")

        # Extract lookup-specific fields
        lookup_name = stanza_data.get("lookup_name")
        filename = stanza_data.get("filename")

        # Set convenience flags based on DEST_KEY and FORMAT
        is_drop = False
        is_index_routing = False
        is_sourcetype_rewrite = False
        is_host_rewrite = False

        if dest_key:
            dest_key_lower = dest_key.lower()
            # Check for nullQueue drop (exact match for 'queue' or '_tcp_routing')
            if (
                dest_key_lower in ("queue", "_tcp_routing")
                and format_str
                and format_str.lower() == "nullqueue"
            ):
                is_drop = True
            # Check for metadata rewrites (case-insensitive)
            elif dest_key_lower == "_metadata:index":
                is_index_routing = True
            elif dest_key_lower == "_metadata:sourcetype":
                is_sourcetype_rewrite = True
            elif dest_key_lower == "_metadata:host":
                is_host_rewrite = True

        # Extract source file and app metadata
        source_file = stanza_data.get("_source_file", "")
        source_app = stanza_data.get("_source_app")
        source_files = stanza_data.get("_source_files", [])
        source_apps = stanza_data.get("_source_apps", [])

        # Store remaining options
        options = {
            k: v
            for k, v in stanza_data.items()
            if k
            not in {
                "REGEX",
                "FORMAT",
                "DEST_KEY",
                "SOURCE_KEY",
                "lookup_name",
                "filename",
                "_source_file",
                "_source_files",
                "_source_app",
                "_source_apps",
            }
        }

        transforms.append(
            TransformStanza(
                stanza_name=stanza_name,
                regex=regex,
                format=format_str,
                dest_key=dest_key,
                source_key=source_key,
                lookup_name=lookup_name,
                filename=filename,
                is_drop=is_drop,
                is_index_routing=is_index_routing,
                is_sourcetype_rewrite=is_sourcetype_rewrite,
                is_host_rewrite=is_host_rewrite,
                options=options,
                source_file=source_file,
                source_app=source_app,
                source_files=source_files,
                source_apps=source_apps,
            )
        )

    logger.info(f"Parsed {len(transforms)} transform stanzas from transforms.conf")
    return transforms


def parse_splunk_config(job_id: int, work_dir: Path | None = None) -> ParsedConfig:
    """Parse all Splunk configuration files for a job and return merged configurations.

    Main entry point for configuration parsing. Applies precedence rules across all
    configuration layers and returns structured ParsedConfig with metadata.

    Args:
        job_id: Job ID to parse configurations for.
        work_dir: Optional work directory path. If not provided, will use
            get_work_directory(job_id).

    Returns:
        ParsedConfig containing all inputs, outputs, props, transforms with metadata.

    Raises:
        FileNotFoundError: If work directory does not exist.
        ValueError: If no configuration files are found.
    """
    logger.info(f"Starting Splunk configuration parsing for job_id={job_id}")

    # Get work directory from storage service or use provided one
    if work_dir is None:
        work_dir = get_work_directory(job_id)
    if not work_dir.exists():
        raise FileNotFoundError(f"Work directory not found: {work_dir}")

    logger.debug(f"Work directory: {work_dir}")

    # Parse all configuration types
    inputs = parse_inputs_conf(work_dir)
    outputs = parse_outputs_conf(work_dir)
    props = parse_props_conf(work_dir)
    transforms = parse_transforms_conf(work_dir)

    # Build host metadata
    host_metadata: dict[str, Any] = {
        "work_directory": str(work_dir),
        "job_id": job_id,
    }

    # Extract hostname if available (try to infer from directory or conf files)
    # This is a best-effort attempt; actual hostname may not be deterministic
    hostname_candidates = []
    server_conf_paths = find_conf_files(work_dir, "server.conf")
    for path, _, _ in server_conf_paths:
        parser = parse_conf_file(path)
        if parser.has_option("general", "serverName"):
            hostname_candidates.append(parser.get("general", "serverName"))
    if hostname_candidates:
        host_metadata["hostname"] = hostname_candidates[-1]  # Use highest precedence

    # List all apps found
    apps_dir = work_dir / "apps"
    if apps_dir.exists():
        apps_found = [d.name for d in apps_dir.iterdir() if d.is_dir()]
        host_metadata["apps"] = sorted(apps_found)
        host_metadata["app_count"] = len(apps_found)

    # Count stanzas by type
    host_metadata["input_count"] = len(inputs)
    host_metadata["output_count"] = len(outputs)
    host_metadata["props_count"] = len(props)
    host_metadata["transforms_count"] = len(transforms)

    # Build traceability map
    traceability: dict[str, list[str]] = {}

    for input_stanza in inputs:
        traceability.setdefault(input_stanza.stanza_name, []).extend(input_stanza.source_files)

    for output_group in outputs:
        group_key = f"tcpout:{output_group.group_name}"
        traceability.setdefault(group_key, []).extend(output_group.source_files)

    for props_stanza in props:
        traceability.setdefault(props_stanza.stanza_name, []).extend(props_stanza.source_files)

    for transform_stanza in transforms:
        traceability.setdefault(transform_stanza.stanza_name, []).extend(
            transform_stanza.source_files
        )

    # Create and return ParsedConfig
    parsed_config = ParsedConfig(
        inputs=inputs,
        outputs=outputs,
        props=props,
        transforms=transforms,
        host_metadata=host_metadata,
        traceability=traceability,
    )

    logger.info(
        f"Parsing complete: {len(inputs)} inputs, {len(outputs)} outputs, "
        f"{len(props)} props, {len(transforms)} transforms"
    )

    return parsed_config
