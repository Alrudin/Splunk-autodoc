"""Unit tests for the parser service."""

from pathlib import Path

import pytest

from app.services.parser import (
    find_conf_files,
    merge_conf_layers,
    parse_inputs_conf,
    parse_outputs_conf,
    parse_props_conf,
    parse_splunk_config,
    parse_transforms_conf,
    redact_sensitive_value,
)
from tests.fixtures.splunk_configs import (
    create_hec_config,
    create_hf_config,
    create_idx_config,
    create_indexer_discovery_config,
    create_precedence_test_config,
    create_uf_config,
)


@pytest.mark.unit
class TestPrecedenceResolution:
    """Test Splunk configuration precedence rules."""

    def test_precedence_layers_order(self, tmp_path: Path):
        """Verify system/default < system/local < app/default < app/local precedence."""
        config_dir = create_precedence_test_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        # Assert exactly one InputStanza for the monitor
        assert len(parsed.inputs) == 1
        input_stanza = parsed.inputs[0]

        # Verify highest precedence wins (app_local_index from apps/test_app/local)
        assert input_stanza.index == "app_local_index"
        assert "apps/test_app/local/inputs.conf" in input_stanza.source_file
        assert input_stanza.source_app == "test_app"

    def test_merge_conf_layers_override(self, tmp_path: Path):
        """Verify later layers override earlier layers in merged config."""
        config_dir = create_precedence_test_config(tmp_path)
        conf_files = find_conf_files(config_dir, "inputs.conf")
        merged = merge_conf_layers(conf_files, "inputs.conf", config_dir)

        # Assert the monitor stanza exists
        monitor_key = "monitor:///var/log/test.log"
        assert monitor_key in merged

        # Verify highest precedence value wins
        assert merged[monitor_key]["index"] == "app_local_index"

    def test_merge_conf_layers_metadata(self, tmp_path: Path):
        """Verify _source_file and _source_app metadata is tracked correctly."""
        config_dir = create_precedence_test_config(tmp_path)
        conf_files = find_conf_files(config_dir, "inputs.conf")
        merged = merge_conf_layers(conf_files, "inputs.conf", config_dir)

        monitor_key = "monitor:///var/log/test.log"
        assert monitor_key in merged

        # Verify metadata points to highest precedence layer
        assert "apps/test_app/local/inputs.conf" in merged[monitor_key]["_source_file"]
        assert merged[monitor_key]["_source_app"] == "test_app"
        assert len(merged[monitor_key]["_source_files"]) == 4  # All four layers
        assert merged[monitor_key]["_source_apps"] == [None, None, "test_app", "test_app"]


