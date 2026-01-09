"""
Path utilities for algorithm containers and services.

Contract:
- Input data live under "<uuid>/original/data/...".
- Derived outputs live under "<uuid>/derived/<stage>/...".
- Artifacts use a base name plus a suffix: _phy.zip, _acqm.zip, _figure.zip, _conn.zip, etc.

Pure helpers here avoid external dependencies to keep container images small and upgrades safe.
"""
from __future__ import annotations
import os
from typing import Optional

ORIGINAL_SEGMENT = os.path.join("original", "data")
DERIVED_SEGMENT = "derived"


def replace_original_to_derived(base_path: str, stage: str) -> str:
    """Replace the 'original/data' segment with 'derived/<stage>' within a data path.

    Examples:
    - <uuid>/original/data/foo.raw.h5 -> <uuid>/derived/kilosort2/foo.raw.h5
    - <uuid>/original/data/subdir/bar.h5 -> <uuid>/derived/lfp/subdir/bar.h5
    """
    if not base_path:
        return base_path
    # Normalize separators to '/' for S3-like paths
    p = base_path.replace("\\", "/")
    return p.replace(ORIGINAL_SEGMENT.replace("\\", "/"), f"{DERIVED_SEGMENT}/{stage}")


def normalize_acqm_source(input_path: str) -> str:
    """Convert various input data file names to their acquisition zip name.

    Handles these common cases:
    - *.raw.h5 -> *_acqm.zip
    - *.raw.h5.raw.h5 -> *_acqm.zip (double extension mishaps)
    - *.h5 -> *_acqm.zip
    - already *_acqm.zip -> unchanged
    """
    if not input_path:
        return input_path
    p = input_path.replace("\\", "/")
    if p.endswith("_acqm.zip"):
        return p
    if p.endswith(".raw.h5.raw.h5"):
        return p[:-len(".raw.h5.raw.h5")] + "_acqm.zip"
    if p.endswith(".raw.h5"):
        return p[:-len(".raw.h5")] + "_acqm.zip"
    if p.endswith(".h5"):
        return p[:-len(".h5")] + "_acqm.zip"
    # Fallback: if it already ends with .zip, keep as-is; else append _acqm.zip
    return p if p.endswith(".zip") else p + "_acqm.zip"


def make_artifact_path(session_uuid: str, stage: str, basename: str, suffix: str, subdir: Optional[str] = None) -> str:
    """Build canonical derived artifact path.

    Result: <uuid>/derived/<stage>/<optional subdir>/<basename><suffix>
    - session_uuid: top-level UUID folder name
    - stage: e.g., 'kilosort2', 'lfp', 'connectivity'
    - basename: name without suffix, e.g., 'chip12345_recordingA'
    - suffix: includes leading underscore, e.g., '_phy.zip', '_acqm.zip', '_figure.zip', '_conn.zip'
    - subdir: optional nested subdirectory before file name
    """
    parts = [session_uuid, DERIVED_SEGMENT, stage]
    if subdir:
        parts.append(subdir)
    return "/".join(parts + [f"{basename}{suffix}"])
