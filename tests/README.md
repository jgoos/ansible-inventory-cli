# Testing Suite
## Ansible Inventory Management System

This directory contains the comprehensive testing suite for the Ansible inventory management system.

---

## 📁 Test Structure

```
tests/
├── README.md                    # This file
├── conftest.py                  # Pytest configuration and shared fixtures
├── test_cli_interface.py        # CLI interface and command routing tests
├── test_core_utils.py           # Core utility functions tests
├── test_integration.py          # Integration and end-to-end tests
├── test_performance.py          # Performance and scalability tests
├── test_security.py             # Security and vulnerability tests
├── test_edge_cases.py           # Edge cases and error handling tests (existing)
├── test_host_manager.py         # Host manager functionality tests (existing)
├── test_instance_validation.py  # Instance validation tests (existing)
└── test_inventory_generation.py # Inventory generation tests (existing)
```

---

## 🧪 Test Categories

### 1. **Unit Tests** 🔧
**Files:** `test_cli_interface.py`, `test_core_utils.py`  
**Purpose:** Test individual functions and classes in isolation

- **CLI Interface Tests** (26 tests)
  - Command registry and routing
  - Argument parsing and validation
  - Error handling and edge cases
  - Output formatting

- **Core Utilities Tests** (42 tests)
  - File operations and I/O
  - Data validation and sanitization
  - Configuration loading
  - Logging and error handling

### 2. **Integration Tests** 🔗
**Files:** `test_integration.py`  
**Purpose:** Test component interactions and workflows

- **CSV to Inventory Pipeline** - Complete data flow testing
- **Multi-Component Integration** - Manager interactions
- **Configuration Integration** - System-wide configuration testing
- **Error Propagation** - Error handling across components

### 3. **End-to-End Tests** 🎯
**Files:** `test_integration.py` (E2E scenarios)  
**Purpose:** Test complete user workflows

- **Complete Inventory Generation** - Full user workflow
- **Host Lifecycle Management** - Add, update, decommission
- **Multi-Environment Scenarios** - Complex deployment patterns
- **Recovery and Rollback** - Error recovery testing

### 4. **Performance Tests** ⚡
**Files:** `test_performance.py`  
**Purpose:** Benchmark performance and scalability

- **CSV Loading Performance** - Various dataset sizes (100-10,000 hosts)
- **Memory Usage Testing** - Memory consumption patterns
- **Concurrent Operations** - Thread safety and parallel processing
- **Scalability Limits** - System behavior at scale

### 5. **Security Tests** 🔒
**Files:** `test_security.py`  
**Purpose:** Validate security and prevent vulnerabilities

- **Input Validation** - Malicious input handling
- **Injection Prevention** - CSV, command, and YAML injection
- **File System Security** - Path traversal and permission validation
- **Configuration Security** - Secure configuration loading

### 6. **Existing Tests** ✅
**Files:** `test_edge_cases.py`, `test_host_manager.py`, etc.  
**Purpose:** Maintain existing functionality (26 tests)

- **Edge Cases** - Boundary conditions and error scenarios
- **Host Manager** - Host management functionality
- **Instance Validation** - Data validation logic
- **Inventory Generation** - Core generation functionality

---

## 🚀 Quick Start

### Prerequisites
```bash
# Install testing dependencies
pip install -r requirements.txt
pip install -e ".[dev,test]"

# Optional: Install performance testing tools
pip install memory-profiler pytest-benchmark
```

### Run All Tests
```bash
# Using make (recommended)
make test

# Using pytest directly
python -m pytest tests/ -v
```

### Run with Coverage
```bash
# Generate coverage report
make test-cov

# Or using pytest
python -m pytest tests/ --cov=scripts --cov-report=html --cov-report=term-missing
```

---

## 🏃 Running Tests

### By Category
```bash
# Unit tests
make test-unit
python -m pytest -m "unit" -v

# Integration tests
make test-integration
python -m pytest -m "integration" -v

# End-to-end tests
python -m pytest -m "e2e" -v

# Performance tests
make test-performance
python -m pytest -m "performance" -v

# Security tests
make test-security
python -m pytest -m "security" -v

# Existing tests
make test-existing
```

### By Test File
```bash
# CLI interface tests
python -m pytest tests/test_cli_interface.py -v

# Core utilities tests
python -m pytest tests/test_core_utils.py -v

# Integration tests
python -m pytest tests/test_integration.py -v

# Performance tests
python -m pytest tests/test_performance.py -v

# Security tests
python -m pytest tests/test_security.py -v
```

