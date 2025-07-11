#!/usr/bin/env python3
"""Integration Tests for Ansible Inventory Management System.

Tests for component interactions, end-to-end workflows, and system integration
scenarios to ensure all parts work together correctly.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from scripts.core.utils import load_csv_data, load_hosts_from_csv
from scripts.managers.inventory_manager import InventoryManager
from scripts.managers.validation_manager import ValidationManager
from scripts.managers.host_manager import HostManager
from scripts.managers.group_vars_manager import GroupVarsManager


class TestCSVToInventoryIntegration:
    """Test complete CSV to inventory generation workflow."""
    
    def test_complete_inventory_generation_workflow(self, tmp_path):
        """Test complete workflow from CSV to inventory files."""
        # Create test CSV with comprehensive data
        csv_file = tmp_path / "hosts.csv"
        csv_content = """hostname,environment,status,cname,instance,site_code,ssl_port,application_service,product_1,product_2,product_3,product_4,primary_application,function,batch_number,patch_mode,dashboard_group,decommission_date
prd-web-use1-1,production,active,web01.example.com,1,use1,443,web_server,web,monitoring,analytics,,nginx,load_balancer,1,auto,web_servers,
prd-api-use1-1,production,active,api01.example.com,1,use1,8443,api_server,api,logging,,,flask,api_gateway,2,manual,api_servers,
prd-db-use1-1,production,active,db01.example.com,1,use1,5432,database_server,db,backup,,,postgresql,database_server,3,auto,db_servers,
dev-web-use1-1,development,active,dev-web01.example.com,1,use1,443,web_server,web,,,nginx,load_balancer,1,auto,web_servers,
test-api-use1-1,test,active,test-api01.example.com,1,use1,8443,api_server,api,,,flask,api_gateway,1,manual,api_servers,"""
        csv_file.write_text(csv_content)
        
        # Initialize inventory manager
        inventory_manager = InventoryManager(csv_file=csv_file)
        
        # Generate inventories for all environments
        result = inventory_manager.generate_inventories()
        
        # Verify generation succeeded
        assert result["status"] == "success"
        assert result["dry_run"] is False
        assert len(result["generated_files"]) > 0
        
        # Verify inventory files were created
        generated_files = [Path(f) for f in result["generated_files"]]
        assert any("production.yml" in f.name for f in generated_files)
        assert any("development.yml" in f.name for f in generated_files)
        assert any("test.yml" in f.name for f in generated_files)
        
        # Verify inventory structure
        production_file = next(f for f in generated_files if "production.yml" in f.name)
        production_data = yaml.safe_load(production_file.read_text())
        
        # Check environment group exists
        assert "env_production" in production_data
        
        # Check application groups exist
        assert "app_web_server" in production_data["env_production"]["children"]
        assert "app_api_server" in production_data["env_production"]["children"]
        assert "app_database_server" in production_data["env_production"]["children"]
        
        # Check product groups exist
        assert "product_web" in production_data["env_production"]["children"]["app_web_server"]["children"]
        assert "product_api" in production_data["env_production"]["children"]["app_api_server"]["children"]
        
        # Check hosts are in correct groups
        web_hosts = production_data["env_production"]["children"]["app_web_server"]["hosts"]
        assert "prd-web-use1-1" in web_hosts
        
        # Verify host_vars files were created
        stats = result["stats"]
        assert stats["total_hosts"] == 3  # 3 production hosts
        assert stats["host_vars_created"] == 3
    
    def test_multi_environment_inventory_generation(self, tmp_path):
        """Test generating inventories for multiple environments."""
        csv_file = tmp_path / "multi_env.csv"
        csv_content = """hostname,environment,status,application_service,product_1
prd-web-01,production,active,web_server,web
prd-api-01,production,active,api_server,api
dev-web-01,development,active,web_server,web
dev-api-01,development,active,api_server,api
tst-web-01,test,active,web_server,web
acc-web-01,acceptance,active,web_server,web"""
        csv_file.write_text(csv_content)
        
        inventory_manager = InventoryManager(csv_file=csv_file)
        
        # Generate specific environments
        result = inventory_manager.generate_inventories(environments=["production", "development"])
        
        assert result["status"] == "success"
        generated_files = [Path(f) for f in result["generated_files"]]
        
        # Should only generate production and development
        assert any("production.yml" in f.name for f in generated_files)
        assert any("development.yml" in f.name for f in generated_files)
        assert not any("test.yml" in f.name for f in generated_files)
        assert not any("acceptance.yml" in f.name for f in generated_files)
    
    def test_inventory_validation_integration(self, tmp_path):
        """Test integration between inventory generation and validation."""
        csv_file = tmp_path / "validation_test.csv"
        csv_content = """hostname,environment,status,application_service
