#!/usr/bin/env python3
"""
Inventory manager - core inventory operations.

Handles the generation of Ansible inventory files and host_vars
from CSV data sources.
"""

import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ..core import CSV_FILE as DEFAULT_CSV_FILE
from ..core import (
    HOST_VARS_HEADER,
    ensure_directory_exists,
    get_logger,
    load_csv_data,
)
from ..core.config import get_environment_info_from_code, load_config
from ..core.models import Host, InventoryConfig, InventoryStats
from .group_vars_manager import GroupVarsManager


class InventoryManager:
    """Manages core inventory operations and file generation."""

    def __init__(
        self,
        csv_file: Optional[Path] = None,
        logger: Optional[Any] = None,
        inventory_key: str = "hostname",
    ) -> None:
        """Initialise the manager with configuration and logging."""
        self.config = InventoryConfig.create_default(inventory_key=inventory_key)
        self.csv_file: Path = csv_file if csv_file is not None else DEFAULT_CSV_FILE
        self.logger = logger if logger else get_logger(__name__)
        self.stats = InventoryStats()

        # Ensure CSV file exists
        if not Path(self.csv_file).exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_file}")

        self.logger.info("Inventory Manager initialized")
        self.logger.info(f"Using CSV source: {self.csv_file}")

    def load_hosts(self, environment: Optional[str] = None) -> List[Host]:
        """Load hosts from CSV with optional environment filtering."""
        # Determine required fields based on inventory key
        if self.config.inventory_key == "cname":
            # When using cname as primary key, either cname or hostname must be present
            # but we'll let the Host model validation handle this
            required_fields = ["environment"]
        else:
            # When using hostname as primary key, hostname is preferred but cname can be fallback
            required_fields = ["environment"]

        csv_data = load_csv_data(
            self.csv_file,
            required_fields=required_fields,
            inventory_key=self.config.inventory_key,
        )
        hosts: List[Host] = []

        normalized_env = None
        if environment:
            env_filter = environment.strip()
            env_info = get_environment_info_from_code(env_filter)
            normalized_env = env_info["name"] if env_info else env_filter
            self.logger.debug(
                f"Normalized environment filter '{environment}' to '{normalized_env}'"
            )

        for row_data in csv_data:
            try:
                # Map environment code to full name if needed
                env_code = row_data.get("environment", "").strip()
                if env_code:
                    env_info = get_environment_info_from_code(env_code)
                    if env_info:
                        # Replace the environment code with the full name
                        row_data["environment"] = env_info["name"]
                        self.logger.debug(
                            f"Mapped environment code '{env_code}' to '{env_info['name']}'"
                        )

                host = Host.from_csv_row(row_data)
                if normalized_env and host.environment != normalized_env:
                    continue
                hosts.append(host)
                self.stats.add_host(host)
            except ValueError as e:
                self.logger.warning(f"Skipping invalid host data: {e}")
                continue

        self.logger.info(f"Loaded {len(hosts)} hosts from CSV")
        return hosts

    def cleanup_orphaned_host_vars(
        self, hosts: List[Host], dry_run: bool = False
    ) -> int:
        """Clean up orphaned host_vars files that don't exist in the current CSV.

        Args:
            hosts: Current list of hosts from CSV
            dry_run: If True, only report what would be removed

        Returns:
            Number of files removed (or would be removed in dry-run)
        """
        # Check if cleanup is enabled in config
        config = load_config()
        if not config.get("features", {}).get("cleanup_orphaned_on_generate", True):
            self.logger.debug("Orphaned file cleanup is disabled in configuration")
            return 0

        # Collect all valid identifiers (both hostnames and cnames)
        valid_identifiers = set()
        for host in hosts:
            if host.hostname:
                valid_identifiers.add(host.hostname)
            if host.cname:
                valid_identifiers.add(host.cname)

        # Find orphaned files
        orphaned_files = []
        if self.config.host_vars_dir.exists():
            for file_path in self.config.host_vars_dir.glob("*.yml"):
                identifier = file_path.stem
                if identifier not in valid_identifiers:
                    orphaned_files.append(file_path)

        if not orphaned_files:
            return 0

        self.logger.info(f"Found {len(orphaned_files)} orphaned host_vars files")

        if dry_run:
            self.logger.info("[DRY RUN] Would remove orphaned files:")
            for file_path in orphaned_files[:5]:  # Show first 5
                self.logger.info(f"  - {file_path.name}")
            if len(orphaned_files) > 5:
                self.logger.info(f"  ... and {len(orphaned_files) - 5} more")
            return len(orphaned_files)

        # Remove orphaned files
        removed_count = 0
        for file_path in orphaned_files:
            try:
                file_path.unlink()
                self.logger.debug(f"Removed orphaned file: {file_path.name}")
                removed_count += 1
            except Exception as e:
                self.logger.error(f"Failed to remove {file_path}: {e}")

        if removed_count > 0:
            self.logger.info(f"Cleaned up {removed_count} orphaned host_vars files")

        return removed_count

    def generate_inventories(
        self, environments: Optional[List[str]] = None, dry_run: bool = False
    ) -> Dict[str, Any]:
        """Generate inventory files for specified environments."""
        self.logger.info("Starting inventory generation")
        start_time = time.time()

        # Reset statistics
        self.stats = InventoryStats()

        try:
            # Load and validate hosts
            hosts = self.load_hosts()
            if not hosts:
                raise ValueError("No valid hosts found in CSV file")

            self.logger.info(f"Loaded {len(hosts)} hosts from CSV")

            # Initialize GroupVarsManager
            group_vars_manager = GroupVarsManager(logger=self.logger)

            # Clean up orphaned host_vars files before generating new ones
            orphaned_count = self.cleanup_orphaned_host_vars(hosts, dry_run)

            # Clean up orphaned group_vars files
            group_orphaned_removed = group_vars_manager.cleanup_orphaned_group_vars(
                hosts, dry_run
            )

            # Filter environments if specified
            target_environments = environments or self.config.environments

            # Generate inventories for each environment
            generated_files = []

            for env in target_environments:
                # Map abbreviation to full name and filename if needed
                env_info = get_environment_info_from_code(env)
                if env_info:
                    env_name = env_info["name"]
                    inventory_filename = env_info["inventory_file"]
                else:
                    env_name = env
                    inventory_filename = f"{env}.yml"
                try:
                    self.logger.info(f"Processing environment: {env_name}")
                    env_hosts = [
                        h
                        for h in hosts
                        if h.environment == env or h.environment == env_name
                    ]

                    if not env_hosts:
                        self.logger.warning(
                            f"No hosts found for environment: {env_name}"
                        )
                        continue

                    if dry_run:
                        self.logger.info(
                            f"[DRY RUN] Would generate inventory for {env_name} "
                            f"with {len(env_hosts)} hosts"
                        )
                    else:
                        # Generate the actual inventory file
                        inventory_file = self._generate_inventory_file(
                            env_name, env_hosts, inventory_filename
                        )
                        generated_files.append(str(inventory_file))
                        self.logger.info(f"Generated inventory file: {inventory_file}")

                except Exception as e:
                    self.logger.error(
                        f"Failed to generate inventory for {env_name}: {e}",
                        exc_info=True,
                    )
                    # Continue with other environments
                    continue

            # Calculate generation time
            self.stats.generation_time = time.time() - start_time

            # Add orphaned count to stats
            self.stats.orphaned_files_removed = orphaned_count

            return {
                "status": "success",
                "generated_files": generated_files,
                "dry_run": dry_run,
                "stats": self.stats.__dict__,
                "environments": target_environments,
                "orphaned_files_removed": orphaned_count,
                "group_vars_created": 0,  # TODO: Implement group vars creation tracking
                "group_orphaned_removed": group_orphaned_removed,
            }

        except FileNotFoundError as e:
            self.logger.error(f"CSV source file not found: {e}")
            return {
                "status": "error",
                "error": f"CSV source file not found: {e}",
                "generated_files": [],
                "dry_run": dry_run,
            }
        except Exception as e:
            self.logger.error(f"Inventory generation failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": f"Failed to generate inventories: {e}",
                "generated_files": [],
                "dry_run": dry_run,
            }

    def create_host_vars(self, host: Host, host_vars_dir: Path) -> None:
        """Create host_vars file for a host.

        Only writes the file if the content has actually changed, making
        the operation idempotent and more efficient.
        """
        ensure_directory_exists(str(host_vars_dir))

        # Get the primary identifier for this host based on inventory key
        primary_id = host.get_inventory_key_value(self.config.inventory_key)

        # Load field mappings from config
        config = load_config()
        field_mappings = config.get("field_mappings", {})
        host_var_fields = field_mappings.get("host_vars", [])

        # Build host_vars with only designated fields
        host_vars: Dict[str, Any] = {}

        # Add fields designated as host_vars
        for field in host_var_fields:
            value = getattr(host, field, None)
            if value is not None:
                # Special handling for ssl_port
                if field == "ssl_port" and value:
                    try:
                        host_vars[field] = int(value)
                    except ValueError:
                        host_vars[field] = value
                else:
                    host_vars[field] = value if value else ""

        # If support_group is a host_var, set it to default if missing or empty
        if "support_group" in host_var_fields:
            if not host_vars.get("support_group"):
                default_support_group = config.get("cmdb", {}).get(
                    "default_support_group", ""
                )
                host_vars["support_group"] = default_support_group

        # Optionally append or prepend short cname to function field
        hosts_config = config.get("hosts", {})
        append_short_cname = hosts_config.get("function_append_short_cname", False)
        cname_position = hosts_config.get("function_short_cname_position", "back")
        if append_short_cname and "function" in host_vars and "cname" in host_vars:
            function_val = host_vars["function"]
            cname_val = host_vars["cname"]
            short_cname = cname_val.split(".")[0] if cname_val else ""
            if function_val and short_cname and short_cname not in function_val:
                if cname_position == "front":
                    host_vars["function"] = f"{short_cname} - {function_val}"
                else:
                    host_vars["function"] = f"{function_val} ({short_cname})"

        # Get all configured fields to exclude from metadata
        all_configured_fields = set(host_var_fields)
        all_configured_fields.update(field_mappings.get("group_references", []))
        # Also exclude computed fields and internal fields
        all_configured_fields.update(["ansible_tags"])

        # Only add metadata fields that aren't already configured elsewhere
        for key, value in host.metadata.items():
            if key not in all_configured_fields:
                host_vars[key] = value

        # Generate the new YAML content
        import io

        yaml_buffer = io.StringIO()
        yaml.dump(host_vars, yaml_buffer, default_flow_style=False, sort_keys=True)
        new_yaml_content = yaml_buffer.getvalue()

        # Use the inventory key-based filename
        host_vars_filename = host.get_host_vars_filename(self.config.inventory_key)
        host_vars_file: Path = host_vars_dir / host_vars_filename

        # Check if file exists and compare content
        should_write = True
        if host_vars_file.exists():
            try:
                with host_vars_file.open("r", encoding="utf-8") as f:
                    existing_lines = f.readlines()

                # Extract existing YAML content (skip header lines)
                yaml_start_index = None
                for i, line in enumerate(existing_lines):
                    if line.strip() == "" and i > 0:
                        yaml_start_index = i + 1
                        break

                if yaml_start_index is not None:
                    existing_yaml_content = "".join(existing_lines[yaml_start_index:])
                    should_write = existing_yaml_content != new_yaml_content
                    if not should_write:
                        self.logger.debug(
                            f"Content unchanged for {host_vars_filename}, skipping write"
                        )

            except Exception as e:
                self.logger.debug(
                    f"Could not read existing host_vars file {host_vars_file}: {e}"
                )
                should_write = True

        # Only write if content has changed or file doesn't exist
        if should_write:
            with host_vars_file.open("w", encoding="utf-8") as f:
                f.write("---\n")
                f.write(f"# Host variables for {primary_id}\n")
                f.write(f"# {HOST_VARS_HEADER}\n")
                f.write("\n")
                f.write(new_yaml_content)
            self.logger.debug(f"Updated host_vars file: {host_vars_filename}")

    def build_environment_inventory(
        self, hosts: List[Host], environment: str
    ) -> Dict[str, Any]:
        """Build inventory dictionary for an environment."""
        inventory: Dict[str, Any] = defaultdict(lambda: {"hosts": {}, "children": {}})

        # Add 'all' group as the top-level parent
        inventory["all"] = {"children": {}}

        for host in hosts:
            if host.environment != environment:
                continue
            host_key = host.get_inventory_key_value(self.config.inventory_key)

            # Ensure environment group exists and is a child of 'all'
            env_group_name = f"env_{environment}"
            if env_group_name not in inventory:
                inventory[env_group_name] = {"hosts": {}, "children": {}}
            inventory["all"]["children"][env_group_name] = {}

            # Add host to environment group
            inventory[env_group_name]["hosts"][host_key] = {}

            # Add application service group as child of environment group
            if host.application_service:
                app_group = host.get_app_group_name()
                if app_group:
                    if app_group not in inventory:
                        inventory[app_group] = {"hosts": {}, "children": {}}
                    inventory[env_group_name]["children"][app_group] = {}
                    inventory[app_group]["hosts"][host_key] = {}

                    # Add product groups as children of application group
                    if host.get_product_ids():
                        for prod_group in host.get_product_group_names():
                            if prod_group not in inventory:
                                inventory[prod_group] = {"hosts": {}, "children": {}}
                            inventory[app_group]["children"][prod_group] = {}
                            inventory[prod_group]["hosts"][host_key] = {}

            # Add site_code group if available (as child of environment group)
            if host.site_code:
                site_code_str = str(host.site_code).strip()
                if site_code_str:
                    site_group = f"site_{site_code_str.lower().replace('-', '_')}"
                    if site_group not in inventory:
                        inventory[site_group] = {"hosts": {}, "children": {}}
                    inventory[env_group_name]["children"][site_group] = {}
                    inventory[site_group]["hosts"][host_key] = {}

            # Add batch_number group if available (as child of environment group)
            if host.batch_number:
                batch_group = host.get_batch_group_name()
                if batch_group:
                    if batch_group not in inventory:
                        inventory[batch_group] = {"hosts": {}, "children": {}}
                    inventory[env_group_name]["children"][batch_group] = {}
                    inventory[batch_group]["hosts"][host_key] = {}

        return dict(inventory)

    def write_inventory_file(
        self, inventory: Dict[str, Any], output_file: Path, title: str
    ) -> None:
        """Write inventory to YAML file, omitting empty groups.

        Only updates the file if the content has actually changed, preserving
        existing timestamps for idempotent behavior.
        """
        ensure_directory_exists(str(output_file.parent))

        # Remove groups with no hosts
        filtered_inventory = {}
        for group, data in inventory.items():
            hosts = data.get("hosts", {})
            if hosts and len(hosts) > 0:
                filtered_inventory[group] = data

        # Generate the new YAML content (without header)
        import io

        yaml_buffer = io.StringIO()
        yaml.dump(
            filtered_inventory, yaml_buffer, default_flow_style=False, sort_keys=True
        )
        new_yaml_content = yaml_buffer.getvalue()

        # Check if file exists and extract existing timestamp and content
        existing_timestamp = None
        existing_yaml_content = None

        if output_file.exists():
            try:
                with output_file.open("r", encoding="utf-8") as f:
                    existing_lines = f.readlines()

                # Extract existing timestamp from header
                for line in existing_lines:
                    if line.strip().startswith("# Generated at:"):
                        existing_timestamp = line.strip()
                        break

                # Extract existing YAML content (everything after the header)
                yaml_start_index = None
                for i, line in enumerate(existing_lines):
                    if (
                        line.strip() == ""
                        and i > 0
                        and existing_lines[i - 1].strip().startswith("# Generated at:")
                    ):
                        yaml_start_index = i + 1
                        break

                if yaml_start_index is not None:
                    existing_yaml_content = "".join(existing_lines[yaml_start_index:])

            except Exception as e:
                self.logger.debug(f"Could not read existing file {output_file}: {e}")

        # Compare YAML content to determine if we need to update
        content_changed = existing_yaml_content != new_yaml_content

        # Use existing timestamp if content hasn't changed, otherwise generate new one
        if not content_changed and existing_timestamp:
            timestamp_line = existing_timestamp
            self.logger.debug(
                f"Content unchanged for {output_file.name}, preserving existing timestamp"
            )
        else:
            timestamp_line = (
                f"# Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            if content_changed:
                self.logger.debug(
                    f"Content changed for {output_file.name}, updating timestamp"
                )
            else:
                self.logger.debug(f"New file {output_file.name}, generating timestamp")

        # Write the file with appropriate timestamp
        with output_file.open("w", encoding="utf-8") as f:
            f.write(
                "# ----------------------------------------------------------------------\n"
            )
            f.write("# AUTO-GENERATED FILE - DO NOT EDIT MANUALLY\n")
            f.write("# This file is generated by the inventory management system.\n")
            f.write(
                "# Any manual changes will be overwritten the next time inventory is generated.\n"
            )
            f.write(
                "# ----------------------------------------------------------------------\n"
            )
            f.write(f"# {title} Inventory\n")
            f.write(
                "# Generated from enhanced CSV with CMDB and patch management integration\n"
            )
            f.write(f"{timestamp_line}\n")
            f.write("\n")
            f.write(new_yaml_content)

    def _generate_inventory_file(
        self,
        environment: str,
        hosts: List[Host],
        inventory_filename: Optional[str] = None,
    ) -> Path:
        """Generate inventory file for a specific environment.

        Args:
            environment: Environment name
            hosts: List of hosts for this environment
            inventory_filename: Optional custom filename for the inventory file

        Returns:
            Path to generated inventory file

        Raises:
            OSError: If file cannot be written
        """
        try:
            # Create host_vars for all active hosts
            active_hosts = [h for h in hosts if h.is_active]
            for host in active_hosts:
                self.create_host_vars(host, self.config.host_vars_dir)

            # Build inventory structure
            inventory = self.build_environment_inventory(active_hosts, environment)

            # Update statistics
            self.stats.application_groups = len(
                [g for g in inventory.keys() if g.startswith("app_")]
            )
            self.stats.product_groups = len(
                [g for g in inventory.keys() if g.startswith("product_")]
            )

            # Write inventory file
            if inventory_filename:
                output_file = self.config.inventory_dir / inventory_filename
            else:
                output_file = self.config.inventory_dir / f"{environment}.yml"
            self.write_inventory_file(
                inventory, output_file, f"{environment.title()} Environment"
            )

            self.logger.info(
                f"Generated {environment} inventory: "
                f"{len(active_hosts)} hosts, "
                f"{self.stats.application_groups} app groups, "
                f"{self.stats.product_groups} product groups"
            )

            return output_file  # type: ignore[no-any-return]

        except OSError as e:
            self.logger.error(f"Failed to write inventory file for {environment}: {e}")
            raise
        except Exception as e:
            self.logger.error(
                f"Unexpected error generating inventory for {environment}: {e}",
                exc_info=True,
            )
            raise ValueError(f"Failed to generate {environment} inventory: {e}") from e

    def get_stats(self) -> InventoryStats:
        """Get current inventory statistics."""
        return self.stats
