#!/usr/bin/env python3
"""
Host manager - host lifecycle management.

Handles host lifecycle operations including decommissioning,
cleanup, and host status management.
"""

import csv
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..core import CSV_FILE as DEFAULT_CSV_FILE  # noqa: E402
from ..core import get_logger  # noqa: E402
from ..core.config import PROJECT_ROOT  # noqa: E402
from ..core.models import InventoryConfig  # noqa: E402
from ..core.utils import (  # noqa: E402
    log_data_modification,
    log_file_access,
    security_audit_log,
)


class HostManager:
    """Manages host lifecycle operations and CSV management."""

    def __init__(
        self, csv_file: Optional[Path] = None, logger: Optional[Any] = None
    ) -> None:
        """Initialise the host manager and load configuration."""
        self.csv_file: Path = csv_file if csv_file is not None else DEFAULT_CSV_FILE
        self.logger = logger if logger else get_logger(__name__)
        self.config = InventoryConfig.create_default()
        self.stats = None
        self.logger.info("Host Manager initialized")
        self.logger.info(f"Using CSV source: {self.csv_file}")

    def load_hosts_from_csv_raw(self) -> List[Dict[str, Any]]:
        """Load raw host data for lifecycle operations."""
        hosts: List[Dict[str, Any]] = []
        with self.csv_file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            # Check if CSV has headers
            if not reader.fieldnames:
                self.logger.error("CSV file has no headers or is empty")
                return hosts

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
            # Don't write empty file - raise an error instead
            raise ValueError(
                "Refusing to write empty CSV file. This would delete all inventory data. "
                "If this is intentional, manually delete the CSV file."
            )

        # Create backup
        backup_dir = PROJECT_ROOT / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup_file = (
            backup_dir / f"hosts_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        shutil.copy2(self.csv_file, backup_file)
        self.logger.info(f"Created backup: {backup_file}")

        # Get original fieldnames from the current CSV to preserve order and any custom fields
        original_fieldnames: List[str] = []
        try:
            with self.csv_file.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                original_fieldnames = (
                    list(reader.fieldnames) if reader.fieldnames else []
                )
        except (OSError, IOError) as e:
            self.logger.warning(
                f"Could not read original fieldnames from {self.csv_file}: {e}"
            )
            original_fieldnames = []
        except Exception as e:
            self.logger.error(f"Unexpected error reading CSV file: {e}")
            original_fieldnames = []

        # If no original fieldnames, use the keys from first host
        fieldnames = (
            original_fieldnames if original_fieldnames else list(hosts[0].keys())
        )

        # Ensure all keys from hosts are included
        all_keys: Set[str] = set()
        for host in hosts:
            all_keys.update(host.keys())

        # Add any missing keys to fieldnames
        for key in all_keys:
            if key not in fieldnames:
                fieldnames.append(key)

        with self.csv_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(hosts)

        log_data_modification(str(self.csv_file), "UPDATE", len(hosts))
        log_file_access(self.csv_file, "WRITE", success=True)
        self.logger.info(f"Updated CSV file: {self.csv_file}")

    def load_hosts(self, environment: Optional[str] = None) -> List[Any]:
        """Load hosts from CSV, optionally filtered by environment.

        Args:
            environment: Optional environment to filter by

        Returns:
            List of Host objects
        """
        from ..core.utils import load_hosts_from_csv

        hosts = load_hosts_from_csv(str(self.csv_file))
        
        if environment:
            hosts = [host for host in hosts if host.environment == environment]
        
        return hosts

    @security_audit_log("Host decommission operation")
    def decommission_host(
        self, hostname: str, date: str, reason: str = "", dry_run: bool = False
    ) -> bool:
        """Decommission a host with detailed logging and error handling.

        Args:
            hostname: Hostname to decommission
            date: Decommission date in YYYY-MM-DD format
            reason: Reason for decommissioning
            dry_run: If True, only show what would be done

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If date format is invalid or in the future
        """
        self.logger.info(f"Starting decommission process for {hostname}")

        # Validate date format
        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d")
            # Ensure date is not in the future
            if parsed_date.date() > datetime.now().date():
                self.logger.warning(f"Decommission date {date} is in the future")
        except ValueError:
            self.logger.error(f"Invalid date format: {date}. Use YYYY-MM-DD")
            return False

        # Sanitize the reason
        sanitized_reason = re.sub(r"[^\w\s\-\.]", "", reason)[:100]

        try:
            hosts = self.load_hosts_from_csv_raw()
            host_found = False

            for host in hosts:
                if host.get("hostname", "").strip() == hostname:
                    host_found = True

                    # Check if already decommissioned
                    if host.get("status", "").strip() == "decommissioned":
                        self.logger.warning(
                            f"Host {hostname} is already decommissioned"
                        )
                        return False

                    if dry_run:
                        self.logger.info(
                            f"[DRY RUN] Would decommission {hostname} on {date}"
                        )
                        if sanitized_reason:
                            self.logger.info(f"[DRY RUN] Reason: {sanitized_reason}")
                        return True

                    # Update the host status
                    host["status"] = "decommissioned"
                    host["decommission_date"] = date
                    host["notes"] = sanitized_reason

                    self.logger.info(
                        f"Decommissioned host {hostname} with date {date}. "
                        f"Reason: {sanitized_reason if sanitized_reason else 'No reason provided'}"
                    )
                    break

            if not host_found:
                self.logger.error(f"Host {hostname} not found in inventory")
                return False

            # Save updated hosts if not dry run and host was found
            if not dry_run and host_found:
                try:
                    self.save_hosts_to_csv(hosts)
                    self.logger.info("Successfully saved updated inventory")
                except Exception as e:
                    self.logger.error(
                        f"Failed to save inventory after decommission: {e}"
                    )
                    return False

            return True

        except Exception as e:
            self.logger.error(
                f"Error during decommission operation: {e}", exc_info=True
            )
            return False

    def list_expired_hosts(
        self, grace_days_override: Optional[int] = None
    ) -> List[Dict]:
        """Return hosts past their grace period that are eligible for cleanup."""
        hosts = self.load_hosts_from_csv_raw()
        expired_hosts = []

        for host in hosts:
            if host.get("status") != "decommissioned" or not host.get(
                "decommission_date"
            ):
                continue

            try:
                decommission_date = datetime.strptime(
                    host["decommission_date"], "%Y-%m-%d"
                )
                environment = host.get("environment")

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

    @security_audit_log("Expired host cleanup operation")
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
            try:
                from ..core.utils import get_secure_user_input

                response = get_secure_user_input(
                    f"Clean up {len(expired_hosts)} expired hosts? [y/N]: ",
                    max_length=5,  # Allow for "yes", "y", "no", "n"
                    timeout=60,
                )
                # Only accept 'y' or 'Y' for confirmation
                if not response or response.lower() != "y":
                    self.logger.info("Cleanup cancelled by user")
                    return 0
            except (TimeoutError, ValueError) as e:
                self.logger.warning(f"Input validation failed: {e}")
                self.logger.info("Cleanup cancelled due to invalid input")
                return 0
            except Exception as e:
                # Handle SecurityError and other exceptions from secure input
                self.logger.warning(f"Input security check failed: {e}")
                self.logger.info("Cleanup cancelled due to security validation")
                return 0
            except (KeyboardInterrupt, EOFError):
                self.logger.info("Cleanup cancelled by user")
                return 0

        # Perform cleanup
        cleaned_count = 0
        for host in expired_hosts:
            hostname = host.get("hostname")
            cname = host.get("cname")

            # Remove host_vars file (check both hostname and cname)
            removed_file = False

            # Try hostname-based file first
            if hostname:
                host_var_file = self.config.host_vars_dir / f"{hostname}.yml"
                if host_var_file.exists():
                    host_var_file.unlink()
                    self.logger.info(f"Removed host_vars file: {hostname}.yml")
                    removed_file = True

            # Also check for cname-based file
            if cname and not removed_file:
                cname_var_file = self.config.host_vars_dir / f"{cname}.yml"
                if cname_var_file.exists():
                    cname_var_file.unlink()
                    self.logger.info(f"Removed host_vars file: {cname}.yml")

            cleaned_count += 1

        # Remove from CSV
        all_hosts = self.load_hosts_from_csv_raw()
        expired_hostnames = {host.get("hostname") for host in expired_hosts}
        remaining_hosts = [
            h for h in all_hosts if h.get("hostname") not in expired_hostnames
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
                    "site_code",
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