@pytest.mark.unit
class TestInputsConfParsing:
    """Test inputs.conf parsing for various input types."""

    def test_parse_monitor_input(self, tmp_path: Path):
        """Parse monitor:// stanza, verify input_type, source_path, sourcetype, index."""
        config_dir = create_uf_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        # Assert 2 monitor inputs
        assert len(parsed.inputs) == 2

        # Find the /var/log/messages monitor
        messages_input = next(
            (i for i in parsed.inputs if i.stanza_name == "monitor:///var/log/messages"),
            None
        )
        assert messages_input is not None
        assert messages_input.input_type == "monitor"
        assert messages_input.source_path == "/var/log/messages"
        assert messages_input.sourcetype == "linux:messages"
        assert messages_input.index == "os"
        assert messages_input.disabled is False

    def test_parse_tcp_input(self, tmp_path: Path):
        """Parse tcp://:9999 input, verify port extraction."""
        from tests.fixtures.splunk_configs import write_conf_file

        inputs_content = """[tcp://:9999]
sourcetype = tcp_input
index = network
"""
        write_conf_file(tmp_path / "system/local/inputs.conf", inputs_content)

        inputs = parse_inputs_conf(tmp_path)
        tcp_input = next((i for i in inputs if i.input_type == "tcp"), None)
        assert tcp_input is not None
        assert tcp_input.port == 9999

    def test_parse_udp_input(self, tmp_path: Path):
        """Parse udp://:514 input, verify port extraction."""
        from tests.fixtures.splunk_configs import write_conf_file

        inputs_content = """[udp://:514]
sourcetype = syslog
index = network
"""
        write_conf_file(tmp_path / "system/local/inputs.conf", inputs_content)

        inputs = parse_inputs_conf(tmp_path)
        udp_input = next((i for i in inputs if i.input_type == "udp"), None)
        assert udp_input is not None
        assert udp_input.port == 514

    def test_parse_splunktcp_input(self, tmp_path: Path):
        """Parse splunktcp://:9997 input, verify port extraction."""
        config_dir = create_idx_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        # Find splunktcp input
        splunktcp_input = next(
            (i for i in parsed.inputs if i.input_type == "splunktcp"),
            None
        )
        assert splunktcp_input is not None
        assert splunktcp_input.port == 9997

    def test_parse_http_input(self, tmp_path: Path):
        """Parse http://token HEC input, verify token extraction."""
        config_dir = create_hec_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        # Find HEC token input
        hec_input = next(
            (i for i in parsed.inputs if i.stanza_name == "http://my_hec_token"),
            None
        )
        assert hec_input is not None
        assert hec_input.input_type == "http"
        assert hec_input.source_path == "my_hec_token"

        # Also verify global http stanza exists
        http_global = next(
            (i for i in parsed.inputs if i.stanza_name == "http"),
            None
        )
        assert http_global is not None

    def test_parse_script_input(self, tmp_path: Path):
        """Parse script://./bin/script.sh input, verify path extraction."""
        from tests.fixtures.splunk_configs import write_conf_file

        inputs_content = """[script://./bin/script.sh]
sourcetype = script_output
index = main
interval = 60
"""
        write_conf_file(tmp_path / "system/local/inputs.conf", inputs_content)

        inputs = parse_inputs_conf(tmp_path)
        script_input = next((i for i in inputs if i.input_type == "script"), None)
        assert script_input is not None
        assert script_input.source_path == "./bin/script.sh"

    def test_parse_disabled_input(self, tmp_path: Path):
        """Parse input with disabled=1/true/yes, verify disabled=True flag."""
        from tests.fixtures.splunk_configs import write_conf_file

        inputs_content = """[monitor:///var/log/disabled1.log]
sourcetype = test
index = main
disabled = 1

[monitor:///var/log/disabled_true.log]
sourcetype = test
index = main
disabled = true

[monitor:///var/log/disabled_yes.log]
sourcetype = test
index = main
disabled = yes
"""
        write_conf_file(tmp_path / "system/local/inputs.conf", inputs_content)

        inputs = parse_inputs_conf(tmp_path)
        assert len(inputs) == 3
        # All three inputs should have disabled = True
        assert all(inp.disabled is True for inp in inputs)


@pytest.mark.unit
class TestOutputsConfParsing:
    """Test outputs.conf parsing for forwarding configuration."""

    def test_parse_tcpout_group(self, tmp_path: Path):
        """Parse tcpout group, verify servers list and group_name."""
        config_dir = create_uf_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        # Assert output groups parsed
        assert len(parsed.outputs) == 1
        output_group = parsed.outputs[0]

        # Verify group details
        assert output_group.group_name == "hf_group"
        assert output_group.servers == ["hf01.example.com:9997"]
        assert output_group.compressed is True

    def test_parse_default_group(self, tmp_path: Path):
        """Parse defaultGroup setting, verify default_group=True."""
        config_dir = create_uf_config(tmp_path)
        outputs = parse_outputs_conf(config_dir)

        # Find hf_group (which is set as defaultGroup)
        hf_group = next((o for o in outputs if o.group_name == "hf_group"), None)
        assert hf_group is not None
        assert hf_group.default_group is True

    def test_parse_ssl_settings(self, tmp_path: Path):
        """Parse SSL settings (sslCertPath, useSSL), verify ssl_enabled=True."""
        config_dir = create_hf_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        # Find idx_group with SSL settings
        idx_group = next((o for o in parsed.outputs if o.group_name == "idx_group"), None)
        assert idx_group is not None
        assert idx_group.ssl_enabled is True
        assert idx_group.ssl_cert_path == "/opt/splunk/etc/auth/server.pem"

    def test_parse_indexer_discovery(self, tmp_path: Path):
        """Parse indexerDiscovery setting, verify indexer_discovery field."""
        config_dir = create_indexer_discovery_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        # Find discovery_group
        discovery_group = next(
            (o for o in parsed.outputs if o.group_name == "discovery_group"),
            None
        )
        assert discovery_group is not None
        assert discovery_group.indexer_discovery == "cluster_master"
        assert "indexer_discovery_details" in discovery_group.options
        assert "master_uri" in discovery_group.options["indexer_discovery_details"]
        assert discovery_group.options["indexer_discovery_details"]["pass4SymmKey"] == "<REDACTED>"

    def test_parse_compression_ack(self, tmp_path: Path):
        """Parse compressed and useACK settings, verify boolean conversion."""
        config_dir = create_uf_config(tmp_path)
        outputs = parse_outputs_conf(config_dir)

        # Verify compressed is True (from config)
        hf_group = next((o for o in outputs if o.group_name == "hf_group"), None)
        assert hf_group is not None
        assert hf_group.compressed is True

    def test_parse_useack_boolean_values(self, tmp_path: Path):
        """Parse useACK with multiple boolean representations (1/true/yes)."""
        from tests.fixtures.splunk_configs import write_conf_file

        outputs_content = """[tcpout:ack_group_1]
server = idx01.example.com:9997
useACK = 1

[tcpout:ack_group_true]
server = idx02.example.com:9997
useACK = true

[tcpout:ack_group_yes]
server = idx03.example.com:9997
useACK = yes
"""
        write_conf_file(tmp_path / "system/local/outputs.conf", outputs_content)

        outputs = parse_outputs_conf(tmp_path)
        assert len(outputs) == 3

        # All three groups should have use_ack = True
        for output_group in outputs:
            assert output_group.use_ack is True


