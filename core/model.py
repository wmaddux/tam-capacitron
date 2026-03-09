"""
Capacity planning input/output model and default values.

See docs/CALCULATION_CATALOG.md for mapping to spreadsheet sources.
All inputs use sensible minimum defaults so the app is usable on load.
"""

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class CapacityInputs:
    """All inputs for the capacity engine. Defaults are minimum safe values."""

    # Topology
    replication_factor: float = 2.0
    nodes_per_cluster: float = 3.0
    devices_per_node: float = 2.0
    device_size_gb: float = 256.0

    # Server / memory
    available_memory_gb: float = 64.0
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
    """Load-from-defaults: return inputs at minimum safe values."""
    return CapacityInputs()


@dataclass
class CapacityOutputs:
    """All outputs from the capacity engine."""

    # Healthy cluster – storage
    device_total_storage_tb: float = 0.0
    total_device_count: float = 0.0
    data_stored_gb: float = 0.0
    total_available_storage_gb: float = 0.0
    storage_utilization_pct: float = 0.0

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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
