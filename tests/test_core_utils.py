#!/usr/bin/env python3
"""Comprehensive Core Utilities Tests.

Tests for all utility functions in scripts/core/utils.py to achieve
high test coverage and ensure reliability.
"""

import csv
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from scripts.core.utils import (
    create_backup_file,
    ensure_directory_exists,
    get_csv_template,
    get_hosts_by_environment,
    get_hosts_by_status,
    get_logger,
    load_csv_data,
    load_hosts_from_csv,
    save_yaml_file,
    setup_logging,
    test_ansible_inventory,
    validate_csv_headers,
    validate_csv_structure,
    validate_environment_decorator,
    validate_hostname_decorator,
)
from scripts.core.models import Host


class TestLoggingUtils:
    """Test logging utility functions."""
    
    def test_setup_logging_default(self):
        """Test logging setup with default parameters."""
        logger = setup_logging()
        assert logger.name == "ansible_inventory_cli"
        assert logger.level == 20  # INFO level
    
    def test_setup_logging_custom_level(self):
        """Test logging setup with custom level."""
        logger = setup_logging(level="DEBUG")
        assert logger.level == 10  # DEBUG level
    
    def test_setup_logging_custom_name(self):
        """Test logging setup with custom name."""
        logger = setup_logging(name="test_logger")
        assert logger.name == "test_logger"
    
    def test_get_logger(self):
        """Test getting a logger instance."""
        logger = get_logger("test_module")
        assert logger.name == "test_module"
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')


class TestFileUtils:
    """Test file utility functions."""
    
    def test_ensure_directory_exists_new(self, tmp_path):
        """Test creating new directory."""
        new_dir = tmp_path / "new_directory"
        ensure_directory_exists(new_dir)
        
        assert new_dir.exists()
        assert new_dir.is_dir()
    
    def test_ensure_directory_exists_existing(self, tmp_path):
        """Test with existing directory."""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()
        
        # Should not raise error
        ensure_directory_exists(existing_dir)
        assert existing_dir.exists()
    
    def test_ensure_directory_exists_nested(self, tmp_path):
        """Test creating nested directories."""
        nested_dir = tmp_path / "level1" / "level2" / "level3"
        ensure_directory_exists(nested_dir)
        
        assert nested_dir.exists()
        assert nested_dir.is_dir()
    
    def test_create_backup_file(self, tmp_path):
        """Test creating backup file."""
        original_file = tmp_path / "original.txt"
        original_file.write_text("test content")
        
        backup_path = create_backup_file(original_file)
        
        assert backup_path.exists()
        assert backup_path.read_text() == "test content"
        assert backup_path.suffix == ".backup"
    
    def test_create_backup_file_nonexistent(self, tmp_path):
        """Test creating backup of nonexistent file."""
        nonexistent = tmp_path / "nonexistent.txt"
        
        with pytest.raises(FileNotFoundError):
            create_backup_file(nonexistent)
    
    def test_save_yaml_file(self, tmp_path):
        """Test saving YAML file."""
        yaml_file = tmp_path / "test.yml"
        test_data = {"key": "value", "list": [1, 2, 3]}
        
        save_yaml_file(yaml_file, test_data)
        
        assert yaml_file.exists()
        loaded_data = yaml.safe_load(yaml_file.read_text())
        assert loaded_data == test_data
    
    def test_save_yaml_file_creates_directory(self, tmp_path):
        """Test saving YAML file creates parent directory."""
        yaml_file = tmp_path / "subdir" / "test.yml"
        test_data = {"key": "value"}
        
        save_yaml_file(yaml_file, test_data)
        
        assert yaml_file.exists()
        assert yaml_file.parent.exists()


