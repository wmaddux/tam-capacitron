"""
FastAPI backend: compute endpoint, defaults, load-collectinfo, and static UI.

Run: uvicorn app.main:app --reload
"""

import tempfile
from pathlib import Path

from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import get_defaults, get_default_cluster_and_namespaces, get_slider_specs
from core.model import (
    CapacityInputs,
    CapacityOutputs,
    ClusterInputs,
    NamespaceInputs,
    get_default_inputs,
)
from core.engine import run_multi
from ingest import run_ingestor, run_ingestor_multi
from ingest.mapping import (
    ingestor_multi_to_cluster_and_namespaces,
    ingestor_output_to_capacity_inputs,
)

app = FastAPI(title="tam-capacitron", version="0.1.0")

STATIC_DIR = Path(__file__).resolve().parent / "static"


_DEFAULTS = get_defaults()


@app.get("/api/defaults")
def api_defaults() -> dict:
    """Return default inputs for Load from defaults (from config/inputs.json). When config has cluster and namespaces, returns { cluster, namespaces }; otherwise flat CapacityInputs-shaped dict."""
    cluster, namespaces = get_default_cluster_and_namespaces()
    if cluster is not None and namespaces is not None:
        return {"cluster": cluster, "namespaces": namespaces}
    return get_default_inputs().to_dict()


@app.get("/api/input-config")
def api_input_config() -> dict:
    """Return defaults and slider schema in one response for the UI. Defaults are either { cluster, namespaces } or flat when config has no cluster/namespaces."""
    cluster, namespaces = get_default_cluster_and_namespaces()
    if cluster is not None and namespaces is not None:
        return {"defaults": {"cluster": cluster, "namespaces": namespaces}, "schema": get_slider_specs()}
    return {"defaults": get_default_inputs().to_dict(), "schema": get_slider_specs()}


class ComputeBody(BaseModel):
    """Inputs as JSON; extra keys ignored. Defaults from config/inputs.json."""

    replication_factor: float = _DEFAULTS.get("replication_factor", 2.0)
    nodes_per_cluster: float = _DEFAULTS.get("nodes_per_cluster", 6.0)
    devices_per_node: float = _DEFAULTS.get("devices_per_node", 3.0)
    device_size_gb: float = _DEFAULTS.get("device_size_gb", 256.0)
    available_memory_gb: float = _DEFAULTS.get("available_memory_gb", 128.0)
    overhead_pct: float = _DEFAULTS.get("overhead_pct", 0.15)
    master_object_count: float = _DEFAULTS.get("master_object_count", 1e6)
    avg_record_size_bytes: float = _DEFAULTS.get("avg_record_size_bytes", 500.0)
    read_pct: float = _DEFAULTS.get("read_pct", 0.5)
    write_pct: float = _DEFAULTS.get("write_pct", 0.5)
    tombstone_pct: float = _DEFAULTS.get("tombstone_pct", 0.0)
    si_count: float = _DEFAULTS.get("si_count", 0.0)
    si_entries_per_object: float = _DEFAULTS.get("si_entries_per_object", 0.0)
    nodes_lost: float = _DEFAULTS.get("nodes_lost", 0.0)


def _compute_body_to_inputs(body: ComputeBody) -> CapacityInputs:
    return CapacityInputs(
        replication_factor=body.replication_factor,
        nodes_per_cluster=body.nodes_per_cluster,
        devices_per_node=body.devices_per_node,
        device_size_gb=body.device_size_gb,
        available_memory_gb=body.available_memory_gb,
        overhead_pct=body.overhead_pct,
        master_object_count=body.master_object_count,
        avg_record_size_bytes=body.avg_record_size_bytes,
        read_pct=body.read_pct,
        write_pct=body.write_pct,
        tombstone_pct=body.tombstone_pct,
        si_count=body.si_count,
        si_entries_per_object=body.si_entries_per_object,
        nodes_lost=body.nodes_lost,
    )


@app.post("/api/compute")
def api_compute(body: ComputeBody) -> dict:
    """Compute outputs from inputs (legacy flat body). Returns outputs only (for immediate reactivity)."""
    from core.model import capacity_inputs_to_cluster_and_namespaces

    inp = _compute_body_to_inputs(body)
    cluster, namespaces = capacity_inputs_to_cluster_and_namespaces(inp)
    out = run_multi(cluster, namespaces)
    return out.to_dict()


class ClusterBody(BaseModel):
    """Cluster-level parameters. cluster_name and default_storage_pattern optional. Defaults from config."""

    nodes_per_cluster: float = _DEFAULTS.get("nodes_per_cluster", 6.0)
    devices_per_node: float = _DEFAULTS.get("devices_per_node", 3.0)
    device_size_gb: float = _DEFAULTS.get("device_size_gb", 256.0)
    available_memory_gb: float = _DEFAULTS.get("available_memory_gb", 128.0)
    overhead_pct: float = _DEFAULTS.get("overhead_pct", 0.15)
    nodes_lost: float = _DEFAULTS.get("nodes_lost", 0.0)
    data_growth_pct_per_year: float = 0.0
    cluster_name: str = ""
    default_storage_pattern: str = "HMA (MMD)"
    vcpus: float = 0.0
    instance_storage: str = ""
    instance_networking: str = ""
    iops_per_disk_k: float = _DEFAULTS.get("iops_per_disk_k", 320.0)
    throughput_per_disk_mbs: float = _DEFAULTS.get("throughput_per_disk_mbs", 1500.0)


