# Makefile for Ansible Inventory CLI
# =================================
# Optimized for RHEL9 where Python3 is the default system Python

# RHEL9 Python3 Configuration
PYTHON3 := python3
VENV_PYTHON := .venv/bin/python3
VENV_PIP := .venv/bin/pip
VENV_DIR := .venv

# Ensure Python3 is available (RHEL9 default)
PYTHON_VERSION_CHECK := $(shell $(PYTHON3) --version 2>/dev/null | grep -q "Python 3" && echo "OK" || echo "MISSING")

.PHONY: help install install-dev test test-cov lint format security clean build pre-commit check health-check python-check

# Default target
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

# Python3 verification for RHEL9
python-check: ## Verify Python3 is available (RHEL9 default)
	@echo "🐍 Checking Python3 availability..."
	@if [ "$(PYTHON_VERSION_CHECK)" = "OK" ]; then \
		echo "✅ Python3 is available"; \
		$(PYTHON3) --version; \
	else \
		echo "❌ Python3 not found. On RHEL9, install with: dnf install python3"; \
		exit 1; \
	fi

## Installation Targets
# Installation (using pyproject.toml as single source of truth)
install: ## Install the package
	$(VENV_PIP) install -e .

install-dev: install ## Install development dependencies
	$(VENV_PIP) install -e ".[dev,test,docs]"
	$(VENV_DIR)/bin/pre-commit install

## Testing Targets
# Testing
test: install-dev ## Run tests
	$(VENV_DIR)/bin/pytest -v

test-cov: install-dev ## Run tests with coverage
	$(VENV_DIR)/bin/pytest --cov=scripts --cov-report=html --cov-report=term-missing --cov-report=xml -v

test-unit: install-dev ## Run unit tests only
	$(VENV_DIR)/bin/pytest tests/ -m "unit" --cov=scripts --cov-fail-under=80 -v

test-integration: install-dev ## Run integration tests only
	$(VENV_DIR)/bin/pytest tests/ -m "integration" --cov=scripts --cov-fail-under=80 -v

test-e2e: install-dev ## Run end-to-end tests only
	$(VENV_DIR)/bin/pytest tests/ -m "e2e" --cov=scripts --cov-fail-under=80 -v

test-performance: install-dev ## Run performance tests only
	$(VENV_DIR)/bin/pytest tests/test_performance.py -v

test-security: install-dev ## Run security tests only
	$(VENV_DIR)/bin/pytest tests/test_security.py -v

test-existing: install-dev ## Run existing tests only
	$(VENV_DIR)/bin/pytest tests/test_edge_cases.py tests/test_host_manager.py tests/test_instance_validation.py tests/test_inventory_generation.py -v

test-all: install-dev ## Run all tests with coverage and fail if below threshold
	$(VENV_DIR)/bin/pytest tests/ --cov=scripts --cov-report=html --cov-report=xml --cov-report=term-missing --cov-fail-under=80 -v

test-parallel: install-dev ## Run tests in parallel
	$(VENV_DIR)/bin/pytest tests/ -n auto -v

test-markers: ## Show available test markers
	@echo "Available test markers: ✅"
	@echo "  unit        - Unit tests"
	@echo "  integration - Integration tests"
	@echo "  e2e         - End-to-end tests"
	@echo "  performance - Performance tests"
	@echo "  security    - Security tests"
	@echo "  slow        - Slow running tests"

test-clean: ## Clean test artifacts
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	rm -rf security-report.json
	rm -rf safety-report.json
	rm -rf benchmark-results.json
	@echo "Test artifacts cleaned! ✅"

## Code Quality Targets
# Code Quality
lint: install-dev ## Run all linting tools
	@echo "Running flake8..."
	$(VENV_DIR)/bin/flake8 scripts/
	@echo "Running mypy..."
	$(VENV_DIR)/bin/mypy scripts/
	@echo "Running bandit..."
	$(VENV_DIR)/bin/bandit -r scripts/
	@echo "Running yamllint..."
	$(VENV_DIR)/bin/yamllint inventory/ ansible.cfg

format: install-dev ## Format code with black and isort
	@echo "Running black..."
	$(VENV_DIR)/bin/black scripts/
	@echo "Running isort..."
	$(VENV_DIR)/bin/isort scripts/

format-check: install-dev ## Check if code is properly formatted
	@echo "Checking black formatting..."
	$(VENV_DIR)/bin/black --check scripts/
	@echo "Checking isort formatting..."
	$(VENV_DIR)/bin/isort --check-only scripts/

