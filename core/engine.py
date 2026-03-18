"""
Capacity calculation engine: evaluates formulas in dependency order.

Accepts CapacityInputs (legacy) or cluster + namespaces (multi-namespace).
Returns CapacityOutputs. No UI; used by API and tests.
Placement-aware: per-namespace memory and storage depend on storage pattern (PI/SI/data on M or D).
"""

import math

from core.model import (
    CapacityInputs,
    CapacityOutputs,
    ClusterInputs,
    NamespaceInputs,
    capacity_inputs_to_cluster_and_namespaces,
)
from core import formulas as F  # noqa: I001


def _placement_from_pattern(storage_pattern: str) -> dict[str, str]:
    """Derive placement (primary, si, data) from storage pattern name. Matches UI placementFromPattern."""
    p = (storage_pattern or "").strip()
    if p == "HMA (MMD)":
        return {"primary": "M", "si": "M", "data": "D"}
    if p == "In-Memory (MMM)":
        return {"primary": "M", "si": "M", "data": "M"}
    if p == "All Flash (DDD)":
        return {"primary": "D", "si": "D", "data": "D"}
    if p == "DMD":
        return {"primary": "D", "si": "M", "data": "D"}
    return {"primary": "M", "si": "M", "data": "D"}


def _projected_data_1yr_gb(data_stored_gb: float, data_growth_pct_per_year: float) -> float:
    """Projected data (GB) after 1 year: current × (1 + growth_rate/100)."""
    return data_stored_gb * (1.0 + data_growth_pct_per_year / 100.0)


def _headroom_to_stop_writes_pct(
    data_stored_gb: float, usable_storage_with_thresholds_gb: float
) -> float | None:
    """Headroom to stop-writes %: 100 × (limit − data_stored) / limit. None if limit <= 0."""
    if usable_storage_with_thresholds_gb <= 0:
        return None
    return 100.0 * (usable_storage_with_thresholds_gb - data_stored_gb) / usable_storage_with_thresholds_gb


def _months_to_stop_writes_est(
    data_stored_gb: float,
    usable_storage_with_thresholds_gb: float,
    data_growth_pct_per_year: float,
) -> float | None:
    """Months until data reaches stop-writes limit (est). None if growth <= 0 or already at/over limit."""
    if data_growth_pct_per_year <= 0 or usable_storage_with_thresholds_gb <= 0:
        return None
    if data_stored_gb >= usable_storage_with_thresholds_gb or data_stored_gb <= 0:
        return None
    ratio = usable_storage_with_thresholds_gb / data_stored_gb
    log_ratio = math.log(ratio)
    log_growth = math.log(1.0 + data_growth_pct_per_year / 100.0)
    if log_growth <= 0:
        return None
    months = 12.0 * log_ratio / log_growth
    return max(0.0, months)


def _get_placement(ns: NamespaceInputs) -> dict[str, str]:
    """Effective placement for namespace: use ns.placement if valid, else derive from storage_pattern."""
    if getattr(ns, "placement", None) and isinstance(ns.placement, dict):
        p = ns.placement
        if all(k in p and p[k] in ("M", "D") for k in ("primary", "si", "data")):
            return p
    return _placement_from_pattern(getattr(ns, "storage_pattern", "HMA (MMD)"))