valid-host-01,production,active,web_server
duplicate-host,production,active,api_server
duplicate-host,production,active,database_server"""
        csv_file.write_text(csv_content)
        
        # First validate the CSV
        validator = ValidationManager(csv_file=csv_file)
        validation_result = validator.validate_csv_data()
        
        # Should detect duplicate hostnames
        assert not validation_result.is_valid
        assert any("duplicate" in error.lower() for error in validation_result.errors)
        
        # Try to generate inventory anyway
        inventory_manager = InventoryManager(csv_file=csv_file)
        generation_result = inventory_manager.generate_inventories()
        
        # Generation should handle duplicates gracefully
        assert generation_result["status"] in ["success", "warning"]


class TestHostManagerIntegration:
    """Test host manager integration with other components."""
    
    def test_host_manager_with_inventory_manager(self, tmp_path):
        """Test host manager integration with inventory manager."""
        csv_file = tmp_path / "host_manager_test.csv"
        csv_content = """hostname,environment,status,application_service,product_1,product_2,batch_number
web-01,production,active,web_server,web,monitoring,1
api-01,production,active,api_server,api,logging,2
db-01,production,active,database_server,db,backup,3"""
        csv_file.write_text(csv_content)
        
        # Initialize managers
        host_manager = HostManager(csv_file=csv_file)
        inventory_manager = InventoryManager(csv_file=csv_file)
        
        # Load hosts through host manager
        hosts = host_manager.load_hosts()
        assert len(hosts) == 3
        
        # Generate inventory using the same CSV
        result = inventory_manager.generate_inventories(environments=["production"])
        
        # Verify host data consistency
        assert result["status"] == "success"
        assert result["stats"]["total_hosts"] == 3
        
        # Check that batch groups are created
        production_file = Path(result["generated_files"][0])
        production_data = yaml.safe_load(production_file.read_text())
        
        # Should have batch groups
        env_children = production_data["env_production"]["children"]
        assert "batch_1" in env_children
        assert "batch_2" in env_children
        assert "batch_3" in env_children
    
    def test_host_lifecycle_integration(self, tmp_path):
        """Test host lifecycle management integration."""
        csv_file = tmp_path / "lifecycle_test.csv"
        csv_content = """hostname,environment,status,application_service,decommission_date
active-host,production,active,web_server,
decom-host,production,decommissioned,web_server,2024-01-01"""
        csv_file.write_text(csv_content)
        
        host_manager = HostManager(csv_file=csv_file)
        inventory_manager = InventoryManager(csv_file=csv_file)
        
        # Load hosts and check lifecycle status
        hosts = host_manager.load_hosts()
        active_hosts = [h for h in hosts if h.status == "active"]
        decom_hosts = [h for h in hosts if h.status == "decommissioned"]
        
        assert len(active_hosts) == 1
        assert len(decom_hosts) == 1
        
        # Generate inventory - should only include active hosts
        result = inventory_manager.generate_inventories(environments=["production"])
        
        # Check that only active hosts are in inventory
        assert result["stats"]["total_hosts"] == 1
        
        production_file = Path(result["generated_files"][0])
        production_data = yaml.safe_load(production_file.read_text())
        
        # Should only have active host
        web_server_hosts = production_data["env_production"]["children"]["app_web_server"]["hosts"]
        assert "active-host" in web_server_hosts
        assert "decom-host" not in web_server_hosts


class TestGroupVarsIntegration:
    """Test group variables integration."""
    
    def test_group_vars_creation_and_cleanup(self, tmp_path):
        """Test group variables creation and cleanup integration."""
        csv_file = tmp_path / "group_vars_test.csv"
        csv_content = """hostname,environment,status,application_service,product_1,site_code,batch_number