class TestCSVUtils:
    """Test CSV utility functions."""
    
    def test_load_csv_data_valid(self, tmp_path):
        """Test loading valid CSV data."""
        csv_file = tmp_path / "test.csv"
        csv_content = "hostname,environment,status\nweb01,production,active\ndb01,development,active"
        csv_file.write_text(csv_content)
        
        data = load_csv_data(csv_file)
        
        assert len(data) == 2
        assert data[0]["hostname"] == "web01"
        assert data[0]["environment"] == "production"
        assert data[1]["hostname"] == "db01"
    
    def test_load_csv_data_empty_file(self, tmp_path):
        """Test loading empty CSV file."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")
        
        data = load_csv_data(csv_file)
        assert data == []
    
    def test_load_csv_data_header_only(self, tmp_path):
        """Test loading CSV with header only."""
        csv_file = tmp_path / "header_only.csv"
        csv_file.write_text("hostname,environment,status\n")
        
        data = load_csv_data(csv_file)
        assert data == []
    
    def test_load_csv_data_malformed_rows(self, tmp_path):
        """Test loading CSV with malformed rows."""
        csv_file = tmp_path / "malformed.csv"
        csv_content = "hostname,environment,status\nweb01,production,active\nmalformed_row\ndb01,development,active"
        csv_file.write_text(csv_content)
        
        data = load_csv_data(csv_file)
        
        # Should handle malformed rows gracefully
        assert len(data) >= 2
        assert any(row["hostname"] == "web01" for row in data)
        assert any(row["hostname"] == "db01" for row in data)
    
    def test_load_csv_data_nonexistent_file(self, tmp_path):
        """Test loading nonexistent CSV file."""
        nonexistent = tmp_path / "nonexistent.csv"
        
        with pytest.raises(FileNotFoundError):
            load_csv_data(nonexistent)
    
    def test_validate_csv_headers_valid(self):
        """Test validating valid CSV headers."""
        headers = ["hostname", "environment", "status", "application_service"]
        result = validate_csv_headers(headers)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_csv_headers_missing_required(self):
        """Test validating CSV headers with missing required fields."""
        headers = ["hostname", "status"]  # Missing environment
        result = validate_csv_headers(headers)
        
        assert not result.is_valid
        assert any("environment" in error for error in result.errors)
    
    def test_validate_csv_headers_invalid_names(self):
        """Test validating CSV headers with invalid names."""
        headers = ["hostname", "environment", "status", "invalid column name"]
        result = validate_csv_headers(headers)
        
        assert not result.is_valid
        assert any("invalid column name" in error for error in result.errors)
    
    def test_validate_csv_structure_valid(self, tmp_path):
        """Test validating valid CSV structure."""
        csv_file = tmp_path / "valid.csv"
        csv_content = "hostname,environment,status\nweb01,production,active\ndb01,development,active"
        csv_file.write_text(csv_content)
        
        result = validate_csv_structure(csv_file)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_csv_structure_duplicates(self, tmp_path):
        """Test validating CSV structure with duplicates."""
        csv_file = tmp_path / "duplicates.csv"
        csv_content = "hostname,environment,status\nweb01,production,active\nweb01,production,active"
        csv_file.write_text(csv_content)
        
        result = validate_csv_structure(csv_file)
        
        assert not result.is_valid
        assert any("duplicate" in error.lower() for error in result.errors)
    
    def test_get_csv_template(self):
        """Test getting CSV template."""
        template = get_csv_template()
        
        assert isinstance(template, str)
        assert "hostname" in template
        assert "environment" in template
        assert "status" in template


class TestHostUtils:
    """Test host utility functions."""
    
    def test_load_hosts_from_csv_valid(self, tmp_path):
        """Test loading hosts from valid CSV."""
        csv_file = tmp_path / "hosts.csv"
        csv_content = "hostname,environment,status,application_service\nweb01,production,active,web_server\ndb01,development,active,database_server"
        csv_file.write_text(csv_content)
        
        hosts = load_hosts_from_csv(csv_file)
        
        assert len(hosts) == 2
        assert all(isinstance(host, Host) for host in hosts)
        assert hosts[0].hostname == "web01"
        assert hosts[0].environment == "production"
        assert hosts[1].hostname == "db01"
    
    def test_load_hosts_from_csv_with_products(self, tmp_path):
        """Test loading hosts with product columns."""
        csv_file = tmp_path / "hosts_products.csv"
        csv_content = "hostname,environment,status,product_1,product_2\nweb01,production,active,web,monitoring\napi01,production,active,api,"
        csv_file.write_text(csv_content)
        
        hosts = load_hosts_from_csv(csv_file)
        
        assert len(hosts) == 2
        assert "product_1" in hosts[0].products
        assert hosts[0].products["product_1"] == "web"
        assert hosts[0].products["product_2"] == "monitoring"
        assert hosts[1].products["product_1"] == "api"
        assert "product_2" not in hosts[1].products or hosts[1].products["product_2"] == ""
    
    def test_get_hosts_by_environment(self, tmp_path):
        """Test filtering hosts by environment."""
        csv_file = tmp_path / "hosts.csv"
        csv_content = "hostname,environment,status\nweb01,production,active\ndb01,development,active\napi01,production,active"
        csv_file.write_text(csv_content)
        
        hosts = load_hosts_from_csv(csv_file)
        prod_hosts = get_hosts_by_environment(hosts, "production")
        
        assert len(prod_hosts) == 2
        assert all(host.environment == "production" for host in prod_hosts)
        assert set(host.hostname for host in prod_hosts) == {"web01", "api01"}
    
    def test_get_hosts_by_status(self, tmp_path):
        """Test filtering hosts by status."""
        csv_file = tmp_path / "hosts.csv"
        csv_content = "hostname,environment,status\nweb01,production,active\ndb01,production,decommissioned\napi01,production,active"
        csv_file.write_text(csv_content)
        
        hosts = load_hosts_from_csv(csv_file)
        active_hosts = get_hosts_by_status(hosts, "active")
        
        assert len(active_hosts) == 2
        assert all(host.status == "active" for host in active_hosts)
        assert set(host.hostname for host in active_hosts) == {"web01", "api01"}


class TestValidationDecorators:
    """Test validation decorator functions."""
    
    def test_validate_hostname_decorator_valid(self):
        """Test hostname validation decorator with valid hostname."""
        @validate_hostname_decorator
        def test_function(hostname):
            return f"Processing {hostname}"
        
        result = test_function("valid-hostname-01")
        assert result == "Processing valid-hostname-01"
    
    def test_validate_hostname_decorator_invalid(self):
        """Test hostname validation decorator with invalid hostname."""
        @validate_hostname_decorator
        def test_function(hostname):
            return f"Processing {hostname}"
        
        with pytest.raises(ValueError, match="Invalid hostname"):
            test_function("invalid_hostname_with_underscores")
    
    def test_validate_hostname_decorator_empty(self):
        """Test hostname validation decorator with empty hostname."""
        @validate_hostname_decorator
        def test_function(hostname):
            return f"Processing {hostname}"
        
        with pytest.raises(ValueError, match="Hostname cannot be empty"):
            test_function("")
    
    def test_validate_environment_decorator_valid(self):
        """Test environment validation decorator with valid environment."""
        @validate_environment_decorator
        def test_function(environment):
            return f"Processing {environment}"
        
        result = test_function("production")
        assert result == "Processing production"
    
    def test_validate_environment_decorator_invalid(self):
        """Test environment validation decorator with invalid environment."""
        @validate_environment_decorator
        def test_function(environment):
            return f"Processing {environment}"
        
        with pytest.raises(ValueError, match="Invalid environment"):
            test_function("invalid_env")
    
    def test_validate_environment_decorator_empty(self):
        """Test environment validation decorator with empty environment."""
        @validate_environment_decorator
        def test_function(environment):
            return f"Processing {environment}"
        
        with pytest.raises(ValueError, match="Environment cannot be empty"):
            test_function("")


class TestAnsibleIntegration:
    """Test Ansible integration utilities."""
    
    @patch('subprocess.run')
    def test_test_ansible_inventory_success(self, mock_run):
        """Test successful Ansible inventory test."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"all": {"hosts": ["host1", "host2"]}}'
        
        result = test_ansible_inventory("/path/to/inventory.yml")
        
        assert result["valid"] is True
        assert result["returncode"] == 0
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_test_ansible_inventory_failure(self, mock_run):
        """Test failed Ansible inventory test."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Error parsing inventory"
        
        result = test_ansible_inventory("/path/to/inventory.yml")
        
        assert result["valid"] is False
        assert result["returncode"] == 1
        assert "Error parsing inventory" in result["stderr"]
    
    @patch('subprocess.run')
    def test_test_ansible_inventory_missing_executable(self, mock_run):
        """Test Ansible inventory test with missing executable."""
        mock_run.side_effect = FileNotFoundError("ansible-inventory not found")
        
        result = test_ansible_inventory("/path/to/inventory.yml")
        
        assert result["valid"] is False
        assert "ansible-inventory not found" in result["error"]


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_load_csv_data_unicode_content(self, tmp_path):
        """Test loading CSV with Unicode content."""
        csv_file = tmp_path / "unicode.csv"
        csv_content = "hostname,environment,status,description\nweb01,production,active,测试服务器\napi01,production,active,API服务器"
        csv_file.write_text(csv_content, encoding='utf-8')
        
        data = load_csv_data(csv_file)
        
        assert len(data) == 2
        assert data[0]["description"] == "测试服务器"
        assert data[1]["description"] == "API服务器"
    
    def test_load_csv_data_large_file(self, tmp_path):
        """Test loading large CSV file."""
        csv_file = tmp_path / "large.csv"
        
        # Create a large CSV file
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["hostname", "environment", "status"])
            
            for i in range(1000):
                writer.writerow([f"host{i:04d}", "production", "active"])
        
        data = load_csv_data(csv_file)
        
        assert len(data) == 1000
        assert data[0]["hostname"] == "host0000"
        assert data[999]["hostname"] == "host0999"
    
    def test_save_yaml_file_complex_data(self, tmp_path):
        """Test saving complex YAML data."""
        yaml_file = tmp_path / "complex.yml"
        complex_data = {
            "environments": {
                "production": {
                    "hosts": ["web01", "web02"],
                    "vars": {"environment": "prod"}
                },
                "development": {
                    "hosts": ["dev01"],
                    "vars": {"environment": "dev"}
                }
            },
            "metadata": {
                "created_at": "2024-01-01T00:00:00Z",
                "version": "1.0.0"
            }
        }
        
        save_yaml_file(yaml_file, complex_data)
        
        assert yaml_file.exists()
        loaded_data = yaml.safe_load(yaml_file.read_text())
        assert loaded_data == complex_data
    
    def test_ensure_directory_exists_permission_error(self, tmp_path):
        """Test directory creation with permission error."""
        # Create a directory and make it read-only
        parent_dir = tmp_path / "readonly"
        parent_dir.mkdir()
        parent_dir.chmod(0o444)  # Read-only
        
        restricted_dir = parent_dir / "restricted"
        
        try:
            # This should handle the permission error gracefully
            with pytest.raises(PermissionError):
                ensure_directory_exists(restricted_dir)
        finally:
            # Clean up - restore permissions
            parent_dir.chmod(0o755)


class TestPerformanceAndMemory:
    """Test performance and memory usage of utility functions."""
    
    def test_load_csv_data_memory_efficiency(self, tmp_path):
        """Test memory efficiency of CSV loading."""
        csv_file = tmp_path / "memory_test.csv"
        
        # Create CSV with many columns
        headers = ["hostname", "environment", "status"] + [f"extra_col_{i}" for i in range(100)]
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            for i in range(100):
                row = [f"host{i}", "production", "active"] + [f"value_{i}_{j}" for j in range(100)]
                writer.writerow(row)
        
        # Should load without memory issues
        data = load_csv_data(csv_file)
        
        assert len(data) == 100
        assert len(data[0]) == 103  # 3 main columns + 100 extra columns
    
    def test_concurrent_file_operations(self, tmp_path):
        """Test concurrent file operations."""
        import threading
        import time
        
        results = []
        
        def create_and_load_csv(thread_id):
            csv_file = tmp_path / f"thread_{thread_id}.csv"
            csv_content = f"hostname,environment,status\nhost{thread_id},production,active"
            csv_file.write_text(csv_content)
            
            data = load_csv_data(csv_file)
            results.append((thread_id, len(data)))
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_and_load_csv, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all operations completed successfully
        assert len(results) == 5
        assert all(count == 1 for _, count in results) 