# Makefile for Ansible Inventory CLI
# =================================

.PHONY: help install install-dev test test-cov lint format security clean build pre-commit check health-check

# Default target
help:
	@echo ""
	@echo "Ansible Inventory CLI - Makefile Commands"
	@echo "========================================="
	@echo ""
	@echo "🚀 Quick Start (for new users):"
	@echo "  check-dependencies   Check if all required dependencies are installed"
	@echo "  setup-dev            Set up development environment"
	@echo "  install-dev          Install development dependencies"
	@echo "  quickstart           Complete setup for new users"
	@echo ""
	@echo "Inventory Management:"
	@echo "  generate             Generate inventory from CSV (safe, cleans up only obsolete host_vars)"
	@echo "  generate-dry-run     Show what would be generated (dry run)"
	@echo "  generate-fresh       Delete ALL host_vars and regenerate from CSV (destructive, use rarely)"
	@echo ""
	@echo "Validation & Health:"
	@echo "  validate             Validate inventory structure"
	@echo "  health-check         Run inventory health check"
	@echo ""
	@echo "Development & Quality:"
	@echo "  install              Install the package"
	@echo "  install-dev          Install development dependencies"
	@echo "  lint                 Run all linting tools"
	@echo "  format               Format code with black and isort"
	@echo "  test                 Run tests"
	@echo "  test-cov             Run tests with coverage"
	@echo "  test-all             Run all tests with coverage threshold"
	@echo "  test-unit            Run unit tests only"
	@echo "  test-integration     Run integration tests only"
	@echo "  test-e2e             Run end-to-end tests only"
	@echo "  test-performance     Run performance tests only"
	@echo "  test-security        Run security tests only"
	@echo "  test-existing        Run existing tests only"
	@echo "  test-parallel        Run tests in parallel"
	@echo "  test-markers         Show available test markers"
	@echo "  test-clean           Clean test artifacts"
	@echo "  security             Run security checks"
	@echo "  check                Run all quality checks"
	@echo "  quality-check        Run comprehensive quality checks"
	@echo "  performance-test     Run performance benchmarks"
	@echo "  clean                Clean build artifacts"
	@echo ""
	@echo "CI/CD:"
	@echo "  ci-install           Install for CI environment"
	@echo "  ci-test              Run tests in CI environment"
	@echo ""

# Installation (using pyproject.toml as single source of truth)
install: ## Install the package
	.venv/bin/python3 -m pip install -e .

install-dev: ## Install development dependencies
	.venv/bin/python3 -m pip install -e ".[dev,test,docs]"
	.venv/bin/pre-commit install

# Testing
test: ## Run tests
	.venv/bin/pytest -v

test-cov: ## Run tests with coverage
	.venv/bin/pytest --cov=scripts --cov-report=html --cov-report=term-missing --cov-report=xml -v

test-unit: ## Run unit tests only
	.venv/bin/pytest tests/ -m "unit" -v

test-integration: ## Run integration tests only
	.venv/bin/pytest tests/ -m "integration" -v

test-e2e: ## Run end-to-end tests only
	.venv/bin/pytest tests/ -m "e2e" -v

test-performance: ## Run performance tests only
	.venv/bin/pytest tests/test_performance.py -v

test-security: ## Run security tests only
	.venv/bin/pytest tests/test_security.py -v

test-existing: ## Run existing tests only
	.venv/bin/pytest tests/test_edge_cases.py tests/test_host_manager.py tests/test_instance_validation.py tests/test_inventory_generation.py -v

test-all: ## Run all tests with coverage and fail if below threshold
	.venv/bin/pytest tests/ --cov=scripts --cov-report=html --cov-report=xml --cov-report=term-missing --cov-fail-under=80 -v

test-parallel: ## Run tests in parallel
	.venv/bin/pytest tests/ -n auto -v

test-markers: ## Show available test markers
	@echo "Available test markers:"
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

# Code Quality
lint: ## Run all linting tools
	@echo "Running flake8..."
	.venv/bin/flake8 scripts/
	@echo "Running mypy..."
	.venv/bin/mypy scripts/
	@echo "Running bandit..."
	.venv/bin/bandit -r scripts/
	@echo "Running yamllint..."
	.venv/bin/yamllint inventory/ ansible.cfg

