# SpikeCanvas Services - Standalone Deployment Guide

This guide helps you deploy the SpikeCanvas services (Maxwell Dashboard, Spike Sorting Listener, and Job Scanner) in your own lab environment.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Detailed Setup](#detailed-setup)
5. [Configuration](#configuration)
6. [Service Architecture](#service-architecture)
7. [Troubleshooting](#troubleshooting)
8. [Production Deployment](#production-deployment)

## Overview

The SpikeCanvas services provide a complete web-based interface for managing electrophysiology data analysis pipelines. The system includes:

- **Maxwell Dashboard**: Web UI for job submission and monitoring (port 8050)
- **Spike Sorting Listener**: MQTT-based job orchestration service
- **Job Scanner**: Kubernetes job status monitor
- **MQTT Broker**: Message broker for service communication
- **Redis**: State persistence and caching

## Prerequisites

### Required

1. **Docker and Docker Compose**
   - Docker Engine 20.10+ or Docker Desktop
   - Docker Compose v2.0+
   
   Install: https://docs.docker.com/get-docker/

2. **Kubernetes Cluster Access**
   - A running Kubernetes cluster (local or cloud)
   - `kubectl` configured with cluster access
   - Valid `~/.kube/config` file
   
   Test: `kubectl get nodes`

3. **S3-Compatible Storage**
   - AWS S3, MinIO, Ceph, or similar
   - Access credentials (access key + secret key)
   - A bucket for storing data
   
   Compatible storage options:
   - AWS S3
   - MinIO (open source, self-hosted)
   - Ceph (open source, distributed)
   - Wasabi, DigitalOcean Spaces, etc.

4. **System Resources**
   - 4GB RAM minimum (8GB+ recommended)
   - 10GB disk space for Docker images and volumes
   - Network access to Kubernetes cluster and S3 endpoint

### Optional but Recommended

- Git (for cloning the repository)
- AWS CLI (for testing S3 connectivity)
- `jq` (for JSON processing)
- A text editor (VS Code, Sublime, vim, etc.)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/braingeneers/SpikeCanvas-EphysPipeline.git
cd SpikeCanvas-EphysPipeline
```

### 2. Configure Environment

```bash
# Copy template
cp .env.template .env

# Edit configuration (see Configuration section below)
nano .env  # or use your preferred editor
```

Minimum required configuration in `.env`:
```bash
S3_BUCKET=your-bucket-name
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
NRP_NAMESPACE=default
```

### 3. Verify Kubernetes Access

```bash
# Test kubectl access
kubectl get nodes

# Create namespace if needed
kubectl create namespace your-namespace

# Verify namespace access
kubectl get pods -n your-namespace
```

### 4. Start Services

```bash
# Pull latest images
docker-compose pull

# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 5. Access Dashboard

Open your browser to: **http://localhost:8050**

### 6. View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f dashboard
docker-compose logs -f listener
docker-compose logs -f mqtt
```

## Detailed Setup

### Step 1: S3 Storage Setup

#### Option A: Using AWS S3

1. Create an S3 bucket:
   ```bash
   aws s3 mb s3://my-lab-ephys-data
   ```

2. Create IAM user with S3 access:
   - Go to AWS Console → IAM → Users → Add User
   - Attach policy: `AmazonS3FullAccess` (or create custom policy)
   - Save access key and secret key

3. Configure `.env`:
   ```bash
   S3_BUCKET=my-lab-ephys-data
   AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
   AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCY
   AWS_REGION=us-west-2
   # Leave ENDPOINT_URL commented for AWS S3
   ```

#### Option B: Using MinIO (Self-Hosted)

1. Install MinIO:
   ```bash
   docker run -d \
     -p 9000:9000 \
     -p 9001:9001 \
     --name minio \
     -e "MINIO_ROOT_USER=admin" \
     -e "MINIO_ROOT_PASSWORD=password123" \
     -v ~/minio/data:/data \
     quay.io/minio/minio server /data --console-address ":9001"
   ```

2. Create bucket via MinIO console (http://localhost:9001) or CLI:
   ```bash
   mc alias set myminio http://localhost:9000 admin password123
   mc mb myminio/ephys-data
   ```

3. Configure `.env`:
   ```bash
   S3_BUCKET=ephys-data
   AWS_ACCESS_KEY_ID=admin
   AWS_SECRET_ACCESS_KEY=password123
   AWS_REGION=us-east-1
   ENDPOINT_URL=http://minio:9000
   S3_ENDPOINT=minio:9000
   ```

#### Option C: Using Existing Ceph/Object Storage

Contact your IT department for:
- Bucket name
- Access credentials
- Endpoint URL

Example configuration:
```bash
S3_BUCKET=lab-storage
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
ENDPOINT_URL=https://storage.mylab.edu
S3_ENDPOINT=storage.mylab.edu
```

### Step 2: Kubernetes Setup

#### Option A: Using Existing Cluster

1. Get kubeconfig from your cluster administrator
2. Copy to `~/.kube/config`
3. Test access:
   ```bash
   kubectl get nodes
   kubectl get namespaces
   ```

#### Option B: Local Development with Minikube

1. Install Minikube:
   ```bash
   # macOS
   brew install minikube
   
   # Linux
   curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
   sudo install minikube-linux-amd64 /usr/local/bin/minikube
   ```

2. Start cluster:
   ```bash
   minikube start --memory=8192 --cpus=4
   kubectl get nodes
   ```

3. Configure `.env`:
   ```bash
   NRP_NAMESPACE=default
   ```

#### Option C: Using Cloud Kubernetes (GKE, EKS, AKS)

Follow your cloud provider's guide to:
1. Create a Kubernetes cluster
2. Get kubeconfig credentials
3. Configure kubectl access

For GPU support (Kilosort), ensure your cluster has GPU nodes.

### Step 3: Network Configuration

#### Docker Network

Services communicate via the internal `maxwell-net` bridge network. No external configuration needed.

#### Port Mapping

By default, these ports are exposed on your host:
- `8050`: Dashboard web interface
- `1883`: MQTT broker (MQTT protocol)
- `9001`: MQTT WebSocket
- `6379`: Redis

To change ports, edit `.env`:
```bash
DASHBOARD_PORT=8050
MQTT_PORT=1883
MQTT_WS_PORT=9001
REDIS_PORT=6379
```

#### Firewall Configuration

If deploying on a server, ensure these ports are accessible:
```bash
# Ubuntu/Debian
sudo ufw allow 8050/tcp
sudo ufw allow 1883/tcp

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8050/tcp
sudo firewall-cmd --permanent --add-port=1883/tcp
sudo firewall-cmd --reload
```

### Step 4: Testing the Setup

#### Test S3 Connectivity

```bash
# Using AWS CLI
aws s3 ls s3://your-bucket --endpoint-url https://your-endpoint

# Test from container
docker-compose exec dashboard aws s3 ls s3://your-bucket
```

#### Test Kubernetes Access

```bash
# From host
kubectl get pods -n your-namespace

# From container
docker-compose exec listener kubectl get pods -n your-namespace
```

#### Test MQTT Broker

```bash
# Subscribe to test topic
docker-compose exec mqtt mosquitto_sub -h localhost -t test

# Publish (in another terminal)
docker-compose exec mqtt mosquitto_pub -h localhost -t test -m "Hello"
```

#### Test Dashboard

1. Open http://localhost:8050
2. You should see the SpikeCanvas dashboard
3. Check that S3 browser shows your bucket
4. Try submitting a test job

## Configuration

### Environment Variables Reference

See `.env.template` for complete documentation. Key variables:

#### Required
- `S3_BUCKET`: Your S3 bucket name
- `AWS_ACCESS_KEY_ID`: S3 access key
- `AWS_SECRET_ACCESS_KEY`: S3 secret key
- `NRP_NAMESPACE`: Kubernetes namespace

#### S3 Configuration
- `S3_PREFIX`: Data organization prefix (default: `ephys`)
- `ENDPOINT_URL`: Custom S3 endpoint (omit for AWS)
- `AWS_REGION`: AWS region

#### Service Configuration
- `DASHBOARD_PORT`: Dashboard port (default: `8050`)
- `MQTT_PORT`: MQTT broker port (default: `1883`)
- `REDIS_PORT`: Redis port (default: `6379`)
- `SCAN_INTERVAL`: Job scan frequency in seconds (default: `60`)

#### Container Images
- `KILOSORT_IMAGE`: Spike sorting container
- `CURATION_IMAGE`: Quality control container
- `CONNECTIVITY_IMAGE`: Connectivity analysis container
- `VISUALIZATION_IMAGE`: Visualization container
- `LFP_IMAGE`: LFP analysis container

### Custom Parameters

Algorithm parameters are stored in S3 at:
```
s3://bucket/services/mqtt_job_listener/params/
```

To customize:
1. Upload your parameter JSON files to this location
2. Reference them in the dashboard when submitting jobs

See `Services/parameters/` directory for templates.

## Service Architecture

### Component Diagram

```
┌─────────────────┐
│   Web Browser   │
└────────┬────────┘
         │ HTTP :8050
         │
┌────────▼────────────────────────────────────────┐
│           Maxwell Dashboard                     │
│  - Job submission UI                            │
│  - S3 data browser                              │
│  - Job monitoring                               │
└────────┬───────────────────┬────────────────────┘
         │                   │
         │ MQTT              │ S3 API
         │ :1883             │
┌────────▼────────┐   ┌──────▼──────┐
│  MQTT Broker    │   │  S3 Storage │
│  (Mosquitto)    │   │             │
└────────┬────────┘   └──────▲──────┘
         │                   │
         │ MQTT              │ S3 API
         │                   │
┌────────▼────────────────────┼────────────────────┐
│    Spike Sorting Listener   │                    │
│  - Listens for job requests │                    │
│  - Creates Kubernetes jobs  │                    │
│  - Tracks job progress      │                    │
└────────┬────────────────────┴────────────────────┘
         │
         │ Kubernetes API
         │
┌────────▼────────────────────────────────────────┐
│         Kubernetes Cluster                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │Kilosort  │  │Curation  │  │Connectivity│    │
│  │   Job    │  │   Job    │  │   Job     │     │
│  └──────────┘  └──────────┘  └──────────┘     │
└────────▲────────────────────────────────────────┘
         │
         │ Kubernetes API
         │
┌────────┴────────┐
│  Job Scanner    │
│  - Monitors jobs│
│  - Updates MQTT │
└─────────────────┘
```

### Data Flow

1. **Job Submission**:
   - User submits job via Dashboard
   - Dashboard publishes MQTT message to topic `jobs/{job_id}/request`

2. **Job Orchestration**:
   - Listener receives MQTT message
   - Listener creates Kubernetes Job with appropriate container image
   - Job runs on Kubernetes cluster
   - Job reads input from S3
   - Job writes output to S3

3. **Job Monitoring**:
   - Scanner polls Kubernetes API for job status
   - Scanner publishes status updates to MQTT topic `jobs/{job_id}/status`
   - Dashboard subscribes to status updates and displays progress

4. **Results Retrieval**:
   - When job completes, results are in S3
   - Dashboard provides links to download/visualize results
   - Next job in pipeline can be triggered automatically

### MQTT Topics

```
jobs/{job_id}/request   - Job submission requests
jobs/{job_id}/status    - Job status updates
jobs/{job_id}/results   - Job completion notifications
jobs/{job_id}/error     - Job error messages
system/health           - Service health checks
```

### S3 Structure

```
s3://bucket/
├── ephys/                          # Data prefix (S3_PREFIX)
│   ├── original/                   # Raw data
│   │   ├── data/                   # 6-well recordings
│   │   └── split/                  # Individual wells
│   ├── derived/                    # Processed data
│   │   ├── kilosort2/              # Spike sorting results
│   │   ├── curated/                # QC-filtered results
│   │   ├── connectivity/           # Connectivity analysis
│   │   ├── lfp/                    # LFP analysis
│   │   └── visualization/          # Plots and figures
└── services/                       # Service data
    └── mqtt_job_listener/          # Listener state
        ├── listener.log            # Job logs
        ├── csvs/                   # Job tracking CSVs
        └── params/                 # Algorithm parameters
```

## Troubleshooting

### Common Issues

#### 1. Services Won't Start

**Error**: `ERROR: Cannot connect to Docker daemon`
```bash
# Solution: Ensure Docker is running
sudo systemctl start docker  # Linux
# or restart Docker Desktop
```

**Error**: `port is already allocated`
```bash
# Solution: Change port in .env or stop conflicting service
# Check what's using the port:
sudo lsof -i :8050
# Kill the process or change DASHBOARD_PORT in .env
```

#### 2. Dashboard Can't Connect to S3

**Error**: `NoSuchBucket` or `AccessDenied`
```bash
# Solution: Verify bucket exists and credentials are correct
aws s3 ls s3://your-bucket --endpoint-url https://your-endpoint

# Check logs:
docker-compose logs dashboard | grep -i s3
```

**Error**: `Could not connect to the endpoint URL`
```bash
# Solution: Check ENDPOINT_URL in .env
# For AWS S3: Comment out ENDPOINT_URL
# For custom S3: Verify URL is correct and accessible
curl https://your-endpoint
```

#### 3. Kubernetes Jobs Not Starting

**Error**: `Error from server (Forbidden): namespaces "xxx" is forbidden`
```bash
# Solution: Verify namespace exists and you have access
kubectl get namespaces
kubectl create namespace your-namespace
```

**Error**: `Failed to pull image`
```bash
# Solution: Verify container images are accessible
docker pull surygeng/kilosort_docker:v0.2

# Or use custom registry:
# Update *_IMAGE variables in .env
```

#### 4. MQTT Connection Issues

**Error**: `Connection refused`
```bash
# Solution: Ensure MQTT container is running
docker-compose ps mqtt
docker-compose logs mqtt

# Restart if needed:
docker-compose restart mqtt
```

#### 5. Redis Connection Issues

```bash
# Check Redis is running:
docker-compose ps redis
docker-compose logs redis

# Test connection:
docker-compose exec redis redis-cli ping
# Should return: PONG
```

### Debugging Commands

```bash
# View all container logs
docker-compose logs --tail=100

# Check container resource usage
docker stats

# Inspect container
docker-compose exec dashboard bash
docker-compose exec listener bash

# View container environment variables
docker-compose exec dashboard env

# Test network connectivity
docker-compose exec dashboard ping mqtt.local
docker-compose exec listener curl -I http://dashboard:8050

# Verify volumes
docker volume ls
docker volume inspect maxwell_mqtt-data

# Restart specific service
docker-compose restart dashboard

# Rebuild service after code changes
docker-compose up -d --build dashboard

# View Docker Compose configuration
docker-compose config
```

### Log Locations

- Dashboard logs: `docker-compose logs dashboard`
- Listener logs: `docker-compose logs listener` or `./listener-logs/`
- Scanner logs: `docker-compose logs scanner`
- MQTT logs: `./mosquitto/log/mosquitto.log`
- Redis logs: `docker-compose logs redis`

### Getting Help

1. Check logs: `docker-compose logs -f [service]`
2. Verify configuration: `docker-compose config`
3. Test components individually (see Testing section)
4. Check GitHub Issues: https://github.com/braingeneers/SpikeCanvas-EphysPipeline/issues
5. Consult documentation: https://github.com/braingeneers/SpikeCanvas-EphysPipeline

## Production Deployment

### Security Hardening

#### 1. Enable MQTT Authentication

See `mosquitto/config/README.md` for detailed instructions.

```bash
# Create password file
docker-compose exec mqtt mosquitto_passwd -c /mosquitto/config/passwords.txt admin

# Edit mosquitto.conf:
allow_anonymous false
password_file /mosquitto/config/passwords.txt

# Restart MQTT
docker-compose restart mqtt
```

Update services to use credentials:
```bash
# In .env:
MQTT_USERNAME=listener
MQTT_PASSWORD=secure-password
```

#### 2. Enable Redis Password

```bash
# Generate secure password
PASSWORD=$(openssl rand -base64 32)

# Update docker-compose.yml:
redis:
  command: redis-server --requirepass $PASSWORD

# Update .env:
REDIS_PASSWORD=$PASSWORD
```

#### 3. Use SSL/TLS

For MQTT:
- Generate SSL certificates (see mosquitto/config/README.md)
- Configure mosquitto.conf with SSL settings
- Expose port 8883 for MQTT over TLS

For Dashboard:
- Use reverse proxy (nginx, traefik)
- Obtain SSL certificate (Let's Encrypt)
- Configure HTTPS

#### 4. Secure AWS Credentials

Best practices:
- Use IAM roles instead of access keys when possible
- Use AWS Secrets Manager for credentials
- Rotate credentials regularly
- Set minimal IAM permissions (principle of least privilege)

#### 5. File Permissions

```bash
# Secure environment file
chmod 600 .env

# Secure kubeconfig
chmod 600 ~/.kube/config

# Secure AWS credentials
chmod 600 ~/.aws/credentials
```

### High Availability

#### 1. External MQTT Broker

Use managed MQTT service:
- AWS IoT Core
- HiveMQ Cloud
- Azure IoT Hub

Update `.env`:
```bash
MQTT_BROKER=your-mqtt-broker.cloud
MQTT_PORT=8883
MQTT_USERNAME=your-username
MQTT_PASSWORD=your-password
```

Comment out `mqtt` service in docker-compose.yml.

#### 2. External Redis

Use managed Redis:
- AWS ElastiCache
- Redis Cloud
- Azure Cache for Redis

Update `.env`:
```bash
REDIS_HOST=your-redis-instance.cloud
REDIS_PORT=6379
REDIS_PASSWORD=your-password
```

Comment out `redis` service in docker-compose.yml.

#### 3. Deploy on Kubernetes

For production-grade high availability, deploy services on Kubernetes:

1. Create Kubernetes manifests from docker-compose:
   ```bash
   kompose convert
   ```

2. Add health checks, resource limits, and autoscaling:
   ```yaml
   resources:
     requests:
       cpu: "500m"
       memory: "1Gi"
     limits:
       cpu: "2"
       memory: "4Gi"
   ```

3. Configure horizontal pod autoscaling:
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: dashboard
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: dashboard
     minReplicas: 2
     maxReplicas: 10
   ```

### Monitoring and Alerting

#### 1. Prometheus Metrics

Add Prometheus exporters:
```yaml
# In docker-compose.yml
prometheus:
  image: prom/prometheus
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
  depends_on:
    - prometheus
```

#### 2. Log Aggregation

Use ELK stack or Grafana Loki:
```yaml
loki:
  image: grafana/loki
  ports:
    - "3100:3100"

promtail:
  image: grafana/promtail
  volumes:
    - /var/log:/var/log
```

#### 3. Health Checks

Configure uptime monitoring:
- UptimeRobot
- Pingdom
- StatusCake

Monitor these endpoints:
- `http://your-server:8050` (Dashboard)
- `tcp://your-server:1883` (MQTT)

### Backup and Recovery

#### 1. Data Backup

Your data is in S3, which should have:
- Versioning enabled
- Cross-region replication
- Lifecycle policies

```bash
# Enable S3 versioning
aws s3api put-bucket-versioning \
  --bucket your-bucket \
  --versioning-configuration Status=Enabled
```

#### 2. Configuration Backup

Backup these files regularly:
- `.env` (credentials)
- `docker-compose.yml`
- `~/.kube/config`
- `mosquitto/config/`
- Custom parameter files

```bash
# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups/spikecanvas/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR
cp .env $BACKUP_DIR/
cp docker-compose.yml $BACKUP_DIR/
cp -r mosquitto/config $BACKUP_DIR/
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
```

#### 3. State Backup

Export Redis and MQTT state:
```bash
# Redis backup
docker-compose exec redis redis-cli SAVE
docker cp maxwell-redis:/data/dump.rdb ./backup/

# MQTT retained messages
docker-compose exec mqtt mosquitto_sub -h localhost -t '#' -v > mqtt_backup.txt
```

### Scaling Recommendations

#### Small Lab (< 10 users)
- Current docker-compose setup is sufficient
- 1 instance of each service
- Local MQTT and Redis

#### Medium Lab (10-50 users)
- Deploy services on Kubernetes
- 2-3 replicas of dashboard
- External managed MQTT and Redis
- Load balancer for dashboard

#### Large Lab (50+ users)
- Full Kubernetes deployment
- Horizontal pod autoscaling
- Dedicated database for job tracking
- CDN for static assets
- Multi-region deployment

## Next Steps

1. **Explore the Dashboard**: Submit test jobs, browse S3 data
2. **Customize Parameters**: Upload custom algorithm parameters to S3
3. **Integrate with Your Workflow**: Set up automated data pipelines
4. **Monitor Performance**: Check job completion times and resource usage
5. **Scale as Needed**: Move to external MQTT/Redis or Kubernetes deployment

## Additional Resources

- **Documentation**: https://github.com/braingeneers/SpikeCanvas-EphysPipeline
- **Paper**: [Multiscale Cloud-Based Pipeline for Neuronal Electrophysiology Analysis](https://www.biorxiv.org/content/10.1101/2024.11.14.623530v2)
- **Docker Documentation**: https://docs.docker.com/
- **Kubernetes Documentation**: https://kubernetes.io/docs/
- **MQTT Documentation**: https://mqtt.org/
- **AWS S3 Documentation**: https://docs.aws.amazon.com/s3/

## Support

For issues, questions, or contributions:
- **GitHub Issues**: https://github.com/braingeneers/SpikeCanvas-EphysPipeline/issues
- **Email**: braingeneers-admins-group@ucsc.edu (for Braingeneers users)

---

**Last Updated**: December 2024
**Version**: 1.0
**Maintainers**: Braingeneers Team, UC Santa Cruz
