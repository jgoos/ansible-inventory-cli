#!/usr/bin/env python3
"""Performance Tests for Ansible Inventory Management System.

Benchmarks and load tests to ensure the system performs well under
various conditions and scales appropriately.
"""

import csv
import gc
import memory_profiler
import time
import threading
from pathlib import Path
from typing import List

import pytest

from scripts.core.utils import load_csv_data, load_hosts_from_csv
from scripts.managers.inventory_manager import InventoryManager
from scripts.managers.validation_manager import ValidationManager
from scripts.managers.host_manager import HostManager


class TestPerformanceBenchmarks:
    """Performance benchmarks for core operations."""
    
    def test_csv_loading_performance(self, tmp_path):
        """Benchmark CSV loading performance with various file sizes."""
        test_cases = [
            (100, "small"),
            (1000, "medium"),
            (5000, "large"),
        ]
        
        results = {}
        
        for size, label in test_cases:
            csv_file = tmp_path / f"perf_test_{label}.csv"
            
            # Generate CSV data
            header = "hostname,environment,status,application_service,product_1,product_2,site_code,batch_number"
            rows = [header]
            
            for i in range(size):
                env = "production" if i % 2 == 0 else "development"
                app = "web_server" if i % 3 == 0 else "api_server" if i % 3 == 1 else "database_server"
                product1 = "web" if i % 3 == 0 else "api" if i % 3 == 1 else "db"
                product2 = "monitoring" if i % 2 == 0 else "logging"
                site = "use1" if i % 2 == 0 else "usw2"
                batch = str((i % 5) + 1)
                
                row = f"host-{i:04d},{env},active,{app},{product1},{product2},{site},{batch}"
                rows.append(row)
            
            csv_file.write_text("\n".join(rows))
            
            # Benchmark loading
            start_time = time.time()
            data = load_csv_data(csv_file)
            end_time = time.time()
            
            load_time = end_time - start_time
            results[label] = {
                "size": size,
                "load_time": load_time,
                "rows_per_second": size / load_time if load_time > 0 else float('inf')
            }
            
            # Verify data integrity
            assert len(data) == size
            assert data[0]["hostname"] == "host-0000"
            assert data[-1]["hostname"] == f"host-{size-1:04d}"
        
        # Performance assertions
        assert results["small"]["load_time"] < 1.0  # < 1 second for 100 rows
        assert results["medium"]["load_time"] < 5.0  # < 5 seconds for 1000 rows
        assert results["large"]["load_time"] < 30.0  # < 30 seconds for 5000 rows
        
        # Scalability check - should be roughly linear
        small_rate = results["small"]["rows_per_second"]
        medium_rate = results["medium"]["rows_per_second"]
        
        # Allow for some variance but should be in same order of magnitude
        assert medium_rate > small_rate * 0.1  # At least 10% of small rate
    
    def test_host_model_creation_performance(self, tmp_path):
        """Benchmark host model creation performance."""
        csv_file = tmp_path / "host_model_perf.csv"
        
        # Generate CSV with many columns
        header = "hostname,environment,status,cname,instance,site_code,ssl_port,application_service"
        header += ",product_1,product_2,product_3,product_4,primary_application,function"
        header += ",batch_number,patch_mode,dashboard_group,decommission_date"
        
        # Add many extra columns
        for i in range(20):
            header += f",extra_col_{i}"
        
        rows = [header]
        
        for i in range(1000):
            row = f"host-{i:04d},production,active,host{i}.example.com,{i},use1,443,web_server"
            row += ",web,monitoring,analytics,,nginx,load_balancer"
            row += f",{(i % 5) + 1},auto,web_servers,"
            
            # Add extra column data
            for j in range(20):
                row += f",extra_value_{i}_{j}"
            
            rows.append(row)
        
        csv_file.write_text("\n".join(rows))
        
        # Benchmark host loading
        start_time = time.time()
        hosts = load_hosts_from_csv(csv_file)
        end_time = time.time()
        
        load_time = end_time - start_time
        
        # Verify results
        assert len(hosts) == 1000
        assert all(hasattr(host, 'hostname') for host in hosts)
        assert all(hasattr(host, 'products') for host in hosts)
        assert all(hasattr(host, 'metadata') for host in hosts)
        
        # Performance assertion
        assert load_time < 10.0  # Should complete within 10 seconds
        
        # Check memory usage of host objects
        host_size = sum(len(str(host.__dict__)) for host in hosts[:10]) / 10
        assert host_size < 1000  # Average host object should be reasonable size
    
    def test_inventory_generation_performance(self, tmp_path):
        """Benchmark inventory generation performance."""
        csv_file = tmp_path / "inventory_perf.csv"
        
        # Generate comprehensive test data
        header = "hostname,environment,status,application_service,product_1,product_2,site_code,batch_number"
        rows = [header]
        
        environments = ["production", "development", "test", "acceptance"]
        applications = ["web_server", "api_server", "database_server", "cache_server"]
        products = ["web", "api", "db", "cache", "monitoring", "logging"]
        sites = ["use1", "usw2", "euw1", "apse1"]
        
        for i in range(2000):
            env = environments[i % len(environments)]
            app = applications[i % len(applications)]
            product1 = products[i % len(products)]
            product2 = products[(i + 1) % len(products)]
            site = sites[i % len(sites)]
            batch = str((i % 10) + 1)
            
            row = f"host-{i:04d},{env},active,{app},{product1},{product2},{site},{batch}"
            rows.append(row)
        
        csv_file.write_text("\n".join(rows))
        
        # Benchmark inventory generation
        inventory_manager = InventoryManager(csv_file=csv_file)
        
        start_time = time.time()
        result = inventory_manager.generate_inventories()
        end_time = time.time()
        
        generation_time = end_time - start_time
        
        # Verify results
        assert result["status"] == "success"
        assert result["stats"]["total_hosts"] == 2000
        assert len(result["generated_files"]) == 4  # 4 environments
        
        # Performance assertions
        assert generation_time < 60.0  # Should complete within 60 seconds
        
        # Check generated file sizes are reasonable
        for file_path in result["generated_files"]:
            file_size = Path(file_path).stat().st_size
            assert file_size < 1024 * 1024  # Less than 1MB per file
    
    def test_validation_performance(self, tmp_path):
        """Benchmark validation performance."""
        csv_file = tmp_path / "validation_perf.csv"
        
        # Generate data with some validation issues
        header = "hostname,environment,status,application_service,product_1"
        rows = [header]
        
        for i in range(3000):
            env = "production" if i % 2 == 0 else "development"
            status = "active" if i % 10 != 0 else "invalid_status"  # 10% invalid
            app = "web_server" if i % 3 == 0 else "api_server"
            product = "web" if i % 3 == 0 else "api"
            
            # Introduce some duplicate hostnames
            hostname = f"host-{i:04d}" if i % 100 != 0 else f"host-{(i-1):04d}"
            
            row = f"{hostname},{env},{status},{app},{product}"
            rows.append(row)
        
        csv_file.write_text("\n".join(rows))
        
        # Benchmark validation
        validator = ValidationManager(csv_file=csv_file)
        
        start_time = time.time()
        result = validator.validate_csv_data()
        end_time = time.time()
        
        validation_time = end_time - start_time
        
        # Verify validation caught issues
        assert not result.is_valid
        assert len(result.errors) > 0
        
        # Performance assertion
        assert validation_time < 30.0  # Should complete within 30 seconds


