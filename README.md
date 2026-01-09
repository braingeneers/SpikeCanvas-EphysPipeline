# SpikeCanvas

A comprehensive, scalable platform for processing and analyzing high-density electrophysiology data from Maxwell biosensor arrays. This pipeline provides end-to-end processing capabilities from raw neural recordings to publication-ready analyses and visualizations.

> **Paper**: Read more about this work in our preprint: [Multiscale Cloud-Based Pipeline for Neuronal Electrophysiology Analysis and Visualization](https://www.biorxiv.org/content/10.1101/2024.11.14.623530v2) (bioRxiv, 2024)

## Overview

The SpikeCanvas is designed for high-throughput processing of neural data with automated spike sorting, quality control, connectivity analysis, and interactive visualization. The platform supports containerized workflows that can be deployed on Kubernetes clusters for scalable data processing.

All algorithms follow a consistent three-step workflow:
1. **Load data from S3** – Download input data (raw recordings, spike-sorting results, or intermediate outputs)
2. **Process** – Apply algorithm-specific computation (spike sorting, connectivity analysis, LFP filtering, curation, or visualization)
3. **Save results to S3** – Upload processed outputs back to S3 storage for downstream use or visualization

## Repository Structure

```
SpikeCanvas-EphysPipeline/
├── Algorithms/              # Core processing algorithms
│   ├── connectivity/        # Functional connectivity analysis
│   ├── kilosort2_simplified/ # Spike sorting with Kilosort2
│   ├── local_field_potential/ # LFP analysis and filtering
│   ├── maxtwo_splitter/     # Data preprocessing and splitting
│   ├── si_curation_docker/  # Quality control and curation
│   └── visualization/       # Data visualization tools
├── Services/                # Platform services and interfaces
│   ├── MaxWell_Dashboard/   # SpikeCanvas web dashboard
│   ├── Spike_Sorting_Listener/ # Job orchestration service
│   ├── job_scanner/         # Job monitoring and status tracking
│   └── parameters/          # Configuration templates
└── performance/            # Benchmarking and optimization tools
```

## Core Algorithms

### Spike Sorting (Kilosort2)
- **Location**: `Algorithms/kilosort2_simplified/`
- **Description**: Automated spike detection and clustering using Kilosort2 algorithm
- **Features**: 
  - GPU-accelerated processing
  - Template matching and drift correction
  - Automated parameter optimization
- **Docker Image**: `surygeng/kilosort_docker:v0.2`

### Quality Control & Curation
- **Location**: `Algorithms/si_curation_docker/`
- **Description**: Automated and manual curation of spike sorting results
- **Features**:
  - Signal-to-noise ratio assessment
  - ISI violation analysis
  - Firing rate quality metrics
  - Manual curation interface
- **Docker Image**: `surygeng/qm_curation:v0.2`

### Connectivity Analysis
- **Location**: `Algorithms/connectivity/`
- **Description**: Functional connectivity and network analysis
- **Features**:
  - Cross-correlation analysis
  - Spike-time tiling coefficient (STTC)
  - Network topology metrics
  - Burst detection and analysis
- **Docker Image**: `surygeng/connectivity:v0.1`

### Visualization
- **Location**: `Algorithms/visualization/`
- **Description**: Interactive plots and data exploration tools
- **Features**:
  - Raster plots and PSTHs
  - Electrode mapping
  - Connectivity heatmaps
  - Statistical summaries
- **Docker Image**: `surygeng/visualization:v0.1`

### Local Field Potential Analysis
- **Location**: `Algorithms/local_field_potential/`
- **Description**: LFP signal processing and spectral analysis
- **Features**:
  - Multi-band frequency filtering
  - Power spectral density analysis
  - Time-frequency decomposition
  - Custom time window analysis
- **Docker Image**: `surygeng/local_field_potential:v0.1`

## Services & Infrastructure

### SpikeCanvas Dashboard
- **Location**: `Services/MaxWell_Dashboard/`
- **Description**: Web-based interface for data processing and analysis
- **Features**:
  - Interactive job submission and monitoring
  - Real-time analytics and visualization
  - Parameter configuration interface
  - Progress tracking with loading indicators
- **Access**: Web dashboard at `http://localhost:8050`
- **Docker Image**: `surygeng/maxwell_dashboard:v0.1`

### Job Orchestration
- **Location**: `Services/Spike_Sorting_Listener/`
- **Description**: Kubernetes-based job management and workflow orchestration
- **Features**:
  - MQTT-based job messaging
  - Automated workflow chaining
  - Resource management and scaling
  - Job status monitoring

### MaxTwo Data Splitter
- **Location**: `Algorithms/maxtwo_splitter/`
- **Description**: Preprocessing algorithm for splitting 6-well MaxTwo recordings into individual well files
- **Features**:
  - Parallel well processing with multiprocessing
  - Memory-optimized file operations
  - Hard-link preservation for efficient storage
  - Automated upload to S3 split directory
- **Docker Image**: `surygeng/maxtwo_splitter:v0.1`

### Job Monitoring
- **Location**: `Services/job_scanner/`
- **Description**: Job status tracking and monitoring utilities
- **Features**:
  - Real-time job status updates
  - Performance monitoring
  - Error handling and recovery
  - Log aggregation

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Kubernetes cluster (for production deployment)
- Access to S3 storage with electrophysiology data
- Python 3.10+ (for local development)

### 1. Launch the Dashboard
```bash
# Clone the repository
git clone https://github.com/braingeneers/SpikeCanvas-EphysPipeline.git
cd SpikeCanvas-EphysPipeline/Services/MaxWell_Dashboard

# Run the local dashboard launcher
./start_dashboard.sh
```
The dashboard runs at http://127.0.0.1:8050/.
Hosted access may be available at https://mxwdash.braingeneers.gi.ucsc.edu (request access in `#braingeneers-helpdesk`).

### 2. Process Data via Dashboard
1. **Select Dataset**: Choose your electrophysiology recording from the UUID dropdown
2. **Configure Pipeline**: Select processing steps (spike sorting, curation, analysis)
3. **Set Parameters**: Customize processing parameters or use defaults
4. **Submit Jobs**: Launch processing jobs and monitor progress
5. **Analyze Results**: View interactive visualizations and download results

### 3. Run Individual Algorithms
```bash
# Example: Run spike sorting on a specific dataset
cd Algorithms/kilosort2_simplified
docker run -v /data:/data surygeng/kilosort_docker:v0.2 \
  python kilosort2_simplified.py /data/recording.raw.h5 /data/params.json

# Example: Run connectivity analysis
cd Algorithms/connectivity
docker run -v /data:/data surygeng/connectivity:v0.1 \
  python run_conn.py /data/sorted_data.zip /data/conn_params.json
```

## Data Formats Supported

- **Raw Recordings**: Maxwell `.raw.h5`, MEArec `.h5`, NWB formats
- **Processed Data**: Phy-compatible spike sorting outputs
- **Curated Results**: Quality-metric annotated datasets (`_qm.zip`, `_acqm.zip`)
- **Connectivity Data**: Network matrices and connectivity metrics
- **Visualization**: Interactive Plotly figures and static exports

## Docker Compose Deployment

This section describes how to deploy the SpikeCanvas services (Dashboard, Listener, Scanner) using Docker Compose on your local server or institution infrastructure.

### Prerequisites

1. **Docker and Docker Compose** installed on your server
2. **S3-compatible storage** (AWS S3, MinIO, or compatible) with credentials
3. **Kubernetes cluster** access for job orchestration (algorithm containers run as K8s jobs)
4. **kubectl configured** with access to your Kubernetes cluster

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/braingeneers/SpikeCanvas-EphysPipeline.git
   cd SpikeCanvas-EphysPipeline
   ```

2. **Create your configuration file**:
   ```bash
   cp .env.template .env
   ```

3. **Edit `.env` with your institution's settings**:
   ```bash
   vim .env
   ```
   
   **Required configuration** (at minimum):
   ```bash
   # S3 Storage Configuration
   S3_BUCKET=your-institution-bucket    # e.g., ucdavis-neural
   S3_PREFIX=ephys                      # Base path prefix in your bucket
   
   # AWS Credentials (choose one method)
   # Method 1: AWS Access Keys (not recommended for production)
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   AWS_REGION=us-west-2
   
   # Method 2: AWS Profile (uses ~/.aws/credentials)
   # AWS_PROFILE=your-profile-name
   ```

4. **Start the services**:
   ```bash
   docker-compose up -d
   ```

5. **Access the dashboard**:
   - Open browser to `http://localhost:8050`
   - Select your dataset UUID and configure processing pipeline

### Configuration Reference

The `.env` file controls all aspects of the pipeline deployment. See `.env.template` for complete documentation.

#### Essential Settings

**S3 Storage Configuration**:
- `S3_BUCKET`: Your institution's S3 bucket name (required)
- `S3_PREFIX`: Base path prefix, typically "ephys" (default: ephys)
- `ENDPOINT_URL`: Custom S3 endpoint for non-AWS S3 (optional)
- `S3_ENDPOINT`: Alternative S3 endpoint variable (optional)

**AWS Credentials** (choose one approach):
- **AWS Profile**: Set `AWS_PROFILE=profile-name`, requires `~/.aws/credentials`
- **Access Keys**: Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`

**Service Storage Paths**:
- `SERVICE_ROOT`: Base path for service data (CSV files, job state)
  - Default: `s3://<S3_BUCKET>/services/mqtt_job_listener`
- `PARAMETER_BUCKET`: Parameter file storage location
  - Default: `s3://<S3_BUCKET>/services/mqtt_job_listener/params`

**Kubernetes Configuration**:
- `NRP_NAMESPACE`: Kubernetes namespace for algorithm jobs (default: braingeneers)

#### Advanced Settings

See `.env.template` for additional configuration options:
- Custom Docker images for algorithms
- Resource limits (CPU, memory, GPU) for algorithm jobs
- Alternative S3 endpoints for private cloud deployments
- Additional bucket paths for integrated datasets

### How Configuration Propagates

Understanding the configuration flow helps troubleshoot deployment issues:

1. **`.env` file** → Contains all configuration values
2. **`docker-compose.yml`** → Loads `.env` and passes values to service containers
3. **Service containers** → Dashboard, Listener, Scanner read env vars for S3 access
4. **Listener spawns jobs** → Injects S3/AWS env vars into algorithm Kubernetes jobs
5. **Algorithm containers** → Inherit S3 configuration, access your institution's bucket

```
.env file
  ↓
Docker Compose (dashboard, listener, scanner)
  ↓
Listener reads config
  ↓
Spawns Kubernetes job with injected env vars
  ↓
Algorithm container (kilosort2, connectivity, etc.)
  ↓
Reads/writes to your S3 bucket
```

### Data Organization

Your S3 bucket should follow this structure:
```
s3://your-bucket/
├── ephys/                           # S3_PREFIX (configurable)
│   ├── 2024-01-15-e-12345/         # Session UUID
│   │   ├── original/
│   │   │   └── data/
│   │   │       └── recording.raw.h5
│   │   └── derived/
│   │       ├── kilosort2/
│   │       │   └── session_phy.zip
│   │       ├── curation/
│   │       │   └── session_acqm.zip
│   │       ├── connectivity/
│   │       │   └── session_conn.zip
│   │       └── visualization/
│   │           └── session_figure.zip
│   └── ...
└── services/                        # SERVICE_ROOT (configurable)
    └── mqtt_job_listener/
        ├── csvs/                    # Job state tracking
        │   └── job_status.csv
        └── params/                  # PARAMETER_BUCKET
            ├── kilosort2/
            ├── connectivity/
            └── ...
```

### Deployment Examples

#### UC Davis Example
```bash
# .env configuration for UC Davis
S3_BUCKET=ucdavis-neural-data
S3_PREFIX=ephys
AWS_PROFILE=ucdavis-prod
NRP_NAMESPACE=ucdavis-neural-lab
SERVICE_ROOT=s3://ucdavis-neural-data/services/mqtt_job_listener
PARAMETER_BUCKET=s3://ucdavis-neural-data/services/mqtt_job_listener/params
```

#### Private MinIO Deployment
```bash
# .env configuration for MinIO (private S3-compatible storage)
S3_BUCKET=ephys-data
S3_PREFIX=ephys
ENDPOINT_URL=https://minio.myinstitution.edu
S3_ENDPOINT=https://minio.myinstitution.edu
AWS_ACCESS_KEY_ID=minio-access-key
AWS_SECRET_ACCESS_KEY=minio-secret-key
NRP_NAMESPACE=neural-processing
```

### Service Management

**View logs**:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f dashboard
docker-compose logs -f listener
docker-compose logs -f scanner
```

**Restart services**:
```bash
# All services
docker-compose restart

# Specific service
docker-compose restart listener
```

**Stop services**:
```bash
docker-compose down
```

**Update configuration**:
1. Edit `.env` file
2. Restart services: `docker-compose restart`
3. Changes apply to all future algorithm jobs

### Troubleshooting

**Dashboard shows no UUIDs**:
- Verify `S3_BUCKET` is set correctly in `.env`
- Check AWS credentials are valid
- Confirm data exists at `s3://<S3_BUCKET>/<S3_PREFIX>/`
- View dashboard logs: `docker-compose logs dashboard`

**Algorithm jobs fail to access S3**:
- Listener injects env vars into jobs - check listener logs: `docker-compose logs listener`
- Verify Kubernetes cluster has network access to S3
- Verify keys are valid and have S3 permissions

**Jobs not appearing in dashboard**:
- Check job_scanner is running: `docker-compose ps scanner`
- Verify `SERVICE_ROOT` or `CSV_BUCKET` points to correct location
- View scanner logs: `docker-compose logs scanner`

**kubectl not configured**:
- Listener needs `~/.kube/config` to spawn Kubernetes jobs
- Verify volume mount in `docker-compose.yml` maps your kubeconfig correctly
- Test: `kubectl get pods -n <NRP_NAMESPACE>`

### Security Best Practices

1. **Restrict S3 permissions** to only necessary buckets and prefixes
2. **Keep `.env` file secure** - add to `.gitignore`, use file permissions (chmod 600)
3. **Rotate credentials regularly**
4. **Use separate buckets** for different security zones (production vs. testing)

### Kubernetes Job Permissions

The Listener service spawns Kubernetes jobs for algorithm processing. Ensure your kubeconfig user has these permissions in the target namespace:

```yaml
# Required RBAC permissions
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: ephys-job-creator
  namespace: <NRP_NAMESPACE>
rules:
- apiGroups: ["batch"]
  resources: ["jobs"]
  verbs: ["create", "get", "list", "watch", "delete"]
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs: ["get", "list", "watch"]
```

### Migrating from Braingeneers Defaults

If you're migrating from the default Braingeneers configuration:

1. **Data migration**: Copy existing data from `s3://braingeneers/ephys/` to your bucket
   ```bash
   aws s3 sync s3://braingeneers/ephys/ s3://your-bucket/ephys/ --profile your-profile
   ```

2. **Update `.env`**: Configure your S3 bucket and credentials

3. **Parameter files**: Copy parameter templates to your bucket
   ```bash
   aws s3 sync Services/parameters/ s3://your-bucket/services/mqtt_job_listener/params/
   ```

4. **Test with one dataset**: Process a single session to validate configuration

## Configuration

### Parameter Templates
- **Location**: `Services/parameters/`
- **Available Configs**: Pipeline, Kilosort2, Curation, Connectivity, LFP, Visualization
- **Customization**: JSON-based parameter files for each processing step

### Docker Configuration
Each algorithm includes:
- `docker/Dockerfile`: Container definition
- `docker/requirements.txt`: Python dependencies
- `k8s/*.yaml`: Kubernetes deployment manifests

## Development

### Local Setup
```bash
# Install development dependencies
pip install -r Services/MaxWell_Dashboard/docker/requirements.txt
pip install braingeneers['iot','analysis','data']

# Run dashboard locally
cd Services/MaxWell_Dashboard/src
python app.py
```

### Adding New Algorithms
1. Create new directory in `Algorithms/`
2. Implement processing script and Docker configuration
3. Add parameter template to `Services/parameters/`
4. Update dashboard job definitions in `Services/MaxWell_Dashboard/src/values.py`

## Performance & Scaling

- **Benchmarking**: See `performance/` directory for speed tests and optimization guides
- **Resource Requirements**: Configurable CPU, memory, and GPU allocation per job
- **Scalability**: Kubernetes-based auto-scaling for large datasets
- **Storage**: S3-compatible cloud storage for data persistence

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Documentation

- **Dashboard Manual**: See `Services/MaxWell_Dashboard/README.md`
- **Algorithm Docs**: Individual README files in each `Algorithms/` subdirectory
- **API Reference**: Auto-generated documentation for core modules
- **Tutorials**: Example workflows and best practices (coming soon)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **UC Santa Cruz Braingeneers**: Platform development and maintenance
- **Maxwell Biosystems**: Hardware and data format support
- **Kilosort Team**: Spike sorting algorithm integration
- **SpikeInterface Community**: Quality control and curation tools

## Support

- **Issues**: GitHub Issues for bug reports and feature requests
- **Discussions**: GitHub Discussions for questions and community support
- **Contact**: [Braingeneers Team](https://braingeneers.gi.ucsc.edu) for technical support

---

**SpikeCanvas** - Advancing Neural Data Analysis Through Open Science

## Pipeline Configuration Layer

To support external institutions (e.g. UC Davis) with their own S3 buckets and credentials, the pipeline uses a centralized configuration layer.

### Configuration Sources (precedence high → low)
1. Environment variables: `S3_BUCKET`, `S3_PREFIX`, `S3_INPUT_PREFIX`, `S3_OUTPUT_PREFIX`, `AWS_REGION`, `AWS_PROFILE`, `AWS_ROLE_ARN`, `AWS_SESSION_NAME`
  - Dashboard/job listener extras: `SERVICE_BUCKET` (CSV/job state), `PARAMETER_BUCKET` (parameter files)
  - Namespace control: `NRP_NAMESPACE` (Kubernetes namespace for job submission; defaults to `braingeneers` if unset)
  - Optional cross-domain buckets: `FLUIDICS_BUCKET` (default `s3://braingeneers/fluidics/`), `INTEGRATED_BUCKET` (default `s3://braingeneers/integrated/`) used when listener infers non-ephys UUID types.
  - Dashboard job submission: `SERVICE_ROOT` (base service path), `SERVICE_BUCKET` (CSV path override), `PARAMETER_BUCKET` (parameter files), `KILOSORT_IMAGE`, `KILOSORT_RUN_ARGS`.
  - Kubernetes job resource tuning: `JOB_CPU_REQUEST`, `JOB_MEM_REQUEST`, `JOB_EPHEMERAL_REQUEST`, `JOB_CPU_LIMIT`, `JOB_MEM_LIMIT`, `JOB_EPHEMERAL_LIMIT`, `JOB_GPU_LIMIT`.
  - S3 endpoint customization: `ENDPOINT_URL`, `S3_ENDPOINT`.
2. YAML file (optional) at `/app/config/pipeline.yaml` or path specified by `PIPELINE_CONFIG`
3. Embedded safe defaults (`prefix = ephys` and no bucket until provided)

### Usage in Code
Import helpers from `Services/common/config.py`:
```python
from Services.common.config import load_config, s3_uri
cfg = load_config()
root = cfg.root()  # e.g. s3://my-bucket/ephys/
data_path = s3_uri('2025-01-01-e-example','original','data','rec0000.raw.h5')
derived_path = s3_uri('2025-01-01-e-example','derived','kilosort2')
```

### Overriding at Runtime
Docker / Kubernetes examples:
```bash
docker run -e S3_BUCKET=ucdavis-neural -e S3_PREFIX=ephys \
  -e NRP_NAMESPACE=ucdavis-neural-lab \
  -e SERVICE_BUCKET=s3://ucdavis-neural/services/mqtt_job_listener \
  -e PARAMETER_BUCKET=s3://ucdavis-neural/services/mqtt_job_listener/params \
  -e FLUIDICS_BUCKET=s3://ucdavis-neural/fluidics/ \
  -e INTEGRATED_BUCKET=s3://ucdavis-neural/integrated/ \
  -e SERVICE_ROOT=s3://ucdavis-neural/services/mqtt_job_listener \
  -e KILOSORT_IMAGE=surygeng/kilosort_docker:v0.3 \
  -e JOB_CPU_REQUEST=12 -e JOB_MEM_REQUEST=24Gi -e JOB_GPU_LIMIT=1 \
  surygeng/kilosort_docker:v0.2 python kilosort2_simplified.py ...
```
```yaml
env:
  - name: S3_BUCKET
    value: ucdavis-neural
  - name: S3_PREFIX
    value: ephys
  - name: NRP_NAMESPACE
    value: ucdavis-neural-lab
  - name: SERVICE_BUCKET
    value: s3://ucdavis-neural/services/mqtt_job_listener
  - name: PARAMETER_BUCKET
    value: s3://ucdavis-neural/services/mqtt_job_listener/params
  - name: FLUIDICS_BUCKET
    value: s3://ucdavis-neural/fluidics/
  - name: INTEGRATED_BUCKET
    value: s3://ucdavis-neural/integrated/
  - name: AWS_REGION
    value: us-west-2
```

Optional YAML file (`pipeline.yaml`):
```yaml
bucket: ucdavis-neural
prefix: ephys
input_prefix: ephys/raw
output_prefix: ephys/derived
region: us-west-2
```

### Path Construction Best Practice
Never hardcode `s3://braingeneers/ephys/`. Always build with `cfg.s3_uri()` or `s3_uri()` helper.

### Credentials
Standard AWS env vars (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) are supported implicitly via the AWS SDK chain.

### Validation
On first import the config layer logs resolved values:
`[pipeline-config] bucket=ucdavis-neural prefix=ephys input=None output=None`

### Testing
Automated test `Services/tests/test_no_hardcoded_bucket.py` ensures no forbidden hardcoded bucket string remains in code.
Optional future test can assert namespace externalization (no direct `NAMESPACE = 'braingeneers'` constants) now that `NRP_NAMESPACE` is supported.

### Migration Notes
Legacy references to `DEFAULT_BUCKET` now use the configuration layer but maintain backward compatibility if config is absent.

## Kubernetes Deployment Configuration

When running in Kubernetes, dynamic S3 settings are provided via a ConfigMap instead of embedding credentials in code.

### Sample ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ephys-config
  namespace: braingeneers
data:
  S3_BUCKET: ucdavis-neural
  S3_PREFIX: ephys
  AWS_ACCESS_KEY_ID: your-access-key
  AWS_SECRET_ACCESS_KEY: your-secret-key
  ENDPOINT_URL: https://s3.braingeneers.gi.ucsc.edu
```
    }
  ]
}
```

### Programmatic Injection
The listener reads the ConfigMap via the Kubernetes API (`k8s_config.load_s3_settings`) and injects `S3_BUCKET` / `S3_PREFIX` env vars into each job's container spec dynamically.

### Local Development Fallback
If the ConfigMap or API is unavailable, environment variables are used. If neither set, code falls back to a default prefix (`ephys`) and bucket must be supplied before S3 operations.

### Rotation & Updates
Updating the ConfigMap updates all future jobs immediately. Long‑lived deployments can periodically re-read or watch for changes if hot reload is needed.



## Algorithm Path Contract and Helpers

To keep containerized algorithms consistent without tight coupling, we use a simple path contract and tiny helper functions.

Contract:
- Inputs live under `<session_uuid>/original/data/...`.
- Outputs live under `<session_uuid>/derived/<stage>/...`.
- Filenames use a base name plus a suffix indicating artifact type.

Common suffixes:
- `_phy.zip` — raw spike sorting output
- `_acqm.zip` — auto-curated spike data
- `_figure.zip` — visualization bundle
- `_conn.zip` — connectivity results

Helpers in `Services/common/path_utils.py`:
- `replace_original_to_derived(base_path, stage)` — swap `original/data` with `derived/<stage>`.
- `normalize_acqm_source(input_path)` — normalize `.raw.h5` / `.h5` inputs to `_acqm.zip`.
- `make_artifact_path(session_uuid, stage, basename, suffix, subdir=None)` — assemble canonical output paths.

These helpers are pure and dependency-free, safe to vendor or pin per container image. Several algorithms now adopt them to reduce drift.
