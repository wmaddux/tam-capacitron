"""
Capacity planning input/output model and default values.

See docs/CALCULATION_CATALOG.md for mapping to spreadsheet sources.
See docs/API_MULTI_NAMESPACE.md for the cluster + namespaces request contract.
All inputs use sensible minimum defaults so the app is usable on load.
"""

from dataclasses import dataclass, asdict, field
from typing import Any


def _default_placement() -> dict[str, str]:
    """Default placement HMA (MMD): PI in M, SI in M, data on D."""
    return {"primary": "M", "si": "M", "data": "D"}


@dataclass
class ClusterInputs:
    """Cluster-level parameters (one value for the whole cluster)."""

    nodes_per_cluster: float = 6.0
    devices_per_node: float = 3.0
    device_size_gb: float = 256.0
    available_memory_gb: float = 128.0
    overhead_pct: float = 0.15
    nodes_lost: float = 0.0
    cluster_name: str = ""
    default_storage_pattern: str = "HMA (MMD)"
    # Server instance specs (for mapping from cloud instance type; not used in calculations yet)
    vcpus: float = 0.0
    instance_storage: str = ""
    instance_networking: str = ""
    # Data growth (% per year) for projected data and months-to-stop-writes
    data_growth_pct_per_year: float = 0.0
    # Performance (Capacity planner v3.0)
    iops_per_disk_k: float = 320.0
    throughput_per_disk_mbs: float = 1500.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ClusterInputs":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class NamespaceInputs:
    """Workload parameters for one namespace."""

    name: str = ""
    replication_factor: float = 2.0
    master_object_count: float = 1e6
    avg_record_size_bytes: float = 500.0
    read_pct: float = 0.5
    write_pct: float = 0.5
    tombstone_pct: float = 0.0
    si_count: float = 0.0
    si_entries_per_object: float = 0.0
    storage_pattern: str = "HMA (MMD)"
    placement: dict = field(default_factory=_default_placement)
    compression_ratio: float = 1.0
    stop_writes_at_storage_pct: float = 90.0
    evict_at_memory_pct: float = 95.0
    min_available_storage_pct: float = 5.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "NamespaceInputs":
        kwargs = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        if "placement" in kwargs and kwargs["placement"] is None:
            kwargs["placement"] = _default_placement()
        return cls(**kwargs)


@dataclass
class CapacityInputs:
    """All inputs for the capacity engine. Defaults are representative of a test cluster (mid-range outputs)."""

    # Topology
    replication_factor: float = 2.0
    nodes_per_cluster: float = 6.0
    devices_per_node: float = 3.0
    device_size_gb: float = 256.0

    # Server / memory
    available_memory_gb: float = 128.0
    overhead_pct: float = 0.15

    # Workload
    master_object_count: float = 1e6
    avg_record_size_bytes: float = 500.0
    read_pct: float = 0.5
    write_pct: float = 0.5
    tombstone_pct: float = 0.0
    si_count: float = 0.0
    si_entries_per_object: float = 0.0

    # Resilience
    nodes_lost: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CapacityInputs":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def get_default_inputs() -> CapacityInputs:
    """Load-from-defaults: return inputs from config/inputs.json, else dataclass defaults."""
    try:
        from app.config import get_defaults
        overrides = get_defaults()
    except Exception:
        overrides = {}
    base = CapacityInputs()
    base_dict = asdict(base)
    for k, v in overrides.items():
        if k in base_dict:
            base_dict[k] = v
    return CapacityInputs(**base_dict)


def capacity_inputs_to_cluster_and_namespaces(
    inp: CapacityInputs,
) -> tuple[ClusterInputs, list[NamespaceInputs]]:
    """
    Convert flat CapacityInputs to cluster + one namespace (for backward compatibility).
    """
    cluster = ClusterInputs(
        nodes_per_cluster=inp.nodes_per_cluster,
        devices_per_node=inp.devices_per_node,
        device_size_gb=inp.device_size_gb,
        available_memory_gb=inp.available_memory_gb,
        overhead_pct=inp.overhead_pct,
        nodes_lost=inp.nodes_lost,
    )
    ns = NamespaceInputs(
        name="",
        replication_factor=inp.replication_factor,
        master_object_count=inp.master_object_count,
        avg_record_size_bytes=inp.avg_record_size_bytes,
        read_pct=inp.read_pct,
        write_pct=inp.write_pct,
        tombstone_pct=inp.tombstone_pct,
        si_count=inp.si_count,
        si_entries_per_object=inp.si_entries_per_object,
    )
    return cluster, [ns]


@dataclass
class CapacityOutputs:
    """All outputs from the capacity engine."""

    # Healthy cluster – storage
    device_total_storage_tb: float = 0.0
    total_device_count: float = 0.0
    data_stored_gb: float = 0.0
    total_available_storage_gb: float = 0.0
    total_storage_used_gb: float = 0.0
    storage_utilization_pct: float = 0.0
    storage_utilization_with_thresholds_pct: float = 0.0
    usable_storage_with_thresholds_gb: float = 0.0  # for Show my work / headroom

    # Healthy cluster – memory
    available_mem_per_cluster_gb: float = 0.0
    memory_utilization_base_pct: float = 0.0
    total_memory_used_base_gb: float = 0.0
    memory_utilization_with_tombstones_pct: float = 0.0
    total_memory_tombstones_gb: float = 0.0

    # Failure scenario
    effective_nodes: float = 0.0
    failure_storage_utilization_pct: float = 0.0
    failure_data_stored_gb: float = 0.0
    failure_total_available_storage_gb: float = 0.0
    failure_memory_utilization_pct: float = 0.0
    failure_memory_used_gb: float = 0.0

    # Per-namespace breakdown (optional)
    per_namespace: list = field(default_factory=list)

    # Data growth (optional; requires data_growth_pct_per_year and thresholds)
    projected_data_1yr_gb: float | None = None
    headroom_to_stop_writes_pct: float | None = None
    months_to_stop_writes_est: float | None = None

    # Performance (Capacity planner v3.0; requires iops_per_disk_k, throughput_per_disk_mbs)
    total_iops_per_node_k: float = 0.0
    estimated_iops_per_cluster_k: float = 0.0
    reads_per_second_k: float = 0.0
    writes_per_second_k: float = 0.0
    read_bandwidth_mbs: float = 0.0
    write_bandwidth_mbs: float = 0.0
    total_throughput_per_node_mbs: float = 0.0
    peak_throughput_per_cluster_mbs: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
