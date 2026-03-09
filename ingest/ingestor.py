"""
Collectinfo ingestor: run asadm against a bundle and map output to capacity dict.

When collectinfo_path is set (bundle zip/tar), runs asadm -cf <path> -e "summary",
parses the output, and returns a dict for the mapping layer. When only
collectinfo_content is provided (no path), returns stub.

Requires asadm on PATH. Optional: set CAPACITRON_NAMESPACE to choose namespace.
"""

from __future__ import annotations

import os
from pathlib import Path

from ingest.asadm_ingest import asadm_summary_to_capacity_dict


def run_ingestor(
    collectinfo_content: bytes | None = None,
    collectinfo_path: str | Path | None = None,
    db_path: str | None = None,
) -> dict:
    """
    Run collectinfo ingestion and return a dict for mapping to CapacityInputs.

    - If collectinfo_path is set (path to a bundle .zip/.tgz/.tar): runs asadm
      -cf <path> -e "summary", parses output, and returns the dict. Requires
      asadm on PATH. If asadm is missing or parse fails, returns stub.
    - If only collectinfo_content (bytes) is provided: returns stub.
    - db_path is ignored (kept for API compatibility).
    """
    path = None
    if collectinfo_path is not None:
        path = str(Path(collectinfo_path).resolve())
    if path and os.path.isfile(path):
        namespace = (os.environ.get("CAPACITRON_NAMESPACE") or "").strip() or None
        d = asadm_summary_to_capacity_dict(path, namespace=namespace)
        if d:
            return d
    return _stub_ingestor_output()


def _stub_ingestor_output() -> dict:
    """Stub output when asadm is not used or ingest fails."""
    return {
        "replication_factor": 2.0,
        "nodes_per_cluster": 16.0,
        "devices_per_node": 2.0,
        "device_size_gb": 1920.0,
        "available_memory_gb": 64.0,
        "overhead_pct": 0.15,
        "object_count": 500_000_000.0,
        "data_used_bytes": 1.2e12,
        "read_transactions": 0.7,
        "write_transactions": 0.3,
        "tombstone_pct": 0.0,
        "si_count": 2.0,
        "si_entries_per_object": 1.0,
    }