security: install-dev ## Run security checks
	@echo "Running bandit security scan..."
	$(VENV_DIR)/bin/bandit -r scripts/ -f json -o security-report.json
	@echo "Running safety check..."
	$(VENV_DIR)/bin/safety check --json --output safety-report.json
	@echo "Security scan complete! ✅"
	@echo "📊 Security Summary:"
	@if [ -f security-report.json ]; then \
		echo "  - Bandit report generated: security-report.json"; \
		echo "  - Review for any high/medium severity issues"; \
	else \
		echo "  - No security report generated"; \
	fi
	@if [ -f safety-report.json ]; then \
		echo "  - Safety report generated: safety-report.json"; \
		echo "  - Review for any vulnerable dependencies"; \
	else \
		echo "  - No safety report generated"; \
	fi

## Pre-commit Targets
# Pre-commit
pre-commit: install-dev ## Run pre-commit hooks
	$(VENV_DIR)/bin/pre-commit run --all-files
	@echo "Pre-commit hooks complete! ✅"

pre-commit-update: install-dev ## Update pre-commit hooks
	$(VENV_DIR)/bin/pre-commit autoupdate
	@echo "Pre-commit hooks updated! ✅"

## Project Health Targets
# Project Health
check: install-dev format-check lint test ## Run all quality checks
	@echo "All checks passed! ✅"

quality-check: install-dev format-check lint test-cov security ## Run comprehensive quality checks
	@echo "Comprehensive quality checks passed! ✅"

performance-test: install-dev ## Run performance benchmarks
	$(VENV_DIR)/bin/pytest tests/test_performance.py --benchmark-only --benchmark-json=benchmark-results.json

health-check: install-dev ## Run inventory health check
	@echo "Running inventory health check..."
	$(VENV_PYTHON) scripts/ansible_inventory_cli.py health
	@echo "Health check complete! ✅"

validate: ## Validate inventory structure
	@echo "Validating inventory structure..."
	ansible-inventory --inventory inventory/production.yml --list > /dev/null
	ansible-inventory --inventory inventory/development.yml --list > /dev/null
	ansible-inventory --inventory inventory/test.yml --list > /dev/null
	ansible-inventory --inventory inventory/acceptance.yml --list > /dev/null
	@echo "Inventory validation complete! ✅"

## Build and Distribution Targets
# Build and Distribution
clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf security-report.json
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "Build artifacts cleaned! ✅"

build: install-dev clean ## Build distribution packages
	$(VENV_PYTHON) -m build
	@echo "Build complete! ✅"

build-wheel: install-dev clean ## Build wheel package only
	$(VENV_PYTHON) -m build --wheel
	@echo "Wheel build complete! ✅"

## Development Environment Targets
# Development Environment
setup-dev: python-check ## Set up development environment (RHEL9 optimized)
	@echo "Setting up development environment for RHEL9..."
	$(PYTHON3) -m venv $(VENV_DIR)
	@echo "Virtual environment created. Activate with: source $(VENV_DIR)/bin/activate"
	@echo "Then run: make install-dev"

check-dependencies: ## Check if all required dependencies are installed
	@echo "🔍 Checking dependencies..."
	@$(VENV_PYTHON) -c "import sys; print(f'Python version: {sys.version}')"
	@$(VENV_PYTHON) -c "import pytest; print('✅ pytest installed')" || echo "❌ pytest missing - run 'make install-dev'"
	@$(VENV_PYTHON) -c "import black; print('✅ black installed')" || echo "❌ black missing - run 'make install-dev'"
	@$(VENV_PYTHON) -c "import flake8; print('✅ flake8 installed')" || echo "❌ flake8 missing - run 'make install-dev'"
	@$(VENV_PYTHON) -c "import yaml; print('✅ PyYAML installed')" || echo "❌ PyYAML missing - run 'make install-dev'"
	@$(VENV_PYTHON) -c "import memory_profiler; print('✅ memory_profiler installed')" || echo "❌ memory_profiler missing - run 'make install-dev'"
	@$(VENV_PYTHON) -c "import xdist; print('✅ pytest-xdist installed')" || echo "❌ pytest-xdist missing - run 'make install-dev'"
	@$(VENV_PYTHON) -c "import pytest_benchmark; print('✅ pytest-benchmark installed')" || echo "❌ pytest-benchmark missing - run 'make install-dev'"
	@$(VENV_DIR)/bin/yamllint --version > /dev/null && echo "✅ yamllint installed" || echo "❌ yamllint missing - run 'make install-dev'"
	@which ansible > /dev/null && echo "✅ ansible installed" || echo "❌ ansible missing - install with 'dnf install ansible-core' (RHEL9) or 'pip install ansible'"
	@echo "Dependency check complete! ✅"

