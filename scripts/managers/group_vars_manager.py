import shutil
import sys
from pathlib import Path
from typing import Any, List, Optional

from ..core import get_logger
from ..core.config import load_config
from ..core.models import Host


class GroupVarsManager:
    """Manages group variables file cleanup based on protected files list."""

    def __init__(self, logger: Optional[Any] = None) -> None:
        """Initialize the manager with configuration and logging."""
        self.config = load_config()
        self.logger = logger if logger else get_logger(__name__)
        self.group_vars_dir = Path(self.config["paths"]["group_vars"])

        # Load protected files list from config
        self.protected_files = self.config.get("group_vars", {}).get(
            "protected_files", []
        )

        self.logger.info("GroupVarsManager initialized")

    def cleanup_orphaned_group_vars(
        self, hosts: List[Host], dry_run: bool = False
    ) -> int:
        """Removes group_vars files that are not in the protected list and are not referenced by hosts."""
        self.logger.info("Starting orphaned group_vars cleanup")

        # Collect all group names that should exist based on host data
        required_group_names = set()
        for host in hosts:
            if host.environment:
                required_group_names.add(f"env_{host.environment}.yml")
            if host.application_service:
                required_group_names.add(f"app_{host.application_service}.yml")
            if host.get_product_ids():
                for prod_id in host.get_product_ids():
                    required_group_names.add(f"product_{prod_id}.yml")
            if host.site_code:
                required_group_names.add(f"site_{host.site_code}.yml")
            if host.dashboard_group:
                required_group_names.add(f"dashboard_{host.dashboard_group}.yml")
            if host.batch_number:
                required_group_names.add(f"batch_{host.batch_number}.yml")

        orphaned_count = 0
        for file_path in self.group_vars_dir.glob("*.yml"):
            file_name = file_path.name

            if file_name in self.protected_files:
                self.logger.debug(
                    f"Skipping protected group_vars file during cleanup: {file_path}"
                )
                continue

            if file_name not in required_group_names:
                if dry_run:
                    self.logger.info(
                        f"[DRY RUN] Would remove orphaned group_vars: {file_path}"
                    )
                else:
                    try:
                        file_path.unlink()
                        self.logger.info(f"Removed orphaned group_vars: {file_path}")
                    except Exception as e:
                        self.logger.error(
                            f"Failed to remove orphaned file {file_path}: {e}"
                        )
                orphaned_count += 1

        # Clean up old subdirectory structure if it exists (from previous auto-generation)
        for subdir in [
            "sites",
            "applications",
            "dashboards",
            "products",
            "functions",
            "templates",
        ]:
            subdir_path = self.group_vars_dir / subdir
            if subdir_path.exists() and subdir_path.is_dir():
                if dry_run:
                    self.logger.info(
                        f"[DRY RUN] Would remove old subdirectory: {subdir_path}"
                    )
                else:
                    shutil.rmtree(subdir_path)
                    self.logger.info(f"Removed old subdirectory: {subdir_path}")
                orphaned_count += 1

        return orphaned_count