class TestMemoryUsage:
    """Test memory usage patterns and efficiency."""
    
    def test_memory_usage_csv_loading(self, tmp_path):
        """Test memory usage during CSV loading."""
        csv_file = tmp_path / "memory_test.csv"
        
        # Generate large CSV
        header = "hostname,environment,status,application_service"
        rows = [header]
        
        for i in range(10000):
            row = f"host-{i:05d},production,active,web_server"
            rows.append(row)
        
        csv_file.write_text("\n".join(rows))
        
        # Monitor memory usage
        gc.collect()  # Clean up before test
        
        @memory_profiler.profile
        def load_csv_with_profiling():
            return load_csv_data(csv_file)
        
        # Load data and check memory usage
        initial_memory = memory_profiler.memory_usage()[0]
        data = load_csv_data(csv_file)
        peak_memory = max(memory_profiler.memory_usage())
        
        memory_increase = peak_memory - initial_memory
        
        # Verify data loaded correctly
        assert len(data) == 10000
        
        # Memory usage should be reasonable
        assert memory_increase < 100  # Less than 100MB increase
        
        # Clean up
        del data
        gc.collect()
    
    def test_memory_usage_host_objects(self, tmp_path):
        """Test memory usage of host objects."""
        csv_file = tmp_path / "host_memory_test.csv"
        
        # Generate CSV with many columns
        header = "hostname,environment,status,cname,instance,site_code,ssl_port,application_service"
        header += ",product_1,product_2,product_3,product_4,primary_application,function"
        header += ",batch_number,patch_mode,dashboard_group,decommission_date"
        
        rows = [header]
        
        for i in range(5000):
            row = f"host-{i:05d},production,active,host{i}.example.com,{i},use1,443,web_server"
            row += ",web,monitoring,analytics,,nginx,load_balancer"
            row += f",{(i % 5) + 1},auto,web_servers,"
            rows.append(row)
        
        csv_file.write_text("\n".join(rows))
        
        # Monitor memory usage during host creation
        gc.collect()
        initial_memory = memory_profiler.memory_usage()[0]
        
        hosts = load_hosts_from_csv(csv_file)
        
        peak_memory = max(memory_profiler.memory_usage())
        memory_increase = peak_memory - initial_memory
        
        # Verify hosts created correctly
        assert len(hosts) == 5000
        
        # Memory usage should be reasonable
        assert memory_increase < 200  # Less than 200MB increase
        
        # Calculate average memory per host
        avg_memory_per_host = memory_increase / len(hosts)
        assert avg_memory_per_host < 0.05  # Less than 50KB per host on average
    
    def test_memory_cleanup_after_generation(self, tmp_path):
        """Test memory cleanup after inventory generation."""
        csv_file = tmp_path / "cleanup_test.csv"
        
        header = "hostname,environment,status,application_service,product_1"
        rows = [header]
        
        for i in range(2000):
            env = "production" if i % 2 == 0 else "development"
            row = f"host-{i:04d},{env},active,web_server,web"
            rows.append(row)
        
        csv_file.write_text("\n".join(rows))
        
        gc.collect()
        initial_memory = memory_profiler.memory_usage()[0]
        
        # Generate inventory
        inventory_manager = InventoryManager(csv_file=csv_file)
        result = inventory_manager.generate_inventories()
        
        peak_memory = max(memory_profiler.memory_usage())
        
        # Clean up
        del inventory_manager
        del result
        gc.collect()
        
        final_memory = memory_profiler.memory_usage()[0]
        
        # Memory should return close to initial level
        memory_leak = final_memory - initial_memory
        assert memory_leak < 50  # Less than 50MB permanent increase


