import sys
from pathlib import Path

# Les scripts s'importent entre eux via "from common import ..."
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
