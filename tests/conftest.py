#!/usr/bin/env python3
"""Pytest configuration and shared fixtures for all tests."""

import csv
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def sample_csv_data():
    """Provide sample CSV data for testing."""
    return """hostname,environment,status,application_service,product_1,product_2,site_code,batch_number
web-01,production,active,web_server,web,monitoring,use1,1
web-02,production,active,web_server,web,monitoring,use1,1
api-01,production,active,api_server,api,logging,use1,2
api-02,production,active,api_server,api,logging,use1,2
db-01,production,active,database_server,db,monitoring,use1,3
db-02,production,active,database_server,db,monitoring,use1,3
web-dev-01,development,active,web_server,web,monitoring,use1,1
api-dev-01,development,active,api_server,api,logging,use1,2
db-dev-01,development,active,database_server,db,monitoring,use1,3
test-web-01,test,active,web_server,web,monitoring,use1,1
test-api-01,test,active,api_server,api,logging,use1,2
acc-web-01,acceptance,active,web_server,web,monitoring,use1,1"""


@pytest.fixture
def minimal_csv_data():
    """Provide minimal CSV data for testing."""
    return """hostname,environment,status
test-host,production,active
test-host-2,development,active"""


@pytest.fixture
def invalid_csv_data():
    """Provide invalid CSV data for testing."""
    return """hostname,environment,status
test-host,production,active
test-host,production,active
invalid-host,invalid_env,active"""


@pytest.fixture
def temp_csv_file(tmp_path, sample_csv_data):
    """Create temporary CSV file with sample data."""
    csv_file = tmp_path / "test_hosts.csv"
    csv_file.write_text(sample_csv_data)
    return csv_file


@pytest.fixture
def minimal_csv_file(tmp_path, minimal_csv_data):
    """Create temporary CSV file with minimal data."""
    csv_file = tmp_path / "minimal_hosts.csv"
    csv_file.write_text(minimal_csv_data)
    return csv_file


@pytest.fixture
def invalid_csv_file(tmp_path, invalid_csv_data):
    """Create temporary CSV file with invalid data."""
    csv_file = tmp_path / "invalid_hosts.csv"
    csv_file.write_text(invalid_csv_data)
    return csv_file


@pytest.fixture
def large_csv_file(tmp_path):
    """Create temporary CSV file with large dataset."""
    csv_file = tmp_path / "large_hosts.csv"
    
    header = "hostname,environment,status,application_service,product_1,product_2,site_code,batch_number"
    rows = [header]
    
    environments = ["production", "development", "test", "acceptance"]
    applications = ["web_server", "api_server", "database_server", "cache_server"]
    products = ["web", "api", "db", "cache", "monitoring", "logging"]
    sites = ["use1", "usw2", "euw1", "apse1"]
    
    for i in range(1000):
        env = environments[i % len(environments)]
        app = applications[i % len(applications)]
        product1 = products[i % len(products)]
        product2 = products[(i + 1) % len(products)]
        site = sites[i % len(sites)]
        batch = str((i % 10) + 1)
        
        row = f"host-{i:04d},{env},active,{app},{product1},{product2},{site},{batch}"
        rows.append(row)
    
    csv_file.write_text("\n".join(rows))
    return csv_file


@pytest.fixture
def temp_inventory_dir(tmp_path):
    """Create temporary inventory directory structure."""
    inventory_dir = tmp_path / "inventory"
    inventory_dir.mkdir()
    
    # Create subdirectories
    (inventory_dir / "host_vars").mkdir()
    (inventory_dir / "group_vars").mkdir()
    
    return inventory_dir


@pytest.fixture
def mock_logger():
    """Provide mocked logger for testing."""
    logger = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    return logger


@pytest.fixture
def mock_inventory_manager():
    """Provide mocked inventory manager."""
    with patch('scripts.managers.inventory_manager.InventoryManager') as mock:
        mock_instance = Mock()
        mock_instance.generate_inventories.return_value = {
            "status": "success",
            "stats": {"total_hosts": 10},
            "generated_files": ["/tmp/test.yml"]
        }
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_validation_manager():
    """Provide mocked validation manager."""
    with patch('scripts.managers.validation_manager.ValidationManager') as mock:
        mock_instance = Mock()
        mock_instance.validate_csv_data.return_value = Mock(
            is_valid=True,
            errors=[],
            warnings=[]
        )
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_host_manager():
    """Provide mocked host manager."""
    with patch('scripts.managers.host_manager.HostManager') as mock:
        mock_instance = Mock()
        mock_instance.add_host.return_value = {"status": "success"}
        mock_instance.update_host.return_value = {"status": "success"}
        mock_instance.decommission_host.return_value = {"status": "success"}
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_hosts_data():
    """Provide sample host data for testing."""
    return [
        {
            "hostname": "web-01",
            "environment": "production",
            "status": "active",
            "application_service": "web_server",
            "product_1": "web",
            "product_2": "monitoring",
            "site_code": "use1",
            "batch_number": "1"
        },
        {
            "hostname": "api-01",
            "environment": "production",
            "status": "active",
            "application_service": "api_server",
            "product_1": "api",
            "product_2": "logging",
            "site_code": "use1",
            "batch_number": "2"
        },
        {
            "hostname": "db-01",
            "environment": "production",
            "status": "active",
            "application_service": "database_server",
            "product_1": "db",
            "product_2": "monitoring",
            "site_code": "use1",
            "batch_number": "3"
        }
    ]


