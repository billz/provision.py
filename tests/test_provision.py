import sys
import tempfile
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