### Specific Tests
```bash
# Run specific test class
python -m pytest tests/test_cli_interface.py::TestModularInventoryCLI -v

# Run specific test method
python -m pytest tests/test_cli_interface.py::TestModularInventoryCLI::test_create_parser -v

# Run tests matching pattern
python -m pytest -k "csv" -v
python -m pytest -k "validation" -v
python -m pytest -k "security" -v
```

### Advanced Options
```bash
# Parallel execution
make test-parallel
python -m pytest tests/ -n auto

# With coverage threshold
make test-all
python -m pytest tests/ --cov=scripts --cov-fail-under=80

# Verbose output with full traceback
python -m pytest tests/ -vv --tb=long --showlocals

# Debug mode
python -m pytest tests/ --pdb
```

---

## ⚙️ Test Configuration

### Pytest Configuration
Configuration is defined in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "--tb=short",
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "performance: Performance tests",
    "security: Security tests",
    "slow: Slow running tests",
]
```

### Coverage Configuration
Configuration is defined in `.coveragerc`:

```ini
[run]
source = scripts
omit = 
    */tests/*
    */venv/*
    */__pycache__/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
```

---

## 🔧 Test Fixtures

### Shared Fixtures
Located in `conftest.py`:

- **`sample_csv_data`** - Sample CSV data for testing
- **`temp_csv_file`** - Temporary CSV file with sample data
- **`large_csv_file`** - Large dataset for performance testing
- **`mock_inventory_manager`** - Mocked inventory manager
- **`mock_validation_manager`** - Mocked validation manager
- **`security_test_data`** - Malicious data for security testing

### Usage Example
```python
def test_csv_loading(temp_csv_file):
    """Test CSV loading with fixture."""
    data = load_csv_data(temp_csv_file)
    assert len(data) > 0
```

---

## 📊 Coverage Analysis

### Generate Coverage Reports
```bash
# HTML report (recommended)
python -m pytest tests/ --cov=scripts --cov-report=html

# Terminal report
python -m pytest tests/ --cov=scripts --cov-report=term-missing

# XML report (for CI)
python -m pytest tests/ --cov=scripts --cov-report=xml

# Combined reports
make test-cov
```

### View Coverage Report
```bash
# Open HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Current Coverage Status
```
Total Statements: 2,477
Covered Statements: 865
Coverage Percentage: 34.92%
Target: 80%+
```

---

## ⚡ Performance Testing

### Performance Benchmarks
```bash
# Run performance tests
make test-performance

# Run with benchmarking
python -m pytest tests/test_performance.py --benchmark-only

# Generate benchmark report
python -m pytest tests/test_performance.py --benchmark-json=results.json
```

### Performance Thresholds
- **CSV Loading:** <30s for 5,000 hosts
- **Inventory Generation:** <60s for 2,000 hosts  
- **Memory Usage:** <200MB for 5,000 hosts
- **Host Model Creation:** <10s for 5,000 hosts

### Performance Test Categories
1. **CSV Loading Performance** - Various file sizes
2. **Inventory Generation Performance** - Complete workflow
3. **Memory Usage Testing** - Memory consumption patterns
4. **Concurrency Testing** - Thread safety validation

---

## 🔒 Security Testing

### Security Test Categories
```bash
# Run all security tests
make test-security

# Run specific security categories
python -m pytest tests/test_security.py::TestInputValidation -v
python -m pytest tests/test_security.py::TestFileSystemSecurity -v
python -m pytest tests/test_security.py::TestConfigurationSecurity -v
```

### Security Validations
1. **Input Validation** - Malicious CSV content handling
2. **Injection Prevention** - CSV, command, and YAML injection
3. **File System Security** - Path traversal and permissions
4. **Configuration Security** - Secure configuration loading
5. **Output Security** - Sensitive data exposure prevention

### Security Scanning
```bash
# Run security scan
make security

# Manual security tools
bandit -r scripts/
safety check
```

---

## 🔄 Local Testing Integration

### Makefile-Based Testing
The testing suite is designed for local execution using Makefile commands:

### Quality Assurance Workflow
1. **Code Quality** - Linting and formatting (`make lint`, `make format`)
2. **Security** - Vulnerability scanning (`make security`)
3. **Unit Tests** - Component testing (`make test-unit`)
4. **Integration Tests** - Component interactions (`make test-integration`)
5. **Performance Tests** - Benchmarking (`make test-performance`)
6. **Security Tests** - Vulnerability testing (`make test-security`)
7. **Comprehensive Testing** - All tests with coverage (`make test-all`)