format: ## Format code with black and isort
	@echo "Running black..."
	.venv/bin/black scripts/
	@echo "Running isort..."
	.venv/bin/isort scripts/

format-check: ## Check if code is properly formatted
	@echo "Checking black formatting..."
	.venv/bin/black --check scripts/
	@echo "Checking isort formatting..."
	.venv/bin/isort --check-only scripts/

security: ## Run security checks
	@echo "Running bandit security scan..."
	.venv/bin/bandit -r scripts/ -f json -o security-report.json || true
	@echo "Running safety check..."
	.venv/bin/safety check --json --output safety-report.json || true
	@echo "Security scan complete!"
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

# Pre-commit
pre-commit: ## Run pre-commit hooks
	.venv/bin/pre-commit run --all-files

pre-commit-update: ## Update pre-commit hooks
	.venv/bin/pre-commit autoupdate

# Project Health
check: format-check lint test ## Run all quality checks
	@echo "All checks passed! ✅"

quality-check: format-check lint test-cov security ## Run comprehensive quality checks
	@echo "Comprehensive quality checks passed! ✅"

performance-test: ## Run performance benchmarks
	.venv/bin/pytest tests/test_performance.py --benchmark-only --benchmark-json=benchmark-results.json || true

health-check: ## Run inventory health check
	@echo "Running inventory health check..."
	.venv/bin/python3 scripts/ansible_inventory_cli.py health

validate: ## Validate inventory structure
	@echo "Validating inventory structure..."
	ansible-inventory --inventory inventory/production.yml --list > /dev/null
	ansible-inventory --inventory inventory/development.yml --list > /dev/null
	ansible-inventory --inventory inventory/test.yml --list > /dev/null
	ansible-inventory --inventory inventory/acceptance.yml --list > /dev/null
	@echo "Inventory validation complete! ✅"

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

build: clean ## Build distribution packages
	.venv/bin/python3 -m build

build-wheel: clean ## Build wheel package only
	.venv/bin/python3 -m build --wheel

# Development Environment
setup-dev: ## Set up development environment
	@echo "Setting up development environment..."
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv .venv; \
		echo "Virtual environment created at .venv/"; \
	else \
		echo "Virtual environment already exists at .venv/"; \
	fi
	@echo "Run: make install-dev"

check-dependencies: ## Check if all required dependencies are installed
	@echo "🔍 Checking dependencies..."
	@.venv/bin/python3 -c "import sys; print(f'Python version: {sys.version}')"
	@.venv/bin/python3 -c "import pytest; print('✅ pytest installed')" || echo "❌ pytest missing - run 'make install-dev'"
	@.venv/bin/python3 -c "import black; print('✅ black installed')" || echo "❌ black missing - run 'make install-dev'"
	@.venv/bin/python3 -c "import flake8; print('✅ flake8 installed')" || echo "❌ flake8 missing - run 'make install-dev'"
	@.venv/bin/python3 -c "import yaml; print('✅ PyYAML installed')" || echo "❌ PyYAML missing - run 'make install-dev'"
	@.venv/bin/python3 -c "import memory_profiler; print('✅ memory_profiler installed')" || echo "❌ memory_profiler missing - run 'make install-dev'"
	@.venv/bin/python3 -c "import xdist; print('✅ pytest-xdist installed')" || echo "❌ pytest-xdist missing - run 'make install-dev'"
	@.venv/bin/python3 -c "import pytest_benchmark; print('✅ pytest-benchmark installed')" || echo "❌ pytest-benchmark missing - run 'make install-dev'"
	@.venv/bin/yamllint --version > /dev/null && echo "✅ yamllint installed" || echo "❌ yamllint missing - run 'make install-dev'"
	@which ansible > /dev/null && echo "✅ ansible installed" || echo "❌ ansible missing - install with 'pip install ansible'"
	@echo "✅ Dependency check complete!"

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

# Ansible specific commands
ansible-check: ## Check Ansible playbook syntax
	@echo "Checking Ansible configuration..."
	ansible --version
	ansible-config dump --only-changed
	@echo "Ansible check complete! ✅"

