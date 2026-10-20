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
    export_cmd=sub.add_parser("export-feedback", help="Export reviewed jobs and feedback data to JSON")
    export_cmd.add_argument("--output",type=Path,default=Path("var/exported_feedback.json"))
    overlay=sub.add_parser("import-overlay")
    overlay.add_argument("path",type=Path)
    args=parser.parse_args()
    settings=Settings.from_env(args.env_file)
    if args.command == "prepare-ocr":
        from .ocr import prepare_weights
        print(f"VietOCR weights ready: {prepare_weights(settings)}")
    elif args.command == "export-feedback":
        import sqlite3
        if not settings.runtime_db.exists():
            print("Chưa có cơ sở dữ liệu runtime.")
            return
        conn = sqlite3.connect(settings.runtime_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT f.feedback_id, f.job_id, f.body AS feedback_body, f.created_at AS feedback_at,
                   j.input_sha256, j.metadata, j.result, j.created_at AS job_at
            FROM feedback f
            JOIN jobs j ON f.job_id = j.job_id
            ORDER BY f.created_at DESC
        """).fetchall()
        records = []
        for r in rows:
            records.append({
                "feedback_id": r["feedback_id"],
                "job_id": r["job_id"],
                "feedback_at": r["feedback_at"],
                "job_at": r["job_at"],
                "input_sha256": r["input_sha256"],
                "metadata": json.loads(r["metadata"]) if r["metadata"] else {},
                "ai_result": json.loads(r["result"]) if r["result"] else {},
                "colleague_feedback": json.loads(r["feedback_body"]) if r["feedback_body"] else {}
            })
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Exported {len(records)} feedback records to {args.output}")
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