### Continuous Integration Ready
The Makefile commands can be easily integrated into any CI/CD system:

```bash
# Example CI workflow
make install-dev
make quality-check
make test-all
make security
```

---

## 🔧 Troubleshooting

### Common Issues

#### Test Discovery
```bash
# Check test discovery
python -m pytest --collect-only

# Verify test files
ls tests/test_*.py
```

#### Import Errors
```bash
# Install in development mode
pip install -e .

# Check imports
python -c "from scripts.core.models import Host; print('OK')"
```

#### Coverage Issues
```bash
# Debug coverage
python -m pytest tests/ --cov=scripts --cov-report=term-missing -v

# Check coverage config
cat .coveragerc
```

#### Performance Issues
```bash
# Install performance dependencies
pip install memory-profiler pytest-benchmark

# Run single performance test
python -m pytest tests/test_performance.py::TestPerformanceBenchmarks::test_csv_loading_performance -v
```

### Debug Mode
```bash
# Debug with full output
python -m pytest tests/ -vv --tb=long --showlocals

# Debug with PDB
python -m pytest tests/ --pdb

# Clean test cache
python -m pytest --cache-clear
```

---

## 📚 Best Practices

### Test Organization
- **One test class per component** being tested
- **Descriptive test names** explaining what's tested
- **Clear test documentation** with docstrings
- **Logical grouping** using markers

### Test Data Management
- **Use fixtures** for reusable test data
- **Isolate test data** using temporary directories
- **Clean up resources** in teardown methods
- **Mock external dependencies** to avoid side effects

### Test Maintenance
- **Keep tests simple** and focused
- **Update tests** when code changes
- **Remove obsolete tests** regularly
- **Maintain coverage** above threshold

### Performance Considerations
- **Use markers** to separate slow tests
- **Parallelize tests** where possible
- **Mock expensive operations** in unit tests
- **Profile tests** to identify bottlenecks

---

## 🛠️ Development Workflow

### Adding New Tests
1. **Create test file** following naming convention
2. **Add appropriate markers** for categorization
3. **Write comprehensive tests** with good coverage
4. **Update documentation** as needed
5. **Run tests** to ensure they pass

### Test File Template
```python
#!/usr/bin/env python3
"""Test module for [component name]."""

import pytest
from unittest.mock import Mock, patch

from scripts.[module] import [component]


class Test[Component]:
    """Test class for [Component] functionality."""
    
    def setup_method(self):
        """Setup method called before each test."""
        pass
    
    @pytest.mark.unit
    def test_[functionality](self, fixture_name):
        """Test [specific functionality]."""
        # Arrange
        # Act
        # Assert
        pass
```

### Running Tests During Development
```bash
# Run tests for current changes
python -m pytest tests/ -x -v

# Run with coverage
python -m pytest tests/ --cov=scripts --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_new_feature.py -v
```

---

## 📖 Additional Resources

### Documentation
- **[Testing Guide](../docs/TESTING_GUIDE.md)** - Comprehensive testing documentation
- **[Test Report](../TEST_REPORT.md)** - Current testing status and metrics
- **[pytest Documentation](https://docs.pytest.org/)** - Official pytest documentation
- **[Coverage.py Documentation](https://coverage.readthedocs.io/)** - Coverage tool documentation

### Tools and Frameworks
- **pytest** - Main testing framework
- **pytest-cov** - Coverage reporting
- **pytest-mock** - Mocking utilities
- **pytest-xdist** - Parallel execution
- **memory-profiler** - Memory usage analysis
- **bandit** - Security linting
- **safety** - Dependency security scanning

### Make Commands
```bash
# Test commands
make test                # Run all tests
make test-cov            # Run tests with coverage
make test-unit           # Run unit tests
make test-integration    # Run integration tests
make test-performance    # Run performance tests
make test-security       # Run security tests
make test-all            # Run all tests with coverage threshold
make test-parallel       # Run tests in parallel
make test-clean          # Clean test artifacts

# Quality commands
make quality-check       # Run comprehensive quality checks
make security            # Run security scans
make performance-test    # Run performance benchmarks
```

---

**Last Updated:** 2024-01-20  
**Version:** 1.0.0  
**Maintainer:** Development Team

For questions or issues with the testing suite, please refer to the [Testing Guide](../docs/TESTING_GUIDE.md) or contact the development team. 