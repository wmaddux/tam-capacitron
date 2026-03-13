"""
Mapping layer: convert ingestor output (dict) to CapacityInputs.

Ingestor output is the contract from tam-tools/tam-flash-report (e.g. SQLite rows
or a structured dict). Direct fields are mapped 1:1 (with unit conversion if needed);
calculated fields use formulas; missing or invalid values fall back to engine defaults.
See docs/COLLECTINFO_INPUT_MAPPING.md.
"""

from __future__ import annotations

from core.model import CapacityInputs, get_default_inputs


def _float(d: dict, key: str, default: float) -> float:
    """Get float from dict or default. Coerce invalid to default."""
    try:
        v = d.get(key)
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def ingestor_output_to_capacity_inputs(ingestor_output: dict) -> CapacityInputs:
    """
    Convert ingestor output dict to CapacityInputs.

    Expected keys (all optional; missing → use default):
    - replication_factor, nodes_per_cluster, devices_per_node, device_size_gb
    - available_memory_gb, overhead_pct
    - master_object_count (or object_count), avg_record_size_bytes (or data_used_bytes + object_count for calc)
    - read_pct, write_pct (or read_transactions, write_transactions for calc)
    - tombstone_pct, si_count, si_entries_per_object
    - nodes_lost (usually omit; default 0)
    """
    defaults = get_default_inputs()
    d = ingestor_output or {}

    # Direct (with fallback to default)
    replication_factor = _float(d, "replication_factor", defaults.replication_factor)
    nodes_per_cluster = _float(d, "nodes_per_cluster", defaults.nodes_per_cluster)
    if nodes_per_cluster < 1:
        nodes_per_cluster = defaults.nodes_per_cluster
    devices_per_node = _float(d, "devices_per_node", defaults.devices_per_node)
    device_size_gb = _float(d, "device_size_gb", defaults.device_size_gb)
    # device_size_bytes -> GB if provided instead
    if "device_size_bytes" in d and device_size_gb == defaults.device_size_gb:
        try:
            device_size_gb = float(d["device_size_bytes"]) / (1024**3)
        except (TypeError, ValueError):
            pass
    available_memory_gb = _float(d, "available_memory_gb", defaults.available_memory_gb)
    overhead_pct = _float(d, "overhead_pct", defaults.overhead_pct)
    master_object_count = _float(d, "master_object_count", defaults.master_object_count)
    if master_object_count == defaults.master_object_count:
        master_object_count = _float(d, "object_count", defaults.master_object_count)
    si_count = _float(d, "si_count", defaults.si_count)
    nodes_lost = _float(d, "nodes_lost", 0.0)

    # avg_record_size_bytes: from ingestor or calculated
    avg_record_size_bytes = _float(d, "avg_record_size_bytes", defaults.avg_record_size_bytes)
    if avg_record_size_bytes == defaults.avg_record_size_bytes and master_object_count > 0:
        data_used_bytes = _float(d, "data_used_bytes", 0.0)
        if data_used_bytes > 0 and replication_factor > 0:
            # Approximate: data stored is replicated
            avg_record_size_bytes = data_used_bytes / (master_object_count * replication_factor)
            avg_record_size_bytes = max(1.0, min(avg_record_size_bytes, 10**7))

    # read_pct / write_pct: from ingestor or calculated from transaction stats
    read_pct = _float(d, "read_pct", defaults.read_pct)
    write_pct = _float(d, "write_pct", defaults.write_pct)
    if (read_pct == defaults.read_pct or write_pct == defaults.write_pct) and (
        "read_transactions" in d or "write_transactions" in d
    ):
        rt = _float(d, "read_transactions", 0.0)
        wt = _float(d, "write_transactions", 0.0)
        total = rt + wt
        if total > 0:
            read_pct = rt / total
            write_pct = wt / total
    if read_pct <= 0 and write_pct <= 0:
        read_pct, write_pct = defaults.read_pct, defaults.write_pct

    tombstone_pct = _float(d, "tombstone_pct", defaults.tombstone_pct)
    si_entries_per_object = _float(d, "si_entries_per_object", defaults.si_entries_per_object)
    if si_entries_per_object == defaults.si_entries_per_object and "si_entry_count" in d and master_object_count > 0:
        try:
            si_entries_per_object = float(d["si_entry_count"]) / master_object_count
        except (TypeError, ValueError):
            pass

    return CapacityInputs(
        replication_factor=replication_factor,
        nodes_per_cluster=nodes_per_cluster,
        devices_per_node=devices_per_node,
        device_size_gb=device_size_gb,
        available_memory_gb=available_memory_gb,
        overhead_pct=overhead_pct,
        master_object_count=master_object_count,
        avg_record_size_bytes=avg_record_size_bytes,
        read_pct=read_pct,
        write_pct=write_pct,
        tombstone_pct=tombstone_pct,
        si_count=si_count,
        si_entries_per_object=si_entries_per_object,
        nodes_lost=nodes_lost,
    )


