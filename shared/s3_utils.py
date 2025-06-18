"""
Shared S3 utilities for both services and processing containers.
"""
import os
import logging
from typing import Optional, Dict, Any
import braingeneers.utils.s3wrangler as wr

logger = logging.getLogger(__name__)

class S3Manager:
    """Unified S3 operations manager."""
    
    def __init__(self, endpoint_url: Optional[str] = None, bucket: Optional[str] = None):
        self.endpoint_url = endpoint_url or os.getenv("ENDPOINT_URL", "https://braingeneers.gi.ucsc.edu")
        self.bucket = bucket or os.getenv("S3_BUCKET", "braingeneers")
        
    def upload_file(self, local_file: str, s3_path: str) -> bool:
        """Upload a file to S3."""
        try:
            logger.info(f"Uploading {local_file} to {s3_path}")
            wr.upload(local_file=local_file, path=s3_path)
            logger.info(f"Successfully uploaded to {s3_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload {local_file} to {s3_path}: {e}")
            return False
    
    def download_file(self, s3_path: str, local_file: str) -> bool:
        """Download a file from S3."""
        try:
            logger.info(f"Downloading {s3_path} to {local_file}")
            wr.download(s3_path, local_file)
            logger.info(f"Successfully downloaded to {local_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to download {s3_path} to {local_file}: {e}")
            return False
    
    def file_exists(self, s3_path: str) -> bool:
        """Check if a file exists in S3."""
        try:
            return wr.does_object_exist(s3_path)
        except Exception as e:
            logger.error(f"Error checking if {s3_path} exists: {e}")
            return False
    
    def list_files(self, s3_prefix: str) -> list:
        """List files with a given prefix."""
        try:
            return wr.list_objects(s3_prefix)
        except Exception as e:
            logger.error(f"Error listing files with prefix {s3_prefix}: {e}")
            return []
    
    def create_upload_path(self, base_path: str, experiment_name: str, 
                          processing_type: str, params_file: Optional[str] = None) -> str:
        """Create standardized S3 upload path."""
        if params_file:
            params_suffix = f"_{params_file.split('/')[-1].split('.')[0]}"
        else:
            params_suffix = "_default"
        
        # Convert processing paths
        if "kilosort2" in base_path:
            upload_path = base_path.replace("kilosort2", f"{processing_type}")
        else:
            upload_path = base_path.replace("original/data", f"derived/{processing_type}")
            
        # Add parameter suffix
        upload_path = upload_path.replace(".zip", f"{params_suffix}.zip")
        
        return upload_path

# Global S3 manager instance
s3_manager = S3Manager()
