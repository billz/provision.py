import sys
import tempfile
import subprocess
from pathlib import Path

# add parent dir to sys.path to import provision module
sys.path.insert(0, str(Path(__file__).parent.parent))

from provision import parse_inventory

def test_basic():
    content = """
    # just a comment
    host1,192.168.1.10
    host2,10.0.0.5
    host3,172.0.10.1

    invalid line
    invalid-host4,999.999.999
    """

    with tempfile.NamedTemporaryFile("w+", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    valid, errors = parse_inventory(tmp_path)

    # test correct parsing
    assert("host1","192.168.1.10") in valid
    assert("host2","10.0.0.5") in valid
    assert("host3","172.0.10.1") in valid
    assert len(valid) == 3

    # invalid entries
    assert len(errors) == 2
    parsed_errors = [e[2] for e in errors]

    assert any("expected 'hostname,ip'" in r for r in parsed_errors)
    assert any("invalid IP" in r for r in parsed_errors)

def test_provision_dry_run():
    """Test running provision.py with --timeout and --dry-run flags"""
    # create a temporary hosts.csv file
    content = """host1,192.168.1.10
host2,10.0.0.5
host3,172.16.0.1
"""

    with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        # get the path to provision.py (in parent directory)
        provision_script = Path(__file__).parent.parent / "provision.py"

        # run the provision.py command with the specified arguments
        result = subprocess.run(
            [sys.executable, str(provision_script), str(tmp_path), "--timeout", "10", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # verify the command executed successfully
        assert result.returncode == 0, f"Command failed with return code {result.returncode}\nStdout: {result.stdout}\nStderr: {result.stderr}"

        # verify dry-run messages appear in output
        assert "DRY-RUN" in result.stderr or "DRY-RUN" in result.stdout, "Expected DRY-RUN output"
        assert "Parsed inventory: 3 valid entries" in result.stderr or "Parsed inventory: 3 valid entries" in result.stdout, "Expected to parse 3 valid entries"

    finally:
        # cleanup temporary file
        tmp_path.unlink()

