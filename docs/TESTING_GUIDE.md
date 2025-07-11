# Testing Guide
## Ansible Inventory Management System

This guide provides comprehensive documentation for the testing suite, including setup, usage, and best practices.

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Test Categories](#test-categories)
3. [Running Tests](#running-tests)
4. [Test Configuration](#test-configuration)
5. [Writing Tests](#writing-tests)
6. [CI/CD Pipeline](#cicd-pipeline)
7. [Coverage Analysis](#coverage-analysis)
8. [Performance Testing](#performance-testing)
9. [Security Testing](#security-testing)
10. [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt
pip install -e ".[dev,test]"

# Additional testing dependencies
pip install memory-profiler pytest-benchmark
```

### Run All Tests
```bash
# Run complete test suite
make test

# Or using pytest directly
python -m pytest tests/ -v
```

### Run with Coverage
```bash
# Generate coverage report
python -m pytest tests/ --cov=scripts --cov-report=html --cov-report=term-missing
```

---

## 🧪 Test Categories

### 1. Unit Tests
**Purpose:** Test individual functions and classes in isolation  
**Location:** `tests/test_cli_interface.py`, `tests/test_core_utils.py`  
**Coverage:** CLI interface, core utilities, data models

```bash
# Run unit tests only
python -m pytest tests/test_cli_interface.py tests/test_core_utils.py -v

# Run with markers
python -m pytest -m "unit" -v
```

**What's Tested:**
- CLI argument parsing and validation
- Command routing and execution
- Core utility functions
- Data model creation and validation
- Configuration loading
- Error handling and edge cases

### 2. Integration Tests
**Purpose:** Test component interactions and workflows  
**Location:** `tests/test_integration.py`  
**Coverage:** Multi-component workflows

```bash
# Run integration tests
python -m pytest tests/test_integration.py -v

# Run with markers
python -m pytest -m "integration" -v
```

**What's Tested:**
- CSV → Host Model → Inventory Generation pipeline
- Manager component interactions
- Configuration integration
- File system operations
- Ansible compatibility

### 3. End-to-End Tests
**Purpose:** Test complete user workflows  
**Location:** `tests/test_integration.py` (E2E scenarios)  
**Coverage:** Full system workflows

```bash
# Run E2E tests
python -m pytest -m "e2e" -v
```

**What's Tested:**
- Complete inventory generation workflow
- Host lifecycle management
- Multi-environment scenarios
- Error recovery and rollback
- Real Ansible integration

### 4. Performance Tests
**Purpose:** Benchmark performance and scalability  
**Location:** `tests/test_performance.py`  
**Coverage:** Performance metrics and scalability

```bash
# Run performance tests
python -m pytest tests/test_performance.py -v

# Run with benchmarking
python -m pytest tests/test_performance.py --benchmark-only
```

**What's Tested:**
- CSV loading performance (various sizes)
- Inventory generation speed
- Memory usage patterns
- Concurrent operation safety
- Scalability limits

### 5. Security Tests
**Purpose:** Validate security and prevent vulnerabilities  
**Location:** `tests/test_security.py`  
**Coverage:** Security validation and attack prevention

```bash
# Run security tests
python -m pytest tests/test_security.py -v

# Run with security markers
python -m pytest -m "security" -v
```

**What's Tested:**
- Input validation and sanitization
- Injection attack prevention
- File system security
- Configuration security
- Data exposure prevention

### 6. Existing Tests
**Purpose:** Maintain existing functionality  
**Location:** `tests/test_edge_cases.py`, `tests/test_host_manager.py`, etc.  
**Coverage:** Established functionality

```bash
# Run existing tests
python -m pytest tests/test_edge_cases.py tests/test_host_manager.py tests/test_instance_validation.py tests/test_inventory_generation.py -v
```

---

## 🏃 Running Tests

### Basic Test Execution

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_cli_interface.py

# Run specific test class
python -m pytest tests/test_cli_interface.py::TestModularInventoryCLI

# Run specific test method
python -m pytest tests/test_cli_interface.py::TestModularInventoryCLI::test_create_parser
```

### Test Filtering

```bash
# Run tests by marker
python -m pytest -m "unit"
python -m pytest -m "integration"
python -m pytest -m "e2e"
python -m pytest -m "performance"
python -m pytest -m "security"

# Run tests by keyword
python -m pytest -k "csv"
python -m pytest -k "validation"
python -m pytest -k "security"

# Exclude specific tests
python -m pytest -m "not performance"
```

### Verbose Output

```bash
# Verbose output
python -m pytest tests/ -v

# Extra verbose with full traceback
python -m pytest tests/ -vv --tb=long

# Show local variables in traceback
python -m pytest tests/ -vv --tb=long --showlocals
```

### Parallel Execution

```bash
# Install pytest-xdist for parallel execution
pip install pytest-xdist

# Run tests in parallel
python -m pytest tests/ -n auto
python -m pytest tests/ -n 4  # Use 4 processes
```

---

## ⚙️ Test Configuration

### pytest Configuration
**File:** `pyproject.toml`

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
**File:** `.coveragerc`

```ini
[run]
source = scripts
omit = 
    */tests/*
    */venv/*
    */__pycache__/*
    */migrations/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
```

### Test Markers

```python
import pytest

# Mark test categories
@pytest.mark.unit
def test_unit_functionality():
    pass

@pytest.mark.integration  
def test_integration_workflow():
    pass

@pytest.mark.e2e
def test_end_to_end_scenario():
    pass

@pytest.mark.performance
def test_performance_benchmark():
    pass

@pytest.mark.security
def test_security_validation():
    pass

@pytest.mark.slow
def test_slow_operation():
    pass
```

---

## ✍️ Writing Tests

### Test Structure

```python
#!/usr/bin/env python3
"""Test module docstring describing the test purpose."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from scripts.core.models import Host
from scripts.managers.inventory_manager import InventoryManager


class TestInventoryManager:
    """Test class for InventoryManager functionality."""
    
    def setup_method(self):
        """Setup method called before each test."""
        self.test_data = {...}
    
    def teardown_method(self):
        """Teardown method called after each test."""
        # Cleanup code
        pass
    
    @pytest.mark.unit
    def test_inventory_generation_success(self, tmp_path):
        """Test successful inventory generation."""
        # Arrange
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("hostname,environment,status\ntest-host,production,active")
        
        # Act
        manager = InventoryManager(csv_file=csv_file)
        result = manager.generate_inventories()
        
        # Assert
        assert result["status"] == "success"
        assert "generated_files" in result
    
    @pytest.mark.integration
    def test_inventory_integration_workflow(self, tmp_path):
        """Test complete inventory workflow integration."""
        # Integration test code
        pass
```

### Test Fixtures

```python
import pytest
import tempfile
from pathlib import Path

@pytest.fixture
def sample_csv_data():
    """Provide sample CSV data for testing."""
    return """hostname,environment,status,application_service
web-01,production,active,web_server
api-01,production,active,api_server
db-01,production,active,database_server"""

@pytest.fixture
def temp_csv_file(tmp_path, sample_csv_data):
    """Create temporary CSV file with sample data."""
    csv_file = tmp_path / "test_hosts.csv"
    csv_file.write_text(sample_csv_data)
    return csv_file

@pytest.fixture
def mock_inventory_manager():
    """Provide mocked inventory manager."""
    with patch('scripts.managers.inventory_manager.InventoryManager') as mock:
        yield mock
```

### Mocking External Dependencies

```python
from unittest.mock import Mock, patch, mock_open

# Mock file operations
@patch('builtins.open', mock_open(read_data='csv,data'))
def test_file_reading():
    # Test code
    pass

# Mock subprocess calls
@patch('subprocess.run')
def test_ansible_command(mock_run):
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "success"
    # Test code

# Mock external APIs
@patch('requests.get')
def test_api_call(mock_get):
    mock_get.return_value.json.return_value = {"status": "ok"}
    # Test code
```

### Parameterized Tests

```python
@pytest.mark.parametrize("environment,expected", [
    ("production", True),
    ("development", True),
    ("test", True),
    ("invalid", False),
])
def test_environment_validation(environment, expected):
    """Test environment validation with various inputs."""
    result = validate_environment(environment)
    assert result == expected

@pytest.mark.parametrize("host_count", [100, 1000, 5000])
def test_performance_scaling(host_count):
    """Test performance with different host counts."""
    # Generate test data
    # Run performance test
    # Assert performance criteria
```

---

## 🔄 Local Testing Workflow

### Makefile-Based Testing
The testing suite is designed to run locally using Makefile commands, providing full control over the testing process.

### Available Test Commands

**Basic Testing:**
```bash
make test                    # Run all tests
make test-cov               # Run tests with coverage
make test-unit              # Run unit tests only
make test-integration       # Run integration tests only
make test-e2e               # Run end-to-end tests only
```

**Specialized Testing:**
```bash
make test-performance       # Run performance tests only
make test-security          # Run security tests only
make test-existing          # Run existing tests only
make test-parallel          # Run tests in parallel
make test-all              # Run all tests with coverage threshold
```

**Quality Assurance:**
```bash
make quality-check          # Run comprehensive quality checks
make security              # Run security scans
make performance-test      # Run performance benchmarks
make lint                  # Run code linting
make format                # Format code
```

### Testing Workflow

1. **Development Testing** - Run relevant tests during development
2. **Pre-commit Testing** - Run quality checks before committing
3. **Integration Testing** - Test component interactions
4. **Performance Testing** - Validate performance benchmarks
5. **Security Testing** - Check for vulnerabilities

### Continuous Integration Options

While GitHub Actions are not currently configured, the Makefile commands can be easily integrated into any CI/CD system:

```bash
# Example CI script
make install-dev
make quality-check
make test-all
make security
```

---

## 📊 Coverage Analysis

### Generating Coverage Reports

```bash
# Generate HTML coverage report
python -m pytest tests/ --cov=scripts --cov-report=html

# Generate XML coverage report (for CI)
python -m pytest tests/ --cov=scripts --cov-report=xml

# Generate terminal coverage report
python -m pytest tests/ --cov=scripts --cov-report=term-missing

# Combined reports
python -m pytest tests/ --cov=scripts --cov-report=html --cov-report=xml --cov-report=term-missing
```

### Coverage Thresholds

```bash
# Fail if coverage below threshold
python -m pytest tests/ --cov=scripts --cov-fail-under=80

# Coverage for specific modules
python -m pytest tests/ --cov=scripts.core --cov-fail-under=90
```

### Coverage Analysis

```bash
# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Coverage Exclusions

```python
# Exclude lines from coverage
def debug_function():  # pragma: no cover
    print("Debug information")

# Exclude blocks
if __name__ == "__main__":  # pragma: no cover
    main()
```

---

## ⚡ Performance Testing

### Running Performance Tests

```bash
# Run all performance tests
python -m pytest tests/test_performance.py -v

# Run specific performance test
python -m pytest tests/test_performance.py::TestPerformanceBenchmarks::test_csv_loading_performance -v

# Run with memory profiling
python -m pytest tests/test_performance.py -v --profile

# Run with benchmarking
python -m pytest tests/test_performance.py --benchmark-only --benchmark-json=results.json
```

### Performance Test Categories

1. **CSV Loading Performance**
   - Tests loading speed for various file sizes
   - Validates scalability with 100-5000 hosts
   - Measures rows processed per second

2. **Inventory Generation Performance**
   - Tests complete inventory generation workflow
   - Validates generation time thresholds
   - Measures file creation efficiency

3. **Memory Usage Testing**
   - Monitors memory consumption patterns
   - Validates memory cleanup after operations
   - Tests for memory leaks

4. **Concurrency Testing**
   - Tests concurrent operation safety
   - Validates thread safety
   - Measures parallel processing efficiency

### Performance Thresholds

```python
# Example performance assertions
assert load_time < 30.0  # CSV loading < 30 seconds for 5000 hosts
assert generation_time < 60.0  # Inventory generation < 60 seconds for 2000 hosts
assert memory_increase < 200  # Memory usage < 200MB for 5000 hosts
```

---

## 🔒 Security Testing

### Running Security Tests

```bash
# Run all security tests
python -m pytest tests/test_security.py -v

# Run specific security test categories
python -m pytest tests/test_security.py::TestInputValidation -v
python -m pytest tests/test_security.py::TestFileSystemSecurity -v

# Run with security markers
python -m pytest -m "security" -v
```

### Security Test Categories

1. **Input Validation**
   - Malicious CSV content handling
   - CSV injection prevention
   - Data sanitization validation

2. **File System Security**
   - Path traversal prevention
   - File permission validation
   - Symlink security testing

3. **Configuration Security**
   - Configuration injection prevention
   - Environment variable security
   - Secure configuration loading

4. **Output Security**
   - Sensitive data exposure prevention
   - Log sanitization
   - Error message security

### Security Scanning Tools

```bash
# Run Bandit security scanner
bandit -r scripts/ -f json -o security-report.json

# Run Safety dependency scanner
safety check --json --output safety-report.json

# Run both with make
make security-check
```

---

## 🔧 Troubleshooting

### Common Issues

#### Test Discovery Issues
```bash
# If tests aren't discovered
python -m pytest --collect-only

# Check test file naming
ls tests/test_*.py

# Verify Python path
python -c "import sys; print(sys.path)"
```

#### Import Errors
```bash
# Install package in development mode
pip install -e .

# Check module imports
python -c "from scripts.core.models import Host; print('Import successful')"
```

#### Coverage Issues
```bash
# Check coverage configuration
cat .coveragerc

# Run coverage with debug
python -m pytest tests/ --cov=scripts --cov-report=term-missing --cov-config=.coveragerc
```

#### Performance Test Issues
```bash
# Install performance testing dependencies
pip install memory-profiler pytest-benchmark

# Run single performance test
python -m pytest tests/test_performance.py::TestPerformanceBenchmarks::test_csv_loading_performance -v -s
```

### Debug Mode

```bash
# Run tests with debug output
python -m pytest tests/ -v -s --tb=long --showlocals

# Run with PDB debugger
python -m pytest tests/ --pdb

# Run with coverage debug
python -m pytest tests/ --cov=scripts --cov-report=term-missing --cov-config=.coveragerc -v
```

### Test Environment Issues

```bash
# Check test environment
python -m pytest --version
python -c "import pytest; print(pytest.__version__)"

# Verify dependencies
pip list | grep pytest
pip check

# Clean test cache
python -m pytest --cache-clear
```

---

## 📚 Best Practices

### Test Organization
- **One test class per component** being tested
- **Descriptive test names** that explain what's being tested
- **Clear test documentation** with docstrings
- **Logical test grouping** using markers and categories

### Test Data Management
- **Use fixtures** for reusable test data
- **Isolate test data** using temporary directories
- **Clean up resources** in teardown methods
- **Mock external dependencies** to avoid side effects

### Test Maintenance
- **Keep tests simple** and focused on single behaviors
- **Update tests** when code changes
- **Remove obsolete tests** that no longer provide value
- **Maintain test coverage** above threshold

### Performance Considerations
- **Use markers** to separate slow tests
- **Parallelize tests** where possible
- **Mock expensive operations** in unit tests
- **Profile tests** to identify bottlenecks

---

## 📖 Additional Resources

### Documentation
- [pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)

### Tools
- **pytest** - Main testing framework
- **pytest-cov** - Coverage reporting
- **pytest-mock** - Mocking utilities
- **pytest-xdist** - Parallel test execution
- **memory-profiler** - Memory usage profiling
- **bandit** - Security linting
- **safety** - Dependency security scanning

### Example Commands
```bash
# Complete test run with coverage
make test-coverage

# Security scan
make security-check

# Performance benchmarks
make performance-test

# All quality checks
make quality-check
```

---

**Last Updated:** 2024-01-20  
**Version:** 1.0.0  
**Maintainer:** Development Team 