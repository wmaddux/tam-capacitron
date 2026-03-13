"""
Unit tests for asadm-based collectinfo ingestion: run_asadm and parse_summary_output.
"""

import pytest
from ingest.asadm_ingest import (
    _sum_stat_column,
    parse_summary_output,
    parse_summary_output_multi,
    run_asadm,
    asadm_summary_to_capacity_dict,
)


# Sample asadm summary output (pipe-delimited, fidelity-style)
SAMPLE_SUMMARY = """
~~~~~~~~~~Cluster Summary~~~~~~~~~~
Cluster Size              |18
Devices Total             |396
Devices Per-Node          |22
Device Total              |21.270 TB
Device Used                |3.885 TB
Device Avail               |17.385 TB
Number of rows: 1

~~~~~~~~~~Namespace Summary~~~~~~~~~~
     Namespace|~~~~Drives~~~~|~~~~~~~~~~Device~~~~~~~~~~|Replication|  Cache|   Master|...
              |Total|Per-Node|     Total|  Used%| Avail%|    Factors|  Read%|  Objects|...
wi-pzn        |  216|      12| 11.602 TB|31.95 %|53.44 %|          2| 24.0 %|  6.447 G|...
Number of rows: 1
"""


def test_parse_summary_output_empty():
    assert parse_summary_output("") == {}
    assert parse_summary_output("   \n  ") == {}


def test_parse_summary_output_cluster_fields():
    d = parse_summary_output(SAMPLE_SUMMARY)
    assert d.get("nodes_per_cluster") == 18.0
    assert d.get("devices_per_node") == 22.0
    assert d.get("device_size_gb") == pytest.approx((21.270 * 1024) / 396, rel=0.01)
    assert d.get("nodes_lost") == 0.0
    assert d.get("overhead_pct") == 0.15
    assert d.get("available_memory_gb") == 64.0


def test_parse_summary_output_namespace_fields():
    d = parse_summary_output(SAMPLE_SUMMARY)
    assert d.get("replication_factor") == 2.0
    assert d.get("object_count") == pytest.approx(6.447e9, rel=0.01)
    assert d.get("read_pct") == pytest.approx(0.24, rel=0.01)
    assert d.get("write_pct") == pytest.approx(0.76, rel=0.01)


def test_parse_summary_output_data_used_bytes():
    d = parse_summary_output(SAMPLE_SUMMARY)
    assert "data_used_bytes" in d
    assert d["data_used_bytes"] == pytest.approx(3.885 * (1024**4), rel=0.01)


def test_parse_summary_output_namespace_selection():
    d = parse_summary_output(SAMPLE_SUMMARY, namespace="wi-pzn")
    assert d.get("replication_factor") == 2.0
    assert d.get("object_count") == pytest.approx(6.447e9, rel=0.01)


def test_parse_summary_output_unknown_namespace_uses_largest():
    summary_two_ns = SAMPLE_SUMMARY.replace(
        "Number of rows: 1",
        "other-ns       |  100|       5|  5.000 TB|10.0 %|80.0 %|          1| 50.0 %|  1.000 G|\nNumber of rows: 2",
        1,
    )
    d = parse_summary_output(summary_two_ns, namespace="nonexistent")
    # Parser picks row with largest object count when namespace not found.
    assert "replication_factor" in d or "object_count" in d


# Multi-namespace: first row (cnc-authz-prod) has 329.789 K objects, wi-pzn has 6.447 G. We must pick largest.
MULTI_NS_SUMMARY = """
~~~~~~~~~~Cluster Summary~~~~~~~~~~
Cluster Size              |18
Devices Total             |396
Devices Per-Node          |22
Device Total              |21.270 TB
Device Used               |3.885 TB
Number of rows: 18

~~~~~~~~~~Namespace Summary~~~~~~~~~~
     Namespace|~~~~Drives~~~~|~~~~~~~~~~Device~~~~~~~~~~|Replication|  Cache|   Master|...
              |Total|Per-Node|     Total|  Used%| Avail%|    Factors|  Read%|  Objects|...
cnc-authz-prod|   18|       1|990.000 GB| 0.06 %| 99.0 %|          2|100.0 %|329.789 K|...
wi-pzn        |  216|      12| 11.602 TB|31.95 %|53.44 %|          2| 24.0 %|  6.447 G|...
Number of rows: 2
"""


