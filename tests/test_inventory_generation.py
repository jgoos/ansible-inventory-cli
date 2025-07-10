import shutil
import subprocess
from pathlib import Path
from typing import List

import pytest
import yaml

from scripts.core.utils import load_csv_data
from scripts.managers.inventory_manager import InventoryManager
from scripts.managers.validation_manager import ValidationManager


def create_csv(tmp_path: Path, rows: List[str]) -> Path:
    """Create a temporary CSV file with the given rows for testing."""
    csv_file = tmp_path / "hosts.csv"
    csv_file.write_text("\n".join(rows))
    return csv_file


def test_generate_inventory(tmp_path: Path):
    """Test basic inventory generation from CSV data."""
    rows = [
        "hostname,environment,status,cname",
        "web01,production,active,",
        "db01,production,active,",
    ]
    csv_file = create_csv(tmp_path, rows)
    manager = InventoryManager(csv_file=csv_file)
    inventory_result = manager.generate_inventories(environments=["production"])

    # Check that the result contains expected data
    assert inventory_result["dry_run"] is False
    assert len(inventory_result["generated_files"]) > 0

    # Check that the inventory file was created
    inv_file = Path(inventory_result["generated_files"][0])
    assert inv_file.exists()

    # Check the content
    data = yaml.safe_load(inv_file.read_text())
    assert "env_production" in data
    assert "hosts" in data["env_production"]
    assert "web01" in data["env_production"]["hosts"]
    assert "db01" in data["env_production"]["hosts"]

    # Check stats first
    stats = inventory_result["stats"]
    assert stats["total_hosts"] == 2

    # Test with ansible-inventory if available
    if shutil.which("ansible-inventory") is None:
        pytest.skip("ansible-inventory executable not found")
    ansible_result = subprocess.run(
        ["ansible-inventory", "-i", str(inv_file), "--list"], capture_output=True
    )
    assert ansible_result.returncode == 0


def test_validate_csv_duplicates(tmp_path: Path):
    """Test validation catches duplicate hostnames in CSV data."""
    rows = [
        "hostname,environment,status,cname",
        "dup,production,active,",
        "dup,production,active,",
    ]
    csv_file = create_csv(tmp_path, rows)
    validator = ValidationManager(csv_file=csv_file)
    result = validator.validate_csv_data()
    assert not result.is_valid
    assert any("Duplicate hostnames" in e for e in result.errors)


def test_load_csv_data_malformed(tmp_path: Path):
    """Test loading CSV data handles malformed rows gracefully."""
    rows = [
        "hostname,environment,status",
        "badrow",  # malformed row
    ]
    csv_file = create_csv(tmp_path, rows)
    data = load_csv_data(csv_file)
    assert len(data) == 1
    assert data[0]["hostname"] == "badrow"


def test_load_hosts_with_env_code(tmp_path: Path):
    """Hosts should load correctly when filtering by environment code."""
    rows = [
        "hostname,environment,status,cname",
        "web01,PRD,active,",
        "db01,PRD,active,",
    ]
    csv_file = create_csv(tmp_path, rows)
    manager = InventoryManager(csv_file=csv_file)
    hosts = manager.load_hosts(environment="prd")
    assert len(hosts) == 2
    assert all(h.environment == "production" for h in hosts)
