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

from core.model import CapacityInputs, CapacityOutputs, get_default_inputs
from core.engine import run
from ingest import run_ingestor, ingestor_output_to_capacity_inputs

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
    device_size_gb: float = 256.0
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


@app.post("/api/compute")
def api_compute(body: ComputeBody) -> dict:
    """Compute outputs from inputs. Returns outputs only (for immediate reactivity)."""
    inp = CapacityInputs(
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
    out: CapacityOutputs = run(inp)
    return out.to_dict()


@app.post("/api/load-collectinfo")
async def api_load_collectinfo(file: UploadFile = File(...)) -> dict:
    """
    Accept a bundle zip or raw collectinfo file; run ingestor and mapping;
    return CapacityInputs as JSON for the front-end to set the form.

    For .zip: writes upload to a temp file and passes its path to the ingestor
    (asadm -cf <path> -e "summary" parses the bundle). Requires asadm on PATH.
    For other files: reads bytes and runs ingestor (stub if no bundle path).
    """
    try:
        filename = (file.filename or "").lower()
        if filename.endswith(".zip"):
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp.write(await file.read())
                tmp.flush()
                tmp_path = tmp.name
            try:
                ingestor_out = run_ingestor(collectinfo_path=tmp_path)
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        else:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Empty file")
            ingestor_out = run_ingestor(collectinfo_content=content)
        inp = ingestor_output_to_capacity_inputs(ingestor_out)
        return inp.to_dict()
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
        "device_size_gb": {"min": 64, "max": 4096, "step": 64},
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
