"""Portable source checks; DOES NOT build ROS or verify DDS communication."""
import ast
import importlib.util
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src/smartyard_lab'))
checks = []
for path in sorted(root.rglob('*.py')):
    if any(part in ('build', 'install', '__pycache__') for part in path.parts):
        continue
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path), feature_version=(3, 10))
    checks.append('Python 3.10 syntax: ' + str(path.relative_to(root)))
for path in root.glob('src/*/package.xml'):
    tree = ET.parse(path)
    assert tree.getroot().findtext('name') == path.parent.name
    checks.append('package.xml: ' + path.parent.name)
for path in root.glob('src/smartyard_interfaces/srv/*.srv'):
    assert path.read_text().splitlines().count('---') == 1
for path in root.glob('src/smartyard_interfaces/action/*.action'):
    assert path.read_text().splitlines().count('---') == 2
manifest = ET.parse(root / 'src/smartyard_interfaces/package.xml').getroot()
assert 'action_msgs' in [element.text for element in manifest.findall('depend')]
path = root / 'src/smartyard_lab/test/test_core.py'
spec = importlib.util.spec_from_file_location('core_tests', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
tests = []
for name in sorted(dir(module)):
    if name.startswith('test_'):
        getattr(module, name)()
        tests.append(name)
report = {
    'source_checks_passed': len(checks), 'core_tests_passed': len(tests),
    'core_tests': tests, 'source_checks': checks,
    'not_executed_here': ['colcon/rosidl build', 'ROS 2 process integration',
                          'WSL2 networking', 'four-PC DDS communication'],
}
destination = root / 'validation/local_checks.json'
destination.parent.mkdir(exist_ok=True)
destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'source_checks': len(checks), 'core_tests': len(tests), 'result': 'PASS'}))