def _run_one_namespace(
    cluster: ClusterInputs,
    ns: NamespaceInputs,
) -> tuple[float, float, float, float, float, dict]:
    """
    Run workload formulas for one namespace with placement and compression.
    Returns (data_stored_gb, memory_base_gb, memory_with_tombstones_gb, storage_used_gb, per_ns_dict).
    - memory_base_gb = index_mem + data_mem (no tombstone factor).
    - memory_with_tombstones_gb = index_mem * (1 + tombstone_pct) + data_mem.
    - storage_used_gb = (PI on D) + (SI on D) + (data on D with compression).
    """
    placement = _get_placement(ns)
    compression_ratio = getattr(ns, "compression_ratio", 1.0)
    if compression_ratio <= 0 or compression_ratio > 1.0:
        compression_ratio = 1.0

    data_stored_gb = F.data_size_gb(
        ns.master_object_count,
        ns.replication_factor,
        ns.avg_record_size_bytes,
    )
    primary_gb = F.primary_index_shmem_gb(ns.replication_factor, ns.master_object_count)
    secondary_gb = F.secondary_index_shmem_gb(
        ns.master_object_count,
        ns.replication_factor,
        ns.si_entries_per_object,
        ns.si_count,
        cluster.nodes_per_cluster,
    )

    # Index memory (only when on M)
    index_mem_gb = 0.0
    if placement.get("primary") == "M":
        index_mem_gb += primary_gb
    if placement.get("si") == "M":
        index_mem_gb += secondary_gb

    # Data memory (only when on M); apply compression_ratio for 7.x in-memory compression
    data_mem_gb = 0.0
    if placement.get("data") == "M":
        data_mem_gb = data_stored_gb * compression_ratio

    memory_base_gb = index_mem_gb + data_mem_gb
    tombstone_pct = getattr(ns, "tombstone_pct", 0.0) or 0.0
    memory_with_tombstones_gb = index_mem_gb * (1.0 + tombstone_pct) + data_mem_gb

    # Storage used (only when on D): PI/SI same size as shmem; data with compression
    storage_used_gb = 0.0
    if placement.get("primary") == "D":
        storage_used_gb += primary_gb
    if placement.get("si") == "D":
        storage_used_gb += secondary_gb
    if placement.get("data") == "D":
        storage_used_gb += data_stored_gb * compression_ratio

    per_ns = {
        "name": ns.name or "",
        "data_stored_gb": data_stored_gb,
        "memory_used_gb": memory_with_tombstones_gb,
        "storage_used_gb": storage_used_gb,
    }
    return (
        data_stored_gb,
        memory_base_gb,
        memory_with_tombstones_gb,
        storage_used_gb,
        per_ns,
    )


