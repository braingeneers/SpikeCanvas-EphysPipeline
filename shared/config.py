"""
Centralized configuration management for the ephys pipeline.
"""
import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

class EphysConfig:
    """Centralized configuration manager for all pipeline components."""
    
    def __init__(self, config_dir: str = "/config"):
        self.config_dir = Path(config_dir)
        self._configs = {}
        self._load_configs()
    
    def _load_configs(self):
        """Load all configuration files."""
        if self.config_dir.exists():
            for config_file in self.config_dir.glob("*.{json,yaml,yml}"):
                with open(config_file) as f:
                    if config_file.suffix == ".json":
                        self._configs[config_file.stem] = json.load(f)
                    else:
                        self._configs[config_file.stem] = yaml.safe_load(f)
    
    def get(self, component: str, key: str = None, default: Any = None) -> Any:
        """Get configuration for a component."""
        config = self._configs.get(component, {})
        if key:
            return config.get(key, default)
        return config
    
    def get_kubernetes_config(self) -> Dict[str, Any]:
        """Get Kubernetes-specific configuration."""
        return {
            "namespace": os.getenv("K8S_NAMESPACE", "braingeneers"),
            "job_prefix": os.getenv("JOB_PREFIX", "edp-"),
            "image_pull_policy": "Always",
            "restart_policy": "Never"
        }
    
    def get_s3_config(self) -> Dict[str, Any]:
        """Get S3-specific configuration."""
        return {
            "endpoint_url": os.getenv("ENDPOINT_URL", "https://braingeneers.gi.ucsc.edu"),
            "bucket": os.getenv("S3_BUCKET", "braingeneers"),
            "region": os.getenv("AWS_REGION", "us-west-1")
        }

# Global configuration instance
config = EphysConfig()
