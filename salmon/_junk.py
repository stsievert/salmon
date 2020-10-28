
from pathlib import Path

if __name__ == "__main__":
    name = "junk"
    ROOT_DIR = Path(__file__).absolute().parent.parent

    out = ROOT_DIR / "out" / f"{name}.log"