web-01,production,active,web_server,web,use1,1
api-01,production,active,api_server,api,use1,2"""
        csv_file.write_text(csv_content)
        
        # Set up temporary group_vars directory
        group_vars_dir = tmp_path / "group_vars"
        group_vars_dir.mkdir()
        
        # Create some existing group vars files
        (group_vars_dir / "old_group.yml").write_text("old_var: value")
        (group_vars_dir / "app_web_server.yml").write_text("existing_var: value")
        
        # Initialize managers
        inventory_manager = InventoryManager(csv_file=csv_file)
        group_vars_manager = GroupVarsManager(group_vars_dir=group_vars_dir)
        
        # Generate inventory
        result = inventory_manager.generate_inventories(environments=["production"])
        assert result["status"] == "success"
        
        # Get groups from generated inventory
        production_file = Path(result["generated_files"][0])
        production_data = yaml.safe_load(production_file.read_text())
        
        # Extract all groups
        all_groups = set()
        def extract_groups(data):
            if isinstance(data, dict):
                for key, value in data.items():
                    if key not in ["hosts", "vars"]:
                        all_groups.add(key)
                        if isinstance(value, dict) and "children" in value:
                            extract_groups(value["children"])
        
        extract_groups(production_data)
        
        # Test group vars cleanup
        orphaned_files = group_vars_manager.cleanup_orphaned_group_vars(all_groups)
        
        # Should identify old_group.yml as orphaned
        assert any("old_group.yml" in str(f) for f in orphaned_files)
        
        # app_web_server.yml should not be orphaned (it's a valid group)
        assert not any("app_web_server.yml" in str(f) for f in orphaned_files)


class TestConfigurationIntegration:
    """Test configuration integration across components."""
    
    def test_configuration_loading_integration(self, tmp_path):
        """Test configuration loading affects all components."""
        # Create custom configuration
        config_file = tmp_path / "custom-config.yml"
        config_content = """
version: "4.0.0"
environments:
  supported: ["production", "staging"]
  codes:
    production: "prd"
    staging: "stg"
hosts:
  inventory_key: "cname"
  valid_status_values: ["active", "inactive"]
"""
        config_file.write_text(config_content)
        
        # Create CSV with custom environment
        csv_file = tmp_path / "config_test.csv"
        csv_content = """hostname,environment,status,cname,application_service
host-01,staging,active,host01.example.com,web_server
host-02,production,active,host02.example.com,api_server"""
        csv_file.write_text(csv_content)
        
        # Test with custom configuration
        with patch('scripts.core.config.CONFIG_FILE', config_file):
            inventory_manager = InventoryManager(csv_file=csv_file)
            result = inventory_manager.generate_inventories()
            
            # Should handle custom environment
            assert result["status"] == "success"
            
            # Check that staging environment is supported
            generated_files = [Path(f) for f in result["generated_files"]]
            assert any("staging.yml" in f.name for f in generated_files)


class TestErrorHandlingIntegration:
    """Test error handling across integrated components."""
    
    def test_csv_error_propagation(self, tmp_path):
        """Test how CSV errors propagate through the system."""
        # Create invalid CSV
        csv_file = tmp_path / "invalid.csv"
        csv_content = """hostname,environment,status
host-01,invalid_env,active
host-02,production,invalid_status"""
        csv_file.write_text(csv_content)
        
        # Test validation
        validator = ValidationManager(csv_file=csv_file)
        validation_result = validator.validate_csv_data()
        
        assert not validation_result.is_valid
        assert len(validation_result.errors) > 0
        
        # Test inventory generation with invalid data
        inventory_manager = InventoryManager(csv_file=csv_file)
        generation_result = inventory_manager.generate_inventories()
        
        # Should handle errors gracefully
        assert generation_result["status"] in ["error", "warning"]
        if generation_result["status"] == "error":
            assert "error" in generation_result
    
    def test_file_permission_error_handling(self, tmp_path):
        """Test file permission error handling."""
        csv_file = tmp_path / "permission_test.csv"
        csv_content = """hostname,environment,status,application_service
host-01,production,active,web_server"""
        csv_file.write_text(csv_content)
        
        # Make CSV file read-only
        csv_file.chmod(0o444)
        
        try:
            inventory_manager = InventoryManager(csv_file=csv_file)
            result = inventory_manager.generate_inventories()
            
            # Should handle read-only file gracefully
            assert result["status"] in ["success", "warning"]
        finally:
            # Restore permissions for cleanup
            csv_file.chmod(0o644)


class TestPerformanceIntegration:
    """Test performance aspects of integrated components."""
    
    def test_large_inventory_generation(self, tmp_path):
        """Test performance with large inventory."""
        csv_file = tmp_path / "large_inventory.csv"
        
        # Generate large CSV
        header = "hostname,environment,status,application_service,product_1,product_2,site_code,batch_number"
        rows = [header]
        
        for i in range(500):  # 500 hosts
            env = "production" if i % 2 == 0 else "development"
            app = "web_server" if i % 3 == 0 else "api_server" if i % 3 == 1 else "database_server"
            product1 = "web" if i % 3 == 0 else "api" if i % 3 == 1 else "db"
            product2 = "monitoring" if i % 2 == 0 else "logging"
            site = "use1" if i % 2 == 0 else "usw2"
            batch = str((i % 5) + 1)
            
            row = f"host-{i:03d},{env},active,{app},{product1},{product2},{site},{batch}"
            rows.append(row)
        
        csv_file.write_text("\n".join(rows))
        
        # Test generation performance
        import time
        start_time = time.time()
        
        inventory_manager = InventoryManager(csv_file=csv_file)
        result = inventory_manager.generate_inventories()
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert generation_time < 30  # 30 seconds max
        assert result["status"] == "success"
        assert result["stats"]["total_hosts"] == 500
        
        # Verify inventory structure is correct
        generated_files = [Path(f) for f in result["generated_files"]]
        production_file = next(f for f in generated_files if "production.yml" in f.name)
        production_data = yaml.safe_load(production_file.read_text())
        
        # Should have proper structure even with large data
        assert "env_production" in production_data
        assert "app_web_server" in production_data["env_production"]["children"]
    
    def test_concurrent_operations(self, tmp_path):
        """Test concurrent operations safety."""
        import threading
        import time
        
        csv_file = tmp_path / "concurrent_test.csv"
        csv_content = """hostname,environment,status,application_service
