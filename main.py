from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    app_path = Path(__file__).with_name("streamlit_app.py")
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        "localhost",
        "--server.port",
        "8501",
        "--server.headless",
        "true",
    ]
    try:
        return subprocess.call(command)
    except KeyboardInterrupt:
        return 0
    except ModuleNotFoundError:
        print("Streamlit is not installed. Install dependencies with: pip install -r requirements.txt")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
