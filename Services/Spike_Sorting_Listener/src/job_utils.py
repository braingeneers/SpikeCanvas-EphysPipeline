"""
Shared utilities for the Spike Sorting Listener service.
Contains common constants and functions used across modules.
"""
import re
import os

# Constants
JOB_PREFIX = "edp-"
try:
    from Services.common.config import load_config
    _cfg = load_config()
    DEFAULT_S3_BUCKET = _cfg.root()
except Exception:
    _fallback_bucket = os.getenv("S3_BUCKET", "braingeneers")
    _fallback_prefix = os.getenv("S3_PREFIX", "ephys")
    DEFAULT_S3_BUCKET = f"s3://{_fallback_bucket}/{_fallback_prefix.rstrip('/')}/"  # env-based fallback
# Kubernetes namespace configurable via env var NRP_NAMESPACE (defaults to braingeneers)
NAMESPACE = os.getenv("NRP_NAMESPACE", "braingeneers")

def format_job_name(raw_name: str,
                    job_ind: int | None = None,
                    prefix: str = JOB_PREFIX) -> str:
    """
    Format a raw name into a Kubernetes-safe job name.
    
    Args:
        raw_name: Raw input name (filename, experiment name, etc.)
        job_ind: Optional job index for CSV-based jobs
        prefix: Job name prefix (default: "edp-")
    
    Returns:
        Kubernetes-compliant job name (max 63 chars, alphanumeric + hyphens)
    """
    stem = raw_name
    if raw_name.endswith(".csv") and job_ind is not None:
        stem = f"{raw_name[:-4]}-{job_ind}"
    elif raw_name.endswith(".raw.h5"):
        stem = raw_name[:-8]
    elif raw_name.endswith(".h5"):
        stem = raw_name[:-3]

    stem = re.sub(r"[^a-z0-9]+", "-", stem.lower())
    stem = stem.strip("-")

    full = f"{prefix}{stem}"
    if len(full) > 63:
        # keep the END of the stem (often has date/well info)
        keep = 63 - len(prefix)
        full = f"{prefix}{stem[-keep:]}"
        full = full.lstrip("-") or "x"   # ensure first char alnum

    return full
