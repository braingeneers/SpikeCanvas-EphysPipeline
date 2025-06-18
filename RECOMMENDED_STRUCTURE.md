# Recommended Project Structure for Maxwell Ephys Pipeline

## Current Issues
1. **Mixed Concerns**: Services and processing containers are at the same level
2. **No Clear Separation**: Infrastructure, application code, and data mixed together
3. **Duplicate Code**: Each component has its own Docker setup, utilities, etc.
4. **Hard to Navigate**: Flat structure makes it difficult to understand relationships
5. **Deployment Complexity**: No clear deployment boundaries

## Recommended Structure

```
maxwell_ephys_pipeline/
├── README.md
├── pyproject.toml                    # Modern Python packaging
├── requirements.txt
├── .gitignore
├── .env.example
│
├── docs/                             # Documentation
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT.md
│   ├── API.md
│   └── TROUBLESHOOTING.md
│
├── shared/                           # Shared libraries and utilities
│   ├── __init__.py
│   ├── maxwell_utils/                # Maxwell-specific utilities
│   │   ├── __init__.py
│   │   ├── data_reader.py
│   │   ├── well_detection.py
│   │   └── gain_mapping.py
│   ├── kubernetes_utils/             # K8s management utilities
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   ├── job_creator.py
│   │   └── pod_scanner.py
│   ├── storage/                      # S3 and storage utilities
│   │   ├── __init__.py
│   │   ├── s3_client.py
│   │   └── data_transfer.py
│   ├── messaging/                    # MQTT and messaging
│   │   ├── __init__.py
│   │   ├── mqtt_client.py
│   │   └── slack_notifier.py
│   └── config/                       # Configuration management
│       ├── __init__.py
│       ├── settings.py
│       └── constants.py
│
├── services/                         # Long-running services
│   ├── mqtt_job_listener/           # Renamed from Spike_Sorting_Listener
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── k8s/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   └── configmap.yaml
│   │   └── src/
│   │       ├── __init__.py
│   │       ├── main.py              # Entry point
│   │       ├── job_listener.py
│   │       ├── job_handler.py
│   │       └── config.py
│   │
│   ├── job_scanner/                 # Pod/job monitoring service
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── k8s/
│   │   │   └── deployment.yaml
│   │   └── src/
│   │       ├── __init__.py
│   │       ├── main.py
│   │       ├── scanner.py
│   │       └── slack_reporter.py
│   │
│   └── web_dashboard/               # Renamed from MaxWell_Dashboard
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── k8s/
│       │   ├── deployment.yaml
│       │   ├── service.yaml
│       │   └── ingress.yaml
│       └── src/
│           ├── __init__.py
│           ├── app.py               # Main Dash app
│           ├── pages/
│           ├── components/
│           └── utils/
│
├── containers/                      # Processing containers (ephemeral)
│   ├── spike_sorting/              # Renamed from kilosort2_simplified
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── k8s/
│   │   │   └── job-template.yaml
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   └── kilosort_runner.py
│   │   └── matlab/                 # MATLAB-specific files
│   │
│   ├── curation/                   # Renamed from si_curation_docker
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── k8s/
│   │   │   └── job-template.yaml
│   │   └── src/
│   │       ├── __init__.py
│   │       ├── main.py
│   │       ├── curation.py
│   │       └── curation_stitch.py
│   │
│   ├── splitter/                   # Renamed from maxtwo_splitter
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── k8s/
│   │   │   └── job-template.yaml
│   │   └── src/
│   │       ├── __init__.py
│   │       ├── main.py
│   │       └── splitter.py
│   │
│   ├── visualization/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── k8s/
│   │   │   └── job-template.yaml
│   │   └── src/
│   │       ├── __init__.py
│   │       ├── main.py
│   │       └── visualizer.py
│   │
│   ├── connectivity/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── k8s/
│   │   │   └── job-template.yaml
│   │   └── src/
│   │       ├── __init__.py
│   │       ├── main.py
│   │       └── connectivity_analysis.py
│   │
│   └── lfp_analysis/               # Renamed from local_field_potential
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── k8s/
│       │   └── job-template.yaml
│       └── src/
│           ├── __init__.py
│           ├── main.py
│           └── lfp_processor.py
│
├── infrastructure/                  # Infrastructure and deployment
│   ├── docker/
│   │   ├── base/
│   │   │   ├── service.Dockerfile   # Base for services
│   │   │   └── container.Dockerfile # Base for containers
│   │   ├── docker-compose.yml       # Local development
│   │   └── build-all.sh
│   │
│   ├── kubernetes/
│   │   ├── namespaces/
│   │   ├── rbac/
│   │   ├── secrets/
│   │   ├── configmaps/
│   │   └── monitoring/
│   │
│   ├── helm/                        # Helm charts for deployment
│   │   ├── maxwell-pipeline/
│   │   ├── services/
│   │   └── containers/
│   │
│   └── terraform/                   # Infrastructure as code
│       ├── aws/
│       ├── gcp/
│       └── modules/
│
├── config/                          # Configuration files
│   ├── environments/
│   │   ├── development.yaml
│   │   ├── staging.yaml
│   │   └── production.yaml
│   ├── parameters/                  # Processing parameters
│   │   ├── spike_sorting/
│   │   ├── curation/
│   │   ├── visualization/
│   │   └── connectivity/
│   └── jobs/                        # Job definitions
│       ├── pipeline_configs/
│       └── templates/
│
├── tests/                           # Test suites
│   ├── unit/
│   │   ├── shared/
│   │   ├── services/
│   │   └── containers/
│   ├── integration/
│   │   ├── test_pipeline.py
│   │   └── test_k8s_deployment.py
│   ├── fixtures/
│   └── conftest.py
│
├── scripts/                         # Utility and deployment scripts
│   ├── build.sh
│   ├── deploy.sh
│   ├── test.sh
│   ├── migrate_data.py
│   └── setup_environment.sh
│
├── data/                           # Development data and schemas
│   ├── schemas/
│   ├── samples/
│   └── test_datasets/
│
└── tools/                          # Development tools
    ├── migration/
    │   ├── migrate_to_new_structure.py
    │   └── validate_structure.py
    ├── monitoring/
    │   ├── health_checks.py
    │   └── log_analyzer.py
    └── development/
        ├── local_setup.py
        └── debug_tools.py
```

