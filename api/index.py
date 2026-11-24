import sys
import os
from pathlib import Path

# Add project root and /var/task to sys.path
root_dir = Path(__file__).resolve().parent.parent
for p in [str(root_dir), "/var/task", os.getcwd()]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.main import app

app = app
