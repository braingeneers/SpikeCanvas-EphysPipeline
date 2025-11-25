from __future__ import annotations
import os
import yaml
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Optional, Dict, Any, List

DEFAULT_CONFIG_PATHS: List[str] = [
    os.getenv("PIPELINE_CONFIG", ""),
    "/app/config/pipeline.yaml",
    "/config/pipeline.yaml",
]

@dataclass
class PipelineConfig:
    bucket: Optional[str] = None  # just bucket name, no scheme
    prefix: str = "ephys"         # root prefix within bucket
    input_prefix: Optional[str] = None  # override for inputs
    output_prefix: Optional[str] = None # override for outputs
    region: Optional[str] = os.getenv("AWS_REGION") or None
    profile: Optional[str] = os.getenv("AWS_PROFILE") or None
    role_arn: Optional[str] = os.getenv("AWS_ROLE_ARN") or None
    session_name: Optional[str] = os.getenv("AWS_SESSION_NAME") or None
    raw: Dict[str, Any] = field(default_factory=dict)

    def s3_uri(self, *parts: str, base: str = "root") -> str:
        bucket = self.bucket or os.getenv("S3_BUCKET")
        if not bucket:
            raise ValueError("S3 bucket not configured (bucket env S3_BUCKET or config.bucket required)")
        if bucket.startswith("s3://"):
            # allow user mistake, strip scheme
            bucket = bucket[len("s3://"):]
        # resolve base prefix
        if base == "root":
            pfx = self.prefix
        elif base == "input":
            pfx = self.input_prefix or self.prefix
        elif base == "output":
            pfx = self.output_prefix or self.prefix
        else:
            raise ValueError(f"Unknown base '{base}'")
        pfx = pfx.strip("/") if pfx else ""
        joined = str(PurePosixPath(pfx).joinpath(*[p for p in parts if p]))
        if joined == ".":
            joined = ""
        return f"s3://{bucket}/{joined}" if joined else f"s3://{bucket}/"

    def root(self) -> str:
        return self.s3_uri()

_cached: Optional[PipelineConfig] = None

def _load_yaml(path: str) -> Dict[str, Any]:
    if not path or not os.path.isfile(path):
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}

def load_config(force_reload: bool = False) -> PipelineConfig:
    global _cached
    if _cached and not force_reload:
        return _cached

    data: Dict[str, Any] = {}
    for p in DEFAULT_CONFIG_PATHS:
        if not p:
            continue
        y = _load_yaml(p)
        data.update({k: v for k, v in y.items() if v is not None})

    # env overrides
    env_map = {
        'bucket': os.getenv('S3_BUCKET'),
        'prefix': os.getenv('S3_PREFIX'),
        'input_prefix': os.getenv('S3_INPUT_PREFIX'),
        'output_prefix': os.getenv('S3_OUTPUT_PREFIX'),
    }
    for k, v in env_map.items():
        if v:
            data[k] = v

    cfg = PipelineConfig(**{k: v for k, v in data.items() if k in PipelineConfig.__dataclass_fields__})
    cfg.raw = data
    _cached = cfg
    # One-time log (print acceptable for early bootstrap)
    print(f"[pipeline-config] bucket={cfg.bucket or os.getenv('S3_BUCKET')} prefix={cfg.prefix} input={cfg.input_prefix} output={cfg.output_prefix}")
    return cfg

def s3_uri(*parts: str, base: str = 'root') -> str:
    return load_config().s3_uri(*parts, base=base)

__all__ = ["PipelineConfig", "load_config", "s3_uri"]