class TestConcurrencyPerformance:
    """Test performance under concurrent operations."""
    
    def test_concurrent_csv_loading(self, tmp_path):
        """Test concurrent CSV loading performance."""
        # Create multiple CSV files
        csv_files = []
        for i in range(5):
            csv_file = tmp_path / f"concurrent_{i}.csv"
            
            header = "hostname,environment,status,application_service"
            rows = [header]
            
            for j in range(500):
                row = f"host-{i}-{j:03d},production,active,web_server"
                rows.append(row)
            
            csv_file.write_text("\n".join(rows))
            csv_files.append(csv_file)
        
        results = []
        
        def load_csv_concurrent(csv_file, thread_id):
            start_time = time.time()
            data = load_csv_data(csv_file)
            end_time = time.time()
            
            results.append({
                "thread_id": thread_id,
                "load_time": end_time - start_time,
                "rows_loaded": len(data)
            })
        
        # Start concurrent loading
        threads = []
        start_time = time.time()
        
        for i, csv_file in enumerate(csv_files):
            thread = threading.Thread(target=load_csv_concurrent, args=(csv_file, i))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Verify results
        assert len(results) == 5
        assert all(r["rows_loaded"] == 500 for r in results)
        
        # Should complete faster than sequential processing
        sequential_time = sum(r["load_time"] for r in results)
        assert total_time < sequential_time * 0.8  # At least 20% faster
    
    def test_concurrent_inventory_generation(self, tmp_path):
        """Test concurrent inventory generation safety."""
        csv_file = tmp_path / "concurrent_gen_test.csv"
        
        header = "hostname,environment,status,application_service"
        rows = [header]
        
        for i in range(1000):
            env = "production" if i % 2 == 0 else "development"
            row = f"host-{i:04d},{env},active,web_server"
            rows.append(row)
        
        csv_file.write_text("\n".join(rows))
        
        results = []
        
        def generate_concurrent(thread_id):
            try:
                inventory_manager = InventoryManager(csv_file=csv_file)
                start_time = time.time()
                result = inventory_manager.generate_inventories()
                end_time = time.time()
                
                results.append({
                    "thread_id": thread_id,
                    "status": result["status"],
                    "generation_time": end_time - start_time,
                    "hosts_processed": result["stats"]["total_hosts"]
                })
            except Exception as e:
                results.append({
                    "thread_id": thread_id,
                    "status": "error",
                    "error": str(e)
                })
        
        # Start concurrent generation
        threads = []
        for i in range(3):
            thread = threading.Thread(target=generate_concurrent, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(results) == 3
        
        # At least one should succeed
        success_count = sum(1 for r in results if r["status"] == "success")
        assert success_count >= 1
        
        # Check for data consistency
        successful_results = [r for r in results if r["status"] == "success"]
        if len(successful_results) > 1:
            # All successful runs should process same number of hosts
            host_counts = [r["hosts_processed"] for r in successful_results]
            assert all(count == host_counts[0] for count in host_counts)


class TestScalabilityLimits:
    """Test system behavior at scale limits."""
    
    def test_maximum_host_count(self, tmp_path):
        """Test system behavior with maximum reasonable host count."""
        csv_file = tmp_path / "max_hosts.csv"
        
        # Generate very large CSV (10K hosts)
        header = "hostname,environment,status,application_service,product_1"
        rows = [header]
        
        for i in range(10000):
            env = "production" if i % 4 == 0 else "development" if i % 4 == 1 else "test" if i % 4 == 2 else "acceptance"
            app = "web_server" if i % 3 == 0 else "api_server" if i % 3 == 1 else "database_server"
            product = "web" if i % 3 == 0 else "api" if i % 3 == 1 else "db"
            
            row = f"host-{i:05d},{env},active,{app},{product}"
            rows.append(row)
        
        csv_file.write_text("\n".join(rows))
        
        # Test loading
        start_time = time.time()
        hosts = load_hosts_from_csv(csv_file)
        load_time = time.time() - start_time
        
        assert len(hosts) == 10000
        assert load_time < 60.0  # Should complete within 60 seconds
        
        # Test inventory generation
        inventory_manager = InventoryManager(csv_file=csv_file)
        
        start_time = time.time()
        result = inventory_manager.generate_inventories()
        generation_time = time.time() - start_time
        
        assert result["status"] == "success"
        assert result["stats"]["total_hosts"] == 10000
        assert generation_time < 120.0  # Should complete within 2 minutes
    
    def test_maximum_column_count(self, tmp_path):
        """Test system behavior with maximum column count."""
        csv_file = tmp_path / "max_columns.csv"
        
        # Generate CSV with many columns
        header = "hostname,environment,status,application_service"
        
        # Add many product columns
        for i in range(50):
            header += f",product_{i+1}"
        
        # Add many extra columns
        for i in range(100):
            header += f",extra_col_{i}"
        
        rows = [header]
        
        for i in range(100):
            row = f"host-{i:03d},production,active,web_server"
            
            # Add product values
            for j in range(50):
                product = f"product_{j}" if j < 5 else ""  # Only first 5 products have values
                row += f",{product}"
            
            # Add extra values
            for j in range(100):
                row += f",extra_value_{i}_{j}"
            
            rows.append(row)
        
        csv_file.write_text("\n".join(rows))
        
        # Test loading
        start_time = time.time()
        hosts = load_hosts_from_csv(csv_file)
        load_time = time.time() - start_time
        
        assert len(hosts) == 100
        assert load_time < 30.0  # Should handle many columns efficiently
        
        # Verify product parsing
        assert len(hosts[0].products) > 0
        assert len(hosts[0].metadata) > 0
    
    def test_performance_regression_detection(self, tmp_path):
        """Test for performance regression detection."""
        # This test establishes baseline performance metrics
        csv_file = tmp_path / "regression_test.csv"
        
        # Standard test data
        header = "hostname,environment,status,application_service,product_1,product_2"
        rows = [header]
        
        for i in range(1000):
            env = "production" if i % 2 == 0 else "development"
            app = "web_server" if i % 3 == 0 else "api_server"
            product1 = "web" if i % 3 == 0 else "api"
            product2 = "monitoring" if i % 2 == 0 else "logging"
            
            row = f"host-{i:04d},{env},active,{app},{product1},{product2}"
            rows.append(row)
        
        csv_file.write_text("\n".join(rows))
        
        # Benchmark all major operations
        benchmarks = {}
        
        # CSV loading
        start_time = time.time()
        data = load_csv_data(csv_file)
        benchmarks["csv_loading"] = time.time() - start_time
        
        # Host creation
        start_time = time.time()
        hosts = load_hosts_from_csv(csv_file)
        benchmarks["host_creation"] = time.time() - start_time
        
        # Inventory generation
        start_time = time.time()
        inventory_manager = InventoryManager(csv_file=csv_file)
        result = inventory_manager.generate_inventories()
        benchmarks["inventory_generation"] = time.time() - start_time
        
        # Validation
        start_time = time.time()
        validator = ValidationManager(csv_file=csv_file)
        validation_result = validator.validate_csv_data()
        benchmarks["validation"] = time.time() - start_time
        
        # Performance thresholds (adjust based on your requirements)
        thresholds = {
            "csv_loading": 5.0,
            "host_creation": 10.0,
            "inventory_generation": 30.0,
            "validation": 15.0
        }
        
        # Check for regressions
        for operation, time_taken in benchmarks.items():
            assert time_taken < thresholds[operation], f"{operation} took {time_taken:.2f}s, threshold is {thresholds[operation]}s"
        
        # Log benchmarks for monitoring
        print(f"\nPerformance Benchmarks (1000 hosts):")
        for operation, time_taken in benchmarks.items():
            print(f"  {operation}: {time_taken:.3f}s") 