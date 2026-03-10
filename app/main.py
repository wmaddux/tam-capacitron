"""
FastAPI backend: compute endpoint, defaults, load-collectinfo, and static UI.

Run: uvicorn app.main:app --reload
"""

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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


@app.get("/api/defaults")
def api_defaults() -> dict:
    """Return default inputs for Load from defaults."""
    return get_default_inputs().to_dict()


class ComputeBody(BaseModel):
    """Inputs as JSON; extra keys ignored."""

    replication_factor: float = 2.0
    nodes_per_cluster: float = 3.0
    devices_per_node: float = 2.0
    device_size_gb: float = 50.0
    available_memory_gb: float = 64.0
    overhead_pct: float = 0.15
    master_object_count: float = 1e6
    avg_record_size_bytes: float = 500.0
    read_pct: float = 0.5
    write_pct: float = 0.5
    tombstone_pct: float = 0.0
    si_count: float = 0.0
    si_entries_per_object: float = 0.0
    nodes_lost: float = 0.0


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
    """Cluster-level parameters. cluster_name is optional and not used in calculations."""

    nodes_per_cluster: float = 3.0
    devices_per_node: float = 2.0
    device_size_gb: float = 50.0
    available_memory_gb: float = 64.0
    overhead_pct: float = 0.15
    nodes_lost: float = 0.0
    cluster_name: str = ""


class NamespaceBody(BaseModel):
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
        cluster_name=body.cluster.cluster_name,
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

    For .zip: runs asadm -cf <path> -e "summary", parses all namespaces.
    For other files: returns stub (one namespace).
    """
    try:
        filename = (file.filename or "").lower()
        if filename.endswith(".zip"):
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
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
    """Return input field metadata (min, max, step) for UI sliders."""
    return {
        "replication_factor": {"min": 1, "max": 4, "step": 1},
        "nodes_per_cluster": {"min": 1, "max": 64, "step": 1},
        "devices_per_node": {"min": 1, "max": 24, "step": 1},
        "device_size_gb": {"min": 50, "max": 4096, "step": 64},
        "available_memory_gb": {"min": 16, "max": 1024, "step": 16},
        "overhead_pct": {"min": 0, "max": 0.5, "step": 0.01},
        "master_object_count": {"min": 1e4, "max": 1e12, "step": 1e6},
        "avg_record_size_bytes": {"min": 100, "max": 1e7, "step": 10000},
        "read_pct": {"min": 0, "max": 1, "step": 0.01},
        "write_pct": {"min": 0, "max": 1, "step": 0.01},
        "tombstone_pct": {"min": 0, "max": 0.5, "step": 0.01},
        "si_count": {"min": 0, "max": 20, "step": 1},
        "si_entries_per_object": {"min": 0, "max": 10, "step": 0.1},
        "nodes_lost": {"min": 0, "max": 16, "step": 1},
    }


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")
