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

from ingest.asadm_ingest import asadm_summary_to_capacity_dict, asadm_summary_to_capacity_multi


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


def run_ingestor_multi(
    collectinfo_content: bytes | None = None,
    collectinfo_path: str | Path | None = None,
) -> dict:
    """
    Run collectinfo ingestion and return cluster + list of namespaces.

    Returns { "cluster": {...}, "namespaces": [ {...}, ... ] }. When
    collectinfo_path is set and is a bundle file, runs asadm and parses all
    namespace rows. When asadm is missing or only content is provided, returns
    stub with one namespace (same defaults as _stub_ingestor_output).
    """
    path = None
    if collectinfo_path is not None:
        path = str(Path(collectinfo_path).resolve())
    if path and os.path.isfile(path):
        multi = asadm_summary_to_capacity_multi(path)
        if multi.get("namespaces"):
            return multi
    return _stub_ingestor_output_multi()


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


def _stub_ingestor_output_multi() -> dict:
    """Stub output for multi-namespace: cluster + one namespace."""
    flat = _stub_ingestor_output()
    return {
        "cluster": {
            "nodes_per_cluster": flat["nodes_per_cluster"],
            "devices_per_node": flat["devices_per_node"],
            "device_size_gb": flat["device_size_gb"],
            "available_memory_gb": flat["available_memory_gb"],
            "overhead_pct": flat["overhead_pct"],
            "nodes_lost": 0.0,
            "data_used_bytes": flat.get("data_used_bytes"),
        },
        "namespaces": [
            {
                "name": "",
                "replication_factor": flat["replication_factor"],
                "object_count": flat["object_count"],
                "read_pct": flat.get("read_pct", 0.7),
                "write_pct": flat.get("write_pct", 0.3),
                "tombstone_pct": flat.get("tombstone_pct", 0.0),
                "si_count": flat.get("si_count", 2.0),
                "si_entries_per_object": flat.get("si_entries_per_object", 1.0),
            }
        ],
    }
