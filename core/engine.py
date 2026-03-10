"""
Capacity calculation engine: evaluates formulas in dependency order.

Accepts CapacityInputs (legacy) or cluster + namespaces (multi-namespace).
Returns CapacityOutputs. No UI; used by API and tests.
"""

from core.model import (
    CapacityInputs,
    CapacityOutputs,
    ClusterInputs,
    NamespaceInputs,
    capacity_inputs_to_cluster_and_namespaces,
)
from core import formulas as F  # noqa: I001


def _run_one_namespace(
    cluster: ClusterInputs,
    ns: NamespaceInputs,
) -> tuple[float, float, float]:
    """
    Run workload formulas for one namespace. Returns (data_stored_gb, total_memory_used_base_gb, tombstone_memory_gb).
    total_memory_used_base_gb = Primary Index Shmem + Secondary Index Shmem (per namespace).
    """
    data_stored_gb = F.data_size_gb(
        ns.master_object_count,
        ns.replication_factor,
        ns.avg_record_size_bytes,
    )
    total_memory_used_base_gb = F.total_memory_used_base_gb(
        cluster.nodes_per_cluster,
        ns.replication_factor,
        ns.master_object_count,
        ns.si_count,
        ns.si_entries_per_object,
    )
    tombstone_memory_gb = total_memory_used_base_gb * ns.tombstone_pct * 0.1
    return data_stored_gb, total_memory_used_base_gb, tombstone_memory_gb


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

    # --- Per-namespace then aggregate ---
    total_data_stored_gb = 0.0
    total_memory_used_base_gb = 0.0
    total_tombstone_memory_gb = 0.0
    for ns in namespaces:
        d, m, t = _run_one_namespace(cluster, ns)
        total_data_stored_gb += d
        total_memory_used_base_gb += m
        total_tombstone_memory_gb += t

    total_memory_with_tombstones_gb = total_memory_used_base_gb + total_tombstone_memory_gb

    # --- Healthy cluster (aggregated) ---
    storage_utilization_pct = F.storage_utilization_pct(
        total_data_stored_gb, total_usable_storage_gb
    )
    memory_utilization_base_pct = F.memory_utilization_base_pct(
        total_memory_used_base_gb, available_mem_per_cluster_gb
    )
    memory_utilization_tombstones_pct = (
        100.0 * total_memory_with_tombstones_gb / available_mem_per_cluster_gb
        if available_mem_per_cluster_gb > 0
        else 0.0
    )

    # --- Failure scenario (aggregated) ---
    failure_storage_util_pct = F.failure_storage_utilization_pct(
        total_data_stored_gb, failure_total_available_gb
    )
    failure_memory_util_pct = (
        100.0 * total_memory_used_base_gb / failure_available_mem_gb
        if failure_available_mem_gb > 0
        else 0.0
    )

    return CapacityOutputs(
        device_total_storage_tb=device_total_storage_tb,
        total_device_count=total_device_count,
        data_stored_gb=total_data_stored_gb,
        total_available_storage_gb=total_usable_storage_gb,
        storage_utilization_pct=storage_utilization_pct,
        available_mem_per_cluster_gb=available_mem_per_cluster_gb,
        memory_utilization_base_pct=memory_utilization_base_pct,
        total_memory_used_base_gb=total_memory_used_base_gb,
        memory_utilization_with_tombstones_pct=memory_utilization_tombstones_pct,
        total_memory_tombstones_gb=total_tombstone_memory_gb,
        effective_nodes=effective_nodes,
        failure_storage_utilization_pct=failure_storage_util_pct,
        failure_data_stored_gb=total_data_stored_gb,
        failure_total_available_storage_gb=failure_total_available_gb,
        failure_memory_utilization_pct=failure_memory_util_pct,
        failure_memory_used_gb=total_memory_used_base_gb,
    )


def run(inp: CapacityInputs) -> CapacityOutputs:
    """
    Run the capacity model in dependency order and return all outputs.
    Backward compatible: converts flat CapacityInputs to cluster + one namespace
    and delegates to run_multi so results are identical to the previous implementation.
    """
    cluster, namespaces = capacity_inputs_to_cluster_and_namespaces(inp)
    return run_multi(cluster, namespaces)