generate: ## Generate inventory from CSV (auto-cleans orphaned files)
	@echo "Generating inventory from CSV..."
	@echo "Note: Orphaned host_vars files will be automatically cleaned up"
	.venv/bin/python3 scripts/ansible_inventory_cli.py generate
	@echo "Inventory generation complete! ✅"

generate-fresh: ## Remove ALL host_vars and regenerate from CSV (DESTRUCTIVE)
	@echo "⚠️  WARNING: This will remove ALL host_vars files and regenerate from CSV"
	@read -p "Are you sure? [y/N]: " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo "Removing all host_vars files..."
	rm -rf inventory/host_vars/*
	@echo "Generating fresh inventory from CSV..."
	.venv/bin/python3 scripts/ansible_inventory_cli.py generate
	@echo "Fresh inventory generation complete! ✅"

generate-dry-run: ## Generate inventory from CSV (dry run)
	@echo "Generating inventory from CSV (dry run)..."
	.venv/bin/python3 scripts/ansible_inventory_cli.py generate --dry-run
	@echo "Dry run complete! ✅"

inventory-stats: ## Show inventory statistics
	@echo "Inventory Statistics:"
	@echo "===================="
	.venv/bin/python3 scripts/ansible_inventory_cli.py health

csv-backup: ## Create CSV backup
	@echo "Creating CSV backup..."
	cp inventory_source/hosts.csv inventory_source/hosts_$(shell date +%Y%m%d_%H%M%S).backup
	@echo "Backup created! 💾"

# Inventory import functionality
import-dry-run: ## Test import of external inventory (requires INVENTORY_FILE)
	@if [ -z "$(INVENTORY_FILE)" ]; then \
		echo "Usage: make import-dry-run INVENTORY_FILE=/path/to/inventory.yml"; \
		exit 1; \
	fi
	.venv/bin/python3 scripts/ansible_inventory_cli.py import --inventory-file "$(INVENTORY_FILE)" --dry-run

import-inventory: ## Import external inventory (requires INVENTORY_FILE)
	@if [ -z "$(INVENTORY_FILE)" ]; then \
		echo "Usage: make import-inventory INVENTORY_FILE=/path/to/inventory.yml"; \
		echo "Optional: make import-inventory INVENTORY_FILE=/path/to/inventory.yml HOST_VARS_DIR=/path/to/host_vars/"; \
		exit 1; \
	fi
	@echo "⚠️  WARNING: This will create a new CSV file with imported inventory data"
	@echo "Make sure to backup your existing CSV first!"
	@read -p "Continue? [y/N]: " confirm && [ "$$confirm" = "y" ] || exit 1
	.venv/bin/python3 scripts/ansible_inventory_cli.py import --inventory-file "$(INVENTORY_FILE)" $(if $(HOST_VARS_DIR),--host-vars-dir "$(HOST_VARS_DIR)")

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
	@echo "  .venv/bin/python3 scripts/ansible_inventory_cli.py import --help"
	@echo "  .venv/bin/python3 scripts/inventory_import.py --help"

# CI/CD helpers
ci-install: ## Install for CI environment
	.venv/bin/python3 -m pip install -e ".[dev,test]"

ci-test: ## Run tests in CI environment
	.venv/bin/pytest --cov=scripts --cov-report=xml --cov-report=term-missing -v

ci-lint: ## Run linting in CI environment
	.venv/bin/flake8 scripts/ --output-file=flake8-report.txt
	.venv/bin/mypy scripts/ --xml-report=mypy-report
	.venv/bin/bandit -r scripts/ -f json -o bandit-report.json

# Version management
version: ## Show current version
	@.venv/bin/python3 -c "import scripts.core.config as config; print(f'Version: {getattr(config, \"VERSION\", \"unknown\")}')"

# Database/CSV operations
backup-all: ## Backup all important files
	@echo "Creating comprehensive backup..."
	cp inventory_source/hosts.csv inventory_source/hosts_$(shell date +%Y%m%d_%H%M%S).backup
	@echo "Backup complete! 💾"

# Performance testing
perf-test: ## Run performance tests
	@echo "Running performance tests..."
	time .venv/bin/python3 scripts/ansible_inventory_cli.py health
	@echo "Performance test complete! ⚡"