quickstart: ## Complete setup for new junior users
	@echo "🚀 QUICKSTART - Setting up Ansible Inventory CLI for new users"
	@echo "================================================================"
	@echo ""
	@echo "Step 1: Installing dependencies..."
	@$(MAKE) install-dev
	@echo ""
	@echo "Step 2: Checking dependencies..."
	@$(MAKE) check-dependencies
	@echo ""
	@echo "Step 3: Running basic validation..."
	@$(MAKE) validate
	@echo ""
	@echo "Step 4: Running health check..."
	@$(MAKE) health-check
	@echo ""
	@echo "Step 5: Formatting code..."
	@$(MAKE) format
	@echo ""
	@echo "Step 6: Running tests..."
	@$(MAKE) test
	@echo ""
	@echo "🎉 QUICKSTART COMPLETE!"
	@echo "======================"
	@echo ""
	@echo "Next steps:"
	@echo "  • Run 'make help' to see all available commands"
	@echo "  • Run 'make generate-dry-run' to see what inventory would be generated"
	@echo "  • Run 'make generate' to generate inventory from CSV"
	@echo "  • Run 'make lint' to check code quality"
	@echo "  • Run 'make test-cov' to run tests with coverage"
	@echo ""
	@echo "Documentation: Check the docs/ directory for detailed guides"

## Ansible and Inventory Targets
# Ansible specific commands
ansible-check: ## Check Ansible playbook syntax
	@echo "Checking Ansible configuration..."
	ansible --version
	ansible-config dump --only-changed
	@echo "Ansible check complete! ✅"

generate: install-dev ## Generate inventory from CSV (auto-cleans orphaned files)
	@echo "Generating inventory from CSV..."
	@echo "Note: Orphaned host_vars files will be automatically cleaned up"
	$(VENV_PYTHON) scripts/ansible_inventory_cli.py generate
	@echo "Inventory generation complete! ✅"

