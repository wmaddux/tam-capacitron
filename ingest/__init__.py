"""
Ingest: bundle parsing, collectinfo ingestion, and mapping to CapacityInputs.

- bundle: open zip, find collectinfo file(s), extract content or paths.
- ingestor: invoke shared tam-tools ingestor (stub until tam-tools integrated).
- mapping: convert ingestor output dict to CapacityInputs.
"""

from ingest.bundle import (
    list_bundle_contents,
    find_collectinfo_in_bundle,
    extract_collectinfo_from_bundle,
)
from ingest.ingestor import run_ingestor
from ingest.mapping import ingestor_output_to_capacity_inputs

__all__ = [
    "list_bundle_contents",
    "find_collectinfo_in_bundle",
    "extract_collectinfo_from_bundle",
    "run_ingestor",
    "ingestor_output_to_capacity_inputs",
]
