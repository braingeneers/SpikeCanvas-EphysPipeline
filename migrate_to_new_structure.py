#!/usr/bin/env python3
"""
Migration script to restructure the maxwell_ephys_pipeline project.
Organizes components into services/ and containers/ directories.
"""

import os
import shutil
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Current workspace root
WORKSPACE_ROOT = Path(__file__).parent

# Define the new structure
SERVICES = [
    "Spike_Sorting_Listener",  # MQTT job listener service
    "job_scanner",             # Pod scanner service  
    "MaxWell_Dashboard"        # Web dashboard service
]

CONTAINERS = [
    "kilosort2_simplified",    # Spike sorting container
    "si_curation_docker",      # Data curation container
    "maxtwo_splitter",         # MaxTwo data splitter container
    "connectivity",            # Connectivity analysis container
    "visualization",           # Visualization container
    "local_field_potential"    # LFP analysis container
]

def create_new_structure():
    """Create the new directory structure."""
    services_dir = WORKSPACE_ROOT / "services"
    containers_dir = WORKSPACE_ROOT / "containers"
    
    # Create new directories
    services_dir.mkdir(exist_ok=True)
    containers_dir.mkdir(exist_ok=True)
    
    logger.info(f"Created {services_dir}")
    logger.info(f"Created {containers_dir}")
    
    return services_dir, containers_dir

def migrate_component(component: str, source_dir: Path, target_dir: Path):
    """Migrate a component to the new structure."""
    source_path = WORKSPACE_ROOT / component
    target_path = target_dir / component
    
    if not source_path.exists():
        logger.warning(f"Source component {component} not found at {source_path}")
        return False
    
    if target_path.exists():
        logger.warning(f"Target {target_path} already exists, skipping")
        return False
    
    # Copy the component
    try:
        shutil.copytree(source_path, target_path)
        logger.info(f"Migrated {component}: {source_path} -> {target_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to migrate {component}: {e}")
        return False

def create_unified_dockerfiles():
    """Create unified Dockerfiles using the new base images."""
    
    # Service Dockerfile template
    service_dockerfile = """# Unified Dockerfile for pipeline services
FROM maxwell-service-base:latest

# Copy service-specific code
COPY src/ /app/src/
COPY requirements.txt /app/ 2>/dev/null || true

# Install service-specific dependencies
RUN if [ -f /app/requirements.txt ]; then pip install --no-cache-dir -r /app/requirements.txt; fi

# Default command (override in kubernetes manifests)
CMD ["python", "/app/src/main.py"]
"""

    # Container Dockerfile template  
    container_dockerfile = """# Unified Dockerfile for processing containers
FROM maxwell-processing-base:latest

# Copy container-specific code
COPY src/ /app/src/
COPY matlab/ /app/matlab/ 2>/dev/null || true
COPY requirements.txt /app/ 2>/dev/null || true

# Install container-specific dependencies
RUN if [ -f /app/requirements.txt ]; then pip install --no-cache-dir -r /app/requirements.txt; fi

# Default command (override in job manifests)
CMD ["python", "/app/src/main.py"]
"""
    
    return service_dockerfile, container_dockerfile

def create_unified_build_system():
    """Create a unified build system for all components."""
    
    build_script = """#!/bin/bash
# Unified build script for Maxwell Ephys Pipeline

set -e

REGISTRY=${REGISTRY:-"localhost:5000"}
TAG=${TAG:-"latest"}
PUSH=${PUSH:-"false"}

echo "Building Maxwell Ephys Pipeline components..."
echo "Registry: $REGISTRY"
echo "Tag: $TAG"

# Build base images first
echo "Building base images..."
docker build -f docker/base/service.dockerfile -t maxwell-service-base:$TAG docker/base/
docker build -f docker/base/processing.dockerfile -t maxwell-processing-base:$TAG docker/base/

# Build services
echo "Building services..."
for service in services/*/; do
    if [ -d "$service" ]; then
        service_name=$(basename "$service")
        echo "Building service: $service_name"
        docker build -f docker/Dockerfile.service -t $REGISTRY/maxwell-$service_name:$TAG $service
        
        if [ "$PUSH" = "true" ]; then
            docker push $REGISTRY/maxwell-$service_name:$TAG
        fi
    fi
done

# Build containers
echo "Building containers..."
for container in containers/*/; do
    if [ -d "$container" ]; then
        container_name=$(basename "$container")
        echo "Building container: $container_name"
        docker build -f docker/Dockerfile.container -t $REGISTRY/maxwell-$container_name:$TAG $container
        
        if [ "$PUSH" = "true" ]; then
            docker push $REGISTRY/maxwell-$container_name:$TAG
        fi
    fi
done

echo "Build complete!"
"""
    
    return build_script

def create_deployment_configs():
    """Create unified deployment configurations."""
    
    # Kubernetes deployment template for services
    service_deployment = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: maxwell-{service_name}
  namespace: braingeneers
spec:
  replicas: 1
  selector:
    matchLabels:
      app: maxwell-{service_name}
  template:
    metadata:
      labels:
        app: maxwell-{service_name}
    spec:
      containers:
      - name: {service_name}
        image: {registry}/maxwell-{service_name}:{tag}
        env:
        - name: COMPONENT_TYPE
          value: "service"
        - name: SERVICE_NAME
          value: "{service_name}"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        volumeMounts:
        - name: config
          mountPath: /config
        - name: shared-data
          mountPath: /data
      volumes:
      - name: config
        configMap:
          name: maxwell-config
      - name: shared-data
        persistentVolumeClaim:
          claimName: maxwell-shared-storage
---
apiVersion: v1
kind: Service
metadata:
  name: maxwell-{service_name}
  namespace: braingeneers
