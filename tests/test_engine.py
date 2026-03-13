"""
Engine tests: run with known inputs and assert outputs match expectations.

Can be extended to compare against exported values from the workbook.
"""

import pytest
from core.model import (
    CapacityInputs,
    ClusterInputs,
    NamespaceInputs,
    capacity_inputs_to_cluster_and_namespaces,
    get_default_inputs,
)
from core.engine import run, run_multi


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


def test_run_multi_one_namespace_matches_run():
    """run_multi(cluster, [one namespace]) must match run(CapacityInputs) for same values."""
    inp = CapacityInputs(
        replication_factor=2.0,
        nodes_per_cluster=5.0,
        devices_per_node=2.0,
        device_size_gb=512.0,
        available_memory_gb=128.0,
        overhead_pct=0.15,
        master_object_count=1e9,
        avg_record_size_bytes=1000.0,
        read_pct=0.6,
        write_pct=0.4,
        tombstone_pct=0.02,
        si_count=2.0,
        si_entries_per_object=1.0,
        nodes_lost=1.0,
    )
    out_legacy = run(inp)
    cluster, namespaces = capacity_inputs_to_cluster_and_namespaces(inp)
    out_multi = run_multi(cluster, namespaces)
    assert out_multi.device_total_storage_tb == out_legacy.device_total_storage_tb
    assert out_multi.total_device_count == out_legacy.total_device_count
    assert out_multi.data_stored_gb == out_legacy.data_stored_gb
    assert out_multi.storage_utilization_pct == out_legacy.storage_utilization_pct
    assert out_multi.available_mem_per_cluster_gb == out_legacy.available_mem_per_cluster_gb
    assert out_multi.total_memory_used_base_gb == out_legacy.total_memory_used_base_gb
    assert out_multi.memory_utilization_base_pct == out_legacy.memory_utilization_base_pct
    assert out_multi.effective_nodes == out_legacy.effective_nodes
    assert out_multi.failure_storage_utilization_pct == out_legacy.failure_storage_utilization_pct
    assert out_multi.failure_memory_utilization_pct == out_legacy.failure_memory_utilization_pct


def test_run_multi_two_namespaces_aggregated():
    """Two namespaces: data_stored and memory_used are sums; utilization from totals."""
    cluster = ClusterInputs(
        nodes_per_cluster=4.0,
        devices_per_node=2.0,
        device_size_gb=256.0,
        available_memory_gb=64.0,
        overhead_pct=0.15,
        nodes_lost=0.0,
    )
    ns1 = NamespaceInputs(
        name="ns1",
        replication_factor=2.0,
        master_object_count=1e6,
        avg_record_size_bytes=500.0,
        read_pct=0.5,
        write_pct=0.5,
        tombstone_pct=0.0,
        si_count=0.0,
        si_entries_per_object=0.0,
    )
    ns2 = NamespaceInputs(
        name="ns2",
        replication_factor=2.0,
        master_object_count=2e6,
        avg_record_size_bytes=300.0,
        read_pct=0.5,
        write_pct=0.5,
        tombstone_pct=0.0,
        si_count=0.0,
        si_entries_per_object=0.0,
    )
    out = run_multi(cluster, [ns1, ns2])
    # Single-namespace data: ns1 ~ (1e6*2*500)/1024^3, ns2 ~ (2e6*2*300)/1024^3
    out_ns1_only = run_multi(cluster, [ns1])
    out_ns2_only = run_multi(cluster, [ns2])
    expected_data_gb = out_ns1_only.data_stored_gb + out_ns2_only.data_stored_gb
    expected_memory_gb = out_ns1_only.total_memory_used_base_gb + out_ns2_only.total_memory_used_base_gb
    assert out.data_stored_gb == pytest.approx(expected_data_gb, rel=1e-9)
    assert out.total_memory_used_base_gb == pytest.approx(expected_memory_gb, rel=1e-9)
    assert out.storage_utilization_pct >= out_ns1_only.storage_utilization_pct
    assert out.storage_utilization_pct >= out_ns2_only.storage_utilization_pct
    assert out.device_total_storage_tb == out_ns1_only.device_total_storage_tb
    assert out.available_mem_per_cluster_gb == out_ns1_only.available_mem_per_cluster_gb


