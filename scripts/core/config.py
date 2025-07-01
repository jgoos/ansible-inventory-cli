#!/usr/bin/env python3
"""
Centralized Configuration for Ansible Inventory Management Scripts

This module loads configuration from inventory-config.yml and provides
backward-compatible access to all configuration values. Environment
variables can override YAML settings.
"""

import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# Version information (fallback if not in YAML)
VERSION: str = "2.0.0"

# Project structure - find project root
PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
SCRIPT_DIR: Path = Path(__file__).parent.parent

# Configuration file path
CONFIG_FILE: Path = PROJECT_ROOT / "inventory-config.yml"

# Global configuration cache
_config_cache: Optional[Dict[str, Any]] = None
_config_lock = threading.Lock()


def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file with caching."""
    global _config_cache

    if _config_cache is not None:
        return _config_cache

    with _config_lock:
        if _config_cache is not None:
            return _config_cache

        # Minimal essential defaults (only for critical functionality)
        # Most configuration should be in inventory-config.yml
        minimal_defaults = {
            "version": "2.0.0",
            "paths": {
                "project_root": ".",
                "inventory_source": "inventory_source",
                "inventory": "inventory",
                "host_vars": "inventory/host_vars",
                "group_vars": "inventory/group_vars",
                "backups": "backups",
                "logs": "logs"
            },
            "data": {
                "csv_file": "inventory_source/hosts.csv"
            },
            "environments": {
                "supported": ["production", "development", "test", "acceptance"]
            },
            "hosts": {
                "valid_status_values": ["active", "decommissioned"],
                "default_status": "active",
                "inventory_key": "hostname"
            },
            "logging": {
                "level": "INFO"
            }
        }

        # Try to load from YAML file
        if CONFIG_FILE.exists():
            try:
                with CONFIG_FILE.open("r", encoding="utf-8") as f:
                    yaml_config = yaml.safe_load(f) or {}
                    # Merge with minimal defaults (YAML overrides defaults)
                    config = _deep_merge(minimal_defaults, yaml_config)
            except Exception as e:
                print(f"Warning: Failed to load {CONFIG_FILE}: {e}")
                print("Using minimal defaults - some features may not work correctly")
                config = minimal_defaults
        else:
            print(f"Warning: Configuration file {CONFIG_FILE} not found")
            print("Please copy inventory-config.yml.example to inventory-config.yml")
            print("Using minimal defaults - some features may not work correctly")
            config = minimal_defaults

        # Apply environment variable overrides
        config = _apply_env_overrides(config)

        _config_cache = config
        return config


def _deep_merge(default: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries, with override taking precedence."""
    result = default.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply environment variable overrides to configuration."""
    # Common environment variable overrides
    env_mappings = {
        "INVENTORY_CSV_FILE": ("data", "csv_file"),
        "INVENTORY_LOG_LEVEL": ("logging", "level"),
        "INVENTORY_KEY": ("hosts", "inventory_key"),
        "INVENTORY_DEFAULT_STATUS": ("hosts", "default_status"),
        "INVENTORY_SUPPORT_GROUP": ("cmdb", "default_support_group"),
    }

    for env_var, (section, key) in env_mappings.items():
        value = os.getenv(env_var)
        if value is not None:
            if section not in config:
                config[section] = {}
            config[section][key] = value

    return config


def get_config() -> Dict[str, Any]:
    """Get the current configuration."""
    return load_config()


def reload_config() -> Dict[str, Any]:
    """Force reload configuration from file."""
    global _config_cache
    _config_cache = None
    return load_config()


# Load configuration once at module import
_config = load_config()

# Backward compatibility - export all original constants
# These maintain the exact same interface as before
# Values come from YAML file with minimal fallbacks

# Version information
VERSION = _config.get("version", "2.0.0")

# Logging configuration
LOG_LEVEL = _config.get("logging", {}).get("level", "INFO")

# Core paths
INVENTORY_SOURCE_DIR = PROJECT_ROOT / _config.get("paths", {}).get("inventory_source", "inventory_source")
INVENTORY_DIR = PROJECT_ROOT / _config.get("paths", {}).get("inventory", "inventory")
HOST_VARS_DIR = INVENTORY_DIR / "host_vars"
GROUP_VARS_DIR = INVENTORY_DIR / "group_vars"
BACKUP_DIR = PROJECT_ROOT / _config.get("paths", {}).get("backups", "backups")

# Primary data file
CSV_FILE = PROJECT_ROOT / _config.get("data", {}).get("csv_file", "inventory_source/hosts.csv")

# File patterns and extensions (with minimal fallbacks)
YAML_EXTENSION = _config.get("formats", {}).get("yaml_extension", ".yml")
BACKUP_EXTENSION = _config.get("formats", {}).get("backup_extension", ".backup")
CSV_EXTENSION = _config.get("formats", {}).get("csv_extension", ".csv")

# Environment configuration
ENVIRONMENTS = _config.get("environments", {}).get("supported", ["production", "development", "test", "acceptance"])
ENVIRONMENT_CODES = _config.get("environments", {}).get("codes", {
    "production": "prd", "development": "dev", "test": "tst", "acceptance": "acc"
})

# Host status values
VALID_STATUS_VALUES = _config.get("hosts", {}).get("valid_status_values", ["active", "decommissioned"])
DEFAULT_STATUS = _config.get("hosts", {}).get("default_status", "active")
DECOMMISSIONED_STATUS = "decommissioned"
VALID_PATCH_MODES = _config.get("hosts", {}).get("valid_patch_modes", ["auto", "manual"])

# Inventory key configuration
VALID_INVENTORY_KEYS = ["hostname", "cname"]
DEFAULT_INVENTORY_KEY = _config.get("hosts", {}).get("inventory_key", "hostname")

# Group naming patterns
GROUP_PREFIXES = _config.get("groups", {}).get("prefixes", {
    "application": "app_", "product": "product_", "environment": "env_"
})

# File naming patterns
INVENTORY_FILE_PATTERN = _config.get("formats", {}).get("inventory_file_pattern", "{environment}.yml")
ENVIRONMENT_GROUP_VAR_PATTERN = _config.get("formats", {}).get("environment_group_var_pattern", "env_{environment}.yml")
HOST_VAR_FILE_PATTERN = _config.get("formats", {}).get("host_var_file_pattern", "{hostname}.yml")

# Grace periods for host cleanup (days)
GRACE_PERIODS = _config.get("hosts", {}).get("grace_periods", {
    "production": 90, "acceptance": 30, "test": 14, "development": 7
})

# Patch management
PATCH_WINDOWS = _config.get("patch_management", {}).get("windows", {
    "batch_1": "Saturday 02:00-04:00 UTC",
    "batch_2": "Saturday 04:00-06:00 UTC",
    "batch_3": "Saturday 06:00-08:00 UTC"
})

# CMDB settings
DEFAULT_SUPPORT_GROUP = _config.get("cmdb", {}).get("default_support_group", "")
DATE_FORMAT = _config.get("formats", {}).get("date", "%Y-%m-%d")
TIMESTAMP_FORMAT = _config.get("formats", {}).get("timestamp", "%Y%m%d_%H%M%S")

# Display settings
CONSOLE_WIDTH = _config.get("display", {}).get("console_width", 60)
TREE_MAX_DEPTH = _config.get("display", {}).get("tree_max_depth", 3)

# File headers and comments
AUTO_GENERATED_HEADER = _config.get("headers", {}).get("auto_generated", "AUTO-GENERATED FILE - DO NOT EDIT MANUALLY")
HOST_VARS_HEADER = _config.get("headers", {}).get("host_vars", "Generated from enhanced CSV with CMDB and patch management fields")

# Required directories for validation
REQUIRED_DIRECTORIES = [INVENTORY_DIR, GROUP_VARS_DIR, HOST_VARS_DIR]

# Expected environment files
EXPECTED_ENV_FILES = [f"env_{env}.yml" for env in ENVIRONMENTS]

# Inventory files to check for auto-generated headers
INVENTORY_FILES_TO_VALIDATE = [f"{env}.yml" for env in ENVIRONMENTS] + ["decommissioned.yml"]

# Command examples (for display purposes)
EXAMPLE_COMMANDS = _config.get("examples", {}).get("commands", {
    "list_hosts": "ansible-inventory --list",
    "show_structure": "ansible-inventory --graph",
    "regenerate": "python3 scripts/ansible_inventory_cli.py generate",
    "validate": "python3 scripts/ansible_inventory_cli.py validate",
    "health_check": "python3 scripts/ansible_inventory_cli.py health"
})


# New configuration utility functions
def get_csv_template_headers() -> List[str]:
    """Get CSV template headers from configuration."""
    return _config.get("data", {}).get("csv_template_headers", [
        "hostname", "environment", "status", "cname", "instance",
        "datacenter", "ssl_port", "application_service", "product_id",
        "primary_application", "function", "batch_number", "patch_mode",
        "dashboard_group", "decommission_date"
    ])


def get_feature_flag(feature: str) -> bool:
    """Get feature flag value from configuration."""
    return _config.get("features", {}).get(feature, False)


def get_csv_file_path() -> Path:
    """Get the CSV file path."""
    return CSV_FILE


def get_available_csv_files() -> List[Path]:
    """Get list of available CSV files in inventory_source directory."""
    csv_file = get_csv_file_path()
    if csv_file.exists():
        return [csv_file]
    return []


def validate_csv_file(csv_path: str) -> Tuple[bool, str]:
    """Validate that a CSV file exists, is readable, and has a valid header."""
    path = Path(csv_path)
    if not path.exists():
        return False, f"File not found: {csv_path}"
    if not path.is_file():
        return False, f"Not a file: {csv_path}"
    if not csv_path.endswith(".csv"):
        return False, f"Not a CSV file: {csv_path}"
    try:
        with path.open("r", encoding="utf-8") as f:
            header = f.readline().strip().split(',')
            expected_headers = get_csv_template_headers()
            if header != expected_headers:
                return False, f"Invalid CSV header. Expected {expected_headers}, but got {header}"
        return True, "Valid CSV file"
    except Exception as e:
        return False, f"Cannot read file: {e}"


def get_inventory_file_path(environment: str) -> Path:
    """Get inventory file path for a specific environment."""
    return INVENTORY_DIR / INVENTORY_FILE_PATTERN.format(environment=environment)


def get_host_vars_file_path(hostname: str) -> Path:
    """Get host_vars file path for a specific hostname."""
    return HOST_VARS_DIR / HOST_VAR_FILE_PATTERN.format(hostname=hostname)


def get_backup_file_path(base_name: str, timestamp: Optional[str] = None) -> Path:
    """Get backup file path with timestamp."""
    if timestamp is None:
        from datetime import datetime

        timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)

    backup_name = f"{base_name}_backup_{timestamp}{CSV_EXTENSION}"
    return BACKUP_DIR / backup_name


def get_environment_group_var_path(environment: str) -> Path:
    """Get group_vars file path for environment."""
    filename = ENVIRONMENT_GROUP_VAR_PATTERN.format(environment=environment)
    return GROUP_VARS_DIR / filename


def validate_environment(environment: str) -> bool:
    """Validate if environment is in the allowed list."""
    return environment in ENVIRONMENTS


def get_patching_window(batch_number: str) -> str:
    """Get patching window for batch number."""
    return PATCH_WINDOWS.get(batch_number, "TBD")


def get_grace_period(environment: str) -> int:
    """Get grace period for environment."""
    return GRACE_PERIODS.get(environment, 30)


def validate_inventory_key(inventory_key: str) -> bool:
    """Validate if inventory key is in the allowed list."""
    return inventory_key in VALID_INVENTORY_KEYS


def get_default_inventory_key() -> str:
    """Get the default inventory key."""
    return DEFAULT_INVENTORY_KEY


def validate_configuration() -> List[str]:
    """
    Validate that the configuration file has all expected sections.

    Returns:
        List of warnings about missing configuration sections
    """
    warnings = []
    config = get_config()

    # Expected sections with their critical sub-keys
    expected_sections = {
        "data": ["csv_template_headers"],
        "environments": ["codes"],
        "hosts": ["valid_patch_modes", "grace_periods"],
        "groups": ["prefixes"],
        "patch_management": ["windows"],
        "cmdb": ["default_support_group"],
        "formats": ["date", "timestamp", "yaml_extension"],
        "display": ["console_width"],
        "headers": ["auto_generated", "host_vars"],
        "features": []  # Optional section
    }

    for section, sub_keys in expected_sections.items():
        if section not in config:
            if section == "features":
                warnings.append(f"Optional section '{section}' not found - feature flags disabled")
            else:
                warnings.append(f"Missing configuration section: '{section}'")
        else:
            # Check sub-keys
            for sub_key in sub_keys:
                if sub_key not in config[section]:
                    warnings.append(f"Missing configuration: '{section}.{sub_key}'")

    return warnings


def print_configuration_status() -> None:
    """Print the current configuration status and any warnings."""
    print("📋 Configuration Status:")
    print(f"   Config file: {CONFIG_FILE}")
    print(f"   File exists: {'✅' if CONFIG_FILE.exists() else '❌'}")

    if CONFIG_FILE.exists():
        warnings = validate_configuration()
        if warnings:
            print("   ⚠️  Configuration warnings:")
            for warning in warnings:
                print(f"      • {warning}")
        else:
            print("   ✅ Configuration complete")
    else:
        print("   💡 Run: cp inventory-config.yml.example inventory-config.yml")


class ErrorMessages:
    """Centralized error messages for consistency."""

    CSV_NOT_FOUND = "❌ CSV file not found: {path}"
    INVALID_HOSTNAME = "❌ Invalid hostname: '{hostname}'"
    ENVIRONMENT_INVALID = (
        "❌ Invalid environment: '{env}'. Must be one of: {valid_envs}"
    )
    HOST_NOT_FOUND = "❌ Host '{hostname}' not found"
    PERMISSION_DENIED = "❌ Permission denied accessing: {path}"
    YAML_PARSE_ERROR = "❌ YAML parsing error in {file}: {error}"
    CONFIG_ERROR = "❌ Configuration error: {error}"
    VALIDATION_FAILED = "❌ Validation failed: {error}"

    @classmethod
    def format_error(cls, template: str, **kwargs: Any) -> str:
        """Format error message with parameters."""
        return template.format(**kwargs)
