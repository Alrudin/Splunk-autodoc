"""Golden Splunk configuration samples for testing parser, resolver, and validator services."""

from pathlib import Path


def write_conf_file(path: Path, content: str) -> None:
    """Write .conf file with proper formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def create_uf_config(base_dir: Path) -> Path:
    """
    Universal Forwarder configuration.
    Use case: Test basic forwarding, no transforms, simple routing.
    """
    # inputs.conf (system/local)
    inputs_content = """[monitor:///var/log/messages]
sourcetype = linux:messages
index = os

[monitor:///var/log/secure]
sourcetype = linux:secure
index = security
"""
    write_conf_file(base_dir / "system/local/inputs.conf", inputs_content)

    # outputs.conf (system/local)
    outputs_content = """[tcpout]
defaultGroup = hf_group

[tcpout:hf_group]
server = hf01.example.com:9997
compressed = true
"""
    write_conf_file(base_dir / "system/local/outputs.conf", outputs_content)

    return base_dir


def create_hf_config(base_dir: Path) -> Path:
    """
    Heavy Forwarder configuration with parsing and routing.
    Use case: Test props/transforms evaluation, index routing, drops, SSL/TLS.
    """
    # inputs.conf (system/local)
    inputs_content = """[splunktcp://:9997]
disabled = false

[monitor:///opt/app/logs/*.log]
sourcetype = app:log
"""
    write_conf_file(base_dir / "system/local/inputs.conf", inputs_content)

    # outputs.conf (system/local)
    outputs_content = """[tcpout]
defaultGroup = idx_group

[tcpout:idx_group]
server = idx01.example.com:9997,idx02.example.com:9997
useSSL = true
sslCertPath = /opt/splunk/etc/auth/server.pem
compressed = true
"""
    write_conf_file(base_dir / "system/local/outputs.conf", outputs_content)

    # props.conf (apps/Splunk_TA_nix/local)
    props_content = """[sourcetype::app:log]
TRANSFORMS-route_by_severity = route_by_severity
TRANSFORMS-drop_debug = drop_debug
"""
    write_conf_file(base_dir / "apps/Splunk_TA_nix/local/props.conf", props_content)

    # transforms.conf (apps/Splunk_TA_nix/local)
    transforms_content = """[route_by_severity]
REGEX = ERROR
DEST_KEY = _MetaData:Index
FORMAT = errors

[drop_debug]
REGEX = DEBUG
DEST_KEY = queue
FORMAT = nullQueue
"""
    write_conf_file(base_dir / "apps/Splunk_TA_nix/local/transforms.conf", transforms_content)

    return base_dir


def create_idx_config(base_dir: Path) -> Path:
    """
    Indexer configuration.
    Use case: Test indexer role detection, no outputs (terminal node).
    """
    # inputs.conf (system/local)
    inputs_content = """[splunktcp://:9997]
disabled = false
"""
    write_conf_file(base_dir / "system/local/inputs.conf", inputs_content)

    # outputs.conf (empty or minimal)
    outputs_content = """# Indexer - no forwarding
"""
    write_conf_file(base_dir / "system/local/outputs.conf", outputs_content)

    return base_dir


def create_hec_config(base_dir: Path) -> Path:
    """
    HEC (HTTP Event Collector) configuration.
    Use case: Test HEC input parsing, http_event_collector protocol.
    """
    # inputs.conf (apps/splunk_httpinput/local)
    inputs_content = """[http://my_hec_token]
index = hec_index
sourcetype = _json
disabled = false

[http]
port = 8088
disabled = false
"""
    write_conf_file(base_dir / "apps/splunk_httpinput/local/inputs.conf", inputs_content)

    # outputs.conf (system/local)
    outputs_content = """[tcpout]
defaultGroup = idx_group

[tcpout:idx_group]
server = idx01.example.com:9997
"""
    write_conf_file(base_dir / "system/local/outputs.conf", outputs_content)

    return base_dir


def create_indexer_discovery_config(base_dir: Path) -> Path:
    """
    Configuration with indexer discovery.
    Use case: Test indexer discovery parsing, placeholder host creation.
    """
    # outputs.conf (system/local)
    outputs_content = """[indexer_discovery:cluster_master]
master_uri = https://cm.example.com:8089
pass4SymmKey = <REDACTED>

[tcpout]
defaultGroup = discovery_group

[tcpout:discovery_group]
indexerDiscovery = cluster_master
useSSL = true
"""
    write_conf_file(base_dir / "system/local/outputs.conf", outputs_content)

    # inputs.conf (system/local)
    inputs_content = """[monitor:///var/log/app.log]
sourcetype = app:log
index = main
"""
    write_conf_file(base_dir / "system/local/inputs.conf", inputs_content)

    return base_dir


def create_dangling_output_config(base_dir: Path) -> Path:
    """
    Configuration with no outputs (dangling).
    Use case: Test DANGLING_OUTPUT finding detection.
    """
    # inputs.conf (system/local)
    inputs_content = """[monitor:///var/log/app.log]
sourcetype = app:log
index = main
"""
    write_conf_file(base_dir / "system/local/inputs.conf", inputs_content)

    # outputs.conf (empty or missing)
    # Don't create outputs.conf file at all to simulate dangling output

    return base_dir


def create_ambiguous_routing_config(base_dir: Path) -> Path:
    """
    Configuration with multiple output groups, no defaultGroup.
    Use case: Test AMBIGUOUS_GROUP finding detection, confidence=derived.
    """
    # inputs.conf (system/local)
    inputs_content = """[monitor:///var/log/app.log]
sourcetype = app:log
index = main
"""
    write_conf_file(base_dir / "system/local/inputs.conf", inputs_content)

    # outputs.conf (system/local)
    outputs_content = """[tcpout]
# No defaultGroup specified

[tcpout:group1]
server = idx01.example.com:9997

[tcpout:group2]
server = idx02.example.com:9997
"""
    write_conf_file(base_dir / "system/local/outputs.conf", outputs_content)

    return base_dir


def create_precedence_test_config(base_dir: Path) -> Path:
    """
    Configuration testing precedence rules.
    Use case: Test precedence resolution (app/local should override all others).
    """
    # system/default
    inputs_content_sys_default = """[monitor:///var/log/test.log]
sourcetype = test
index = default_index
"""
    write_conf_file(base_dir / "system/default/inputs.conf", inputs_content_sys_default)

    # system/local
    inputs_content_sys_local = """[monitor:///var/log/test.log]
sourcetype = test
index = local_index
"""
    write_conf_file(base_dir / "system/local/inputs.conf", inputs_content_sys_local)

    # apps/test_app/default
    inputs_content_app_default = """[monitor:///var/log/test.log]
sourcetype = test
index = app_default_index
"""
    write_conf_file(base_dir / "apps/test_app/default/inputs.conf", inputs_content_app_default)

    # apps/test_app/local (should win)
    inputs_content_app_local = """[monitor:///var/log/test.log]
sourcetype = test
index = app_local_index
"""
    write_conf_file(base_dir / "apps/test_app/local/inputs.conf", inputs_content_app_local)

    return base_dir
