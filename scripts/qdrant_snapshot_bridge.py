"""Bridge a Qdrant financial_docs snapshot into local markdown files.

The downloaded .snapshot file is a Qdrant collection snapshot, not raw PDFs.
Use this script to:

1. Inspect the snapshot archive.
2. Restore it into a running local Qdrant server.
3. Export point payloads into data/external_financial_docs for this app.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tarfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import EXTERNAL_DOCS_DIR, PROJECT_ROOT as CONFIG_PROJECT_ROOT, ensure_project_dirs
from src.financial_metadata import infer_financial_metadata, sanitize_metadata


DEFAULT_SNAPSHOT = CONFIG_PROJECT_ROOT / "financial_docs-6842273198355691-2025-12-30-17-57-38.snapshot"
DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_COLLECTION = "financial_docs"


class QdrantUnavailable(RuntimeError):
    """Raised when the optional Qdrant snapshot server is not reachable."""


def inspect_snapshot(snapshot_path: Path) -> dict[str, Any]:
    if not tarfile.is_tarfile(snapshot_path):
        raise ValueError(f"{snapshot_path} is not a readable tar/Qdrant snapshot.")

    with tarfile.open(snapshot_path) as archive:
        members = archive.getmembers()
        config = _read_json_member(archive, "config.json")
        return {
            "snapshot": str(snapshot_path),
            "size_mb": round(snapshot_path.stat().st_size / (1024 * 1024), 2),
            "member_count": len(members),
            "top_level_members": [member.name for member in members[:30]],
            "config": config,
        }


def restore_snapshot(
    snapshot_path: Path,
    qdrant_url: str,
    collection: str,
    api_key: str | None = None,
    wait: bool = True,
) -> dict[str, Any]:
    """Upload a collection snapshot to Qdrant's restore endpoint."""

    import requests

    assert_qdrant_available(qdrant_url, api_key)
    endpoint = f"{qdrant_url.rstrip('/')}/collections/{collection}/snapshots/upload"
    headers = {"api-key": api_key} if api_key else {}
    params = {"wait": str(wait).lower(), "priority": "snapshot"}
    with snapshot_path.open("rb") as snapshot_file:
        response = requests.post(
            endpoint,
            headers=headers,
            params=params,
            files={"snapshot": (snapshot_path.name, snapshot_file, "application/octet-stream")},
            timeout=600,
        )
    response.raise_for_status()
    return response.json()


