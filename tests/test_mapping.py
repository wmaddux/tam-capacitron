"""
Tests for mapping layer: ingestor output dict -> CapacityInputs.
"""

import pytest
from core.model import CapacityInputs, get_default_inputs
from core.engine import run
from ingest.mapping import ingestor_output_to_capacity_inputs


def test_mapping_empty_dict_returns_defaults():
    inp = ingestor_output_to_capacity_inputs({})
    default = get_default_inputs()
    assert inp.replication_factor == default.replication_factor
    assert inp.nodes_per_cluster == default.nodes_per_cluster
    assert inp.nodes_lost == 0.0


def test_mapping_direct_fields():
    d = {
        "replication_factor": 3.0,
        "nodes_per_cluster": 10.0,
        "devices_per_node": 4.0,
        "device_size_gb": 512.0,
        "available_memory_gb": 128.0,
        "overhead_pct": 0.2,
        "object_count": 1e9,
        "si_count": 5.0,
    }
    inp = ingestor_output_to_capacity_inputs(d)
    assert inp.replication_factor == 3.0
    assert inp.nodes_per_cluster == 10.0
    assert inp.devices_per_node == 4.0
    assert inp.device_size_gb == 512.0
    assert inp.available_memory_gb == 128.0
    assert inp.overhead_pct == 0.2
    assert inp.master_object_count == 1e9
    assert inp.si_count == 5.0
    assert inp.nodes_lost == 0.0


def test_mapping_calculated_read_write_pct():
    d = {
        "read_transactions": 70.0,
        "write_transactions": 30.0,
    }
    inp = ingestor_output_to_capacity_inputs(d)
    assert inp.read_pct == pytest.approx(0.7)
    assert inp.write_pct == pytest.approx(0.3)


def test_mapping_avg_record_size_from_data_used():
    d = {
        "object_count": 1_000_000.0,
        "data_used_bytes": 2e9,
        "replication_factor": 2.0,
    }
    inp = ingestor_output_to_capacity_inputs(d)
    # data_used / (object_count * rf) = 2e9 / (1e6 * 2) = 1000
    assert inp.avg_record_size_bytes == pytest.approx(1000.0)


def test_mapping_stub_output_produces_valid_inputs():
    """Stub ingestor output should map to inputs that run through the engine."""
    from ingest.ingestor import _stub_ingestor_output
    d = _stub_ingestor_output()
    inp = ingestor_output_to_capacity_inputs(d)
    out = run(inp)
    assert out.storage_utilization_pct >= 0
    assert out.memory_utilization_base_pct >= 0
    assert out.effective_nodes == inp.nodes_per_cluster - inp.nodes_lost


def test_ingestor_multi_to_cluster_and_namespaces():
    from ingest.mapping import ingestor_multi_to_cluster_and_namespaces

    multi = {
        "cluster": {
            "nodes_per_cluster": 9.0,
            "devices_per_node": 2.0,
            "device_size_gb": 1024.0,
            "available_memory_gb": 128.0,
            "overhead_pct": 0.15,
            "nodes_lost": 0.0,
        },
        "namespaces": [
            {
                "name": "ns1",
                "replication_factor": 2.0,
                "object_count": 1e9,
                "read_pct": 0.6,
                "write_pct": 0.4,
                "tombstone_pct": 0.0,
                "si_count": 0.0,
                "si_entries_per_object": 0.0,
            },
        ],
    }
    out = ingestor_multi_to_cluster_and_namespaces(multi)
    assert "cluster" in out
    assert "namespaces" in out
    assert out["cluster"]["nodes_per_cluster"] == 9.0
    assert out["cluster"]["devices_per_node"] == 2.0
    assert len(out["namespaces"]) == 1
    assert out["namespaces"][0]["name"] == "ns1"
    assert out["namespaces"][0]["replication_factor"] == 2.0
    assert out["namespaces"][0]["master_object_count"] == 1e9
    assert out["namespaces"][0]["read_pct"] == 0.6


def test_ingestor_multi_to_cluster_and_namespaces_empty_namespaces_uses_default():
    from ingest.mapping import ingestor_multi_to_cluster_and_namespaces

    out = ingestor_multi_to_cluster_and_namespaces({"cluster": {"nodes_per_cluster": 4.0}, "namespaces": []})
    assert len(out["namespaces"]) == 1
    assert out["namespaces"][0]["master_object_count"] == get_default_inputs().master_object_count
