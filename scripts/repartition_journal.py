#!/usr/bin/env python3
from pathlib import Path
import os
import sys

repo_root = Path(__file__).resolve().parents[1]
os.execvp(
    "python3",
    ["python3", str(repo_root / "partnerOS" / "eventsCapture" / "scripts" / "repartition_journal.py"), *sys.argv[1:]],
)
