"""
Capacity calculation engine: evaluates formulas in dependency order.

Accepts CapacityInputs, returns CapacityOutputs. No UI; used by API and tests.
"""

from core.model import CapacityInputs, CapacityOutputs
from core import formulas as F  # noqa: I001


def run(inp: CapacityInputs) -> CapacityOutputs:
    """
    Run the capacity model in dependency order and return all outputs.
    """
    # --- Topology & storage (no dependency on workload) ---
    device_total_storage_tb = F.device_total_storage_tb(
        inp.nodes_per_cluster, inp.devices_per_node, inp.device_size_gb
    )
    total_device_count = F.total_device_count(
        inp.nodes_per_cluster, inp.devices_per_node
    )
    total_usable_storage_gb = F.total_usable_storage_cluster_gb(
        inp.nodes_per_cluster,
        inp.devices_per_node,
        inp.device_size_gb,
    )

    # --- Memory (per-node and cluster) ---
    available_after_overhead_gb = F.available_memory_after_overhead_gb(
        inp.available_memory_gb, inp.overhead_pct
    )
    available_mem_per_cluster_gb = F.available_mem_per_cluster_gb(
        inp.nodes_per_cluster, available_after_overhead_gb
    )

    # --- Workload-derived ---
    total_objects = F.total_objects(
        inp.replication_factor, inp.master_object_count
    )
    data_stored_gb = F.data_size_gb(
        inp.master_object_count,
        inp.replication_factor,
        inp.avg_record_size_bytes,
    )
    total_memory_used_base_gb = F.total_memory_used_base_gb(
        total_objects, inp.avg_record_size_bytes
    )

    # --- Tombstone memory (simplified: extra bytes per tombstone pct) ---
    tombstone_memory_gb = (
        total_memory_used_base_gb * inp.tombstone_pct * 0.1
    )  # placeholder scale
    total_memory_with_tombstones_gb = total_memory_used_base_gb + tombstone_memory_gb

    # --- Healthy cluster outputs ---
    storage_utilization_pct = F.storage_utilization_pct(
        data_stored_gb, total_usable_storage_gb
    )
    memory_utilization_base_pct = F.memory_utilization_base_pct(
        total_memory_used_base_gb, available_mem_per_cluster_gb
    )
    memory_utilization_tombstones_pct = (
        100.0 * total_memory_with_tombstones_gb / available_mem_per_cluster_gb
        if available_mem_per_cluster_gb > 0
        else 0.0
    )

    # --- Failure scenario ---
    effective_nodes = F.effective_nodes(
        inp.nodes_per_cluster, inp.nodes_lost
    )
    failure_total_available_gb = F.failure_usable_storage_gb(
        effective_nodes,
        inp.devices_per_node,
        inp.device_size_gb,
    )
    failure_storage_util_pct = F.failure_storage_utilization_pct(
        data_stored_gb, failure_total_available_gb
    )
    # Failure memory: same data, less available nodes
    failure_available_mem_gb = effective_nodes * available_after_overhead_gb
    failure_memory_util_pct = (
        100.0 * total_memory_used_base_gb / failure_available_mem_gb
        if failure_available_mem_gb > 0
        else 0.0
    )

    return CapacityOutputs(
        device_total_storage_tb=device_total_storage_tb,
        total_device_count=total_device_count,
        data_stored_gb=data_stored_gb,
        total_available_storage_gb=total_usable_storage_gb,
        storage_utilization_pct=storage_utilization_pct,
        available_mem_per_cluster_gb=available_mem_per_cluster_gb,
        memory_utilization_base_pct=memory_utilization_base_pct,
        total_memory_used_base_gb=total_memory_used_base_gb,
        memory_utilization_with_tombstones_pct=memory_utilization_tombstones_pct,
        total_memory_tombstones_gb=tombstone_memory_gb,
        effective_nodes=effective_nodes,
        failure_storage_utilization_pct=failure_storage_util_pct,
        failure_data_stored_gb=data_stored_gb,
        failure_total_available_storage_gb=failure_total_available_gb,
        failure_memory_utilization_pct=failure_memory_util_pct,
        failure_memory_used_gb=total_memory_used_base_gb,
    )
