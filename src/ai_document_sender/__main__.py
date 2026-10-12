"""Run the local API or explicitly import verified directory data."""
import argparse
import json
from pathlib import Path
from .config import Settings


def main():
    parser=argparse.ArgumentParser(description="Outgoing recipients backend")
    parser.add_argument("--env-file",type=Path)
    sub=parser.add_subparsers(dest="command")
    sub.add_parser("serve")
    sub.add_parser("prepare-ocr", help="Download the local VietOCR model once")
    overlay=sub.add_parser("import-overlay")
    overlay.add_argument("path",type=Path)
    args=parser.parse_args()
    settings=Settings.from_env(args.env_file)
    if args.command == "prepare-ocr":
        from .ocr import prepare_weights
        print(f"VietOCR weights ready: {prepare_weights(settings)}")
    elif args.command == "import-overlay":
        from .jobs import JobStore
        records=json.loads(args.path.read_text(encoding="utf-8-sig"))
        if not isinstance(records,list): parser.error("Overlay must be a JSON list of verified records")
        count=JobStore(settings).import_overlay(records)
        print(f"Imported {count} verified overlay records")
    else:
        import uvicorn
        from .api import create_app
        uvicorn.run(create_app(settings),host=settings.host,port=settings.port)


if __name__ == "__main__": main()
