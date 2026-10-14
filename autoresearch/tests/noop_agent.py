"""Fake agent for the enforcement smoke test: adds a harmless comment to method.py only."""
from pathlib import Path

m = Path(__file__).resolve().parents[2] / "src/wapusk_greenup/method.py"
m.write_text(m.read_text() + "\n# fake agent comment\n")
print("added a comment to method.py")