def ingestor_multi_to_cluster_and_namespaces(multi_output: dict) -> dict:
    """
    Convert multi-namespace ingestor output to API shape: cluster + namespaces.

    multi_output must have "cluster" (dict) and "namespaces" (list of dicts).
    Returns { "cluster": { cluster_name, nodes_per_cluster, ... }, "namespaces": [ { name, replication_factor, master_object_count, avg_record_size_bytes, ... }, ... ] }.
    Uses engine defaults for missing values. When there is exactly one namespace and
    cluster has data_used_bytes, avg_record_size is derived for that namespace.
    """
    defaults = get_default_inputs()
    cluster_in = (multi_output or {}).get("cluster") or {}
    namespaces_in = (multi_output or {}).get("namespaces") or []

    # Cluster
    cluster = {
        "cluster_name": (cluster_in.get("cluster_name") or "").strip(),
        "nodes_per_cluster": _float(cluster_in, "nodes_per_cluster", defaults.nodes_per_cluster),
        "devices_per_node": _float(cluster_in, "devices_per_node", defaults.devices_per_node),
        "device_size_gb": _float(cluster_in, "device_size_gb", defaults.device_size_gb),
        "available_memory_gb": _float(cluster_in, "available_memory_gb", defaults.available_memory_gb),
        "overhead_pct": _float(cluster_in, "overhead_pct", defaults.overhead_pct),
        "nodes_lost": _float(cluster_in, "nodes_lost", 0.0),
    }
    if cluster["nodes_per_cluster"] < 1:
        cluster["nodes_per_cluster"] = defaults.nodes_per_cluster

    # Optional: derive avg_record_size for single namespace when cluster has data_used
    cluster_data_used = _float(cluster_in, "data_used_bytes", 0.0)
    single_ns_avg_record: float | None = None
    if len(namespaces_in) == 1 and cluster_data_used > 0:
        ns0 = namespaces_in[0]
        obj = _float(ns0, "object_count", defaults.master_object_count)
        rf = _float(ns0, "replication_factor", defaults.replication_factor)
        if obj > 0 and rf > 0:
            single_ns_avg_record = cluster_data_used / (obj * rf)
            single_ns_avg_record = max(1.0, min(single_ns_avg_record, 10**7))

    namespaces = []
    for ns_in in namespaces_in:
        master_object_count = _float(ns_in, "master_object_count", defaults.master_object_count)
        if master_object_count == defaults.master_object_count:
            master_object_count = _float(ns_in, "object_count", defaults.master_object_count)
        replication_factor = _float(ns_in, "replication_factor", defaults.replication_factor)
        read_pct = _float(ns_in, "read_pct", defaults.read_pct)
        write_pct = _float(ns_in, "write_pct", defaults.write_pct)
        if read_pct <= 0 and write_pct <= 0:
            read_pct, write_pct = defaults.read_pct, defaults.write_pct
        avg_record_size_bytes = _float(ns_in, "avg_record_size_bytes", defaults.avg_record_size_bytes)
        if avg_record_size_bytes == defaults.avg_record_size_bytes and single_ns_avg_record is not None:
            avg_record_size_bytes = single_ns_avg_record
        # Per-namespace data_used_bytes (from asadm show stat device_data_bytes/device_used_bytes)
        # so Data stored matches Device Used when loading from collectinfo (model_calculation_storage_util).
        if avg_record_size_bytes == defaults.avg_record_size_bytes:
            ns_data_used = _float(ns_in, "data_used_bytes", 0.0)
            drives_total = _float(ns_in, "drives_total", -1.0)
            # No device (drives_total 0) or no objects: contribute 0 to device data
            if master_object_count == 0 or (drives_total == 0 and ns_data_used <= 0):
                avg_record_size_bytes = 0.0
            elif ns_data_used > 0 and master_object_count > 0 and replication_factor > 0:
                avg_record_size_bytes = ns_data_used / (master_object_count * replication_factor)
                avg_record_size_bytes = max(1.0, min(avg_record_size_bytes, 10**7))
        drives_total = _float(ns_in, "drives_total", -1.0)
        storage_pattern = "In-Memory (MMM)" if drives_total == 0 else "HMA (MMD)"
        placement = (
            {"primary": "M", "si": "M", "data": "M"}
            if drives_total == 0
            else {"primary": "M", "si": "M", "data": "D"}
        )
        namespaces.append({
            "name": (ns_in.get("name") or "").strip(),
            "replication_factor": replication_factor,
            "master_object_count": master_object_count,
            "avg_record_size_bytes": avg_record_size_bytes,
            "read_pct": read_pct,
            "write_pct": write_pct,
            "tombstone_pct": _float(ns_in, "tombstone_pct", defaults.tombstone_pct),
            "si_count": _float(ns_in, "si_count", defaults.si_count),
            "si_entries_per_object": _float(ns_in, "si_entries_per_object", defaults.si_entries_per_object),
            "storage_pattern": storage_pattern,
            "placement": placement,
        })
    if not namespaces:
        namespaces = [{
            "name": "",
            "replication_factor": defaults.replication_factor,
            "master_object_count": defaults.master_object_count,
            "avg_record_size_bytes": defaults.avg_record_size_bytes,
            "read_pct": defaults.read_pct,
            "write_pct": defaults.write_pct,
            "tombstone_pct": defaults.tombstone_pct,
            "si_count": defaults.si_count,
            "si_entries_per_object": defaults.si_entries_per_object,
        }]
    return {"cluster": cluster, "namespaces": namespaces}