spec:
  selector:
    app: maxwell-{service_name}
  ports:
  - port: 8080
    targetPort: 8080
"""

    # Job template for containers
    container_job = """apiVersion: batch/v1
kind: Job
metadata:
  name: maxwell-{container_name}-{job_id}
  namespace: braingeneers
spec:
  template:
    spec:
      containers:
      - name: {container_name}
        image: {registry}/maxwell-{container_name}:{tag}
        env:
        - name: COMPONENT_TYPE
          value: "container"
        - name: CONTAINER_NAME
          value: "{container_name}"
        - name: JOB_ID
          value: "{job_id}"
        resources:
          requests:
            memory: "{memory_request}"
            cpu: "{cpu_request}"
          limits:
            memory: "{memory_limit}"
            cpu: "{cpu_limit}"
        volumeMounts:
        - name: shared-data
          mountPath: /data
        - name: config
          mountPath: /config
      volumes:
      - name: shared-data
        persistentVolumeClaim:
          claimName: maxwell-shared-storage
      - name: config
        configMap:
          name: maxwell-config
      restartPolicy: Never
  backoffLimit: 3
"""
    
    return service_deployment, container_job

def main():
    """Main migration function."""
    logger.info("Starting Maxwell Ephys Pipeline restructuring...")
    
    # Create new directory structure
    services_dir, containers_dir = create_new_structure()
    
    # Migrate services
    logger.info("Migrating services...")
    services_migrated = 0
    for service in SERVICES:
        if migrate_component(service, WORKSPACE_ROOT, services_dir):
            services_migrated += 1
    
    # Migrate containers
    logger.info("Migrating containers...")
    containers_migrated = 0
    for container in CONTAINERS:
        if migrate_component(container, WORKSPACE_ROOT, containers_dir):
            containers_migrated += 1
    
    # Create unified build system
    logger.info("Creating unified build system...")
    build_script = create_unified_build_system()
    
    build_file = WORKSPACE_ROOT / "build.sh"
    with open(build_file, 'w') as f:
        f.write(build_script)
    os.chmod(build_file, 0o755)
    
    # Create unified Dockerfiles
    service_dockerfile, container_dockerfile = create_unified_dockerfiles()
    
    docker_dir = WORKSPACE_ROOT / "docker"
    docker_dir.mkdir(exist_ok=True)
    
    with open(docker_dir / "Dockerfile.service", 'w') as f:
        f.write(service_dockerfile)
    
    with open(docker_dir / "Dockerfile.container", 'w') as f:
        f.write(container_dockerfile)
    
    # Create deployment templates
    service_deployment, container_job = create_deployment_configs()
    
    k8s_dir = WORKSPACE_ROOT / "k8s"
    k8s_dir.mkdir(exist_ok=True)
    
    with open(k8s_dir / "service-template.yaml", 'w') as f:
        f.write(service_deployment)
    
    with open(k8s_dir / "container-job-template.yaml", 'w') as f:
        f.write(container_job)
    
    # Create integration test structure
    test_dir = WORKSPACE_ROOT / "tests" / "integration"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    integration_test = """#!/usr/bin/env python3
'''
Integration tests for the Maxwell Ephys Pipeline.
Tests end-to-end workflows across services and containers.
'''

import pytest
import logging
from pathlib import Path

# Import shared utilities
import sys
sys.path.append(str(Path(__file__).parent.parent / "shared"))

from kubernetes_utils import KubernetesManager
from s3_utils import S3Manager
from config import EphysConfig

class TestPipelineIntegration:
    '''Test full pipeline integration.'''
    
    def setup_method(self):
        '''Setup test environment.'''
        self.k8s = KubernetesManager()
        self.s3 = S3Manager()
        self.config = EphysConfig()
    
    def test_service_health(self):
        '''Test that all services are healthy.'''
        services = ["spike-sorting-listener", "job-scanner", "maxwell-dashboard"]
        
        for service in services:
            # Check if service pods are running
            pods = self.k8s.core_v1.list_namespaced_pod(
                namespace="braingeneers",
                label_selector=f"app=maxwell-{service}"
            )
            assert len(pods.items) > 0, f"No pods found for service {service}"
            
            # Check pod status
            for pod in pods.items:
                assert pod.status.phase == "Running", f"Pod {pod.metadata.name} not running"
    
    def test_job_submission_and_completion(self):
        '''Test job submission through MQTT and completion.'''
        # This would test the full workflow:
        # 1. Submit MQTT message
        # 2. Verify job creation
        # 3. Wait for completion
        # 4. Check outputs in S3
        pass
    
    def test_shared_utilities(self):
        '''Test shared utility functions.'''
        # Test Maxwell data reader
        # Test S3 operations
        # Test Kubernetes operations
        pass

if __name__ == "__main__":
    pytest.main([__file__])
"""
    
    with open(test_dir / "test_integration.py", 'w') as f:
        f.write(integration_test)
    
    # Summary
    logger.info("Migration completed!")
    logger.info(f"Services migrated: {services_migrated}/{len(SERVICES)}")
    logger.info(f"Containers migrated: {containers_migrated}/{len(CONTAINERS)}")
    logger.info("Created unified build system")
    logger.info("Created deployment templates")
    logger.info("Created integration test framework")
    
    logger.info("\nNext steps:")
    logger.info("1. Review migrated components in services/ and containers/")
    logger.info("2. Update individual component imports to use shared utilities")
    logger.info("3. Test the unified build system: ./build.sh")
    logger.info("4. Deploy using the new Kubernetes templates")
    logger.info("5. Run integration tests: python tests/integration/test_integration.py")

if __name__ == "__main__":
    main()
