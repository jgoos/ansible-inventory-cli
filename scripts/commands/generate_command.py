#!/usr/bin/env python3
"""
Generate command - inventory generation.

This command handles the generation of Ansible inventory files from CSV data.
It creates environment-specific inventories and host_vars files.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from ..core import get_logger
from ..core.config import get_default_inventory_key
from ..managers.inventory_manager import InventoryManager
from .base import BaseCommand, CommandResult


class GenerateCommand(BaseCommand):
    """Command to generate inventory files and host variables."""

    logger: logging.Logger  # Explicitly declare logger as non-optional

    def __init__(
        self, csv_file: Optional[Path] = None, logger: Optional[logging.Logger] = None
    ) -> None:
        """Initialise the command with optional CSV path and logger."""
        super().__init__(csv_file, logger)
        self.logger = logger or get_logger(__name__)
        self.inventory_manager = InventoryManager(csv_file, self.logger)

    def add_parser_arguments(self, parser: Any) -> None:
        """Add generate-specific arguments to parser."""
        parser.add_argument(
            "--output-dir",
            "-o",
            type=Path,
            default=Path("inventory"),
            help="Output directory for inventory files (default: inventory)",
        )
        parser.add_argument(
            "--host-vars-dir",
            type=Path,
            default=Path("inventory/host_vars"),
            help="Output directory for host_vars files (default: inventory/host_vars)",
        )
        parser.add_argument(
            "--environments",
            "-e",
            nargs="+",
            help="Specific environments to generate (default: all)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be generated without creating files",
        )
        parser.add_argument(
            "--inventory-key",
            choices=["hostname", "cname"],
            default=get_default_inventory_key(),
            help="Key to use for inventory host entries (default: from config)",
        )

    def execute(self, args: Any) -> Dict[str, Any]:
        """Execute the generate command."""
        try:
            self.logger.info("🎯 Starting inventory generation")

            # Create inventory manager with the specified inventory key
            inventory_manager = InventoryManager(
                self.csv_file,
                self.logger,
                inventory_key=getattr(args, "inventory_key", "hostname"),
            )

            if args.dry_run:
                return self._dry_run_generate(args, inventory_manager)

            # Generate inventories using the manager
            result = inventory_manager.generate_inventories(
                environments=args.environments,
                dry_run=args.dry_run,
            )

            # Extract statistics from the result
            generated_files = result.get("generated_files", [])
            stats = result.get("stats", {})
            orphaned_removed = result.get("orphaned_files_removed", 0)

            # Prepare result
            result_data = {
                "command": "generate",
                "success": True,
                "statistics": {
                    "total_hosts": stats.get("total_hosts", 0),
                    "active_hosts": stats.get("active_hosts", 0),
                    "decommissioned_hosts": stats.get("decommissioned_hosts", 0),
                    "generation_time": stats.get("generation_time", 0),
                    "environment_counts": stats.get("environment_counts", {}),
                    "application_groups": stats.get("application_groups", 0),
                    "product_groups": stats.get("product_groups", 0),
                    "orphaned_files_removed": orphaned_removed,
                },
                "generated_files": generated_files,
                "output_paths": {
                    "inventory_dir": str(inventory_manager.config.inventory_dir),
                    "host_vars_dir": str(inventory_manager.config.host_vars_dir),
                },
                "inventory_key": getattr(args, "inventory_key", "hostname"),
            }

            return CommandResult(
                success=True,
                data=result_data,
                message="✅ Generated inventories using {} as inventory key".format(
                    getattr(args, "inventory_key", "hostname")
                ),
            ).to_dict()

        except FileNotFoundError as e:
            error_msg = f"CSV file not found: {e}"
            self.logger.error(error_msg)
            return CommandResult(success=False, error=error_msg).to_dict()

        except Exception as e:
            error_msg = f"Generation failed: {e}"
            self.logger.error(error_msg)
            return CommandResult(success=False, error=error_msg).to_dict()

    def _dry_run_generate(
        self, args: Any, inventory_manager: InventoryManager
    ) -> Dict[str, Any]:
        """Perform a dry run to show what would be generated."""
        try:
            # Perform dry run on inventory manager to get full stats
            result = inventory_manager.generate_inventories(
                environments=args.environments,
                dry_run=True,
            )

            # Load hosts to show what would be processed
            hosts = inventory_manager.load_hosts()

            # Group by environment
            env_stats = {}
            for host in hosts:
                if host.environment not in env_stats:
                    env_stats[host.environment] = {"active": 0, "decommissioned": 0}

                if host.is_active:
                    env_stats[host.environment]["active"] += 1
                else:
                    env_stats[host.environment]["decommissioned"] += 1

            # Filter environments if specified
            target_environments = args.environments or list(env_stats.keys())

            # Calculate what would be generated
            total_files = 0
            total_host_vars = 0

            for env in target_environments:
                if env in env_stats:
                    total_files += 1  # One inventory file per environment
                    total_host_vars += env_stats[env][
                        "active"
                    ]  # One host_vars per active host

            result_data = {
                "command": "generate",
                "dry_run": True,
                "would_generate": {
                    "inventory_files": total_files,
                    "host_vars_files": total_host_vars,
                    "environments": target_environments,
                    "environment_stats": env_stats,
                    "orphaned_files": result.get("orphaned_files_removed", 0),
                },
                "output_paths": {
                    "inventory_dir": str(args.output_dir),
                    "host_vars_dir": str(args.host_vars_dir),
                },
            }

            self.logger.info(
                "[DRY RUN] Would generate {} inventory files and {} host_vars files".format(
                    total_files, total_host_vars
                )
            )

            return CommandResult(
                success=True,
                data=result_data,
                message="[DRY RUN] Would generate {} inventory files and {} host_vars files".format(
                    total_files, total_host_vars
                ),
            ).to_dict()

        except Exception as e:
            error_msg = f"Dry run failed: {e}"
            self.logger.error(error_msg)
            return CommandResult(success=False, error=error_msg).to_dict()

    def _print_usage_examples(self, output_dir: str) -> str:
        """Generate usage examples for the generated inventory."""
        lines = [
            "",
            "🎯 **Test the comprehensive inventory:**",
            f"   ansible-inventory -i {output_dir}/production.yml --list",
            f"   ansible-inventory -i {output_dir}/production.yml --graph",
            f"   ansible app_identity_management -i {output_dir}/production.yml --list-hosts",
            f"   ansible product_directory_service_a -i {output_dir}/production.yml --list-hosts",
            "",
            "🔧 **Enterprise Features - CMDB & Patch Management:**",
            f"   ansible-inventory -i {output_dir}/production.yml --host prd-dirsvc1-use1-01",
            f"   ansible production -i {output_dir}/production.yml -m debug -a 'var=batch_number'",
            f"   ansible production -i {output_dir}/production.yml -m debug -a 'var=cmdb_discovery'",
            "",
            "💡 **Advanced Usage:**",
            "   # Use custom CSV file",
            "   ansible-inventory-cli generate --csv-file inventory_source/hosts_production.csv",
            "   # Generate specific environments only",
            "   ansible-inventory-cli generate --environments production test",
            "   # Custom output directory",
            "   ansible-inventory-cli generate --output-dir custom_inventory",
            "   # Use CNAME as inventory key instead of hostname",
            "   ansible-inventory-cli generate --inventory-key cname",
        ]
        return "\n".join(lines)

    def format_text_output(self, result: Dict[str, Any]) -> str:
        """Format result for text output."""
        if not result.get("success", False):
            return f"❌ Generation failed: {result.get('error', 'Unknown error')}"

        data = result.get("data", {})

        if data.get("dry_run"):
            would_generate = data.get("would_generate", {})
            lines = [
                "🔍 DRY RUN - Inventory Generation Preview",
                "Would generate: {} inventory files".format(
                    would_generate.get("inventory_files", 0)
                ),
                "Would generate: {} host_vars files".format(
                    would_generate.get("host_vars_files", 0)
                ),
                "Target environments: {}".format(
                    ", ".join(would_generate.get("environments", []))
                ),
                "",
                "Environment breakdown:",
            ]

            for env, stats in would_generate.get("environment_stats", {}).items():
                lines.append(
                    "  {}: {} active, {} decommissioned".format(
                        env, stats["active"], stats["decommissioned"]
                    )
                )

            # Add orphaned files info
            orphaned = would_generate.get("orphaned_files", 0)
            if orphaned > 0:
                lines.append("")
                lines.append(f"Would clean up: {orphaned} orphaned host_vars files")

            return "\n".join(lines)

        else:
            stats = data.get("statistics", {})
            output_dir = data.get("output_paths", {}).get("inventory_dir", "inventory")

            lines = [
                "✅ INVENTORY GENERATION COMPLETED",
                "📊 Statistics:",
                f"   Total hosts: {stats.get('total_hosts', 0)}",
                f"   Active: {stats.get('active_hosts', 0)}",
                f"   Decommissioned: {stats.get('decommissioned_hosts', 0)}",
                f"   Generation time: {stats.get('generation_time', 0)}s",
            ]

            # Add orphaned files cleanup info
            orphaned_removed = stats.get("orphaned_files_removed", 0)
            if orphaned_removed > 0:
                lines.append(f"   Orphaned files cleaned: {orphaned_removed}")

            lines.extend(
                [
                    "",
                    f"🎯 Generated inventories in {output_dir}",
                ]
            )

            env_counts = stats.get("environment_counts", {})
            if env_counts:
                lines.append("")
                lines.append("Environment breakdown:")
                for env, count in sorted(env_counts.items()):
                    lines.append(f"  {env}: {count}")

            # Add usage examples
            lines.append(self._print_usage_examples(output_dir))

            return "\n".join(lines)
