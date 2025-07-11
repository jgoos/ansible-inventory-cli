#!/usr/bin/env python3
"""
Health command - system health monitoring.

This command provides comprehensive health monitoring for the inventory system,
including file consistency checks, orphaned file detection, and health scoring.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from ..core import get_logger
from ..managers.validation_manager import ValidationManager
from .base import BaseCommand, CommandResult


class HealthCommand(BaseCommand):
    """Command to perform health monitoring and scoring."""

    logger: logging.Logger  # Explicitly declare logger as non-optional

    def __init__(
        self, csv_file: Optional[Path] = None, logger: Optional[logging.Logger] = None
    ) -> None:
        """Initialise the command with optional CSV path and logger."""
        super().__init__(csv_file, logger)
        self.logger = logger or get_logger(__name__)
        self.validation_manager = ValidationManager(csv_file, self.logger)

    def add_parser_arguments(self, parser: Any) -> None:
        """Add health-specific arguments to parser."""
        parser.add_argument(
            "--detailed", action="store_true", help="Show detailed health information"
        )
        parser.add_argument(
            "--threshold",
            type=float,
            default=70.0,
            help="Health score threshold for warnings (default: 70.0)",
        )

    def execute(self, args: Any) -> Dict[str, Any]:
        """Execute the health command."""
        try:
            self.logger.info("🏥 Starting health monitoring")

            # Get health information from validation manager
            health_result = self.validation_manager.check_health()

            # Add command metadata
            result_data = {"command": "health", "success": True, **health_result}

            # Check if health score meets threshold
            health_score = health_result.get("health_score", 0)
            threshold = args.threshold

            if health_score < threshold:
                warning_msg = "Health score {}% is below threshold {}%".format(
                    health_score, threshold
                )
                self.logger.warning(warning_msg)
                result_data["warning"] = warning_msg

            message = "Health Score: {}% ({})".format(
                health_score, health_result.get("health_status", "UNKNOWN")
            )

            return CommandResult(
                success=True, data=result_data, message=message
            ).to_dict()

        except Exception as e:
            error_msg = f"Health check failed: {e}"
            self.logger.error(error_msg)
            return CommandResult(success=False, error=error_msg).to_dict()

    def format_text_output(self, result: Dict[str, Any]) -> str:
        """Format health result for text output."""
        if not result.get("success", False):
            return f"❌ Health check failed: {result.get('error', 'Unknown error')}"

        data = result.get("data", {})

        # Header
        lines = ["🏥 INVENTORY HEALTH MONITORING"]

        # Main health metrics
        health_score = data.get("health_score", 0)
        health_status = data.get("health_status", "UNKNOWN")

        # Status emoji
        status_emoji = {
            "EXCELLENT": "🟢",
            "GOOD": "🟡",
            "FAIR": "🟠",
            "POOR": "🔴",
            "CRITICAL": "🚨",
        }.get(health_status, "❓")

        lines.extend(
            [
                "Health Score: {} {}% ({})".format(
                    status_emoji, health_score, health_status
                ),
                "Total Hosts: {}".format(data.get("total_hosts", 0)),
                "Active Hosts: {}".format(data.get("active_hosts", 0)),
                "Orphaned Files: {}".format(data.get("orphaned_host_vars", 0)),
                "Missing Files: {}".format(data.get("missing_host_vars", 0)),
            ]
        )

        # Show warning if below threshold
        if "warning" in data:
            lines.append(f"\n⚠️  {data['warning']}")

        # Orphaned files examples
        orphaned_files = data.get("orphaned_files", [])
        if orphaned_files:
            lines.append("\n📄 Orphaned host_vars examples:")
            for filename in orphaned_files[:3]:  # Show first 3
                lines.append("   • {}.yml".format(filename))
            if len(orphaned_files) > 3:
                lines.append("   ... and {} more".format(len(orphaned_files) - 3))

        # Missing files examples
        missing_files = data.get("missing_files", [])
        if missing_files:
            lines.append("\n❓ Missing host_vars examples:")
            for hostname in missing_files[:3]:  # Show first 3
                lines.append("   • {}.yml".format(hostname))
            if len(missing_files) > 3:
                lines.append("   ... and {} more".format(len(missing_files) - 3))

        # Recommendations
        recommendations = data.get("recommendations", [])
        if recommendations:
            lines.append("\n💡 Recommendations:")
            for rec in recommendations:
                lines.append(f"   • {rec}")

        return "\n".join(lines)