host-01,production,active,web_server
host-02,production,active,api_server"""
        csv_file.write_text(csv_content)
        
        results = []
        
        def generate_inventory(thread_id):
            try:
                inventory_manager = InventoryManager(csv_file=csv_file)
                result = inventory_manager.generate_inventories()
                results.append((thread_id, result["status"]))
            except Exception as e:
                results.append((thread_id, f"error: {e}"))
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=generate_inventory, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # At least one should succeed
        assert len(results) == 3
        success_count = sum(1 for _, status in results if status == "success")
        assert success_count >= 1


class TestAnsibleIntegration:
    """Test Ansible integration and compatibility."""
    
    @pytest.mark.skipif(shutil.which("ansible-inventory") is None, reason="ansible-inventory not available")
    def test_ansible_inventory_compatibility(self, tmp_path):
        """Test generated inventory works with ansible-inventory command."""
        csv_file = tmp_path / "ansible_test.csv"
        csv_content = """hostname,environment,status,application_service,product_1,site_code
web-01,production,active,web_server,web,use1
api-01,production,active,api_server,api,use1
db-01,production,active,database_server,db,use1"""
        csv_file.write_text(csv_content)
        
        inventory_manager = InventoryManager(csv_file=csv_file)
        result = inventory_manager.generate_inventories(environments=["production"])
        
        assert result["status"] == "success"
        
        # Test with ansible-inventory
        production_file = Path(result["generated_files"][0])
        
        # Test listing hosts
        list_result = subprocess.run(
            ["ansible-inventory", "-i", str(production_file), "--list"],
            capture_output=True,
            text=True
        )
        
        assert list_result.returncode == 0
        
        # Parse JSON output
        import json
        inventory_data = json.loads(list_result.stdout)
        
        # Verify structure
        assert "env_production" in inventory_data
        assert "app_web_server" in inventory_data
        assert "product_web" in inventory_data
        
        # Test getting host info
        host_result = subprocess.run(
            ["ansible-inventory", "-i", str(production_file), "--host", "web-01"],
            capture_output=True,
            text=True
        )
        
        assert host_result.returncode == 0
        host_data = json.loads(host_result.stdout)
        
        # Should have host variables
        assert isinstance(host_data, dict)
    
    def test_inventory_graph_structure(self, tmp_path):
        """Test inventory graph structure is valid."""
        csv_file = tmp_path / "graph_test.csv"
        csv_content = """hostname,environment,status,application_service,product_1,product_2,site_code,batch_number
web-01,production,active,web_server,web,monitoring,use1,1
api-01,production,active,api_server,api,logging,use1,2"""
        csv_file.write_text(csv_content)
        
        inventory_manager = InventoryManager(csv_file=csv_file)
        result = inventory_manager.generate_inventories(environments=["production"])
        
        assert result["status"] == "success"
        
        # Load and verify graph structure
        production_file = Path(result["generated_files"][0])
        production_data = yaml.safe_load(production_file.read_text())
        
        # Verify hierarchical structure
        env_prod = production_data["env_production"]
        assert "children" in env_prod
        
        # Check app groups
        app_web = env_prod["children"]["app_web_server"]
        assert "children" in app_web
        assert "hosts" in app_web
        
        # Check product groups under app groups
        product_web = app_web["children"]["product_web"]
        assert "hosts" in product_web
        
        # Verify no circular references
        def check_circular_refs(data, visited=None):
            if visited is None:
                visited = set()
            
            if isinstance(data, dict):
                for key, value in data.items():
                    if key in visited:
                        return False  # Circular reference detected
                    visited.add(key)
                    if not check_circular_refs(value, visited.copy()):
                        return False
            elif isinstance(data, list):
                for item in data:
                    if not check_circular_refs(item, visited.copy()):
                        return False
            
            return True
        
        assert check_circular_refs(production_data) 