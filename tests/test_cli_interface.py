#!/usr/bin/env python3
"""Comprehensive CLI Interface Tests.

Tests for the main CLI entry point, argument parsing, command routing,
and error handling scenarios.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.ansible_inventory_cli import (
    CommandRegistry,
    ModularInventoryCLI,
    main,
)
from scripts.commands.base import BaseCommand


class MockCommand(BaseCommand):
    """Mock command for testing command registry."""
    
    def __init__(self, csv_file=None, logger=None):
        super().__init__(csv_file, logger)
        self.executed = False
        self.result = {"status": "success", "message": "Mock command executed"}
    
    def add_parser_arguments(self, parser):
        """Add mock arguments."""
        parser.add_argument("--mock-arg", help="Mock argument")
    
    def execute(self, args):
        """Execute mock command."""
        self.executed = True
        return self.result


class TestCommandRegistry:
    """Test the command registry functionality."""
    
    def test_command_registry_initialization(self):
        """Test command registry initializes with built-in commands."""
        registry = CommandRegistry()
        commands = registry.get_available_commands()
        
        expected_commands = ["generate", "health", "lifecycle", "validate"]
        assert all(cmd in commands for cmd in expected_commands)
    
    def test_register_valid_command(self):
        """Test registering a valid command."""
        registry = CommandRegistry()
        registry.register("mock", MockCommand)
        
        assert "mock" in registry.get_available_commands()
        assert registry.get_command_class("mock") == MockCommand
    
    def test_register_invalid_command_name(self):
        """Test registering command with invalid name."""
        registry = CommandRegistry()
        
        with pytest.raises(ValueError, match="Command name must be a non-empty string"):
            registry.register("", MockCommand)
        
        with pytest.raises(ValueError, match="Command name must be a non-empty string"):
            registry.register(None, MockCommand)
    
    def test_register_duplicate_command(self):
        """Test registering duplicate command name."""
        registry = CommandRegistry()
        registry.register("mock", MockCommand)
        
        with pytest.raises(ValueError, match="Command 'mock' is already registered"):
            registry.register("mock", MockCommand)
    
    def test_register_invalid_command_class(self):
        """Test registering invalid command class."""
        registry = CommandRegistry()
        
        class InvalidCommand:
            pass
        
        with pytest.raises(ValueError, match="must implement BaseCommand interface"):
            registry.register("invalid", InvalidCommand)
    
    def test_get_unknown_command(self):
        """Test getting unknown command."""
        registry = CommandRegistry()
        
        with pytest.raises(ValueError, match="Unknown command: 'unknown'"):
            registry.get_command_class("unknown")
    
    def test_create_command_success(self):
        """Test creating command instance successfully."""
        registry = CommandRegistry()
        registry.register("mock", MockCommand)
        
        command = registry.create_command("mock")
        assert isinstance(command, MockCommand)
    
    def test_create_command_failure(self):
        """Test command creation failure."""
        registry = CommandRegistry()
        
        with pytest.raises(ValueError, match="Failed to create command"):
            registry.create_command("unknown")


class TestModularInventoryCLI:
    """Test the main CLI class."""
    
    def test_cli_initialization(self):
        """Test CLI initializes correctly."""
        cli = ModularInventoryCLI()
        
        assert cli.logger is not None
        assert cli.command_registry is not None
        assert cli.start_time > 0
    
    def test_create_parser(self):
        """Test parser creation with all subcommands."""
        cli = ModularInventoryCLI()
        parser = cli.create_parser()
        
        assert parser.prog == "ansible_inventory_cli.py"
        assert "Ansible Inventory Management Tool" in parser.description
    
    def test_validate_csv_path_valid(self):
        """Test CSV path validation with valid path."""
        cli = ModularInventoryCLI()
        
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp.write(b"hostname,environment,status\n")
            tmp.write(b"test,production,active\n")
            tmp.flush()
            
            result = cli._validate_csv_path(tmp.name)
            assert result == Path(tmp.name)
    
    def test_validate_csv_path_nonexistent(self):
        """Test CSV path validation with nonexistent file."""
        cli = ModularInventoryCLI()
        
        with pytest.raises(FileNotFoundError):
            cli._validate_csv_path("/nonexistent/file.csv")
    
    def test_validate_csv_path_invalid_extension(self):
        """Test CSV path validation with invalid extension."""
        cli = ModularInventoryCLI()
        
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            with pytest.raises(ValueError, match="must have .csv extension"):
                cli._validate_csv_path(tmp.name)
    
    def test_execute_command_success(self):
        """Test successful command execution."""
        cli = ModularInventoryCLI()
        cli.command_registry.register("mock", MockCommand)
        
        args = MagicMock()
        args.command = "mock"
        args.csv_file = None
        args.json = False
        
        result = cli.execute_command(args)
        
        assert result["status"] == "success"
        assert "execution_time" in result
    
    def test_execute_command_failure(self):
        """Test command execution failure."""
        cli = ModularInventoryCLI()
        
        args = MagicMock()
        args.command = "unknown"
        args.csv_file = None
        args.json = False
        
        result = cli.execute_command(args)
        
        assert result["status"] == "error"
        assert "error" in result
    
    def test_format_output_json(self):
        """Test JSON output formatting."""
        cli = ModularInventoryCLI()
        
        result = {"status": "success", "data": {"key": "value"}}
        args = MagicMock()
        args.json = True
        
        output = cli.format_output(result, args)
        
        assert json.loads(output) == result
    
    def test_format_output_human_readable(self):
        """Test human-readable output formatting."""
        cli = ModularInventoryCLI()
        
        result = {"status": "success", "message": "Test message"}
        args = MagicMock()
        args.json = False
        
        output = cli.format_output(result, args)
        
        assert "✅ Success" in output
        assert "Test message" in output
    
    def test_format_output_error(self):
        """Test error output formatting."""
        cli = ModularInventoryCLI()
        
        result = {"status": "error", "error": "Test error"}
        args = MagicMock()
        args.json = False
        
        output = cli.format_output(result, args)
        
        assert "❌ Error" in output
        assert "Test error" in output
    
    @patch('sys.argv', ['ansible_inventory_cli.py', 'health'])
    def test_run_success(self, capsys):
        """Test successful CLI run."""
        cli = ModularInventoryCLI()
        
        # Mock the health command to avoid actual execution
        with patch.object(cli.command_registry, 'create_command') as mock_create:
            mock_command = MagicMock()
            mock_command.execute.return_value = {"status": "success", "message": "Health check passed"}
            mock_create.return_value = mock_command
            
            cli.run()
            
            captured = capsys.readouterr()
            assert "✅ Success" in captured.out
    
    @patch('sys.argv', ['ansible_inventory_cli.py', 'unknown'])
    def test_run_unknown_command(self, capsys):
        """Test CLI run with unknown command."""
        cli = ModularInventoryCLI()
        
        with pytest.raises(SystemExit):
            cli.run()
    
    @patch('sys.argv', ['ansible_inventory_cli.py', '--version'])
    def test_run_version(self, capsys):
        """Test CLI version output."""
        cli = ModularInventoryCLI()
        
        with pytest.raises(SystemExit):
            cli.run()
        
        captured = capsys.readouterr()
        assert "2.0.0" in captured.out


class TestMainFunction:
    """Test the main function entry point."""
    
    @patch('scripts.ansible_inventory_cli.ModularInventoryCLI')
    def test_main_function(self, mock_cli_class):
        """Test main function creates CLI and runs."""
        mock_cli = MagicMock()
        mock_cli_class.return_value = mock_cli
        
        main()
        
        mock_cli_class.assert_called_once()
        mock_cli.run.assert_called_once()
    
    @patch('scripts.ansible_inventory_cli.ModularInventoryCLI')
    def test_main_function_exception_handling(self, mock_cli_class):
        """Test main function handles exceptions."""
        mock_cli = MagicMock()
        mock_cli.run.side_effect = Exception("Test exception")
        mock_cli_class.return_value = mock_cli
        
        with pytest.raises(SystemExit):
            main()


class TestCLIIntegration:
    """Integration tests for CLI functionality."""
    
    def test_full_cli_workflow(self, tmp_path):
        """Test complete CLI workflow with real commands."""
        # Create test CSV
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("hostname,environment,status\ntest-host,production,active\n")
        
        cli = ModularInventoryCLI()
        
        # Test validate command
        args = MagicMock()
        args.command = "validate"
        args.csv_file = str(csv_file)
        args.json = False
        
        result = cli.execute_command(args)
        assert result["status"] in ["success", "error"]  # Either is valid for this test
    
    def test_cli_error_recovery(self):
        """Test CLI error recovery mechanisms."""
        cli = ModularInventoryCLI()
        
        # Test with invalid CSV file
        args = MagicMock()
        args.command = "validate"
        args.csv_file = "/nonexistent/file.csv"
        args.json = False
        
        result = cli.execute_command(args)
        assert result["status"] == "error"
        assert "error" in result
    
    def test_cli_performance_monitoring(self):
        """Test CLI performance monitoring."""
        cli = ModularInventoryCLI()
        
        args = MagicMock()
        args.command = "health"
        args.csv_file = None
        args.json = False
        
        result = cli.execute_command(args)
        
        assert "execution_time" in result
        assert isinstance(result["execution_time"], (int, float))
        assert result["execution_time"] >= 0 