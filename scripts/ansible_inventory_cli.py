#!/usr/bin/env python3
"""
Modular Ansible Inventory CLI.

A comprehensive command-line interface for managing Ansible inventory files
with support for multiple data sources and dynamic inventory generation.

Author: J Goossens <jgoos@users.noreply.github.com>
Version: 2.0.0

CSV Product Columns (Dynamic System):
-------------------------------------
This system supports a flexible number of product columns in your CSV file.

- You may define any number of columns named product_1, product_2, product_3, ...
- Each host can use as many or as few product columns as needed.
- Empty product columns are ignored for that host.
- There is no need for quoting or comma-separated product lists.
- Example CSV:

    hostname,environment,application_service,product_1,product_2,product_3
    prd-web-use1-1,production,web_server,web,analytics,monitoring
    dev-api-use1-1,development,api_server,api,,
    test-db-use1-1,test,database_server,db,backup,

- The system will automatically add each host to all relevant product groups (e.g., product_web, product_analytics, ...).
- You may add more product columns as needed (product_4, product_5, ...).
- Validation ensures there are no gaps in product column numbering for each host.

Migration:
----------
If you have an old CSV with a single 'product_id' column (comma-separated), use:
    python3 scripts/convert_csv_to_dynamic_products.py inventory_source/hosts.csv

This will convert your CSV to the new format with product_1, product_2, ... columns.

For more details, see the README or documentation.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

if __name__ == "__main__" and __package__ is None:
    # Add the parent directory to sys.path so "scripts" is treated as a package
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "scripts"

from .commands.base import BaseCommand  # noqa: E402
from .core import (  # noqa: E402
    CSV_FILE,
    LOG_LEVEL,
    PROJECT_ROOT,
    VERSION,
    get_logger,
    setup_logging,
)


class CommandRegistry:
    """Registry for all available CLI commands.

    This registry automatically discovers and manages all available commands,
    providing a centralized location for command registration and instantiation.
    """

    def __init__(self) -> None:
        """Initialise the registry with built-in commands."""
        self._commands: Dict[str, Any] = {}
        self._register_commands()

    def _register_commands(self) -> None:
        """Auto-discover and register all commands.

        This method imports and registers all built-in commands.
        Commands should follow the naming convention: {name}Command
        """
        try:
            from .commands.generate_command import GenerateCommand
            from .commands.health_command import HealthCommand
            from .commands.lifecycle_command import LifecycleCommand
            from .commands.validate_command import ValidateCommand

            self.register("generate", GenerateCommand)
            self.register("health", HealthCommand)
            self.register("validate", ValidateCommand)
            self.register("lifecycle", LifecycleCommand)

        except ImportError as e:
            raise ImportError(f"Failed to import command modules: {e}") from e

    def register(self, name: str, command_class: Any) -> None:
        """Register a new command with validation.

        Args:
            name: Command name (used in CLI)
            command_class: Class that implements BaseCommand interface

        Raises:
            ValueError: If command name is invalid or already registered
        """
        if not name or not isinstance(name, str):
            raise ValueError("Command name must be a non-empty string")

        if name in self._commands:
            raise ValueError(f"Command '{name}' is already registered")

        # Validate that command_class is a proper command
        if not hasattr(command_class, "execute") or not hasattr(
            command_class, "add_parser_arguments"
        ):
            raise ValueError(
                f"Command class '{command_class.__name__}' must implement "
                "BaseCommand interface (execute and add_parser_arguments methods)"
            )

        self._commands[name] = command_class

    def get_command_class(self, name: str) -> Any:
        """Get the class for a registered command.

        Args:
            name: Command name

        Returns:
            Command class

        Raises:
            ValueError: If command is not registered
        """
        if name not in self._commands:
            available = ", ".join(sorted(self._commands.keys()))
            raise ValueError(
                f"Unknown command: '{name}'. Available commands: {available}"
            )
        return self._commands[name]

    def get_available_commands(self) -> List[str]:
        """Get list of all registered command names.

        Returns:
            Sorted list of command names
        """
        return sorted(self._commands.keys())

    def create_command(
        self, name: str, csv_file: Optional[Path] = None, logger: Optional[Any] = None
    ) -> BaseCommand:
        """Create a command instance with the given parameters.

        Args:
            name: Command name
            csv_file: Optional CSV file path
            logger: Optional logger instance

        Returns:
            Instantiated command object

        Raises:
            ValueError: If command creation fails
        """
        try:
            command_class = self.get_command_class(name)
            return command_class(csv_file, logger)
        except Exception as e:
            raise ValueError(f"Failed to create command '{name}': {e}") from e


class ModularInventoryCLI:
    """Ansible Inventory Management CLI."""

    def __init__(self) -> None:
        """Create the CLI and prepare logging."""
        self.logger = get_logger(__name__)
        self.command_registry = CommandRegistry()
        self.start_time = time.time()
        self._last_command = None

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

CSV Product Columns (Dynamic System):
-------------------------------------
- Use columns named product_1, product_2, product_3, ... in your CSV.
- Each host can use as many or as few product columns as needed.
- Empty product columns are ignored.
- Example:
    hostname,environment,application_service,product_1,product_2,product_3
    prd-web-use1-1,production,web_server,web,analytics,monitoring
    dev-api-use1-1,development,api_server,api,,
    test-db-use1-1,test,database_server,db,backup,
- The system will automatically add each host to all relevant product groups.
- To migrate from old CSVs, use:
    python3 scripts/convert_csv_to_dynamic_products.py inventory_source/hosts.csv

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
            type=self._validate_csv_path,
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
                try:
                    # Try to use static method first, fall back to instance method
                    if hasattr(command_class, "add_parser_arguments_static"):
                        command_class.add_parser_arguments_static(command_parser)
                    else:
                        temp_command = command_class()
                        temp_command.add_parser_arguments(command_parser)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to initialize command {command_name}: {e}"
                    )
                    # Create a minimal parser as fallback
                    pass

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

            # Store command instance for reuse in formatting
            self._last_command = command

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
                # Reuse the command instance if available
                command = getattr(self, "_last_command", None)
                if command is None:
                    command = self.command_registry.create_command(
                        command_name, getattr(args, "csv_file", None), self.logger
                    )

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
        """Run the command-line interface."""
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

    def _validate_csv_path(self, path_str: str) -> Path:
        """Validate the CSV file path to ensure it doesn't escape the project boundaries."""
        path = Path(path_str)

        # Convert to absolute path for comparison
        if not path.is_absolute():
            path = Path.cwd() / path

        # Get the absolute project root path
        project_root_abs = PROJECT_ROOT.resolve()

        try:
            # Resolve the path to handle any .. or symlinks
            path_abs = path.resolve()

            # Check if the path is within the project root
            path_abs.relative_to(project_root_abs)
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"CSV file path must be within the project directory: {path_str}"
            )

        # Check if file exists
        if not path_abs.exists():
            raise argparse.ArgumentTypeError(f"CSV file does not exist: {path_str}")

        # Check if it's a regular file
        if not path_abs.is_file():
            raise argparse.ArgumentTypeError(
                f"CSV file must be a regular file: {path_str}"
            )

        # Check if it's a CSV file
        if not path_abs.suffix.lower() == ".csv":
            raise argparse.ArgumentTypeError(
                f"File must have .csv extension: {path_str}"
            )

        return path_abs


def main() -> None:
    """Execute the CLI entry point."""
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