@pytest.mark.unit
class TestPropsConfParsing:
    """Test props.conf parsing for sourcetype and transform references."""

    def test_parse_sourcetype_stanza(self, tmp_path: Path):
        """Parse [sourcetype::apache:access], verify stanza_type and stanza_value."""
        from tests.fixtures.splunk_configs import write_conf_file

        props_content = """[sourcetype::apache:access]
LINE_BREAKER = ([\\r\\n]+)
TIME_FORMAT = %d/%b/%Y:%H:%M:%S
"""
        write_conf_file(tmp_path / "system/local/props.conf", props_content)

        props = parse_props_conf(tmp_path)
        assert len(props) == 1
        assert props[0].stanza_type == "sourcetype"
        assert props[0].stanza_value == "apache:access"

    def test_parse_source_stanza(self, tmp_path: Path):
        """Parse [source::/var/log/*.log], verify stanza_type."""
        from tests.fixtures.splunk_configs import write_conf_file

        props_content = """[source::/var/log/*.log]
sourcetype = syslog
"""
        write_conf_file(tmp_path / "system/local/props.conf", props_content)

        props = parse_props_conf(tmp_path)
        assert len(props) == 1
        assert props[0].stanza_type == "source"
        assert props[0].stanza_value == "/var/log/*.log"

    def test_parse_host_stanza(self, tmp_path: Path):
        """Parse [host::webserver*], verify stanza_type."""
        from tests.fixtures.splunk_configs import write_conf_file

        props_content = """[host::webserver*]
sourcetype = webserver_logs
"""
        write_conf_file(tmp_path / "system/local/props.conf", props_content)

        props = parse_props_conf(tmp_path)
        assert len(props) == 1
        assert props[0].stanza_type == "host"
        assert props[0].stanza_value == "webserver*"

    def test_parse_transforms_references(self, tmp_path: Path):
        """Parse TRANSFORMS-routing reference, verify transforms list."""
        config_dir = create_hf_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        # Find the app:log sourcetype props stanza
        app_log_props = next(
            (p for p in parsed.props if p.stanza_value == "app:log"),
            None
        )
        assert app_log_props is not None
        assert "route_by_severity" in app_log_props.transforms
        assert "drop_debug" in app_log_props.transforms

    def test_parse_multiple_transforms(self, tmp_path: Path):
        """Parse multiple TRANSFORMS-* settings, verify order preserved."""
        from tests.fixtures.splunk_configs import write_conf_file

        props_content = """[sourcetype::test]
TRANSFORMS-a = transform_a
TRANSFORMS-b = transform_b
TRANSFORMS-c = transform_c
"""
        write_conf_file(tmp_path / "system/local/props.conf", props_content)

        props = parse_props_conf(tmp_path)
        assert len(props) == 1
        assert props[0].transforms == ["transform_a", "transform_b", "transform_c"]

    def test_parse_comma_separated_transforms(self, tmp_path: Path):
        """Parse comma-separated TRANSFORMS in single key, verify order preserved."""
        from tests.fixtures.splunk_configs import write_conf_file

        props_content = """[sourcetype::test]
TRANSFORMS-routing = a, b, c
"""
        write_conf_file(tmp_path / "system/local/props.conf", props_content)

        props = parse_props_conf(tmp_path)
        assert len(props) == 1
        assert props[0].transforms == ["a", "b", "c"]


