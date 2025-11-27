# EphysPipeline Deployment Guide

Complete guide for deploying EphysPipeline in any environment - from desktop to enterprise cloud.

## Choose Your Deployment Scenario

### 🖥️ Desktop/Laptop (Quickest)
**Best for:** First-time users, small labs, development, testing

**Time to deploy:** 5 minutes

**See:** [QUICK_START.md](QUICK_START.md)

---

### 🖧 Server (Recommended for Teams)
**Best for:** Lab servers, shared access, persistent deployment

**Time to deploy:** 15-30 minutes

**See:** [Server Deployment](#server-deployment) below

---

### 🏢 Custom Docker Registry
**Best for:** Institutions wanting full control, custom modifications

**Time to deploy:** 1-2 hours

**See:** [CUSTOM_BUILD_GUIDE.md](CUSTOM_BUILD_GUIDE.md)

---

### ☁️ Kubernetes/Cloud
**Best for:** Large-scale, high-availability, multi-institution

**Time to deploy:** 2-4 hours

**See:** [Kubernetes Deployment](#kubernetes-deployment) below

---

## Prerequisites (All Deployments)

### Required
- Docker and Docker Compose (or Kubernetes)
- Internet connection
- AWS credentials for S3 access
- S3 bucket name

### Recommended
- Basic understanding of Docker
- Familiarity with command line
- Text editor

---

## Server Deployment

Deploy EphysPipeline on a Linux server for team access.

### System Requirements

**Minimum:**
- Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- 8 GB RAM
- 50 GB free disk space
- 4 CPU cores
- Static IP or hostname

**Recommended:**
- 16+ GB RAM
- 100+ GB SSD storage
- 8+ CPU cores
- Dedicated server or VM

### Step 1: Install Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

Verify installation:
```bash
docker --version
docker-compose --version
```

### Step 2: Clone Repository

```bash
git clone https://github.com/braingeneers/EphysPipeline.git
cd EphysPipeline
```

### Step 3: Configure S3 Access

**Option A: AWS Credentials File (Recommended)**

```bash
mkdir -p ~/.aws
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
EOF

chmod 600 ~/.aws/credentials
```

**Option B: IAM Instance Role (EC2 Only)**

If running on EC2, attach an IAM role with S3 access. No credentials file needed.

**Option C: Environment Variables**

```bash
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
```

### Step 4: Create Configuration

```bash
cat > pipeline.yaml << EOF
bucket: your-institution-bucket
prefix: ephys
region: us-west-2
EOF
```

Customize the values for your institution.

### Step 5: Configure Firewall

Allow access to the dashboard port:

```bash
# Ubuntu/Debian with ufw
sudo ufw allow 8050/tcp

# CentOS/RHEL with firewalld
sudo firewall-cmd --permanent --add-port=8050/tcp
sudo firewall-cmd --reload
```

### Step 6: Start Services

```bash
docker-compose up -d
```

Check status:
```bash
docker-compose ps
docker-compose logs -f
```

### Step 7: Access Dashboard

From any computer on your network:
```
http://server-ip-address:8050
```

Example:
```
http://192.168.1.100:8050
http://lab-server.university.edu:8050
```

### Managing the Deployment

**View logs:**
```bash
docker-compose logs -f dashboard
```

**Restart services:**
```bash
docker-compose restart
```

**Stop services:**
```bash
docker-compose down
```

**Update to latest version:**
```bash
git pull
docker-compose pull
docker-compose up -d
```

**Check resource usage:**
```bash
docker stats
```

### Automatic Startup on Boot

Create a systemd service:

```bash
sudo cat > /etc/systemd/system/ephys-pipeline.service << EOF
[Unit]
Description=EphysPipeline Services
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/EphysPipeline
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=your-username

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ephys-pipeline
sudo systemctl start ephys-pipeline
```

---

## Kubernetes Deployment

For production environments requiring high availability and scalability.

### Prerequisites

- Kubernetes cluster (EKS, GKE, AKS, or self-hosted)
- kubectl configured to access your cluster
- Helm (optional, but recommended)

### Step 1: Create Namespace

```bash
kubectl create namespace ephys-pipeline
```

### Step 2: Create ConfigMap

```bash
cat > pipeline-config.yaml << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: pipeline-config
  namespace: ephys-pipeline
data:
  pipeline.yaml: |
    bucket: your-institution-bucket
    prefix: ephys
    region: us-west-2
EOF

kubectl apply -f pipeline-config.yaml
```

### Step 3: Create Secret for AWS Credentials

```bash
kubectl create secret generic aws-credentials \
  --namespace ephys-pipeline \
  --from-file=credentials=$HOME/.aws/credentials \
  --from-file=config=$HOME/.aws/config
```

Or for specific keys:
```bash
kubectl create secret generic aws-credentials \
  --namespace ephys-pipeline \
  --from-literal=AWS_ACCESS_KEY_ID=your-key \
  --from-literal=AWS_SECRET_ACCESS_KEY=your-secret
```

### Step 4: Deploy Dashboard

```bash
cat > dashboard-deployment.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dashboard
  namespace: ephys-pipeline
spec:
  replicas: 1
  selector:
    matchLabels:
      app: dashboard
  template:
    metadata:
      labels:
        app: dashboard
    spec:
      containers:
      - name: dashboard
        image: surygeng/maxwell_dashboard:latest
        ports:
        - containerPort: 8050
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
        - name: aws-credentials
          mountPath: /root/.aws
          readOnly: true
        env:
        - name: AWS_REGION
          value: "us-west-2"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
      volumes:
      - name: config
        configMap:
          name: pipeline-config
      - name: aws-credentials
        secret:
          secretName: aws-credentials
---
apiVersion: v1
kind: Service
metadata:
  name: dashboard
  namespace: ephys-pipeline
spec:
  selector:
    app: dashboard
  ports:
  - port: 8050
    targetPort: 8050
  type: LoadBalancer
EOF

kubectl apply -f dashboard-deployment.yaml
```

### Step 5: Access Dashboard

Get the external IP:
```bash
kubectl get service dashboard -n ephys-pipeline
```

Access at:
```
http://<EXTERNAL-IP>:8050
```

### Ingress Setup (Optional)

For domain name access with HTTPS:

```bash
cat > ingress.yaml << EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dashboard-ingress
  namespace: ephys-pipeline
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - ephys.your-domain.com
    secretName: dashboard-tls
  rules:
  - host: ephys.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: dashboard
            port:
              number: 8050
EOF

kubectl apply -f ingress.yaml
```

---

## Docker Compose Files

The repository includes different compose files for different scenarios:

### `docker-compose.yml` (Default)
Uses pre-built images from Docker Hub. Best for quick start and desktop use.

```bash
docker-compose up
```

### `docker-compose.custom.yml` (Custom Registry)
Builds images locally and uses your custom registry.

```bash
docker-compose -f docker-compose.custom.yml up --build
```

### `docker-compose.prod.yml` (Production)
Production-ready configuration with resource limits, health checks, and restart policies.

```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## Configuration Files

All deployments share the same configuration format.

### Minimal Configuration
```yaml
bucket: your-bucket
prefix: ephys
```

### Full Configuration
```yaml
bucket: your-institution-bucket
prefix: ephys
input_prefix: raw-recordings
output_prefix: processed-results
region: us-west-2
profile: default
```

See [Services/common/CONFIG_USAGE_GUIDE.md](Services/common/CONFIG_USAGE_GUIDE.md) for all options.

---

## Security Considerations

### Network Security
- Use firewall rules to restrict access
- Consider VPN for remote access
- Use HTTPS with proper certificates (Kubernetes Ingress)
- Don't expose to public internet without authentication

### AWS Security
- Use IAM roles instead of access keys when possible
- Follow principle of least privilege
- Enable S3 bucket encryption
- Use separate IAM users for different environments
- Rotate credentials regularly

### Docker Security
- Run containers as non-root user (where possible)
- Keep Docker and images up to date
- Scan images for vulnerabilities
- Use secrets management for sensitive data

---

## Monitoring and Logging

### View Logs (Docker Compose)
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f dashboard

# Last 100 lines
docker-compose logs --tail=100 dashboard
```

### View Logs (Kubernetes)
```bash
# Get pods
kubectl get pods -n ephys-pipeline

# View logs
kubectl logs -f <pod-name> -n ephys-pipeline

# Stream logs from all pods
kubectl logs -f -l app=dashboard -n ephys-pipeline
```

### Resource Monitoring
```bash
# Docker
docker stats

# Kubernetes
kubectl top pods -n ephys-pipeline
kubectl top nodes
```

---

## Backup and Disaster Recovery

### What to Backup
1. **Configuration files**
   - `pipeline.yaml`
   - `docker-compose.yml` (if modified)
   - Environment variable files

2. **AWS credentials** (encrypted)
   - `~/.aws/credentials`
   - `~/.aws/config`

3. **Custom code** (if modified)
   - Any changes to source code
   - Custom Docker images

### Backup S3 Configuration

The pipeline itself doesn't store data - everything is in S3. Ensure you have:
- S3 versioning enabled
- S3 backup/replication strategy
- Regular S3 bucket snapshots

### Disaster Recovery

To recover from server failure:

1. Install Docker on new server
2. Clone repository
3. Restore `pipeline.yaml` and credentials
4. Run `docker-compose up -d`

Total recovery time: ~10 minutes

---

## Troubleshooting

### Container Won't Start

Check logs:
```bash
docker-compose logs dashboard
```

Common issues:
- Missing configuration file
- Invalid AWS credentials
- Port already in use
- Insufficient resources

### Cannot Access Dashboard

1. Check container is running:
   ```bash
   docker-compose ps
   ```

2. Check firewall:
   ```bash
   sudo ufw status  # Ubuntu
   sudo firewall-cmd --list-ports  # CentOS
   ```

3. Test locally first:
   ```bash
   curl http://localhost:8050
   ```

### S3 Access Denied

1. Verify credentials:
   ```bash
   aws s3 ls s3://your-bucket/
   ```

2. Check IAM permissions

3. Verify bucket name in config

### High Resource Usage

Limit resources in docker-compose.yml:
```yaml
services:
  dashboard:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

---

## Performance Tuning

### For Small Datasets (< 1TB)
- 4 CPU cores
- 8 GB RAM
- Standard storage

### For Medium Datasets (1-10TB)
- 8 CPU cores
- 16 GB RAM
- SSD storage

### For Large Datasets (> 10TB)
- 16+ CPU cores
- 32+ GB RAM
- NVMe SSD storage
- Consider Kubernetes for scaling

---

## Upgrading

### Minor Updates
```bash
git pull
docker-compose pull
docker-compose up -d
```

### Major Updates
1. Read release notes
2. Backup configuration
3. Test in development first
4. Update production

### Rolling Back
```bash
git checkout <previous-version>
docker-compose pull
docker-compose up -d
```

---

## Getting Help

- **Quick Start Issues:** [QUICK_START.md](QUICK_START.md)
- **Configuration Help:** [Services/common/CONFIG_USAGE_GUIDE.md](Services/common/CONFIG_USAGE_GUIDE.md)
- **Custom Builds:** [CUSTOM_BUILD_GUIDE.md](CUSTOM_BUILD_GUIDE.md)
- **GitHub Issues:** https://github.com/braingeneers/EphysPipeline/issues
- **Slack:** #braingeneers-helpdesk channel

---

## Next Steps

After deployment:
1. Process a test dataset
2. Configure job parameters
3. Set up monitoring
4. Document your setup
5. Train team members

---

**Deployment complete!** 🎉 Your EphysPipeline is ready for production use.