generate-fresh: install-dev ## Remove ALL host_vars and regenerate from CSV (DESTRUCTIVE)
	@echo "⚠️  WARNING: This will remove ALL host_vars files and regenerate from CSV"
	@read -p "Are you sure? [y/N]: " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo "Removing all host_vars files..."
	rm -rf inventory/host_vars/*
	@echo "Generating fresh inventory from CSV..."
	$(VENV_PYTHON) scripts/ansible_inventory_cli.py generate
	@echo "Fresh inventory generation complete! ✅"

generate-dry-run: install-dev ## Generate inventory from CSV (dry run)
	@echo "Generating inventory from CSV (dry run)..."
	$(VENV_PYTHON) scripts/ansible_inventory_cli.py generate --dry-run
	@echo "Dry run complete! ✅"

inventory-stats: install-dev ## Show inventory statistics
	@echo "Inventory Statistics:"
	@echo "===================="
	$(VENV_PYTHON) scripts/ansible_inventory_cli.py health

csv-backup: ## Create CSV backup
	@echo "Creating CSV backup..."
	cp inventory_source/hosts.csv inventory_source/hosts_$(shell date +%Y%m%d_%H%M%S).backup
	@echo "Backup created! ✅"

# Inventory import functionality
import-dry-run: install-dev ## Test import of external inventory (requires INVENTORY_FILE)
	@if [ -z "$(INVENTORY_FILE)" ]; then \
		echo "Usage: make import-dry-run INVENTORY_FILE=/path/to/inventory.yml"; \
		exit 1; \
	fi
	$(VENV_PYTHON) scripts/ansible_inventory_cli.py import --inventory-file "$(INVENTORY_FILE)" --dry-run

import-inventory: install-dev ## Import external inventory (requires INVENTORY_FILE)
	@if [ -z "$(INVENTORY_FILE)" ]; then \
		echo "Usage: make import-inventory INVENTORY_FILE=/path/to/inventory.yml"; \
		echo "Optional: make import-inventory INVENTORY_FILE=/path/to/inventory.yml HOST_VARS_DIR=/path/to/host_vars/"; \
		exit 1; \
	fi
	@echo "⚠️  WARNING: This will create a new CSV file with imported inventory data"
	@echo "Make sure to backup your existing CSV first!"
	@read -p "Continue? [y/N]: " confirm && [ "$$confirm" = "y" ] || exit 1
	$(VENV_PYTHON) scripts/ansible_inventory_cli.py import --inventory-file "$(INVENTORY_FILE)" $(if $(HOST_VARS_DIR),--host-vars-dir "$(HOST_VARS_DIR)")

import-help: ## Show import usage examples
	@echo "🔄 INVENTORY IMPORT COMMANDS"
	@echo "============================"
	@echo ""
	@echo "Test import (dry run):"
	@echo "  make import-dry-run INVENTORY_FILE=/path/to/existing/inventory.yml"
	@echo ""
	@echo "Import with host_vars:"
	@echo "  make import-inventory INVENTORY_FILE=/path/to/inventory.yml HOST_VARS_DIR=/path/to/host_vars/"
	@echo ""
	@echo "Direct command usage:"
	@echo "  $(VENV_PYTHON) scripts/ansible_inventory_cli.py import --help"
	@echo "  $(VENV_PYTHON) scripts/inventory_import.py --help"

## CI/CD Targets
# CI/CD helpers
ci-install: ## Install for CI environment
	$(VENV_PIP) install -e ".[dev,test]"

ci-test: ## Run tests in CI environment
	$(VENV_DIR)/bin/pytest --cov=scripts --cov-report=xml --cov-report=term-missing -v

ci-lint: ## Run linting in CI environment
	$(VENV_DIR)/bin/flake8 scripts/ --output-file=flake8-report.txt
	$(VENV_DIR)/bin/mypy scripts/ --xml-report=mypy-report
	$(VENV_DIR)/bin/bandit -r scripts/ -f json -o bandit-report.json

## Version and Backup Targets
# Version management
version: install-dev ## Show current version
	@$(VENV_PYTHON) -c "import scripts.core.config as config; print(f'Version: {getattr(config, \"VERSION\", \"unknown\")}')"

# Database/CSV operations
backup-all: ## Backup all important files
	@echo "Creating comprehensive backup..."
	cp inventory_source/hosts.csv inventory_source/hosts_$(shell date +%Y%m%d_%H%M%S).backup
	@echo "Backup complete! ✅"

# Performance testing
perf-test: install-dev ## Run performance tests
	@echo "Running performance tests..."
	timeout 300 time $(VENV_PYTHON) scripts/ansible_inventory_cli.py health || echo "Timeout occurred"
	@echo "Profiling memory usage..."
	$(VENV_DIR)/bin/mprof run $(VENV_PYTHON) scripts/ansible_inventory_cli.py health
	@echo "Performance test complete! ⚡"

# Documentation checks
docs-check: ## Run spell and style checks on documentation
	@echo "Running cspell on markdown files..."
	cspell --no-progress "**/*.md"
	@echo "Running vale style check..."
	vale --minAlertLevel=error .
	@echo "Documentation checks complete! ✅"

# Watch targets
watch: install-dev ## Watch for changes in CSV and regenerate inventory
	@echo "Watching for changes in inventory_source/hosts.csv..."
	@ls inventory_source/hosts.csv | entr make generate

## Container Management (Podman) - RHEL9 Default
podman-build: ## Build Podman image (RHEL9 optimized)
	podman build -t ansible-inventory-cli .

podman-run: ## Run Podman container
	podman run -v $(PWD)/inventory:/inventory ansible-inventory-cli

podman-test: ## Run tests in Podman container
	podman run ansible-inventory-cli make test

## RHEL9 System Integration
rhel9-install-system-deps: ## Install system dependencies on RHEL9
	@echo "Installing RHEL9 system dependencies..."
	@echo "Note: This requires sudo privileges"
	sudo dnf install -y python3 python3-pip python3-venv python3-devel
	sudo dnf install -y ansible-core
	@echo "RHEL9 system dependencies installed! ✅"

rhel9-setup: rhel9-install-system-deps setup-dev ## Complete RHEL9 setup
	@echo "🎯 RHEL9 setup complete!"
	@echo "Python3 version: $(shell $(PYTHON3) --version)"
	@echo "Virtual environment: $(VENV_DIR)"
	@echo "Ready to run: make install-dev"
