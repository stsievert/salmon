from frontend._version import get_versions
from pathlib import Path

root = Path(__file__).parent

version = get_versions()["version"]
init = root / "frontend" / "frontend" / "__init__.py"
lines = init.read_text().split("\n")
idx = [i for i, l in enumerate(lines) if "__version__" in l]
assert len(idx) == 1
_version = lines[idx[0]].split("=")
_version = [v.strip() for v in _version]
_version[-1] = f'"{version}"'
lines[idx[0]] = " = ".join(_version)
lines = [line for line in lines if line]
out = "\n".join(lines)
with open(str(init), "w") as f:
    print(out, file=f)