@pytest.mark.unit
class TestTransformsConfParsing:
    """Test transforms.conf parsing for routing and filtering rules."""

    def test_parse_index_routing_transform(self, tmp_path: Path):
        """Parse DEST_KEY=_MetaData:Index transform, verify is_index_routing=True."""
        config_dir = create_hf_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        # Find route_by_severity transform
        route_transform = next(
            (t for t in parsed.transforms if t.stanza_name == "route_by_severity"),
            None
        )
        assert route_transform is not None
        assert route_transform.is_index_routing is True
        assert route_transform.dest_key == "_MetaData:Index"
        assert route_transform.format == "errors"
        assert route_transform.regex == "ERROR"

    def test_parse_drop_transform(self, tmp_path: Path):
        """Parse DEST_KEY=queue, FORMAT=nullQueue transform, verify is_drop=True."""
        config_dir = create_hf_config(tmp_path)
        transforms = parse_transforms_conf(config_dir)

        # Find drop_debug transform
        drop_transform = next(
            (t for t in transforms if t.stanza_name == "drop_debug"),
            None
        )
        assert drop_transform is not None
        assert drop_transform.is_drop is True
        assert drop_transform.regex == "DEBUG"

    def test_parse_sourcetype_rewrite(self, tmp_path: Path):
        """Parse DEST_KEY=_MetaData:Sourcetype, verify is_sourcetype_rewrite=True."""
        from tests.fixtures.splunk_configs import write_conf_file

        transforms_content = """[rewrite_sourcetype]
REGEX = .
DEST_KEY = _MetaData:Sourcetype
FORMAT = new_sourcetype
"""
        write_conf_file(tmp_path / "system/local/transforms.conf", transforms_content)

        transforms = parse_transforms_conf(tmp_path)
        assert len(transforms) == 1
        assert transforms[0].is_sourcetype_rewrite is True

    def test_parse_regex_format(self, tmp_path: Path):
        """Parse REGEX and FORMAT fields, verify extraction."""
        config_dir = create_hf_config(tmp_path)
        transforms = parse_transforms_conf(config_dir)

        # Both transforms should have regex and format
        for transform in transforms:
            assert transform.regex is not None
            if transform.stanza_name == "route_by_severity":
                assert transform.regex == "ERROR"
                assert transform.format == "errors"
            elif transform.stanza_name == "drop_debug":
                assert transform.regex == "DEBUG"
                assert transform.format == "nullQueue"


@pytest.mark.unit
class TestSensitiveValueRedaction:
    """Test redaction of sensitive configuration values."""

    def test_redact_pass4symmkey(self, tmp_path: Path):
        """Verify pass4SymmKey is redacted to <REDACTED>."""
        from tests.fixtures.splunk_configs import write_conf_file

        outputs_content = """[indexer_discovery:cluster_master]
master_uri = https://cm.example.com:8089
pass4SymmKey = s3cr3t

[tcpout]
defaultGroup = discovery_group

[tcpout:discovery_group]
indexerDiscovery = cluster_master
useSSL = true
"""
        write_conf_file(tmp_path / "system/local/outputs.conf", outputs_content)

        # Also need an inputs.conf for parse_splunk_config to work
        inputs_content = """[monitor:///var/log/app.log]
sourcetype = app:log
index = main
"""
        write_conf_file(tmp_path / "system/local/inputs.conf", inputs_content)

        parsed = parse_splunk_config(job_id=1, work_dir=tmp_path)

        # Find discovery_group output
        discovery_group = next(
            (o for o in parsed.outputs if o.group_name == "discovery_group"),
            None
        )
        assert discovery_group is not None
        assert "indexer_discovery_details" in discovery_group.options
        assert discovery_group.options["indexer_discovery_details"]["pass4SymmKey"] == "<REDACTED>"

        # Verify original secret does not appear in any parsed outputs
        for output_group in parsed.outputs:
            output_str = str(output_group.options)
            assert "s3cr3t" not in output_str

    def test_redact_sslpassword(self, tmp_path: Path):
        """Verify sslPassword is redacted."""
        from tests.fixtures.splunk_configs import write_conf_file

        outputs_content = """[tcpout:test_group]
server = idx01.example.com:9997
useSSL = true
sslPassword = super_secret_password
"""
        write_conf_file(tmp_path / "system/local/outputs.conf", outputs_content)

        outputs = parse_outputs_conf(tmp_path)
        assert len(outputs) == 1

        # Verify sslPassword is in options and redacted
        test_group = outputs[0]
        assert "sslPassword" in test_group.options
        assert test_group.options["sslPassword"] == "<REDACTED>"

        # Verify original password does not appear in serialized options
        options_str = str(test_group.options)
        assert "super_secret_password" not in options_str

        # Verify redaction function works
        assert redact_sensitive_value("sslPassword", "super_secret_password") == "<REDACTED>"

    def test_redact_token(self, tmp_path: Path):
        """Verify token fields are redacted."""
        from tests.fixtures.splunk_configs import write_conf_file

        inputs_content = """[http://hec_token_123]
token = abc123def456
index = main
"""
        write_conf_file(tmp_path / "system/local/inputs.conf", inputs_content)

        inputs = parse_inputs_conf(tmp_path)
        assert len(inputs) == 1

        # Verify token is in options and redacted
        hec_input = inputs[0]
        assert "token" in hec_input.options
        assert hec_input.options["token"] == "<REDACTED>"

        # Verify original token does not appear in any input stanza data
        # Check all string fields and options
        assert "abc123def456" not in str(hec_input.stanza_name)
        assert "abc123def456" not in str(hec_input.options)
        assert "abc123def456" not in str(hec_input.source_path or "")
        assert "abc123def456" not in str(hec_input.index or "")

        # Test the redaction function directly
        assert redact_sensitive_value("token", "abc123def456") == "<REDACTED>"

    def test_preserve_normal_values(self, tmp_path: Path):
        """Verify non-sensitive values are not redacted."""
        config_dir = create_uf_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        # Verify normal values are not redacted
        # Index names
        assert any(i.index == "os" for i in parsed.inputs)
        assert any(i.index == "security" for i in parsed.inputs)

        # Hostnames and ports
        assert any("hf01.example.com:9997" in o.servers for o in parsed.outputs)

        # Test redaction function with normal values
        assert redact_sensitive_value("index", "os") == "os"
        assert redact_sensitive_value("server", "hf01.example.com:9997") == "hf01.example.com:9997"
        assert redact_sensitive_value("port", "9997") == "9997"


