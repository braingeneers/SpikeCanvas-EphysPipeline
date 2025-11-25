"""Kubernetes configuration helper for dynamic S3 settings.

Reads ConfigMap `ephys-config` (same namespace) to obtain S3 bucket/prefix.
Falls back to environment variables if API access fails.
Final fallback: existing DEFAULT bucket logic from config.py.
"""
from __future__ import annotations
from typing import Dict
import os

def load_s3_settings(namespace: str = "braingeneers",
                     configmap_name: str = "ephys-config") -> Dict[str, str]:
    # Try Kubernetes API
    try:
        from kubernetes import client, config as k8s_config
        try:
            k8s_config.load_incluster_config()
        except Exception:
            k8s_config.load_kube_config()
        api = client.CoreV1Api()
        cm = api.read_namespaced_config_map(name=configmap_name, namespace=namespace)
        data = cm.data or {}
        bucket = data.get("S3_BUCKET") or os.getenv("S3_BUCKET")
        prefix = data.get("S3_PREFIX") or os.getenv("S3_PREFIX") or "ephys"
    except Exception:
        bucket = os.getenv("S3_BUCKET")
        prefix = os.getenv("S3_PREFIX") or "ephys"

    # Normalize bucket (no scheme) and build full root
    if bucket and bucket.startswith("s3://"):
        bucket = bucket[len("s3://"):]
    if bucket:
        root = f"s3://{bucket}/{prefix.rstrip('/')}/"
        bucket_val = bucket
    else:
        # If no bucket provided anywhere, fall back to env override or leave blank to force configuration.
        env_bucket = os.getenv("S3_BUCKET")
        if env_bucket:
            root = f"s3://{env_bucket}/{prefix.rstrip('/')}/"
            bucket_val = env_bucket
        else:
            # Deferred root (consumer should detect and error if used without substitution)
            root = f"s3://<unset-bucket>/{prefix.rstrip('/')}/"
            bucket_val = "<unset-bucket>"
    return {"bucket": bucket_val, "prefix": prefix, "root": root}

__all__ = ["load_s3_settings"]