## Key Improvements

### 1. Clear Separation of Concerns
- **Services**: Long-running applications (MQTT listener, web dashboard, job scanner)
- **Containers**: Ephemeral processing tasks (spike sorting, curation, etc.)
- **Shared**: Common utilities used across components
- **Infrastructure**: Deployment and infrastructure code

### 2. Standardized Structure
Each service/container follows the same pattern:
```
component_name/
├── Dockerfile
├── requirements.txt
├── k8s/
└── src/
```

### 3. Centralized Configuration
- Environment-specific configs
- Parameter files organized by function
- Job templates and definitions

### 4. Better Deployment Story
- Helm charts for Kubernetes deployment
- Docker Compose for local development
- Infrastructure as Code with Terraform

### 5. Proper Python Package Structure
- Shared utilities as proper Python packages
- Clear import paths
- Modern packaging with pyproject.toml

### 6. Comprehensive Testing
- Unit tests for each component
- Integration tests for the pipeline
- Test fixtures and utilities

## Migration Benefits

1. **Maintainability**: Clear boundaries and responsibilities
2. **Scalability**: Easy to add new processing containers
3. **Deployment**: Standardized deployment patterns
4. **Development**: Better local development experience
5. **Monitoring**: Centralized logging and monitoring
6. **Documentation**: Better organization of docs and examples

## Migration Strategy

1. **Phase 1**: Move to new directory structure
2. **Phase 2**: Standardize Dockerfiles and K8s manifests
3. **Phase 3**: Consolidate shared utilities
4. **Phase 4**: Implement centralized configuration
5. **Phase 5**: Add comprehensive testing
6. **Phase 6**: Set up proper CI/CD pipelines