def export_collection(
    output_dir: Path,
    qdrant_url: str,
    collection: str,
    api_key: str | None = None,
    batch_size: int = 64,
    max_points: int | None = None,
) -> dict[str, Any]:
    """Scroll Qdrant points and write payload text into markdown files."""

    import requests

    assert_qdrant_available(qdrant_url, api_key)
    ensure_project_dirs()
    output_dir.mkdir(parents=True, exist_ok=True)
    exported = 0
    skipped = 0
    offset: Any | None = None

    while True:
        payload: dict[str, Any] = {
            "limit": batch_size,
            "with_payload": True,
            "with_vector": False,
        }
        if offset is not None:
            payload["offset"] = offset

        response = requests.post(
            f"{qdrant_url.rstrip('/')}/collections/{collection}/points/scroll",
            headers={"api-key": api_key} if api_key else {},
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        result = response.json().get("result", {})
        points = result.get("points", [])
        if not points:
            break

        for point in points:
            if max_points is not None and exported >= max_points:
                return {"exported": exported, "skipped": skipped, "output_dir": str(output_dir)}
            if write_point_markdown(point, output_dir):
                exported += 1
            else:
                skipped += 1

        offset = result.get("next_page_offset")
        if offset is None:
            break

    return {"exported": exported, "skipped": skipped, "output_dir": str(output_dir)}


def qdrant_status(qdrant_url: str, api_key: str | None = None) -> dict[str, Any]:
    """Return a small health/status payload for a Qdrant server."""

    import requests

    endpoint = f"{qdrant_url.rstrip('/')}/"
    try:
        response = requests.get(endpoint, headers={"api-key": api_key} if api_key else {}, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise QdrantUnavailable(qdrant_help_message(qdrant_url)) from exc
    try:
        payload = response.json()
    except ValueError:
        payload = {"response": response.text[:500]}
    return {"qdrant_url": qdrant_url, "reachable": True, "response": payload}


def assert_qdrant_available(qdrant_url: str, api_key: str | None = None) -> None:
    qdrant_status(qdrant_url, api_key)


def qdrant_help_message(qdrant_url: str) -> str:
    return (
        f"Qdrant is not reachable at {qdrant_url}.\n\n"
        "The downloaded .snapshot is a Qdrant collection snapshot. Restore/export requires a running Qdrant server.\n\n"
        "Fast workaround if Docker is installed:\n"
        "  docker run -p 6333:6333 -p 6334:6334 -v \"%cd%\\outputs\\qdrant_storage:/qdrant/storage\" qdrant/qdrant\n\n"
        "Then retry:\n"
        "  .\\.venv\\Scripts\\python.exe scripts\\qdrant_snapshot_bridge.py restore-export --qdrant-url http://localhost:6333 --collection financial_docs\n\n"
        "The app itself does not require Qdrant. You can still run Streamlit, load sample docs, upload files, and use Chroma/Ollama normally."
    )


def write_point_markdown(point: dict[str, Any], output_dir: Path) -> bool:
    payload = point.get("payload") or {}
    text, metadata = extract_text_and_metadata(payload)
    if not text.strip():
        return False

    point_id = str(point.get("id", "unknown"))
    source = str(metadata.get("source") or metadata.get("source_file") or metadata.get("file_name") or point_id)
    inferred = infer_financial_metadata(source, text)
    for key, value in inferred.items():
        metadata.setdefault(key, value)
    metadata["point_id"] = point_id
    metadata = sanitize_metadata(metadata)

    company = str(metadata.get("company_name", "unknown_company"))
    doc_type = str(metadata.get("doc_type", "unknown_doc"))
    year = str(metadata.get("fiscal_year", "unknown_year"))
    target_dir = output_dir / safe_filename(company) / safe_filename(f"{doc_type}_{year}")
    target_dir.mkdir(parents=True, exist_ok=True)

    base = safe_filename(Path(source).stem or f"point_{point_id}")
    content_type = safe_filename(str(metadata.get("content_type", "text")))
    page = safe_filename(str(metadata.get("page", metadata.get("page_number", ""))))
    filename = f"{base}_{content_type}"
    if page:
        filename += f"_page_{page}"
    filename += f"_{safe_filename(point_id)}.md"

    frontmatter = "\n".join(f"{key}: {json.dumps(value)}" for key, value in sorted(metadata.items()))
    target = target_dir / filename
    target.write_text(f"---\n{frontmatter}\n---\n\n{text.strip()}\n", encoding="utf-8")
    return True


def extract_text_and_metadata(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    metadata = dict(payload.get("metadata") or {}) if isinstance(payload.get("metadata"), dict) else {}
    for key, value in payload.items():
        if key == "metadata":
            continue
        if key not in {"page_content", "content", "text", "document"}:
            metadata.setdefault(key, value)

    text = ""
    for key in ["page_content", "content", "text", "document"]:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            text = value
            break

    if not text:
        text = longest_string_value(payload)

    return text, metadata


def longest_string_value(value: Any) -> str:
    candidates: list[str] = []
    if isinstance(value, str):
        candidates.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            candidate = longest_string_value(item)
            if candidate:
                candidates.append(candidate)
    elif isinstance(value, list):
        for item in value:
            candidate = longest_string_value(item)
            if candidate:
                candidates.append(candidate)
    return max(candidates, key=len, default="")


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return cleaned[:120] or "unknown"


def _read_json_member(archive: tarfile.TarFile, name: str) -> dict[str, Any] | None:
    try:
        member = archive.extractfile(name)
    except KeyError:
        return None
    if member is None:
        return None
    return json.loads(member.read().decode("utf-8", errors="replace"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Restore/export a Qdrant financial_docs snapshot.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect the snapshot archive.")
    inspect_parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)

    status_parser = subparsers.add_parser("status", help="Check whether Qdrant is reachable.")
    add_qdrant_args(status_parser)

    restore_parser = subparsers.add_parser("restore", help="Restore the snapshot into Qdrant.")
    add_qdrant_args(restore_parser)
    restore_parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)

    export_parser = subparsers.add_parser("export", help="Export restored Qdrant payloads to markdown.")
    add_qdrant_args(export_parser)
    export_parser.add_argument("--output-dir", type=Path, default=EXTERNAL_DOCS_DIR)
    export_parser.add_argument("--batch-size", type=int, default=64)
    export_parser.add_argument("--max-points", type=int, default=None)

    roundtrip_parser = subparsers.add_parser("restore-export", help="Restore the snapshot, then export markdown.")
    add_qdrant_args(roundtrip_parser)
    roundtrip_parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    roundtrip_parser.add_argument("--output-dir", type=Path, default=EXTERNAL_DOCS_DIR)
    roundtrip_parser.add_argument("--batch-size", type=int, default=64)
    roundtrip_parser.add_argument("--max-points", type=int, default=None)

    return parser


def add_qdrant_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--qdrant-url", default=DEFAULT_QDRANT_URL)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--api-key", default=None)


def main() -> None:
    args = build_parser().parse_args()

    try:
        if args.command == "inspect":
            print(json.dumps(inspect_snapshot(args.snapshot), indent=2))
            return

        if args.command == "status":
            print(json.dumps(qdrant_status(args.qdrant_url, args.api_key), indent=2))
            return

        if args.command == "restore":
            print(json.dumps(restore_snapshot(args.snapshot, args.qdrant_url, args.collection, args.api_key), indent=2))
            return

        if args.command == "export":
            print(
                json.dumps(
                    export_collection(args.output_dir, args.qdrant_url, args.collection, args.api_key, args.batch_size, args.max_points),
                    indent=2,
                )
            )
            return

        if args.command == "restore-export":
            restore_result = restore_snapshot(args.snapshot, args.qdrant_url, args.collection, args.api_key)
            export_result = export_collection(
                args.output_dir,
                args.qdrant_url,
                args.collection,
                args.api_key,
                args.batch_size,
                args.max_points,
            )
            print(json.dumps({"restore": restore_result, "export": export_result}, indent=2))
    except QdrantUnavailable as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
