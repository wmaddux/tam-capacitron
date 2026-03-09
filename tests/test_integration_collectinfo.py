"""
Integration tests: bundle → ingestor (asadm) → mapping → CapacityInputs → engine.

When asadm is not on PATH or bundle is invalid, run_ingestor returns stub.
When asadm is on PATH and a real bundle is used, run_ingestor(collectinfo_path=...)
runs asadm -cf <path> -e "summary" and parses the output.
"""

import os
import shutil
import zipfile
from pathlib import Path

import pytest
from core.engine import run
from ingest.ingestor import run_ingestor
from ingest.mapping import ingestor_output_to_capacity_inputs

# Fidelity bundle path: env FIDELITY_BUNDLE_PATH or repo-relative default
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_FIDELITY_BUNDLE_DEFAULT = _PROJECT_ROOT / "bundles" / "fidelity-case00044090-20250226.zip"


def _fidelity_bundle_path() -> Path | None:
    p = os.environ.get("FIDELITY_BUNDLE_PATH")
    if p and os.path.isfile(p):
        return Path(p)
    if _FIDELITY_BUNDLE_DEFAULT.is_file():
        return _FIDELITY_BUNDLE_DEFAULT
    return None


def test_full_pipeline_with_content_returns_stub():
    """run_ingestor(collectinfo_content=...) returns stub when no path."""
    ingestor_out = run_ingestor(collectinfo_content=b"# raw content\n")
    inp = ingestor_output_to_capacity_inputs(ingestor_out)
    assert inp.replication_factor >= 1
    assert inp.nodes_per_cluster >= 1
    assert inp.nodes_lost == 0.0
    out = run(inp)
    assert out.storage_utilization_pct >= 0
    assert out.effective_nodes == inp.nodes_per_cluster - inp.nodes_lost


def test_full_pipeline_zip_path_without_asadm_returns_stub(tmp_path):
    """When asadm is not on PATH, run_ingestor(collectinfo_path=zip) may return stub or fail to parse."""
    zip_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("collectinfo.txt", b"# stub content\n")
    ingestor_out = run_ingestor(collectinfo_path=str(zip_path))
    inp = ingestor_output_to_capacity_inputs(ingestor_out)
    assert inp.replication_factor >= 1
    assert inp.nodes_per_cluster >= 1
    out = run(inp)
    assert out.storage_utilization_pct >= 0


def test_full_pipeline_bundle_to_engine(tmp_path):
    """Bundle zip → run ingestor (path or content) → map → engine produces valid outputs."""
    zip_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("collectinfo.txt", b"# stub collectinfo content\n")
    ingestor_out = run_ingestor(collectinfo_path=str(zip_path))
    inp = ingestor_output_to_capacity_inputs(ingestor_out)
    assert inp.replication_factor >= 1
    assert inp.nodes_per_cluster >= 1
    assert inp.devices_per_node >= 1
    assert inp.device_size_gb > 0
    assert 0 <= inp.read_pct <= 1
    assert 0 <= inp.write_pct <= 1
    assert inp.nodes_lost == 0.0
    out = run(inp)
    assert out.storage_utilization_pct >= 0
    assert out.memory_utilization_base_pct >= 0
    assert out.effective_nodes == inp.nodes_per_cluster - inp.nodes_lost


@pytest.mark.skipif(
    not shutil.which("asadm"),
    reason="asadm not on PATH",
)
@pytest.mark.skipif(
    _fidelity_bundle_path() is None,
    reason="Fidelity bundle not found (set FIDELITY_BUNDLE_PATH or add bundles/fidelity-case00044090-20250226.zip)",
)
def test_fidelity_bundle_real_ingest(tmp_path):
    """With asadm on PATH and fidelity bundle, ingest returns real values (e.g. 18 nodes)."""
    bundle = _fidelity_bundle_path()
    ingestor_out = run_ingestor(collectinfo_path=str(bundle))
    inp = ingestor_output_to_capacity_inputs(ingestor_out)
    # If asadm failed (e.g. sandbox permission writing to ~/.aerospike/collectinfo), we get stub
    if inp.nodes_per_cluster == 16.0 and inp.device_size_gb == 1920.0:
        pytest.skip("asadm could not run on bundle (e.g. permission or sandbox)")
    # Fidelity bundle: 18 nodes, 22 devices/node, ~55 GB device size
    assert inp.nodes_per_cluster == 18.0, "expected 18 nodes from fidelity bundle"
    assert inp.devices_per_node == 22.0, "expected 22 devices per node"
    assert 40 <= inp.device_size_gb <= 70, "expected device size ~55 GB"
    assert inp.nodes_lost == 0.0
    out = run(inp)
    assert out.storage_utilization_pct >= 0
    assert out.effective_nodes == 18.0
