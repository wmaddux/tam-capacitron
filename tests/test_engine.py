"""
Engine tests: run with known inputs and assert outputs match expectations.

Can be extended to compare against exported values from the workbook.
"""

import pytest
from core.model import CapacityInputs, get_default_inputs
from core.engine import run


def test_run_with_defaults():
    inp = get_default_inputs()
    out = run(inp)
    assert out.total_device_count == inp.nodes_per_cluster * inp.devices_per_node
    assert out.device_total_storage_tb > 0
    assert out.data_stored_gb >= 0
    assert out.storage_utilization_pct >= 0
    assert out.effective_nodes == inp.nodes_per_cluster - inp.nodes_lost


def test_run_with_workbook_like_inputs():
    """Inputs similar to Compare tab: RF=2, nodes=9, devices=11, device 1024 GB, etc."""
    inp = CapacityInputs(
        replication_factor=2.0,
        nodes_per_cluster=9.0,
        devices_per_node=11.0,
        device_size_gb=1024.0,
        available_memory_gb=195.0,
        overhead_pct=0.15,
        master_object_count=7.08e9,
        avg_record_size_bytes=5063.0,
        read_pct=0.393,
        write_pct=0.607,
        tombstone_pct=0.0,
        si_count=0.0,
        si_entries_per_object=0.0,
        nodes_lost=3.0,
    )
    out = run(inp)
    # Compare tab: device total storage ~97.75 TB
    assert 90 <= out.device_total_storage_tb <= 105
    assert out.total_device_count == 99.0
    assert out.effective_nodes == 6.0
    assert out.data_stored_gb > 0
    assert out.storage_utilization_pct >= 0
