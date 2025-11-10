"""Unit tests for the parser service."""

from pathlib import Path

import pytest

from app.services.parser import (
    parse_splunk_config,
    # TODO: Import additional parser functions as they are implemented:
    # parse_inputs_conf,
    # parse_outputs_conf,
    # parse_props_conf,
    # parse_transforms_conf,
    # redact_sensitive_value,
    # merge_conf_layers,
    # find_conf_files,
)
from tests.fixtures.splunk_configs import (
    create_ambiguous_routing_config,
    create_dangling_output_config,
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
        # TODO: Create precedence test config
        # config_dir = create_precedence_test_config(tmp_path)
        # parsed = parse_splunk_config(config_dir)
        # TODO: Assert final index value is from app/local layer (should be 'app_local_index')
        # TODO: Verify source_file metadata tracks highest precedence layer
        pass

    def test_merge_conf_layers_override(self, tmp_path: Path):
        """Verify later layers override earlier layers in merged config."""
        # TODO: Create multi-layer config
        # TODO: Call merge_conf_layers with files from all layers
        # TODO: Assert values from higher precedence layers win
        pass

    def test_merge_conf_layers_metadata(self, tmp_path: Path):
        """Verify _source_file and _source_app metadata is tracked correctly."""
        # TODO: Merge configs from multiple layers
        # TODO: Assert _source_file points to highest precedence file
        # TODO: Assert _source_app is correctly identified
        pass


@pytest.mark.unit
class TestInputsConfParsing:
    """Test inputs.conf parsing for various input types."""

    def test_parse_monitor_input(self, tmp_path: Path):
        """Parse monitor:// stanza, verify input_type, source_path, sourcetype, index."""
        # TODO: Create UF config with monitor inputs
        # config_dir = create_uf_config(tmp_path)
        # parsed = parse_splunk_config(config_dir)
        # TODO: Assert inputs list contains monitor stanzas
        # TODO: Verify input_type == "monitor"
        # TODO: Verify source_path == "/var/log/messages"
        # TODO: Verify sourcetype == "linux:messages"
        # TODO: Verify index == "os"
        pass

    def test_parse_tcp_input(self, tmp_path: Path):
        """Parse tcp://:9999 input, verify port extraction."""
        # TODO: Create config with tcp input
        # TODO: Parse and verify input_type == "tcp"
        # TODO: Verify port == 9999
        pass

    def test_parse_udp_input(self, tmp_path: Path):
        """Parse udp://:514 input, verify port extraction."""
        # TODO: Create config with udp input
        # TODO: Verify input_type == "udp"
        # TODO: Verify port == 514
        pass

    def test_parse_splunktcp_input(self, tmp_path: Path):
        """Parse splunktcp://:9997 input, verify port extraction."""
        # TODO: Create indexer config with splunktcp input
        # config_dir = create_idx_config(tmp_path)
        # parsed = parse_splunk_config(config_dir)
        # TODO: Verify input_type == "splunktcp"
        # TODO: Verify port == 9997
        pass

    def test_parse_http_input(self, tmp_path: Path):
        """Parse http://token HEC input, verify token extraction."""
        # TODO: Create HEC config
        # config_dir = create_hec_config(tmp_path)
        # parsed = parse_splunk_config(config_dir)
        # TODO: Verify input_type == "http"
        # TODO: Verify token is extracted
        pass

    def test_parse_script_input(self, tmp_path: Path):
        """Parse script://./bin/script.sh input, verify path extraction."""
        # TODO: Create config with script input
        # TODO: Verify input_type == "script"
        # TODO: Verify script path is extracted
        pass

    def test_parse_disabled_input(self, tmp_path: Path):
        """Parse input with disabled=1, verify disabled=True flag."""
        # TODO: Create config with disabled input
        # TODO: Verify disabled field is True
        pass


@pytest.mark.unit
class TestOutputsConfParsing:
    """Test outputs.conf parsing for forwarding configuration."""

    def test_parse_tcpout_group(self, tmp_path: Path):
        """Parse tcpout group, verify servers list and group_name."""
        # TODO: Create UF config with tcpout group
        # config_dir = create_uf_config(tmp_path)
        # parsed = parse_splunk_config(config_dir)
        # TODO: Verify output groups are parsed
        # TODO: Verify group_name == "hf_group"
        # TODO: Verify servers list contains "hf01.example.com:9997"
        pass

    def test_parse_default_group(self, tmp_path: Path):
        """Parse defaultGroup setting, verify default_group=True."""
        # TODO: Parse config with defaultGroup setting
        # TODO: Verify default_group field is True for the specified group
        pass

    def test_parse_ssl_settings(self, tmp_path: Path):
        """Parse SSL settings (sslCertPath, useSSL), verify ssl_enabled=True."""
        # TODO: Create HF config with SSL
        # config_dir = create_hf_config(tmp_path)
        # parsed = parse_splunk_config(config_dir)
        # TODO: Verify ssl_enabled == True
        # TODO: Verify ssl_cert_path is extracted
        pass

    def test_parse_indexer_discovery(self, tmp_path: Path):
        """Parse indexerDiscovery setting, verify indexer_discovery field."""
        # TODO: Create indexer discovery config
        # config_dir = create_indexer_discovery_config(tmp_path)
        # parsed = parse_splunk_config(config_dir)
        # TODO: Verify indexer_discovery field is set
        # TODO: Verify master_uri is extracted
        pass

    def test_parse_compression_ack(self, tmp_path: Path):
        """Parse compressed and useACK settings, verify boolean conversion."""
        # TODO: Parse config with compressed=true, useACK=true
        # TODO: Verify boolean fields are correctly converted
        pass


@pytest.mark.unit
class TestPropsConfParsing:
    """Test props.conf parsing for sourcetype and transform references."""

    def test_parse_sourcetype_stanza(self, tmp_path: Path):
        """Parse [sourcetype::apache:access], verify stanza_type and stanza_value."""
        # TODO: Parse props.conf with sourcetype stanza
        # TODO: Verify stanza_type == "sourcetype"
        # TODO: Verify stanza_value == "apache:access"
        pass

    def test_parse_source_stanza(self, tmp_path: Path):
        """Parse [source::/var/log/*.log], verify stanza_type."""
        # TODO: Parse props.conf with source stanza
        # TODO: Verify stanza_type == "source"
        pass

    def test_parse_host_stanza(self, tmp_path: Path):
        """Parse [host::webserver*], verify stanza_type."""
        # TODO: Parse props.conf with host stanza
        # TODO: Verify stanza_type == "host"
        pass

    def test_parse_transforms_references(self, tmp_path: Path):
        """Parse TRANSFORMS-routing reference, verify transforms list."""
        # TODO: Create HF config with transforms
        # config_dir = create_hf_config(tmp_path)
        # parsed = parse_splunk_config(config_dir)
        # TODO: Verify props stanzas contain transforms references
        # TODO: Verify transforms list includes "route_by_severity" and "drop_debug"
        pass

    def test_parse_multiple_transforms(self, tmp_path: Path):
        """Parse multiple TRANSFORMS-* settings, verify order preserved."""
        # TODO: Parse props with multiple TRANSFORMS-a, TRANSFORMS-b
        # TODO: Verify order is preserved in transforms list
        pass


@pytest.mark.unit
class TestTransformsConfParsing:
    """Test transforms.conf parsing for routing and filtering rules."""

    def test_parse_index_routing_transform(self, tmp_path: Path):
        """Parse DEST_KEY=_MetaData:Index transform, verify is_index_routing=True."""
        # TODO: Create HF config with index routing transform
        # config_dir = create_hf_config(tmp_path)
        # parsed = parse_splunk_config(config_dir)
        # TODO: Verify transform has is_index_routing == True
        # TODO: Verify target index is extracted from FORMAT field
        pass

    def test_parse_drop_transform(self, tmp_path: Path):
        """Parse DEST_KEY=queue, FORMAT=nullQueue transform, verify is_drop=True."""
        # TODO: Parse drop transform
        # TODO: Verify is_drop == True
        # TODO: Verify REGEX pattern is extracted
        pass

    def test_parse_sourcetype_rewrite(self, tmp_path: Path):
        """Parse DEST_KEY=_MetaData:Sourcetype, verify is_sourcetype_rewrite=True."""
        # TODO: Parse sourcetype rewrite transform
        # TODO: Verify is_sourcetype_rewrite == True
        pass

    def test_parse_regex_format(self, tmp_path: Path):
        """Parse REGEX and FORMAT fields, verify extraction."""
        # TODO: Parse transform with REGEX and FORMAT
        # TODO: Verify both fields are correctly extracted
        pass


@pytest.mark.unit
class TestSensitiveValueRedaction:
    """Test redaction of sensitive configuration values."""

    def test_redact_pass4symmkey(self, tmp_path: Path):
        """Verify pass4SymmKey is redacted to <REDACTED>."""
        # TODO: Create config with pass4SymmKey
        # config_dir = create_indexer_discovery_config(tmp_path)
        # parsed = parse_splunk_config(config_dir)
        # TODO: Verify pass4SymmKey value contains "<REDACTED>"
        # TODO: Original value should not appear in parsed config
        pass

    def test_redact_sslpassword(self, tmp_path: Path):
        """Verify sslPassword is redacted."""
        # TODO: Create config with sslPassword
        # TODO: Verify value is redacted
        pass

    def test_redact_token(self, tmp_path: Path):
        """Verify token fields are redacted."""
        # TODO: Create config with tokens
        # TODO: Verify tokens are redacted
        pass

    def test_preserve_normal_values(self, tmp_path: Path):
        """Verify non-sensitive values are not redacted."""
        # TODO: Parse config with normal values
        # TODO: Verify index names, hostnames, ports are not redacted
        pass


@pytest.mark.unit
class TestCompleteConfigParsing:
    """Test parsing of complete Splunk configurations."""

    def test_parse_splunk_config_complete(self, tmp_path: Path):
        """Parse complete config, verify all components."""
        # TODO: Create HF config (most complex scenario)
        # config_dir = create_hf_config(tmp_path)
        # parsed = parse_splunk_config(config_dir)
        # TODO: Verify parsed has inputs, outputs, props, transforms
        # TODO: Verify host_metadata contains hostname
        # TODO: Verify traceability map is populated
        pass

    def test_parse_splunk_config_empty(self, tmp_path: Path):
        """Handle empty config gracefully."""
        # TODO: Create empty directory
        # parsed = parse_splunk_config(tmp_path)
        # TODO: Verify returns empty/default ParsedConfig
        # TODO: Should not raise errors
        pass

    def test_parse_splunk_config_missing_work_dir(self, tmp_path: Path):
        """Raise FileNotFoundError for missing directory."""
        # TODO: Call parse_splunk_config with non-existent path
        # TODO: Verify raises FileNotFoundError
        pass

    def test_parse_splunk_config_hostname_extraction(self, tmp_path: Path):
        """Verify hostname extraction from server.conf."""
        # TODO: Create config with server.conf containing serverName
        # TODO: Verify hostname is extracted to host_metadata
        pass

    def test_parse_splunk_config_apps_metadata(self, tmp_path: Path):
        """Verify apps list in host_metadata."""
        # TODO: Create config with multiple apps
        # TODO: Verify apps list includes all app directories
        pass
