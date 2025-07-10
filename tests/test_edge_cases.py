#!/usr/bin/env python3
"""
Edge case tests for the inventory management system.

Tests various edge cases, error conditions, and boundary conditions.
"""

import pytest
import tempfile
import csv
from pathlib import Path
import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.core.models import Host
from scripts.core.utils import load_csv_data, validate_hostname, validate_date_format
from scripts.managers.inventory_manager import InventoryManager


class TestHostModelEdgeCases:
    """Test edge cases in Host model validation."""

    def test_empty_hostname_and_cname(self):
        """Test that Host requires either hostname or cname."""
        with pytest.raises(ValueError, match="Either hostname or cname is required"):
            Host(
                hostname="",
                cname="",
                environment="production",
                status="active"
            )

    def test_invalid_environment(self):
        """Test invalid environment validation."""
        with pytest.raises(ValueError, match="Invalid environment"):
            Host(
                hostname="test",
                environment="invalid_env",
                status="active"
            )

    def test_invalid_status(self):
        """Test invalid status validation."""
        with pytest.raises(ValueError, match="Invalid status"):
            Host(
                hostname="test",
                environment="production",
                status="invalid_status"
            )

    def test_invalid_instance_leading_zeros(self):
        """Test that instance with leading zeros is invalid."""
        with pytest.raises(ValueError, match="Invalid instance"):
            Host(
                hostname="test",
                environment="production",
                status="active",
                instance="01"
            )

    def test_valid_instance_zero(self):
        """Test that instance '0' is valid."""
        host = Host(
            hostname="test",
            environment="production",
            status="active",
            instance="0"
        )
        assert host.instance == "0"


class TestCSVLoadingEdgeCases:
    """Test edge cases in CSV loading."""

    def test_nonexistent_csv_file(self):
        """Test loading from nonexistent CSV file."""
        with pytest.raises(FileNotFoundError):
            load_csv_data(Path("/nonexistent/file.csv"))

    def test_empty_csv_file(self):
        """Test loading from empty CSV file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            # Write only headers
            f.write("hostname,environment,status\n")
            csv_path = Path(f.name)

        try:
            hosts = load_csv_data(csv_path)
            assert hosts == []
        finally:
            csv_path.unlink()


class TestValidationFunctions:
    """Test validation utility functions."""

    def test_validate_hostname_valid(self):
        """Test valid hostname validation."""
        assert validate_hostname("test-host-01") is None
        assert validate_hostname("web01") is None

    def test_validate_hostname_invalid(self):
        """Test invalid hostname validation."""
        assert validate_hostname("") is not None
        assert validate_hostname("host with spaces") is not None
        assert validate_hostname("host.with.dots") is not None

    def test_validate_date_format_valid(self):
        """Test valid date format validation."""
        assert validate_date_format("2025-01-01") is None
        assert validate_date_format("2024-12-31") is None

    def test_validate_date_format_invalid(self):
        """Test invalid date format validation."""
        assert validate_date_format("2025-13-01") is not None  # Invalid month
        assert validate_date_format("not-a-date") is not None


if __name__ == "__main__":
    pytest.main([__file__]) 