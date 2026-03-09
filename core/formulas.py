"""
Capacity formulas: human-readable, one function per calculation.

See docs/CALCULATION_CATALOG.md for mapping to spreadsheet sources (one-time reference).
"""

from __future__ import annotations


# --- Constants (see CALCULATION_CATALOG for source refs) ---
MTU_BYTES = 1500.0
HEADER_OVERHEAD = 320.0
FRAGMENTATION_FACTOR = 0.024  # (1 - this) = usable storage fraction
RECORD_METADATA_BYTES = 64.0  # per-record overhead


def device_total_storage_tb(
    nodes_per_cluster: float,
    devices_per_node: float,
    device_size_gb: float,
) -> float:
    """Total device storage in TB: (nodes × devices per node × device size GB) / 1024."""
    return (nodes_per_cluster * devices_per_node * device_size_gb) / 1024.0


def total_device_count(nodes_per_cluster: float, devices_per_node: float) -> float:
    """Total device count: nodes per cluster × devices per node."""
    return nodes_per_cluster * devices_per_node


def available_memory_after_overhead_gb(
    available_memory_gb: float, overhead_pct: float
) -> float:
    """Usable memory per node after overhead: available memory × (1 − overhead pct)."""
    return available_memory_gb * (1.0 - overhead_pct)


def memory_overhead_gb(available_memory_gb: float, overhead_pct: float) -> float:
    """Overhead amount in GB: available memory − available after overhead."""
    return available_memory_gb - available_memory_after_overhead_gb(
        available_memory_gb, overhead_pct
    )


def total_objects(replication_factor: float, master_object_count: float) -> float:
    """Total object count (replicated): replication factor × master object count."""
    return replication_factor * master_object_count


def data_size_gb(
    master_object_count: float,
    replication_factor: float,
    avg_record_size_bytes: float,
) -> float:
    """Data size in GB: (master objects × replication × avg record size bytes) / 1024³."""
    return (
        master_object_count * replication_factor * avg_record_size_bytes
    ) / (1024.0**3)


def usable_storage_per_node_gb(
    devices_per_node: float,
    device_size_gb: float,
    fragmentation_factor: float = FRAGMENTATION_FACTOR,
) -> float:
    """Usable storage per node in GB: devices per node × device size × (1 − fragmentation factor)."""
    return devices_per_node * device_size_gb * (1.0 - fragmentation_factor)


def total_usable_storage_cluster_gb(
    nodes_per_cluster: float,
    devices_per_node: float,
    device_size_gb: float,
    fragmentation_factor: float = FRAGMENTATION_FACTOR,
) -> float:
    """Total usable storage for cluster in GB: nodes × devices per node × device size × (1 − fragmentation factor)."""
    return (
        nodes_per_cluster
        * devices_per_node
        * device_size_gb
        * (1.0 - fragmentation_factor)
    )


def available_mem_per_cluster_gb(
    nodes_per_cluster: float, available_memory_after_overhead_gb: float
) -> float:
    """Available memory for cluster in GB: nodes per cluster × available memory after overhead per node."""
    return nodes_per_cluster * available_memory_after_overhead_gb


def total_memory_used_base_gb(
    total_objects: float,
    avg_record_size_bytes: float,
) -> float:
    """Memory for primary index (data) in GB: total objects × avg record size bytes / 1024³."""
    return (total_objects * avg_record_size_bytes) / (1024.0**3)


def storage_utilization_pct(
    data_stored_gb: float, total_available_storage_gb: float
) -> float:
    """Storage utilization %: 100 × (data stored GB / total available storage GB)."""
    if total_available_storage_gb <= 0:
        return 0.0
    return 100.0 * data_stored_gb / total_available_storage_gb


def memory_utilization_base_pct(
    total_memory_used_base_gb: float, available_mem_per_cluster_gb: float
) -> float:
    """Base memory utilization %: 100 × (memory used base GB / available mem per cluster GB)."""
    if available_mem_per_cluster_gb <= 0:
        return 0.0
    return 100.0 * total_memory_used_base_gb / available_mem_per_cluster_gb


def effective_nodes(nodes_per_cluster: float, nodes_lost: float) -> float:
    """Effective nodes after failure: nodes per cluster − nodes lost (min 0)."""
    return max(0.0, nodes_per_cluster - nodes_lost)


def failure_usable_storage_gb(
    effective_nodes: float,
    devices_per_node: float,
    device_size_gb: float,
    fragmentation_factor: float = FRAGMENTATION_FACTOR,
) -> float:
    """Usable storage in failure scenario in GB: effective nodes × devices per node × device size × (1 − fragmentation factor)."""
    return (
        effective_nodes
        * devices_per_node
        * device_size_gb
        * (1.0 - fragmentation_factor)
    )


def failure_storage_utilization_pct(
    data_stored_gb: float, failure_total_available_gb: float
) -> float:
    """Storage utilization % in failure scenario: 100 × (data stored / failure total available GB)."""
    if failure_total_available_gb <= 0:
        return 0.0
    return 100.0 * data_stored_gb / failure_total_available_gb