@pytest.mark.unit
class TestCompleteConfigParsing:
    """Test parsing of complete Splunk configurations."""

    def test_parse_splunk_config_complete(self, tmp_path: Path):
        """Parse complete config, verify all components."""
        config_dir = create_hf_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        # Verify all components are present
        assert len(parsed.inputs) > 0
        assert len(parsed.outputs) > 0
        assert len(parsed.props) > 0
        assert len(parsed.transforms) > 0

        # Verify host_metadata
        assert "job_id" in parsed.host_metadata
        assert parsed.host_metadata["job_id"] == 1
        assert "work_directory" in parsed.host_metadata
        assert "input_count" in parsed.host_metadata
        assert "output_count" in parsed.host_metadata

        # Verify traceability
        assert len(parsed.traceability) > 0

        # Verify traceability includes expected stanza identifiers from HF config
        assert "splunktcp://:9997" in parsed.traceability
        assert "tcpout:idx_group" in parsed.traceability
        assert "sourcetype::app:log" in parsed.traceability
        assert "route_by_severity" in parsed.traceability

    def test_parse_splunk_config_empty(self, tmp_path: Path):
        """Handle empty config gracefully."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        parsed = parse_splunk_config(job_id=1, work_dir=empty_dir)

        # Verify empty lists
        assert parsed.inputs == []
        assert parsed.outputs == []
        assert parsed.props == []
        assert parsed.transforms == []

        # Verify basic metadata still exists
        assert "job_id" in parsed.host_metadata
        assert "work_directory" in parsed.host_metadata

    def test_parse_splunk_config_missing_work_dir(self, tmp_path: Path):
        """Raise FileNotFoundError for missing directory."""
        non_existent_path = tmp_path / "does_not_exist"

        with pytest.raises(FileNotFoundError):
            parse_splunk_config(job_id=1, work_dir=non_existent_path)

    def test_parse_splunk_config_hostname_extraction(self, tmp_path: Path):
        """Verify hostname extraction from server.conf."""
        from tests.fixtures.splunk_configs import write_conf_file

        server_content = """[general]
serverName = test-host-01
"""
        write_conf_file(tmp_path / "system/local/server.conf", server_content)

        parsed = parse_splunk_config(job_id=1, work_dir=tmp_path)

        assert "hostname" in parsed.host_metadata
        assert parsed.host_metadata["hostname"] == "test-host-01"

    def test_parse_splunk_config_apps_metadata(self, tmp_path: Path):
        """Verify apps list in host_metadata."""
        config_dir = create_hf_config(tmp_path)
        parsed = parse_splunk_config(job_id=1, work_dir=config_dir)

        # Verify apps metadata
        assert "apps" in parsed.host_metadata
        assert "Splunk_TA_nix" in parsed.host_metadata["apps"]
        assert "app_count" in parsed.host_metadata
        assert parsed.host_metadata["app_count"] >= 1