class NamespaceBody(BaseModel):
    """Workload parameters for one namespace; placement and thresholds optional."""

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
    placement: Optional[dict] = None  # { primary: 'M'|'D', si: 'M'|'D', data: 'M'|'D' }
    compression_ratio: float = 1.0
    stop_writes_at_storage_pct: float = 90.0
    evict_at_memory_pct: float = 95.0
    min_available_storage_pct: float = 5.0


class ComputeV2Body(BaseModel):
    """Multi-namespace request: cluster + list of namespaces. At least one namespace required."""

    cluster: ClusterBody
    namespaces: list[NamespaceBody]


@app.post("/api/compute-v2")
def api_compute_v2(body: ComputeV2Body) -> dict:
    """
    Compute outputs from cluster + namespaces. Aggregates data and memory across
    namespaces; returns cluster-level outputs. See docs/API_MULTI_NAMESPACE.md.
    """
    if not body.namespaces:
        raise HTTPException(status_code=400, detail="At least one namespace is required")
    cluster = ClusterInputs(
        nodes_per_cluster=body.cluster.nodes_per_cluster,
        devices_per_node=body.cluster.devices_per_node,
        device_size_gb=body.cluster.device_size_gb,
        available_memory_gb=body.cluster.available_memory_gb,
        overhead_pct=body.cluster.overhead_pct,
        nodes_lost=body.cluster.nodes_lost,
        data_growth_pct_per_year=body.cluster.data_growth_pct_per_year,
        cluster_name=body.cluster.cluster_name,
        default_storage_pattern=body.cluster.default_storage_pattern,
        vcpus=body.cluster.vcpus,
        instance_storage=body.cluster.instance_storage or "",
        instance_networking=body.cluster.instance_networking or "",
        iops_per_disk_k=body.cluster.iops_per_disk_k,
        throughput_per_disk_mbs=body.cluster.throughput_per_disk_mbs,
    )
    namespaces = [
        NamespaceInputs(
            name=ns.name,
            replication_factor=ns.replication_factor,
            master_object_count=ns.master_object_count,
            avg_record_size_bytes=ns.avg_record_size_bytes,
            read_pct=ns.read_pct,
            write_pct=ns.write_pct,
            tombstone_pct=ns.tombstone_pct,
            si_count=ns.si_count,
            si_entries_per_object=ns.si_entries_per_object,
            storage_pattern=ns.storage_pattern,
            placement=ns.placement if ns.placement is not None else {"primary": "M", "si": "M", "data": "D"},
            compression_ratio=ns.compression_ratio,
            stop_writes_at_storage_pct=ns.stop_writes_at_storage_pct,
            evict_at_memory_pct=ns.evict_at_memory_pct,
            min_available_storage_pct=ns.min_available_storage_pct,
        )
        for ns in body.namespaces
    ]
    out = run_multi(cluster, namespaces)
    return out.to_dict()


def _cluster_and_namespaces_to_legacy_flat(cluster: dict, namespaces: list[dict]) -> dict:
    """Build flat CapacityInputs-shaped dict from cluster + first namespace (for legacy UI)."""
    from core.model import CapacityInputs

    if not namespaces:
        return get_default_inputs().to_dict()
    ns = namespaces[0]
    inp = CapacityInputs(
        replication_factor=ns["replication_factor"],
        nodes_per_cluster=cluster["nodes_per_cluster"],
        devices_per_node=cluster["devices_per_node"],
        device_size_gb=cluster["device_size_gb"],
        available_memory_gb=cluster["available_memory_gb"],
        overhead_pct=cluster["overhead_pct"],
        master_object_count=ns["master_object_count"],
        avg_record_size_bytes=ns["avg_record_size_bytes"],
        read_pct=ns["read_pct"],
        write_pct=ns["write_pct"],
        tombstone_pct=ns["tombstone_pct"],
        si_count=ns["si_count"],
        si_entries_per_object=ns["si_entries_per_object"],
        nodes_lost=cluster["nodes_lost"],
    )
    return inp.to_dict()


@app.post("/api/load-collectinfo")
async def api_load_collectinfo(file: UploadFile = File(...)) -> dict:
    """
    Accept a bundle zip or raw collectinfo file; run ingestor and mapping;
    return cluster + namespaces (and legacy flat form for existing UI).

    Response: { "cluster": {...}, "namespaces": [ {...}, ... ], "legacy": {...} }.
    Use "cluster" and "namespaces" for multi-namespace UI; use "legacy" for the
    current single-namespace form (Load from collectinfo populates from first namespace).

    For .zip, .tgz, .tar: runs asadm -cf <path> -e "summary", parses all namespaces.
    For other files: returns stub (one namespace).
    """
    try:
        filename = (file.filename or "").lower()
        bundle_suffixes = (".zip", ".tgz", ".tar")
        if any(filename.endswith(s) for s in bundle_suffixes):
            suffix = next(s for s in bundle_suffixes if filename.endswith(s))
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(await file.read())
                tmp.flush()
                tmp_path = tmp.name
            try:
                multi_out = run_ingestor_multi(collectinfo_path=tmp_path)
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        else:
            await file.read()  # consume upload
            multi_out = run_ingestor_multi(collectinfo_path=None)
        api_shape = ingestor_multi_to_cluster_and_namespaces(multi_out)
        legacy = _cluster_and_namespaces_to_legacy_flat(
            api_shape["cluster"], api_shape["namespaces"]
        )
        return {
            "cluster": api_shape["cluster"],
            "namespaces": api_shape["namespaces"],
            "legacy": legacy,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/schema")
def api_schema() -> dict:
    """Return input field metadata (min, max, step) for UI sliders (from config/inputs.json)."""
    return get_slider_specs()


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")