@pytest.fixture
def sample_inventory_data():
    """Provide sample inventory data for testing."""
    return {
        "all": {
            "children": {
                "production": {
                    "children": {
                        "web_servers": {
                            "hosts": {
                                "web-01": {},
                                "web-02": {}
                            }
                        },
                        "api_servers": {
                            "hosts": {
                                "api-01": {},
                                "api-02": {}
                            }
                        }
                    }
                }
            }
        }
    }


@pytest.fixture
def performance_test_data():
    """Provide performance test data."""
    return {
        "small_dataset": 100,
        "medium_dataset": 1000,
        "large_dataset": 5000,
        "csv_loading_threshold": 30.0,
        "inventory_generation_threshold": 60.0,
        "memory_usage_threshold": 200.0
    }


@pytest.fixture
def security_test_data():
    """Provide security test data."""
    return {
        "malicious_csv": """hostname,environment,status,description
injection-host,production,active,"'; DROP TABLE hosts; --"
script-host,production,active,"<script>alert('xss')</script>"
path-host,production,active,"../../../etc/passwd"
command-host,production,active,"$(rm -rf /)"
null-host,production,active,"\x00\x01\x02"
unicode-host,production,active,"🚨💀🔥"
""",
        "malicious_headers": """=cmd|'/c calc'!A0,environment,status,application_service
@SUM(1+1)*cmd|'/c calc'!A0,production,active,web_server
+cmd|'/c calc'!A0,production,active,api_server
-cmd|'/c calc'!A0,production,active,database_server""",
        "path_traversal_csv": """hostname,environment,status,config_file
normal-host,production,active,/etc/nginx/nginx.conf
traversal-host,production,active,../../../etc/passwd
windows-traversal,production,active,..\\..\\..\\windows\\system32\\config\\sam
null-byte,production,active,/etc/passwd\x00.txt
relative-path,production,active,./config/../../../etc/shadow
"""
    }


@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path, monkeypatch):
    """Set up test environment for all tests."""
    # Set temporary directory as working directory
    monkeypatch.chdir(tmp_path)
    
    # Create test directories
    (tmp_path / "inventory").mkdir()
    (tmp_path / "inventory" / "host_vars").mkdir()
    (tmp_path / "inventory" / "group_vars").mkdir()
    (tmp_path / "inventory_source").mkdir()
    
    # Set environment variables for testing
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("LOG_LEVEL", "INFO")


@pytest.fixture
def mock_ansible_command():
    """Mock ansible command execution."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "ansible-inventory test successful"
        mock_run.return_value.stderr = ""
        yield mock_run


@pytest.fixture
def mock_file_operations():
    """Mock file operations for testing."""
    with patch('builtins.open') as mock_open, \
         patch('pathlib.Path.exists') as mock_exists, \
         patch('pathlib.Path.mkdir') as mock_mkdir, \
         patch('pathlib.Path.write_text') as mock_write:
        
        mock_exists.return_value = True
        mock_mkdir.return_value = None
        mock_write.return_value = None
        
        yield {
            'open': mock_open,
            'exists': mock_exists,
            'mkdir': mock_mkdir,
            'write_text': mock_write
        }


# Test markers for categorizing tests
pytest_plugins = []

# Configure pytest markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


# Test collection configuration
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add markers based on test file names
        if "test_cli_interface" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "test_core_utils" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "test_performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        elif "test_security" in item.nodeid:
            item.add_marker(pytest.mark.security)
        
        # Add markers based on test names
        if "performance" in item.name.lower():
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        elif "security" in item.name.lower():
            item.add_marker(pytest.mark.security)
        elif "integration" in item.name.lower():
            item.add_marker(pytest.mark.integration)
        elif "e2e" in item.name.lower() or "end_to_end" in item.name.lower():
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.slow) 