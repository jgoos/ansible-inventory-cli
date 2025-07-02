#!/usr/bin/env python3
"""
Host Manager - Host Lifecycle Management

Handles host lifecycle operations including decommissioning,
cleanup, and host status management.
"""

import csv
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).parent.parent.absolute()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from core import CSV_FILE as DEFAULT_CSV_FILE
from core import get_logger
from core.config import PROJECT_ROOT
from core.models import InventoryConfig

SCRIPT_DIR = Path(__file__).parent.parent.absolute()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


class HostManager:
    """Manages host lifecycle operations and CSV management."""

    def __init__(
        self, csv_file: Optional[Path] = None, logger: Optional[Any] = None
    ) -> None:
        self.csv_file: Path = csv_file if csv_file is not None else DEFAULT_CSV_FILE
        self.logger = logger if logger else get_logger(__name__)
        self.config = InventoryConfig.create_default()
        self.stats = None
        self.logger.info("Host Manager initialized")
        self.logger.info(f"Using CSV source: {self.csv_file}")

    def load_hosts_from_csv_raw(self) -> List[Dict]:
        """Load raw host data for lifecycle operations."""
        hosts = []
        with self.csv_file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                hostname = row.get("hostname", "").strip()
                if hostname and not hostname.startswith("#"):
                    hosts.append(row)
        return hosts

    def save_hosts_to_csv(self, hosts: List[Dict]) -> None:
        """Save hosts back to CSV file with backup."""
        if not hosts:
            self.logger.warning("No hosts to save, CSV file will be empty.")
            # Create backup
            backup_dir = PROJECT_ROOT / "backups"
            backup_dir.mkdir(exist_ok=True)
            backup_file = (
                backup_dir
                / f"hosts_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            shutil.copy2(self.csv_file, backup_file)
            self.logger.info(f"Created backup: {backup_file}")
            # Write empty file
            with self.csv_file.open("w", newline="", encoding="utf-8") as f:
                f.write("")
            return

        # Create backup
        backup_dir = PROJECT_ROOT / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup_file = (
            backup_dir / f"hosts_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        shutil.copy2(self.csv_file, backup_file)
        self.logger.info(f"Created backup: {backup_file}")

        # Write updated CSV
        fieldnames = hosts[0].keys()
        with self.csv_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(hosts)

        self.logger.info(f"Updated CSV file: {self.csv_file}")

    def decommission_host(
        self, hostname: str, date: str, reason: str = "", dry_run: bool = False
    ) -> bool:
        """Mark a host as decommissioned with specified date."""
        hosts = self.load_hosts_from_csv_raw()

        # Sanitize reason input
        sanitized_reason = re.sub(r"[^a-zA-Z0-9 _-]", "", reason)

        # Find the host
        host_found = False
        for host in hosts:
            if host["hostname"] == hostname:
                if host["status"] == "decommissioned":
                    self.logger.warning(f"Host {hostname} is already decommissioned")
                    return False

                # Validate date format
                try:
                    datetime.strptime(date, "%Y-%m-%d")
                except ValueError:
                    self.logger.error(f"Invalid date format: {date}. Use YYYY-MM-DD")
                    return False

                if dry_run:
                    self.logger.info(
                        f"[DRY RUN] Would decommission {hostname} with date {date}"
                    )
                    return True

                # Update host status
                host["status"] = "decommissioned"
                host["decommission_date"] = date
                host_found = True

                self.logger.info(
                    f"Decommissioned host {hostname} with date {date}. "
                    f"Reason: {sanitized_reason}"
                )
                break

        if not host_found:
            self.logger.error(f"Host {hostname} not found in CSV")
            return False

        # Save changes
        if not dry_run:
            self.save_hosts_to_csv(hosts)

        return True

    def list_expired_hosts(
        self, grace_days_override: Optional[int] = None
    ) -> List[Dict]:
        """List hosts that are past their grace period and eligible for cleanup."""
        hosts = self.load_hosts_from_csv_raw()
        expired_hosts = []

        for host in hosts:
            if host["status"] != "decommissioned" or not host.get("decommission_date"):
                continue

            try:
                decommission_date = datetime.strptime(
                    host["decommission_date"], "%Y-%m-%d"
                )
                environment = host["environment"]

                # Use override or environment-specific grace period
                grace_days = grace_days_override or self.config.grace_periods.get(
                    environment, 30
                )
                expiry_date = decommission_date + timedelta(days=grace_days)

                if datetime.now() > expiry_date:
                    days_expired = (datetime.now() - expiry_date).days
                    expired_hosts.append(
                        {
                            **host,
                            "days_expired": days_expired,
                            "expiry_date": expiry_date.strftime("%Y-%m-%d"),
                            "grace_period": grace_days,
                        }
                    )
            except ValueError:
                continue

        return expired_hosts

    def cleanup_expired_hosts(
        self,
        grace_days_override: Optional[int] = None,
        dry_run: bool = False,
        auto_confirm: bool = False,
        max_hosts: Optional[int] = None,
    ) -> int:
        """Clean up expired hosts."""
        expired_hosts = self.list_expired_hosts(grace_days_override)

        if not expired_hosts:
            self.logger.info("No expired hosts found for cleanup")
            return 0

        # Limit hosts if specified
        if max_hosts:
            expired_hosts = expired_hosts[:max_hosts]

        if dry_run:
            self.logger.info(
                f"[DRY RUN] Would clean up {len(expired_hosts)} expired hosts:"
            )
            for host in expired_hosts:
                self.logger.info(
                    f"  {host['hostname']} - expired {host['days_expired']} days ago"
                )
            return len(expired_hosts)

        # Confirm cleanup unless auto-confirm
        if not auto_confirm:
            response = input(f"Clean up {len(expired_hosts)} expired hosts? [y/N]: ")
            if response.lower() != "y":
                self.logger.info("Cleanup cancelled by user")
                return 0

        # Perform cleanup
        cleaned_count = 0
        for host in expired_hosts:
            hostname = host["hostname"]

            # Remove host_vars file
            host_var_file = self.config.host_vars_dir / f"{hostname}.yml"
            if host_var_file.exists():
                host_var_file.unlink()
                self.logger.info(f"Removed host_vars file: {hostname}.yml")

            cleaned_count += 1

        # Remove from CSV
        all_hosts = self.load_hosts_from_csv_raw()
        expired_hostnames = {host["hostname"] for host in expired_hosts}
        remaining_hosts = [
            h for h in all_hosts if h["hostname"] not in expired_hostnames
        ]
        self.save_hosts_to_csv(remaining_hosts)

        self.logger.info(f"Cleaned up {cleaned_count} expired hosts")
        return cleaned_count

    def create_template_csv(self, output_path: Optional[Path] = None) -> None:
        """Create a template CSV with headers only."""
        template_csv = output_path or (
            PROJECT_ROOT / "inventory_source" / "hosts_template.csv"
        )
        template_csv.parent.mkdir(exist_ok=True)

        with template_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "hostname",
                    "environment",
                    "status",
                    "application_service",
                    "product_id",
                    "location",
                    "instance",
                    "batch_number",
                    "patch_mode",
                    "dashboard_group",
                    "primary_application",
                    "function",
                    "ssl_port",
                    "decommission_date",
                    "cname",
                ]
            )

        self.logger.info(f"Created template CSV: {template_csv}")