def test_run_multi_empty_namespaces_raises():
    """run_multi requires at least one namespace."""
    cluster = ClusterInputs(nodes_per_cluster=3.0)
    with pytest.raises(ValueError, match="At least one namespace"):
        run_multi(cluster, [])


def test_run_multi_returns_per_namespace_and_total_storage_used():
    """run_multi returns per_namespace list and total_storage_used_gb."""
    cluster = ClusterInputs(nodes_per_cluster=3.0, devices_per_node=2.0, device_size_gb=100.0)
    ns = NamespaceInputs(
        name="test",
        replication_factor=2.0,
        master_object_count=1e6,
        avg_record_size_bytes=500.0,
        si_count=0.0,
        si_entries_per_object=0.0,
    )
    out = run_multi(cluster, [ns])
    assert hasattr(out, "per_namespace")
    assert len(out.per_namespace) == 1
    assert out.per_namespace[0]["name"] == "test"
    assert "data_stored_gb" in out.per_namespace[0]
    assert "memory_used_gb" in out.per_namespace[0]
    assert "storage_used_gb" in out.per_namespace[0]
    assert out.total_storage_used_gb >= 0
    assert out.total_storage_used_gb == pytest.approx(out.per_namespace[0]["storage_used_gb"], rel=1e-9)


def test_run_multi_placement_all_d_storage_only():
    """With All Flash (DDD), storage_used includes PI + SI + data; memory used is minimal (no index/data on M)."""
    cluster = ClusterInputs(nodes_per_cluster=3.0, devices_per_node=2.0, device_size_gb=500.0)
    ns = NamespaceInputs(
        name="flash",
        replication_factor=2.0,
        master_object_count=1e6,
        avg_record_size_bytes=400.0,
        storage_pattern="All Flash (DDD)",
        placement={"primary": "D", "si": "D", "data": "D"},
        compression_ratio=1.0,
        si_count=1.0,
        si_entries_per_object=0.5,
    )
    out = run_multi(cluster, [ns])
    assert out.per_namespace[0]["storage_used_gb"] > 0
    assert out.per_namespace[0]["memory_used_gb"] == 0.0
    assert out.total_memory_used_base_gb == 0.0
    assert out.total_storage_used_gb >= out.data_stored_gb  # PI + SI + data on D


def test_run_multi_placement_all_m_memory_only():
    """With In-Memory (MMM), memory_used includes PI + SI + data; storage_used is 0."""
    cluster = ClusterInputs(nodes_per_cluster=3.0, devices_per_node=2.0, device_size_gb=500.0)
    ns = NamespaceInputs(
        name="mem",
        replication_factor=2.0,
        master_object_count=500_000.0,
        avg_record_size_bytes=200.0,
        storage_pattern="In-Memory (MMM)",
        placement={"primary": "M", "si": "M", "data": "M"},
        compression_ratio=1.0,
        si_count=0.0,
        si_entries_per_object=0.0,
    )
    out = run_multi(cluster, [ns])
    assert out.per_namespace[0]["storage_used_gb"] == 0.0
    assert out.per_namespace[0]["memory_used_gb"] > 0
    assert out.total_storage_used_gb == 0.0
    assert out.storage_utilization_pct == 0.0


def test_run_multi_compression_reduces_storage_used():
    """With data on D and compression_ratio < 1, storage_used is less than data_stored."""
    cluster = ClusterInputs(nodes_per_cluster=3.0, devices_per_node=2.0, device_size_gb=500.0)
    ns_no_comp = NamespaceInputs(
        name="nocomp",
        replication_factor=2.0,
        master_object_count=1e6,
        avg_record_size_bytes=500.0,
        compression_ratio=1.0,
        si_count=0.0,
        si_entries_per_object=0.0,
    )
    ns_comp = NamespaceInputs(
        name="comp",
        replication_factor=2.0,
        master_object_count=1e6,
        avg_record_size_bytes=500.0,
        compression_ratio=0.5,
        si_count=0.0,
        si_entries_per_object=0.0,
    )
    out_no = run_multi(cluster, [ns_no_comp])
    out_comp = run_multi(cluster, [ns_comp])
    assert out_comp.total_storage_used_gb < out_no.total_storage_used_gb
    assert out_comp.per_namespace[0]["storage_used_gb"] == pytest.approx(
        out_no.per_namespace[0]["storage_used_gb"] * 0.5, rel=1e-5
    )
