#!/usr/bin/env python3
"""
Ansible Inventory Management CLI

A comprehensive tool for managing Ansible inventories using CSV data sources
with a clean modular command architecture.

Author: J Goossens <jgoos@users.noreply.github.com>
Version: 2.0.0
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Add current directory to path for imports
SCRIPT_DIR = Path(__file__).parent.absolute()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from commands.base import BaseCommand
from core import CSV_FILE, LOG_LEVEL, VERSION, get_logger, setup_logging

class CommandRegistry:
    """Registry for all available CLI commands."""

    def __init__(self) -> None:
        self._commands: Dict[str, Any] = {}
        self._register_commands()

    def _register_commands(self) -> None:
        """Auto-discover and register all commands."""
        from commands.generate_command import GenerateCommand
        from commands.health_command import HealthCommand
        from commands.lifecycle_command import LifecycleCommand
        from commands.validate_command import ValidateCommand

        self.register("generate", GenerateCommand)
        self.register("health", HealthCommand)
        self.register("validate", ValidateCommand)
        self.register("lifecycle", LifecycleCommand)

    def register(self, name: str, command_class: Any) -> None:
        """Register a new command."""
        self._commands[name] = command_class

    def get_command_class(self, name: str) -> Any:
        """Get the class for a registered command."""
        if name not in self._commands:
            raise ValueError(f"Unknown command: {name}")
        return self._commands[name]

    def create_command(
        self, name: str, csv_file: Optional[Path] = None, logger: Optional[Any] = None
    ) -> BaseCommand:
        """Create an instance of a registered command."""
        command_class = self.get_command_class(name)
        return command_class(csv_file=csv_file, logger=logger)

    def get_available_commands(self) -> list[str]:
        """Get a list of all registered command names."""
        return sorted(self._commands.keys())


class ModularInventoryCLI:
    """Ansible Inventory Management CLI."""

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        self.command_registry = CommandRegistry()
        self.start_time = time.time()

    def create_parser(self) -> argparse.ArgumentParser:
        """Create the main argument parser with all subcommands."""
        parser = argparse.ArgumentParser(
            description="Ansible Inventory Management Tool",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Generate inventory files
  %(prog)s generate --dry-run
  %(prog)s generate --environments production development

  # Health monitoring
  %(prog)s health --threshold 80

  # Validation
  %(prog)s validate --comprehensive

  # Host lifecycle management
  %(prog)s lifecycle decommission --hostname prd-web-use1-1 --date 2025-1-15
  %(prog)s lifecycle cleanup --dry-run

  # Import existing inventories
  

  

For more information, see the documentation at:
https://github.com/your-org/inventory-structure
            """,
        )

        # Global arguments
        parser.add_argument(
            "--version", action="version", version=f"%(prog)s {VERSION}"
        )
        parser.add_argument(
            "--csv-file",
            type=Path,
            default=CSV_FILE,
            help=f"CSV source file (default: {CSV_FILE})",
        )
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default=LOG_LEVEL,
            help=f"Logging level (default: {LOG_LEVEL})",
        )
        parser.add_argument(
            "--json", action="store_true", help="Output results in JSON format"
        )
        parser.add_argument(
            "--quiet", "-q", action="store_true", help="Suppress non-error output"
        )
        parser.add_argument(
            "--timing", action="store_true", help="Show execution timing information"
        )

        # Create subparsers for commands
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Add all registered commands
        for command_name in self.command_registry.get_available_commands():
            command_class = self.command_registry.get_command_class(command_name)

            # Create subparser for this command
            if command_name == "lifecycle":
                command_parser = subparsers.add_parser(
                    command_name, help="Host lifecycle management"
                )
            
            elif command_name == "generate":
                command_parser = subparsers.add_parser(
                    command_name, help="Generate inventory files from CSV"
                )
            elif command_name == "health":
                command_parser = subparsers.add_parser(
                    command_name, help="Monitor inventory health and consistency"
                )
            elif command_name == "validate":
                command_parser = subparsers.add_parser(
                    command_name, help="Validate inventory structure and data"
                )
            else:
                command_parser = subparsers.add_parser(command_name)

            # Let the command class add its arguments
            if command_class:
                temp_command = command_class()
                temp_command.add_parser_arguments(command_parser)

        return parser

    def execute_command(self, args: Any) -> dict:
        """Execute the specified command with arguments."""
        if not args.command:
            return {
                "success": False,
                "error": "No command specified. Use --help to see available commands.",
            }

        try:
            # Create command instance
            command = self.command_registry.create_command(
                args.command, args.csv_file, self.logger
            )

            # Execute the command
            result = command.execute(args)

            # Add timing information if requested
            if args.timing:
                execution_time = time.time() - self.start_time
                result["execution_time"] = round(execution_time, 3)

            if not isinstance(result, dict):
                return {"success": False, "error": "Command did not return a dict."}
            return result

        except ValueError:
            return {"success": False, "error": f"Unknown command: {args.command}"}
        except FileNotFoundError as e:
            self.logger.error(f"File not found: {e}")
            return {"success": False, "error": f"File not found: {e}"}
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}", exc_info=True)
            return {"success": False, "error": f"An unexpected error occurred: {e}"}

    def format_output(self, result: dict, args: Any) -> str:
        """Format command result for output."""
        if args.json:
            return json.dumps(result, indent=2, default=str)

        # Try to use command-specific formatting if available
        command_name = getattr(args, "command", None)
        if command_name:
            try:
                command = self.command_registry.create_command(command_name)
                if hasattr(command, "format_text_output"):
                    output = command.format_text_output(result)
                    if not isinstance(output, str):
                        return str(output)
                    return output
            except Exception as e:
                self.logger.error(
                    f"Error formatting output for command '{command_name}': {e}",
                    exc_info=True,
                )
                # Fall back to generic formatting

        # Generic text formatting
        if result.get("success", False):
            lines = []
            if result.get("message"):
                lines.append(f"✅ {result['message']}")

            if result.get("data"):
                lines.append(json.dumps(result["data"], indent=2, default=str))

            # Show timing if available
            if "execution_time" in result:
                lines.append(f"⏱️  Execution time: {result['execution_time']}s")

            return "\n".join(lines) if lines else "✅ Command completed successfully"
        else:
            error = result.get("error", "Unknown error")
            return f"❌ {error}"

    def run(self, argv: Any = None) -> None:
        """Main entry point for the CLI."""
        parser = self.create_parser()
        args = parser.parse_args(argv)

        # Setup logging
        setup_logging(args.log_level)

        # Log startup information
        if not args.quiet:
            self.logger.info(f"Ansible Inventory Management CLI v{VERSION}")
            self.logger.info(f"CSV Source: {args.csv_file}")

        # Execute command
        result = self.execute_command(args)

        # Format and output result
        if not args.quiet or not result.get("success", False):
            output = self.format_output(result, args)
            print(output)

        # Exit with appropriate code
        sys.exit(0 if result.get("success", False) else 1)


def main() -> None:
    """Main entry point."""
    try:
        cli = ModularInventoryCLI()
        cli.run()
    except FileNotFoundError as e:
        logger = get_logger(__name__)
        logger.error(f"File not found: {e}")
        print(f"❌ File not found: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()