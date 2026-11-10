"""
Entry point of the packaged Smart Office backend (smartoffice-backend.exe, built by build_backend.bat).
The desktop app starts it with --port and the AFMI_DATA_DIR environment variable.
"""
import argparse
import multiprocessing

import uvicorn

from backend.main import app


def main():
    parser = argparse.ArgumentParser(description="AFMI Smart Office backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    if args.host not in ("127.0.0.1", "localhost"):
        parser.error("Le backend n'écoute que sur la boucle locale (127.0.0.1).")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