def run_multi(cluster: ClusterInputs, namespaces: list[NamespaceInputs]) -> CapacityOutputs:
    """
    Run the capacity model for cluster + multiple namespaces. Aggregates data stored
    and memory used across namespaces; computes cluster-level utilization from totals.
    """
    if not namespaces:
        raise ValueError("At least one namespace is required")

    # --- Cluster-level (no workload) ---
    device_total_storage_tb = F.device_total_storage_tb(
        cluster.nodes_per_cluster, cluster.devices_per_node, cluster.device_size_gb
    )
    total_device_count = F.total_device_count(
        cluster.nodes_per_cluster, cluster.devices_per_node
    )
    total_usable_storage_gb = F.total_usable_storage_cluster_gb(
        cluster.nodes_per_cluster,
        cluster.devices_per_node,
        cluster.device_size_gb,
    )
    available_after_overhead_gb = F.available_memory_after_overhead_gb(
        cluster.available_memory_gb, cluster.overhead_pct
    )
    available_mem_per_cluster_gb = F.available_mem_per_cluster_gb(
        cluster.nodes_per_cluster, available_after_overhead_gb
    )
    effective_nodes = F.effective_nodes(cluster.nodes_per_cluster, cluster.nodes_lost)
    failure_total_available_gb = F.failure_usable_storage_gb(
        effective_nodes,
        cluster.devices_per_node,
        cluster.device_size_gb,
    )
    failure_available_mem_gb = effective_nodes * available_after_overhead_gb

    # --- Per-namespace then aggregate (placement- and compression-aware) ---
    total_data_stored_gb = 0.0
    total_memory_used_base_gb = 0.0
    total_memory_with_tombstones_gb = 0.0
    total_storage_used_gb = 0.0
    per_namespace_list: list = []
    for ns in namespaces:
        d, mem_base, mem_tombstones, storage_used, per_ns = _run_one_namespace(cluster, ns)
        total_data_stored_gb += d
        total_memory_used_base_gb += mem_base
        total_memory_with_tombstones_gb += mem_tombstones
        total_storage_used_gb += storage_used
        per_namespace_list.append(per_ns)

    total_memory_tombstones_gb = total_memory_with_tombstones_gb - total_memory_used_base_gb

    # --- Healthy cluster (aggregated): storage util uses placement-aware total_storage_used_gb ---
    storage_utilization_pct = F.storage_utilization_pct(
        total_storage_used_gb, total_usable_storage_gb
    )
    # MaxDataPct = min(stop_writes_at_storage_pct, 100 - min_available_storage_pct); use min across namespaces (most conservative)
    max_data_pct = 100.0
    for ns in namespaces:
        stop = getattr(ns, "stop_writes_at_storage_pct", 90.0) or 90.0
        min_avail = getattr(ns, "min_available_storage_pct", 5.0) or 5.0
        pct = min(stop, 100.0 - min_avail)
        if pct < max_data_pct:
            max_data_pct = pct
    usable_storage_with_thresholds_gb = F.usable_storage_with_max_data_pct(
        total_usable_storage_gb, max_data_pct
    )
    storage_utilization_with_thresholds_pct = F.storage_utilization_with_thresholds_pct(
        total_storage_used_gb, usable_storage_with_thresholds_gb
    )
    memory_utilization_base_pct = F.memory_utilization_base_pct(
        total_memory_used_base_gb, available_mem_per_cluster_gb
    )
    memory_utilization_tombstones_pct = (
        100.0 * total_memory_with_tombstones_gb / available_mem_per_cluster_gb
        if available_mem_per_cluster_gb > 0
        else 0.0
    )

    # --- Failure scenario (aggregated): use same placement-aware totals ---
    failure_storage_util_pct = F.failure_storage_utilization_pct(
        total_storage_used_gb, failure_total_available_gb
    )
    failure_memory_util_pct = (
        100.0 * total_memory_used_base_gb / failure_available_mem_gb
        if failure_available_mem_gb > 0
        else 0.0
    )

    # --- Performance (Capacity planner v3.0): effective read/write pct and avg record size (weighted by data_stored_gb) ---
    total_iops_per_node_k = 0.0
    estimated_iops_per_cluster_k = 0.0
    reads_per_second_k = 0.0
    writes_per_second_k = 0.0
    read_bandwidth_mbs = 0.0
    write_bandwidth_mbs = 0.0
    total_throughput_per_node_mbs = 0.0
    peak_throughput_per_cluster_mbs = 0.0
    iops_per_disk_k = getattr(cluster, "iops_per_disk_k", 0.0) or 0.0
    throughput_per_disk_mbs = getattr(cluster, "throughput_per_disk_mbs", 0.0) or 0.0
    if iops_per_disk_k > 0 or throughput_per_disk_mbs > 0:
        if total_data_stored_gb > 0 and per_namespace_list:
            weight_sum = sum(p.get("data_stored_gb", 0) or 0 for p in per_namespace_list)
            if weight_sum > 0:
                read_pct_eff = sum(
                    (getattr(ns, "read_pct", 0.5) or 0.5) * (per_namespace_list[i].get("data_stored_gb") or 0)
                    for i, ns in enumerate(namespaces)
                ) / weight_sum
                write_pct_eff = sum(
                    (getattr(ns, "write_pct", 0.5) or 0.5) * (per_namespace_list[i].get("data_stored_gb") or 0)
                    for i, ns in enumerate(namespaces)
                ) / weight_sum
                avg_record_size_eff = sum(
                    (getattr(ns, "avg_record_size_bytes", 500) or 500) * (per_namespace_list[i].get("data_stored_gb") or 0)
                    for i, ns in enumerate(namespaces)
                ) / weight_sum
            else:
                read_pct_eff = getattr(namespaces[0], "read_pct", 0.5) or 0.5
                write_pct_eff = getattr(namespaces[0], "write_pct", 0.5) or 0.5
                avg_record_size_eff = getattr(namespaces[0], "avg_record_size_bytes", 500) or 500
        else:
            read_pct_eff = getattr(namespaces[0], "read_pct", 0.5) or 0.5 if namespaces else 0.5
            write_pct_eff = getattr(namespaces[0], "write_pct", 0.5) or 0.5 if namespaces else 0.5
            avg_record_size_eff = getattr(namespaces[0], "avg_record_size_bytes", 500) or 500 if namespaces else 500
        if iops_per_disk_k > 0:
            total_iops_per_node_k = F.total_iops_per_node_k(cluster.devices_per_node, iops_per_disk_k)
            estimated_iops_per_cluster_k = F.estimated_iops_per_cluster_k(
                cluster.nodes_per_cluster, total_iops_per_node_k
            )
            reads_per_second_k = F.reads_per_second_k(read_pct_eff, estimated_iops_per_cluster_k)
            writes_per_second_k = F.writes_per_second_k(write_pct_eff, estimated_iops_per_cluster_k)
            read_bandwidth_mbs = F.read_bandwidth_mbs(reads_per_second_k, avg_record_size_eff)
            write_bandwidth_mbs = F.write_bandwidth_mbs(writes_per_second_k, avg_record_size_eff)
        if throughput_per_disk_mbs > 0:
            total_throughput_per_node_mbs = F.total_throughput_per_node_mbs(
                cluster.devices_per_node, throughput_per_disk_mbs
            )
            peak_throughput_per_cluster_mbs = F.peak_throughput_per_cluster_mbs(
                total_throughput_per_node_mbs, cluster.nodes_per_cluster
            )

    return CapacityOutputs(
        device_total_storage_tb=device_total_storage_tb,
        total_device_count=total_device_count,
        data_stored_gb=total_data_stored_gb,
        total_available_storage_gb=total_usable_storage_gb,
        total_storage_used_gb=total_storage_used_gb,
        storage_utilization_pct=storage_utilization_pct,
        storage_utilization_with_thresholds_pct=storage_utilization_with_thresholds_pct,
        usable_storage_with_thresholds_gb=usable_storage_with_thresholds_gb,
        available_mem_per_cluster_gb=available_mem_per_cluster_gb,
        memory_utilization_base_pct=memory_utilization_base_pct,
        total_memory_used_base_gb=total_memory_used_base_gb,
        memory_utilization_with_tombstones_pct=memory_utilization_tombstones_pct,
        total_memory_tombstones_gb=total_memory_tombstones_gb,
        effective_nodes=effective_nodes,
        failure_storage_utilization_pct=failure_storage_util_pct,
        failure_data_stored_gb=total_data_stored_gb,
        failure_total_available_storage_gb=failure_total_available_gb,
        failure_memory_utilization_pct=failure_memory_util_pct,
        failure_memory_used_gb=total_memory_used_base_gb,
        per_namespace=per_namespace_list,
        projected_data_1yr_gb=_projected_data_1yr_gb(
            total_data_stored_gb,
            getattr(cluster, "data_growth_pct_per_year", 0.0) or 0.0,
        ),
        headroom_to_stop_writes_pct=_headroom_to_stop_writes_pct(
            total_data_stored_gb,
            usable_storage_with_thresholds_gb,
        ),
        months_to_stop_writes_est=_months_to_stop_writes_est(
            total_data_stored_gb,
            usable_storage_with_thresholds_gb,
            getattr(cluster, "data_growth_pct_per_year", 0.0) or 0.0,
        ),
        total_iops_per_node_k=total_iops_per_node_k,
        estimated_iops_per_cluster_k=estimated_iops_per_cluster_k,
        reads_per_second_k=reads_per_second_k,
        writes_per_second_k=writes_per_second_k,
        read_bandwidth_mbs=read_bandwidth_mbs,
        write_bandwidth_mbs=write_bandwidth_mbs,
        total_throughput_per_node_mbs=total_throughput_per_node_mbs,
        peak_throughput_per_cluster_mbs=peak_throughput_per_cluster_mbs,
    )


def run(inp: CapacityInputs) -> CapacityOutputs:
    """
    Run the capacity model in dependency order and return all outputs.
    Backward compatible: converts flat CapacityInputs to cluster + one namespace
    and delegates to run_multi so results are identical to the previous implementation.
    """
    cluster, namespaces = capacity_inputs_to_cluster_and_namespaces(inp)
    return run_multi(cluster, namespaces)
