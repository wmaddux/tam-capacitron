"""
Bundle parser: open zip archives, list contents, find collectinfo file(s), extract for ingestor.

Supports bundles like bundles/fidelity-case00044090-20250226.zip that contain
collectinfo plus logs and other artifacts. Design allows adding log discovery later.
"""

import zipfile
from pathlib import Path
from typing import BinaryIO

# Common collectinfo naming patterns (case-insensitive)
COLLECTINFO_NAME_PATTERNS = (
    "collectinfo",
    "collect_info",
    ".collectinfo",
)


def list_bundle_contents(bundle_path: str | Path) -> list[str]:
    """List all entry names in a zip bundle."""
    path = Path(bundle_path)
    if not path.exists():
        raise FileNotFoundError(f"Bundle not found: {path}")
    if not zipfile.is_zipfile(path):
        raise ValueError(f"Not a zip file: {path}")
    with zipfile.ZipFile(path, "r") as zf:
        return zf.namelist()


def _is_collectinfo_name(name: str) -> bool:
    """Return True if the entry name looks like a collectinfo file."""
    lower = name.lower()
    return any(p in lower for p in COLLECTINFO_NAME_PATTERNS)


def find_collectinfo_in_bundle(bundle_path: str | Path) -> list[str]:
    """
    Return entry names inside the zip that are collectinfo files.
    Uses name patterns; does not inspect content.
    """
    names = list_bundle_contents(bundle_path)
    return [n for n in names if _is_collectinfo_name(n) and not n.endswith("/")]


def extract_collectinfo_from_bundle(
    bundle_path: str | Path, entry_name: str | None = None
) -> bytes:
    """
    Extract collectinfo content from the bundle as bytes.
    If entry_name is None, use the first collectinfo entry found.
    Raises ValueError if no collectinfo entry exists.
    """
    path = Path(bundle_path)
    if not path.exists() or not zipfile.is_zipfile(path):
        raise ValueError(f"Invalid or missing bundle: {path}")
    candidates = find_collectinfo_in_bundle(path)
    if not candidates:
        raise ValueError(f"No collectinfo file found in bundle: {path}")
    name = entry_name if entry_name is not None else candidates[0]
    if name not in candidates and name not in list_bundle_contents(path):
        raise ValueError(f"Entry not in bundle: {name}")
    with zipfile.ZipFile(path, "r") as zf:
        return zf.read(name)


def extract_collectinfo_from_file(file_like: BinaryIO) -> bytes:
    """Read raw collectinfo content from an already-open file (e.g. uploaded file)."""
    return file_like.read()
