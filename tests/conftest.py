import sys
from pathlib import Path

# The backend modules are loaded by path inside Hermes; import them directly here.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard"))
