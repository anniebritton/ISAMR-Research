"""Fake agent for the enforcement smoke test: edits method.py and a forbidden file, and creates a new file."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
m = root / "src/wapusk_greenup/method.py"
m.write_text(m.read_text() + "\n# fake agent edit\n")
(root / "README.md").write_text((root / "README.md").read_text() + "\nfake agent edit\n")
(root / "autoresearch" / "planted.py").write_text("print('planted')\n")
print("edited method.py, README.md, and planted a new file")
