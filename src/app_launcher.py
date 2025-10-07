# src/app_launcher.py
# Rev 0.1.1
from __future__ import annotations

from main import main as run_app

def main() -> int:
    return run_app()

if __name__ == "__main__":
    raise SystemExit(main())
