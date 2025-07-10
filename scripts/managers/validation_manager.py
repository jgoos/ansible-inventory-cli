#!/usr/bin/env python3
"""
Validation manager - health and validation operations.

Handles comprehensive validation of inventory structure, data consistency,
and health monitoring with scoring and recommendations.
"""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ..core import get_logger  # noqa: E402
from ..core.config import CSV_FILE  # noqa: E402
from ..core.models import InventoryConfig, ValidationResult  # noqa: E402
from .inventory_manager import InventoryManager  # noqa: E402


class ValidationManager:
    """Manages comprehensive validation operations and health monitoring."""

    def __init__(
        self, csv_file: Optional[Path] = None, logger: Optional[Any] = None
    ) -> None:
        """Initialise the validation manager."""
        self.csv_file: Path = csv_file if csv_file is not None else CSV_FILE
        self.logger = logger if logger else get_logger(__name__)
        self.config = InventoryConfig.create_default()
        self.inventory_manager = InventoryManager(self.csv_file, self.logger)
        self.env_counts: Dict[str, int] = {}

        self.logger.info("Validation Manager initialized")

    def validate_structure(self) -> Dict[str, Any]:
        """Validate inventory structure and configuration."""
        self.logger.info("Starting infrastructure validation")

        validation = ValidationResult()
        issues = []
        warnings = []

        # Directory structure validation
        required_dirs = [
            self.config.inventory_dir,
            self.config.group_vars_dir,
            self.config.host_vars_dir,
        ]
        for dir_path in required_dirs:
            if not dir_path.exists():
                issues.append(f"Missing directory: {dir_path}")
                validation.add_error(f"Missing directory: {dir_path}")
            else:
                self.logger.debug(f"Directory verified: {dir_path}")

        # Environment configuration validation
        for env in self.config.environments:
            env_file = self.config.group_vars_dir / f"env_{env}.yml"
            if not env_file.exists():
                warnings.append(f"Environment file not found: {env_file}")
                validation.add_warning(f"Environment file not found: {env_file}")
            else:
                try:
                    with env_file.open("r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if not data:
                            validation.add_warning(f"env_{env}.yml is empty")
                except Exception as e:
                    validation.add_error(f"YAML error in {env_file}: {e}")

        # CSV validation
        try:
            hosts = self.inventory_manager.load_hosts()
            self.logger.info(f"CSV validation passed: {len(hosts)} hosts loaded")
        except Exception as e:
            validation.add_error(f"CSV validation failed: {e}")

        # Ansible validation (optional)
        ansible_version = self._check_ansible()

        return {
            "passed": validation.is_valid,
            "issues": issues,
            "warnings": warnings,
            "summary": validation.get_summary(),
            "total_errors": len(validation.errors),
            "total_warnings": len(validation.warnings),
            "ansible_version": ansible_version,
        }

    def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health monitoring."""
        self.logger.info("Starting health monitoring")

        # Load hosts and find orphaned files
        hosts = self.inventory_manager.load_hosts()
        csv_identifiers = set()

        # Collect all possible identifiers (both hostnames and cnames)
        for host in hosts:
            if host.hostname:
                csv_identifiers.add(host.hostname)
            if host.cname:
                csv_identifiers.add(host.cname)

        orphaned_host_vars = []
        if self.config.host_vars_dir.exists():
            for file_path in self.config.host_vars_dir.glob("*.yml"):
                identifier = file_path.stem
                if identifier not in csv_identifiers:
                    orphaned_host_vars.append(identifier)

        missing_host_vars = []
        active_hosts = [h for h in hosts if h.is_active]
        for host in active_hosts:
            # Check for host_vars file using the inventory key
            inventory_key_value = host.get_inventory_key_value(
                self.inventory_manager.config.inventory_key
            )
            host_var_file = self.config.host_vars_dir / f"{inventory_key_value}.yml"
            if not host_var_file.exists():
                missing_host_vars.append(inventory_key_value)

        # Calculate health score
        total_active = len(active_hosts)
        orphaned_count = len(orphaned_host_vars)
        missing_count = len(missing_host_vars)

        if total_active == 0:
            health_score = 0.0
        else:
            # Base score from coverage
            coverage_score = max(0, (total_active - missing_count) / total_active * 100)
            # Penalty for orphaned files
            orphaned_penalty = min(orphaned_count * 2, 20)
            health_score = max(0, coverage_score - orphaned_penalty)

        # Health classification
        if health_score >= 95:
            health_status = "EXCELLENT"
        elif health_score >= 85:
            health_status = "GOOD"
        elif health_score >= 70:
            health_status = "FAIR"
        elif health_score >= 50:
            health_status = "POOR"
        else:
            health_status = "CRITICAL"

        return {
            "health_score": round(health_score, 1),
            "health_status": health_status,
            "total_hosts": len(hosts),
            "active_hosts": total_active,
            "orphaned_host_vars": orphaned_count,
            "missing_host_vars": missing_count,
            "orphaned_files": orphaned_host_vars[:5],  # Show first 5 examples
            "missing_files": missing_host_vars[:5],  # Show first 5 examples
            "recommendations": self._generate_health_recommendations(
                health_score, orphaned_count, missing_count
            ),
        }

    def validate_csv_data(self) -> ValidationResult:
        """Validate CSV data for consistency and completeness."""
        validation = ValidationResult()

        try:
            hosts = self.inventory_manager.load_hosts()

            # Check for duplicate hostnames
            hostnames = [host.hostname for host in hosts if host.hostname]
            duplicates = {name for name in hostnames if hostnames.count(name) > 1}
            if duplicates:
                validation.add_error(
                    f"Duplicate hostnames found: {', '.join(duplicates)}"
                )

            # Check for invalid environments
            invalid_envs = set()
            for host in hosts:
                if host.environment not in self.config.environments:
                    invalid_envs.add(host.environment)
            if invalid_envs:
                validation.add_error(
                    f"Invalid environments found: {', '.join(invalid_envs)}"
                )

            # Check for missing required fields
            missing_fields = []
            for host in hosts:
                if not host.hostname:
                    missing_fields.append("hostname")
                if not host.environment:
                    missing_fields.append("environment")
            if missing_fields:
                validation.add_warning(
                    f"Missing required fields: {', '.join(set(missing_fields))}"
                )

            # Environment distribution check
            env_counts: Dict[str, int] = {}
            # Initialize all configured environments with 0
            for env in self.config.environments:
                env_counts[env] = 0

            # Count hosts per environment
            for host in hosts:
                if host.environment in env_counts:
                    env_counts[host.environment] += 1

            for env, count in env_counts.items():
                if count == 0:
                    validation.add_warning(f"No hosts found for environment: {env}")
                elif count > 100:
                    validation.add_warning(f"Large number of hosts in {env}: {count}")

            self.logger.info(f"CSV validation completed: {len(hosts)} hosts validated")

        except Exception as e:
            validation.add_error(f"CSV validation failed: {e}")

        return validation

    def validate_host_vars_consistency(self) -> ValidationResult:
        """Validate that host_vars files match CSV data."""
        validation = ValidationResult()

        try:
            hosts = self.inventory_manager.load_hosts()
            csv_identifiers = set()

            # Collect all possible identifiers (both hostnames and cnames)
            for host in hosts:
                if host.hostname:
                    csv_identifiers.add(host.hostname)
                if host.cname:
                    csv_identifiers.add(host.cname)

            # Check for orphaned host_vars files
            if self.config.host_vars_dir.exists():
                for file_path in self.config.host_vars_dir.glob("*.yml"):
                    identifier = file_path.stem
                    if identifier not in csv_identifiers:
                        validation.add_warning(
                            f"Orphaned host_vars file: {identifier}.yml"
                        )

            # Check for missing host_vars files
            active_hosts = [h for h in hosts if h.is_active]
            for host in active_hosts:
                # Check using the inventory key
                inventory_key_value = host.get_inventory_key_value(
                    self.inventory_manager.config.inventory_key
                )
                host_var_file = self.config.host_vars_dir / f"{inventory_key_value}.yml"
                if not host_var_file.exists():
                    validation.add_warning(
                        f"Missing host_vars file: {inventory_key_value}.yml"
                    )
                else:
                    # Validate YAML syntax
                    try:
                        with host_var_file.open("r", encoding="utf-8") as f:
                            yaml.safe_load(f)
                    except yaml.YAMLError as e:
                        validation.add_error(
                            f"YAML error in {inventory_key_value}.yml: {e}"
                        )

        except Exception as e:
            validation.add_error(f"Host vars validation failed: {e}")

        return validation

    def _check_ansible(self) -> Optional[str]:
        """Check if Ansible is available and get version.

        Returns:
            Ansible version string or None if not available
        """
        try:
            # Use absolute path for ansible for security
            ansible_path = shutil.which("ansible")
            if not ansible_path:
                self.logger.debug("Ansible not found in PATH")
                return None

            # Run ansible --version with timeout
            result = subprocess.run(
                [ansible_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode == 0:
                # Extract version from first line
                version_line = result.stdout.split("\n")[0] if result.stdout else ""
                self.logger.debug(f"Found Ansible: {version_line}")
                return version_line
            else:
                self.logger.warning(
                    f"Ansible check failed with exit code {result.returncode}: "
                    f"{result.stderr[:100]}"
                )
                return None

        except subprocess.TimeoutExpired:
            self.logger.warning("Ansible version check timed out")
            return None
        except OSError as e:
            self.logger.debug(f"Could not check Ansible version: {e}")
            return None
        except Exception as e:
            self.logger.warning(f"Unexpected error checking Ansible: {e}")
            return None

    def _generate_health_recommendations(
        self, score: float, orphaned: int, missing: int
    ) -> List[str]:
        """Generate actionable health recommendations."""
        recommendations = []

        if missing > 0:
            recommendations.append(
                f"Generate missing host_vars for {missing} hosts: python scripts/ansible_inventory_cli.py generate"
            )

        if orphaned > 0:
            recommendations.append(
                f"Clean up {orphaned} orphaned host_vars files: python scripts/ansible_inventory_cli.py lifecycle cleanup"
            )

        if score < 85:
            recommendations.append("Review inventory maintenance procedures")

        if score >= 95:
            recommendations.append(
                "✅ Inventory health is excellent - no action required"
            )

        return recommendations
