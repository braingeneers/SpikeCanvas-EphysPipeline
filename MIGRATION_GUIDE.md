# Maxwell Ephys Pipeline - Migration to Unified Architecture

## Overview

This document outlines the migration from the original component-based structure to a unified architecture with shared utilities, better separation of concerns, and improved maintainability.

## New Architecture

### Directory Structure

```
maxwell_ephys_pipeline/
├── services/                           # Long-running services
│   ├── Spike_Sorting_Listener/        # MQTT job listener
│   ├── job_scanner/                   # Pod/job scanner  
│   └── MaxWell_Dashboard/             # Web dashboard
├── containers/                        # Processing containers
│   ├── kilosort2_simplified/          # Spike sorting
│   ├── si_curation_docker/            # Data curation
│   ├── maxtwo_splitter/               # MaxTwo splitter
│   ├── connectivity/                  # Connectivity analysis
│   ├── visualization/                 # Visualization
│   └── local_field_potential/         # LFP analysis
├── shared/                            # Shared utilities
│   ├── maxwell_utils.py               # Maxwell data handling
│   ├── kubernetes_utils.py            # K8s operations
│   ├── s3_utils.py                    # S3 operations
│   └── config.py                      # Configuration management
├── docker/                            # Unified Docker configs
│   ├── base/                          # Base images
│   │   ├── service.dockerfile         # Base for services
│   │   └── processing.dockerfile      # Base for containers
│   ├── Dockerfile.service             # Service template
│   └── Dockerfile.container           # Container template
├── k8s/                              # Kubernetes manifests
│   ├── service-template.yaml          # Service deployments
│   └── container-job-template.yaml    # Job templates
├── tests/                            # Testing framework
│   ├── unit/                         # Unit tests
│   └── integration/                  # Integration tests
├── build.sh                         # Unified build script
└── migrate_to_new_structure.py      # Migration script
```

### Key Principles

1. **Services vs Containers**:
   - **Services**: Long-running processes (MQTT listeners, web servers, scanners)
   - **Containers**: Short-lived processing tasks (sorting, curation, analysis)

2. **Shared Utilities**: Common functionality consolidated in `shared/`
   - Maxwell data handling with dynamic well detection
   - Kubernetes operations with job/pod management
   - S3 operations with retry logic
   - Centralized configuration management

3. **Unified Build System**: Single build script for all components
   - Base images for common dependencies
   - Template Dockerfiles for consistent builds
   - Parallel build support for faster builds

## Migration Steps

### 1. Structural Migration

Run the migration script to reorganize the project:

```bash
python migrate_to_new_structure.py
```

This will:
- Create `services/` and `containers/` directories
- Move components to appropriate directories
- Create unified build system
- Generate deployment templates

### 2. Update Component Imports

Each component needs to be updated to use shared utilities:

```python
# Add to the top of each Python file
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

# Import shared utilities
from maxwell_utils import MaxwellDataReader
from kubernetes_utils import KubernetesManager
from s3_utils import S3Manager
from config import EphysConfig
```

### 3. Build and Deploy

Use the unified build system:

```bash
# Basic build
./build.sh

# Build and push to registry
./build.sh -r your-registry.com -t v1.0 -p

# Parallel build with verbose output
./build.sh -j -v
```

## Shared Utilities

### MaxwellDataReader

Unified Maxwell data handling with dynamic well detection:

```python
from maxwell_utils import MaxwellDataReader

reader = MaxwellDataReader(file_path)
wells = reader.get_available_wells()  # ['well000', 'well001', ...]
gain = reader.get_gain(well_index=0)
mapping = reader.get_mapping(well_index=0)
```

### KubernetesManager

Unified Kubernetes operations:

```python
from kubernetes_utils import KubernetesManager

k8s = KubernetesManager(namespace="braingeneers")
success = k8s.delete_pod_and_job("pod-name")
completion_time = k8s.get_pod_completion_time(pod)
```

### S3Manager

Unified S3 operations with retry logic:

```python
from s3_utils import S3Manager

s3 = S3Manager()
s3.upload_file(local_path, s3_path)
data = s3.download_file(s3_path)
```

### EphysConfig

Centralized configuration management:

```python
from config import EphysConfig

config = EphysConfig()
slack_topic = config.get("pipeline", "slack_topic")
k8s_namespace = config.get("kubernetes", "namespace", "braingeneers")
```

## Updated Well Detection

The major fix applied to resolve hardcoded "well000" references:

### Before (Hardcoded)
```python
# Old approach - breaks with different well configurations
dataset['recordings']['rec0000']['well000']['settings']['lsb'][0]
```

### After (Dynamic)
```python
# New approach - works with any well configuration
rec_group = dataset['recordings']['rec0000']
well_keys = [key for key in rec_group.keys() if key.startswith('well')]
well_keys.sort()  # Consistent ordering

if not well_keys:
    raise KeyError("No well groups found")

well_key = well_keys[0]  # Or iterate through all wells
gain = dataset['recordings']['rec0000'][well_key]['settings']['lsb'][0]
```

## Enhanced Job Scanner

The job scanner now properly deletes both Kubernetes jobs and pods:

```python
def delete_pod_and_job(self, pod_name: str) -> bool:
    """Delete both pod and its associated job."""
    # 1. Try owner references first
    # 2. Fall back to name pattern matching
    # 3. Delete job then pod with proper error handling
```

## Configuration Management

Components can now use centralized configuration:

```yaml
# /config/pipeline.yaml
pipeline:
  slack_topic: "telemetry/slack/TOSLACK/ephys-data-pipeline"
  job_prefix: "edp-"
  scan_interval: 1800  # 30 minutes

kubernetes:
  namespace: "braingeneers"
  
s3:
  bucket: "s3://braingeneers/ephys/"
  retry_attempts: 3
```

## Testing Framework

### Unit Tests
```bash
# Run unit tests for shared utilities
python -m pytest tests/unit/
```

### Integration Tests
```bash
# Run end-to-end pipeline tests
python tests/integration/test_integration.py
```

## Deployment

### Services (Long-running)
```bash
# Deploy MQTT listener service
kubectl apply -f k8s/service-template.yaml
```

### Containers (Processing jobs)
```bash
# Submit processing job
kubectl apply -f k8s/container-job-template.yaml
```

## Benefits of New Architecture

1. **Reduced Code Duplication**: Shared utilities eliminate repetitive code
2. **Better Maintainability**: Centralized changes affect all components
3. **Improved Testing**: Shared utilities can be thoroughly unit tested
4. **Consistent Configuration**: Single source of truth for settings
5. **Faster Builds**: Base images reduce build times
6. **Better Organization**: Clear separation between services and containers

## Migration Checklist

- [ ] Run migration script
- [ ] Update component imports to use shared utilities
- [ ] Test shared utilities with unit tests
- [ ] Build components with new build system
- [ ] Deploy services to Kubernetes
- [ ] Submit test processing jobs
- [ ] Run integration tests
- [ ] Monitor logs for any issues
- [ ] Update documentation

## Troubleshooting

### Import Errors
```python
# If shared utilities can't be imported, add path manually:
import sys
import os
sys.path.append('/path/to/shared')
```

### Build Issues
```bash
# Clean Docker cache and rebuild
docker system prune -f
./build.sh --cleanup --cleanup-old
```

### Kubernetes Issues
```bash
# Check pod logs
kubectl logs -f pod-name -n braingeneers

# Check job status
kubectl get jobs -n braingeneers
```

## Next Steps

1. **Complete Migration**: Finish updating all components
2. **Performance Optimization**: Monitor and optimize resource usage
3. **Enhanced Monitoring**: Add metrics and alerting
4. **Documentation Updates**: Update user guides and API docs
5. **CI/CD Pipeline**: Automate builds and deployments

## Contact

For questions about the migration or architecture, please:
- Check the troubleshooting section above
- Review shared utility documentation
- File an issue with detailed error messages
- Contact the development team