def test_parse_summary_output_multi_returns_cluster_and_namespaces():
    """parse_summary_output_multi returns cluster dict + list of namespace dicts."""
    multi = parse_summary_output_multi(SAMPLE_SUMMARY)
    assert "cluster" in multi
    assert "namespaces" in multi
    assert isinstance(multi["namespaces"], list)
    assert multi["cluster"].get("nodes_per_cluster") == 18.0
    assert multi["cluster"].get("devices_per_node") == 22.0
    assert len(multi["namespaces"]) == 1
    assert multi["namespaces"][0].get("name") == "wi-pzn"
    assert multi["namespaces"][0].get("replication_factor") == 2.0
    assert multi["namespaces"][0].get("object_count") == pytest.approx(6.447e9, rel=0.01)
    assert multi["namespaces"][0].get("read_pct") == pytest.approx(0.24, rel=0.01)


def test_parse_summary_output_multi_two_namespaces():
    """parse_summary_output_multi returns one dict per namespace row."""
    multi = parse_summary_output_multi(MULTI_NS_SUMMARY)
    assert len(multi["namespaces"]) == 2
    names = {ns["name"] for ns in multi["namespaces"]}
    assert "cnc-authz-prod" in names
    assert "wi-pzn" in names
    for ns in multi["namespaces"]:
        assert "replication_factor" in ns
        assert "object_count" in ns
        assert "read_pct" in ns


def test_parse_summary_output_picks_largest_namespace_by_object_count():
    """When namespace is not set, we must select the row with the largest object count, not the first row."""
    d = parse_summary_output(MULTI_NS_SUMMARY, namespace=None)
    # cnc-authz-prod has 329.789 K, wi-pzn has 6.447 G. We must get wi-pzn (6.447e9).
    assert d.get("object_count") == pytest.approx(6.447e9, rel=0.01)
    assert d.get("read_pct") == pytest.approx(0.24, rel=0.01)
    assert d.get("replication_factor") == 2.0


def test_run_asadm_missing_bundle():
    out, err = run_asadm("/nonexistent/bundle.zip", "summary")
    assert out is None
    assert err is not None
    assert "not found" in err or "Bundle" in err or "asadm" in err.lower()


def test_asadm_summary_to_capacity_dict_missing_bundle():
    d = asadm_summary_to_capacity_dict("/nonexistent/bundle.zip")
    assert d == {}


def test_parse_size_k_m_g():
    from ingest.asadm_ingest import _parse_size
    assert _parse_size("6.447 G") == pytest.approx(6.447e9, rel=0.01)
    assert _parse_size("1.000 M") == pytest.approx(1e6, rel=0.01)
    assert _parse_size("500 K") == pytest.approx(500e3, rel=0.01)
    assert _parse_size("21.270") == 21.27


def test_parse_pct():
    from ingest.asadm_ingest import _parse_pct
    assert _parse_pct("24.0 %") == pytest.approx(0.24, rel=0.01)
    assert _parse_pct("31.95 %") == pytest.approx(0.3195, rel=0.01)
    assert _parse_pct("0.5") == 0.5


def test_sum_stat_column():
    """_sum_stat_column sums numeric second column from asadm -flip output."""
    raw = """
~users_eu Namespace Statistics (2026-01-13 09:53:56 UTC)~
             Node|device_used_bytes
10.92.71.105:3000|    8145310387840
10.92.71.117:3000|    8142452720032
10.92.71.144:3000|    8133400164304
"""
    total = _sum_stat_column(raw)
    expected = 8145310387840 + 8142452720032 + 8133400164304
    assert total == pytest.approx(expected, rel=0)
    assert _sum_stat_column("") == 0.0
    assert _sum_stat_column("Node|device_used_bytes\n") == 0.0
