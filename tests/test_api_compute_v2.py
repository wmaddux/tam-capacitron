"""
API tests: POST /api/compute (legacy) and POST /api/compute-v2 (multi-namespace).

Ensures backward compatibility and that compute-v2 accepts cluster + namespaces.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_api_compute_legacy_returns_outputs():
    """POST /api/compute with flat body returns outputs."""
    body = {
        "replication_factor": 2.0,
        "nodes_per_cluster": 4.0,
        "devices_per_node": 2.0,
        "device_size_gb": 256.0,
        "available_memory_gb": 64.0,
        "overhead_pct": 0.15,
        "master_object_count": 1e6,
        "avg_record_size_bytes": 500.0,
        "read_pct": 0.5,
        "write_pct": 0.5,
        "tombstone_pct": 0.0,
        "si_count": 0.0,
        "si_entries_per_object": 0.0,
        "nodes_lost": 0.0,
    }
    r = client.post("/api/compute", json=body)
    assert r.status_code == 200
    data = r.json()
    assert "storage_utilization_pct" in data
    assert "data_stored_gb" in data
    assert "effective_nodes" in data
    assert data["effective_nodes"] == 4.0


def test_api_compute_v2_one_namespace_matches_legacy():
    """POST /api/compute-v2 with cluster + one namespace returns same outputs as /api/compute."""
    flat = {
        "replication_factor": 2.0,
        "nodes_per_cluster": 5.0,
        "devices_per_node": 2.0,
        "device_size_gb": 512.0,
        "available_memory_gb": 128.0,
        "overhead_pct": 0.15,
        "master_object_count": 1e9,
        "avg_record_size_bytes": 1000.0,
        "read_pct": 0.6,
        "write_pct": 0.4,
        "tombstone_pct": 0.02,
        "si_count": 2.0,
        "si_entries_per_object": 1.0,
        "nodes_lost": 1.0,
    }
    r_legacy = client.post("/api/compute", json=flat)
    assert r_legacy.status_code == 200
    out_legacy = r_legacy.json()

    v2_body = {
        "cluster": {
            "nodes_per_cluster": flat["nodes_per_cluster"],
            "devices_per_node": flat["devices_per_node"],
            "device_size_gb": flat["device_size_gb"],
            "available_memory_gb": flat["available_memory_gb"],
            "overhead_pct": flat["overhead_pct"],
            "nodes_lost": flat["nodes_lost"],
        },
        "namespaces": [
            {
                "name": "default",
                "replication_factor": flat["replication_factor"],
                "master_object_count": flat["master_object_count"],
                "avg_record_size_bytes": flat["avg_record_size_bytes"],
                "read_pct": flat["read_pct"],
                "write_pct": flat["write_pct"],
                "tombstone_pct": flat["tombstone_pct"],
                "si_count": flat["si_count"],
                "si_entries_per_object": flat["si_entries_per_object"],
            }
        ],
    }
    r_v2 = client.post("/api/compute-v2", json=v2_body)
    assert r_v2.status_code == 200
    out_v2 = r_v2.json()

    assert out_v2["data_stored_gb"] == out_legacy["data_stored_gb"]
    assert out_v2["storage_utilization_pct"] == out_legacy["storage_utilization_pct"]
    assert out_v2["total_memory_used_base_gb"] == out_legacy["total_memory_used_base_gb"]
    assert out_v2["effective_nodes"] == out_legacy["effective_nodes"]


def test_api_compute_v2_two_namespaces_aggregated():
    """POST /api/compute-v2 with two namespaces returns aggregated outputs."""
    body = {
        "cluster": {
            "nodes_per_cluster": 4.0,
            "devices_per_node": 2.0,
            "device_size_gb": 256.0,
            "available_memory_gb": 64.0,
            "overhead_pct": 0.15,
            "nodes_lost": 0.0,
        },
        "namespaces": [
            {
                "name": "ns1",
                "replication_factor": 2.0,
                "master_object_count": 1e6,
                "avg_record_size_bytes": 500.0,
                "read_pct": 0.5,
                "write_pct": 0.5,
                "tombstone_pct": 0.0,
                "si_count": 0.0,
                "si_entries_per_object": 0.0,
            },
            {
                "name": "ns2",
                "replication_factor": 2.0,
                "master_object_count": 2e6,
                "avg_record_size_bytes": 300.0,
                "read_pct": 0.5,
                "write_pct": 0.5,
                "tombstone_pct": 0.0,
                "si_count": 0.0,
                "si_entries_per_object": 0.0,
            },
        ],
    }
    r = client.post("/api/compute-v2", json=body)
    assert r.status_code == 200
    data = r.json()
    # More data than either namespace alone
    r1 = client.post(
        "/api/compute-v2",
        json={"cluster": body["cluster"], "namespaces": [body["namespaces"][0]]},
    )
    r2 = client.post(
        "/api/compute-v2",
        json={"cluster": body["cluster"], "namespaces": [body["namespaces"][1]]},
    )
    assert r1.status_code == 200 and r2.status_code == 200
    d1 = r1.json()
    d2 = r2.json()
    assert data["data_stored_gb"] == pytest.approx(
        d1["data_stored_gb"] + d2["data_stored_gb"], rel=1e-9
    )
    assert data["total_memory_used_base_gb"] == pytest.approx(
        d1["total_memory_used_base_gb"] + d2["total_memory_used_base_gb"], rel=1e-9
    )


def test_api_compute_v2_empty_namespaces_400():
    """POST /api/compute-v2 with empty namespaces returns 400."""
    r = client.post(
        "/api/compute-v2",
        json={
            "cluster": {"nodes_per_cluster": 3.0},
            "namespaces": [],
        },
    )
    assert r.status_code == 400


def test_api_load_collectinfo_returns_cluster_namespaces_legacy():
    """POST /api/load-collectinfo returns cluster, namespaces, and legacy keys."""
    # Upload a non-zip file to get stub response (no asadm path)
    r = client.post(
        "/api/load-collectinfo",
        files={"file": ("test.txt", b"not a zip", "text/plain")},
    )
    assert r.status_code == 200
    data = r.json()
    assert "cluster" in data
    assert "namespaces" in data
    assert "legacy" in data
    assert isinstance(data["namespaces"], list)
    assert len(data["namespaces"]) >= 1
    assert "nodes_per_cluster" in data["cluster"]
    assert "replication_factor" in data["legacy"]
    assert data["legacy"]["nodes_per_cluster"] == data["cluster"]["nodes_per_cluster"]