#!/usr/bin/env python3
"""
Lifecycle command - host lifecycle management.

This command handles host lifecycle operations including decommissioning,
cleanup, and expired host management.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from ..core import get_logger
from ..managers.host_manager import HostManager

from .base import BaseCommand, CommandResult



class LifecycleCommand(BaseCommand):
    """Command to manage host lifecycle operations."""

    logger: logging.Logger  # Explicitly declare logger as non-optional

    def __init__(
        self, csv_file: Optional[Path] = None, logger: Optional[logging.Logger] = None
    ) -> None:
        """Initialise the command with optional CSV path and logger."""
        super().__init__(csv_file, logger)
        self.logger = logger or get_logger(__name__)
        self.host_manager = HostManager(csv_file, self.logger)

    def add_parser_arguments(self, parser: Any) -> None:
        """Add lifecycle-specific arguments to parser."""
        lifecycle_subparsers = parser.add_subparsers(
            dest="lifecycle_action", help="Lifecycle actions"
        )

        # Decommission command
        decommission_parser = lifecycle_subparsers.add_parser(
            "decommission", help="Decommission a host"
        )
        decommission_parser.add_argument(
            "--hostname", required=True, help="Hostname to decommission"
        )
        decommission_parser.add_argument(
            "--date", required=True, help="Decommission date (YYYY-MM-DD)"
        )
        decommission_parser.add_argument(
            "--reason", default="", help="Reason for decommissioning"
        )
        decommission_parser.add_argument(
            "--dry-run", action="store_true", help="Show what would be done"
        )

        # List expired command
        list_parser = lifecycle_subparsers.add_parser(
            "list-expired", help="List expired hosts"
        )
        list_parser.add_argument(
            "--grace-days", type=int, help="Override grace period days"
        )

        # Cleanup command
        cleanup_parser = lifecycle_subparsers.add_parser(
            "cleanup", help="Clean up expired hosts"
        )
        cleanup_parser.add_argument(
            "--grace-days", type=int, help="Override grace period days"
        )
        cleanup_parser.add_argument(
            "--dry-run", action="store_true", help="Show what would be cleaned up"
        )
        cleanup_parser.add_argument(
            "--auto-confirm", action="store_true", help="Skip confirmation prompt"
        )
        cleanup_parser.add_argument(
            "--max-hosts", type=int, help="Maximum number of hosts to clean up"
        )

    def execute(self, args: Any) -> Dict[str, Any]:
        """Execute the lifecycle command."""
        try:
            action = getattr(args, "lifecycle_action", None)

            if action == "decommission":
                return self._handle_decommission(args)
            elif action == "list-expired":
                return self._handle_list_expired(args)
            elif action == "cleanup":
                return self._handle_cleanup(args)
            else:
                return CommandResult(
                    success=False,
                    error="No lifecycle action specified. Use 'decommission', 'list-expired', or 'cleanup'.",
                ).to_dict()

        except Exception as e:
            error_msg = f"Lifecycle operation failed: {e}"
            self.logger.error(error_msg)
            return CommandResult(success=False, error=error_msg).to_dict()

    def _handle_decommission(self, args: Any) -> Dict[str, Any]:
        """Handle host decommissioning."""
        self.logger.info(f"🔄 Decommissioning host: {args.hostname}")

        success = self.host_manager.decommission_host(
            hostname=args.hostname,
            date=args.date,
            reason=args.reason,
            dry_run=args.dry_run,
        )

        if success:
            action_text = "Would decommission" if args.dry_run else "Decommissioned"
            message = f"{action_text} host {args.hostname} with date {args.date}"

            result_data = {
                "command": "lifecycle",
                "action": "decommission",
                "hostname": args.hostname,
                "date": args.date,
                "reason": args.reason,
                "dry_run": args.dry_run,
                "success": True,
            }

            return CommandResult(
                success=True, data=result_data, message=message
            ).to_dict()
        else:
            error_msg = f"Failed to decommission host {args.hostname}"
            return CommandResult(success=False, error=error_msg).to_dict()

    def _handle_list_expired(self, args: Any) -> Dict[str, Any]:
        """Handle listing expired hosts."""
        self.logger.info("📋 Listing expired hosts")

        expired_hosts = self.host_manager.list_expired_hosts(
            grace_days_override=args.grace_days
        )

        result_data = {
            "command": "lifecycle",
            "action": "list-expired",
            "expired_hosts": expired_hosts,
            "total_expired": len(expired_hosts),
            "grace_days_override": args.grace_days,
        }

        message = f"Found {len(expired_hosts)} expired hosts"

        return CommandResult(success=True, data=result_data, message=message).to_dict()

    def _handle_cleanup(self, args: Any) -> Dict[str, Any]:
        """Handle cleaning up expired hosts."""
        self.logger.info("🧹 Cleaning up expired hosts")

        cleaned_count = self.host_manager.cleanup_expired_hosts(
            grace_days_override=args.grace_days,
            dry_run=args.dry_run,
            auto_confirm=args.auto_confirm,
            max_hosts=args.max_hosts,
        )

        action_text = "Would clean up" if args.dry_run else "Cleaned up"
        message = f"{action_text} {cleaned_count} expired hosts"

        result_data = {
            "command": "lifecycle",
            "action": "cleanup",
            "cleaned_count": cleaned_count,
            "dry_run": args.dry_run,
            "grace_days_override": args.grace_days,
            "max_hosts": args.max_hosts,
            "auto_confirm": args.auto_confirm,
        }

        return CommandResult(success=True, data=result_data, message=message).to_dict()

    def format_text_output(self, result: Dict[str, Any]) -> str:
        """Format lifecycle result for text output."""
        if not result.get("success", False):
            return (
                f"❌ Lifecycle operation failed: {result.get('error', 'Unknown error')}"
            )

        data = result.get("data", {})
        action = data.get("action", "unknown")

        if action == "decommission":
            hostname = data.get("hostname", "unknown")
            date = data.get("date", "unknown")
            reason = data.get("reason", "")
            dry_run = data.get("dry_run", False)

            action_emoji = "🔍" if dry_run else "✅"
            action_text = "Would decommission" if dry_run else "Decommissioned"

            lines = [
                "🔄 HOST DECOMMISSIONING",
                f"{action_emoji} {action_text} host: {hostname}",
                f"Date: {date}",
            ]

            if reason:
                lines.append(f"Reason: {reason}")

            if dry_run:
                lines.append("\n🔍 This was a dry run - no changes were made")

            return "\n".join(lines)

        elif action == "list-expired":
            expired_hosts = data.get("expired_hosts", [])
            total_expired = data.get("total_expired", 0)
            grace_override = data.get("grace_days_override")

            lines = ["📋 EXPIRED HOSTS REPORT", f"Total expired hosts: {total_expired}"]

            if grace_override:
                lines.append(f"Grace period override: {grace_override} days")

            if expired_hosts:
                lines.append("\nExpired hosts:")
                for host in expired_hosts[:10]:  # Show first 10
                    hostname = host.get("hostname", "unknown")
                    days_expired = host.get("days_expired", 0)
                    environment = host.get("environment", "unknown")
                    lines.append(
                        f"  • {hostname} ({environment}) - expired {days_expired} days ago"
                    )

                if len(expired_hosts) > 10:
                    lines.append(f"  ... and {len(expired_hosts) - 10} more")
            else:
                lines.append("\n✅ No expired hosts found")

            return "\n".join(lines)

        elif action == "cleanup":
            cleaned_count = data.get("cleaned_count", 0)
            dry_run = data.get("dry_run", False)
            max_hosts = data.get("max_hosts")

            action_emoji = "🔍" if dry_run else "✅"
            action_text = "Would clean up" if dry_run else "Cleaned up"

            lines = [
                "🧹 HOST CLEANUP OPERATION",
                f"{action_emoji} {action_text}: {cleaned_count} hosts",
            ]

            if max_hosts:
                lines.append(f"Maximum hosts limit: {max_hosts}")

            if dry_run:
                lines.append("\n🔍 This was a dry run - no changes were made")
            elif cleaned_count > 0:
                lines.append("\n✅ Cleanup completed successfully")
            else:
                lines.append("\n✅ No hosts required cleanup")

            return "\n".join(lines)

        else:
            return f"❓ Unknown lifecycle action: {action}"
