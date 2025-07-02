#!/usr/bin/env python3
"""
Validate Command - Infrastructure Validation

This command handles comprehensive validation of the inventory structure,
CSV data consistency, and Ansible configuration integrity.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

SCRIPT_DIR = Path(__file__).parent.parent.absolute()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from core import get_logger
from core.utils import create_csv_file, get_csv_template
from managers.validation_manager import ValidationManager

from .base import BaseCommand, CommandResult


class ValidateCommand(BaseCommand):
    """Command to validate inventory structure and configuration."""

    def __init__(
        self, csv_file: Optional[Path] = None, logger: Optional[Any] = None
    ) -> None:
        super().__init__(csv_file, logger)
        self.logger = logger or get_logger(__name__)
        self.validation_manager = ValidationManager(csv_file, self.logger)

    def add_parser_arguments(self, parser: Any) -> None:
        """Add validate-specific arguments to parser."""
        parser.add_argument(
            "--comprehensive",
            action="store_true",
            help="Run comprehensive validation including CSV and host_vars consistency",
        )
        parser.add_argument(
            "--csv-only", action="store_true", help="Validate only CSV data structure"
        )
        parser.add_argument(
            "--structure-only",
            action="store_true",
            help="Validate only directory structure and configuration",
        )
        parser.add_argument(
            "--template",
            action="store_true",
            help="Show CSV template with required headers",
        )
        parser.add_argument(
            "--create-csv",
            type=Path,
            metavar="FILE",
            help="Create a new CSV file with template content",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing file when using --create-csv",
        )

    def execute(self, args: Any) -> Dict[str, Any]:
        """Execute the validate command."""
        try:
            # Handle CSV creation request
            if args.create_csv:
                try:
                    create_csv_file(args.create_csv, args.overwrite)
                    return CommandResult(
                        success=True,
                        data={"created_file": str(args.create_csv)},
                        message=f"✅ Created CSV file: {args.create_csv}",
                    ).to_dict()
                except Exception as e:
                    return CommandResult(
                        success=False,
                        error=f"Failed to create CSV file: {e}",
                    ).to_dict()

            # Handle template request
            if args.template:
                template = get_csv_template()
                return CommandResult(
                    success=True,
                    data={"template": template},
                    message="CSV template generated",
                ).to_dict()

            self.logger.info("✅ Starting infrastructure validation")

            validation_results = {}
            overall_success = True
            total_errors = 0
            total_warnings = 0

            # Determine what to validate based on arguments
            if args.csv_only:
                # Only CSV validation
                csv_validation = self.validation_manager.validate_csv_data()
                validation_results["csv_validation"] = {
                    "passed": csv_validation.is_valid,
                    "errors": csv_validation.errors,
                    "warnings": csv_validation.warnings,
                    "summary": csv_validation.get_summary(),
                }
                overall_success = csv_validation.is_valid
                total_errors = len(csv_validation.errors)
                total_warnings = len(csv_validation.warnings)

            elif args.structure_only:
                # Only structure validation
                structure_result = self.validation_manager.validate_structure()
                validation_results["structure_validation"] = structure_result
                overall_success = structure_result.get("passed", False)
                total_errors = structure_result.get("total_errors", 0)
                total_warnings = structure_result.get("total_warnings", 0)

            else:
                # Standard validation (structure + basic CSV)
                structure_result = self.validation_manager.validate_structure()
                validation_results["structure_validation"] = structure_result

                overall_success = structure_result.get("passed", False)
                total_errors = structure_result.get("total_errors", 0)
                total_warnings = structure_result.get("total_warnings", 0)

                # If comprehensive validation requested, add more checks
                if args.comprehensive:
                    csv_validation = self.validation_manager.validate_csv_data()
                    validation_results["csv_validation"] = {
                        "passed": csv_validation.is_valid,
                        "errors": csv_validation.errors,
                        "warnings": csv_validation.warnings,
                        "summary": csv_validation.get_summary(),
                    }

                    host_vars_validation = (
                        self.validation_manager.validate_host_vars_consistency()
                    )
                    validation_results["host_vars_validation"] = {
                        "passed": host_vars_validation.is_valid,
                        "errors": host_vars_validation.errors,
                        "warnings": host_vars_validation.warnings,
                        "summary": host_vars_validation.get_summary(),
                    }

                    # Update overall results
                    overall_success = (
                        overall_success
                        and csv_validation.is_valid
                        and host_vars_validation.is_valid
                    )
                    total_errors += len(csv_validation.errors) + len(
                        host_vars_validation.errors
                    )
                    total_warnings += len(csv_validation.warnings) + len(
                        host_vars_validation.warnings
                    )

            # Prepare result
            result_data = {
                "command": "validate",
                "success": overall_success,
                "validation_results": validation_results,
                "summary": {
                    "total_errors": total_errors,
                    "total_warnings": total_warnings,
                    "overall_status": "PASSED" if overall_success else "FAILED",
                },
            }

            status_text = "PASSED" if overall_success else "FAILED"
            message = (
                f"Validation {status_text}: {total_errors} errors, "
                f"{total_warnings} warnings"
            )

            return CommandResult(
                success=overall_success, data=result_data, message=message
            ).to_dict()

        except Exception as e:
            error_msg = f"Validation failed: {e}"
            self.logger.error(error_msg)
            return CommandResult(success=False, error=error_msg).to_dict()

    def format_text_output(self, result: Dict[str, Any]) -> str:
        """Format validation result for text output."""
        if not result.get("success", False) and "error" in result:
            return f"❌ Validation failed: {result.get('error', 'Unknown error')}"

        data = result.get("data", {})

        # Handle CSV creation output
        if "created_file" in data:
            file_path = data["created_file"]
            lines = [
                f"✅ CSV file created successfully: {file_path}",
                "",
                "📝 Next steps:",
                "1. Edit the CSV file to add your host data",
                "2. Remove the # comments from example rows to activate them",
                "3. Run 'ansible-inventory-cli validate' to check your data",
                "4. Run 'ansible-inventory-cli generate' to create inventory files",
                "",
                "💡 Tip: Use 'ansible-inventory-cli validate --template' "
                "to see the CSV format",
            ]
            return "\n".join(lines)

        # Handle template output
        if "template" in data:
            return f"📄 CSV Template:\n\n{data['template']}"
        validation_results = data.get("validation_results", {})
        summary = data.get("summary", {})

        # Header
        overall_status = summary.get("overall_status", "UNKNOWN")
        status_emoji = "✅" if overall_status == "PASSED" else "❌"

        lines = [
            "🔍 INVENTORY VALIDATION RESULTS",
            f"Overall Status: {status_emoji} {overall_status}",
            f"Total Errors: {summary.get('total_errors', 0)}",
            f"Total Warnings: {summary.get('total_warnings', 0)}",
            "",
        ]

        # Structure validation
        if "structure_validation" in validation_results:
            struct_result = validation_results["structure_validation"]
            struct_status = (
                "✅ PASSED" if struct_result.get("passed", False) else "❌ FAILED"
            )
            lines.append(f"📁 Structure Validation: {struct_status}")

            if struct_result.get("issues"):
                lines.append("   Issues:")
                for issue in struct_result["issues"][:5]:  # Show first 5
                    lines.append(f"     • {issue}")

            if struct_result.get("warnings"):
                lines.append("   Warnings:")
                for warning in struct_result["warnings"][:5]:  # Show first 5
                    lines.append(f"     • {warning}")

            if struct_result.get("ansible_version"):
                lines.append(f"   Ansible Version: {struct_result['ansible_version']}")

            lines.append("")

        # CSV validation
        if "csv_validation" in validation_results:
            csv_result = validation_results["csv_validation"]
            csv_status = "✅ PASSED" if csv_result.get("passed", False) else "❌ FAILED"
            lines.append(f"📄 CSV Data Validation: {csv_status}")

            if csv_result.get("errors"):
                lines.append("   Errors:")
                for error in csv_result["errors"][:5]:  # Show first 5
                    lines.append(f"     • {error}")

            if csv_result.get("warnings"):
                lines.append("   Warnings:")
                for warning in csv_result["warnings"][:5]:  # Show first 5
                    lines.append(f"     • {warning}")

            lines.append("")

        # Host vars validation
        if "host_vars_validation" in validation_results:
            hv_result = validation_results["host_vars_validation"]
            hv_status = "✅ PASSED" if hv_result.get("passed", False) else "❌ FAILED"
            lines.append(f"🖥️  Host Vars Validation: {hv_status}")

            if hv_result.get("errors"):
                lines.append("   Errors:")
                for error in hv_result["errors"][:5]:  # Show first 5
                    lines.append(f"     • {error}")

            if hv_result.get("warnings"):
                lines.append("   Warnings:")
                for warning in hv_result["warnings"][:5]:  # Show first 5
                    lines.append(f"     • {warning}")

            lines.append("")

        # Summary
        if overall_status == "PASSED":
            lines.append("🎉 All validations passed successfully!")
        else:
            lines.append("🔧 Please address the issues above and run validation again.")

        return "\n".join(lines)
