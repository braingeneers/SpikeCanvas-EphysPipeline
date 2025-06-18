"""
Shared Kubernetes utilities for job and pod management.
"""
import logging
from typing import Optional, Dict, Any, List
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)

class KubernetesManager:
    """Unified Kubernetes operations manager."""
    
    def __init__(self, namespace: str = "braingeneers"):
        self.namespace = namespace
        self.core_v1 = None
        self.batch_v1 = None
        self._setup_clients()
    
    def _setup_clients(self):
        """Setup Kubernetes API clients."""
        try:
            config.load_kube_config()
        except:
            config.load_incluster_config()
        
        self.core_v1 = client.CoreV1Api()
        self.batch_v1 = client.BatchV1Api()
    
    def refresh_clients(self):
        """Refresh Kubernetes clients (useful for token renewal)."""
        self._setup_clients()
    
    def get_pod_completion_time(self, pod) -> str:
        """Safely extract completion time from pod conditions."""
        if pod.status.conditions is None or len(pod.status.conditions) == 0:
            return "Unknown"
        
        latest_timestamp = None
        for condition in pod.status.conditions:
            if condition.last_transition_time:
                if latest_timestamp is None or condition.last_transition_time > latest_timestamp:
                    latest_timestamp = condition.last_transition_time
        
        if latest_timestamp:
            return self._format_timestamp(latest_timestamp)
        return "Unknown"
    
    def delete_pod_and_job(self, pod_name: str) -> bool:
        """Delete both pod and its associated job."""
        success = True
        
        # First delete the job
        if not self._delete_associated_job(pod_name):
            success = False
        
        # Then delete the pod
        if not self._delete_pod(pod_name):
            success = False
            
        return success
    
    def _delete_associated_job(self, pod_name: str) -> bool:
        """Delete the job associated with a pod."""
        try:
            # Try to get pod to check owner references
            try:
                pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=self.namespace)
                if pod.metadata.owner_references:
                    for owner_ref in pod.metadata.owner_references:
                        if owner_ref.kind == "Job":
                            job_name = owner_ref.name
                            logger.info(f"Found job {job_name} via owner reference for pod {pod_name}")
                            return self._delete_job(job_name)
            except ApiException:
                pass
            
            # Fallback: search by name pattern
            job_list = self.batch_v1.list_namespaced_job(namespace=self.namespace)
            for job in job_list.items:
                job_name = job.metadata.name
                if pod_name.startswith(job_name):
                    logger.info(f"Found job {job_name} via name pattern for pod {pod_name}")
                    return self._delete_job(job_name)
            
            logger.warning(f"No associated job found for pod {pod_name}")
            return True  # Not an error if no job found
            
        except ApiException as e:
            logger.error(f"Exception when finding job for pod {pod_name}: {e}")
            return False
    
    def _delete_job(self, job_name: str) -> bool:
        """Delete a specific job."""
        try:
            self.batch_v1.delete_namespaced_job(
                name=job_name,
                namespace=self.namespace,
                body=client.V1DeleteOptions(
                    propagation_policy='Foreground',
                    grace_period_seconds=0
                )
            )
            logger.info(f"Deleted job {job_name}")
            return True
        except ApiException as e:
            logger.error(f"Exception when deleting job {job_name}: {e}")
            return False
    
    def _delete_pod(self, pod_name: str) -> bool:
        """Delete a specific pod."""
        try:
            self.core_v1.delete_namespaced_pod(
                name=pod_name,
                namespace=self.namespace,
                body=client.V1DeleteOptions(
                    propagation_policy='Foreground',
                    grace_period_seconds=0
                )
            )
            logger.info(f"Deleted pod {pod_name}")
            return True
        except ApiException as e:
            logger.error(f"Exception when deleting pod {pod_name}: {e}")
            return False
    
    def _format_timestamp(self, timestamp) -> str:
        """Format timestamp to local time string."""
        from dateutil.tz import gettz
        to_zone = gettz("US/Pacific")
        local_ts = timestamp.astimezone(to_zone)
        return local_ts.strftime("%Y-%m-%d %H:%M:%S")
