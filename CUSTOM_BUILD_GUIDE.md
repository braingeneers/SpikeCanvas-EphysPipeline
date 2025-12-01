# Custom Build Guide

Build and deploy EphysPipeline using your own Docker registry instead of pre-built images.

## When to Use This Guide

Use custom builds when you need:
-  Full control over Docker images
-  Custom code modifications
-  Your own Docker registry (not Docker Hub)
-  Air-gapped or restricted environments
-  Compliance requirements
-  Custom base images or dependencies

For quick deployment with pre-built images, see [QUICK_START.md](QUICK_START.md) instead.

## Prerequisites

- Docker installed
- Docker Compose installed
- Access to a Docker registry (Docker Hub, AWS ECR, Google GCR, or private registry)
- Registry credentials configured
- 20+ GB free disk space for building

## Overview

The custom build process:
1. Configure your Docker registry
2. Build all service images locally
3. Tag images with your registry
4. Push images to your registry
5. Deploy using your custom images

## Step 1: Configure Docker Registry

### Option A: Docker Hub (Public or Private)

```bash
# Login to Docker Hub
docker login

# Set registry variables
export REGISTRY="your-dockerhub-username"
export TAG="latest"
```

### Option B: AWS ECR

```bash
# Login to ECR
aws ecr get-login-password --region us-west-2 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.us-west-2.amazonaws.com

# Set registry variables
export REGISTRY="123456789012.dkr.ecr.us-west-2.amazonaws.com/ephys"
export TAG="latest"
```

### Option C: Google Container Registry (GCR)

```bash
# Configure Docker for GCR
gcloud auth configure-docker

# Set registry variables
export REGISTRY="gcr.io/your-project-id/ephys"
export TAG="latest"
```

### Option D: Private Registry

```bash
# Login to your private registry
docker login registry.yourcompany.com

# Set registry variables
export REGISTRY="registry.yourcompany.com/ephys"
export TAG="latest"
```

## Step 2: Build All Images

### Using the Build Script (Recommended)

Create a build script:

```bash
cat > build-all.sh << 'EOF'
#!/bin/bash
set -e

# Configuration
REGISTRY="${REGISTRY:-localhost}"
TAG="${TAG:-latest}"

echo "Building all EphysPipeline images..."
echo "Registry: $REGISTRY"
echo "Tag: $TAG"
echo ""

# Build Dashboard
echo "Building Dashboard..."
docker build \
  -f Services/MaxWell_Dashboard/docker/Dockerfile \
  -t ${REGISTRY}/maxwell_dashboard:${TAG} \
  Services/MaxWell_Dashboard

# Build Job Scanner (if exists)
if [ -d "Services/job_scanner/docker" ]; then
  echo "Building Job Scanner..."
  docker build \
    -f Services/job_scanner/docker/Dockerfile \
    -t ${REGISTRY}/job_scanner:${TAG} \
    Services/job_scanner
fi

# Build MQTT Listener (if exists)
if [ -d "Services/Spike_Sorting_Listener/docker" ]; then
  echo "Building MQTT Listener..."
  docker build \
    -f Services/Spike_Sorting_Listener/docker/Dockerfile \
    -t ${REGISTRY}/mqtt_listener:${TAG} \
    Services/Spike_Sorting_Listener
fi

echo ""
echo "Build complete!"
echo ""
echo "Images built:"
docker images | grep -E "${REGISTRY}/(maxwell_dashboard|job_scanner|mqtt_listener)"
EOF

chmod +x build-all.sh
```

Run the build:

```bash
export REGISTRY="your-registry"
export TAG="v1.0"
./build-all.sh
```

### Manual Build (Dashboard Only)

If you only need the dashboard:

```bash
cd Services/MaxWell_Dashboard

docker build \
  -f docker/Dockerfile \
  -t your-registry/maxwell_dashboard:v1.0 \
  .
```

### Build Options

**Use build cache for faster builds:**
```bash
docker build --cache-from=${REGISTRY}/maxwell_dashboard:latest ...
```

**Build without cache (clean build):**
```bash
docker build --no-cache ...
```

**Multi-architecture build:**
```bash
docker buildx build --platform linux/amd64,linux/arm64 ...
```

## Step 3: Test Images Locally

Before pushing, test locally:

```bash
# Test dashboard
docker run --rm \
  -e S3_BUCKET=test-bucket \
  -p 8050:8050 \
  ${REGISTRY}/maxwell_dashboard:${TAG}
```

Access `http://localhost:8050` to verify it works.

## Step 4: Push Images to Registry

### Using the Push Script

```bash
cat > push-all.sh << 'EOF'
#!/bin/bash
set -e

REGISTRY="${REGISTRY:-localhost}"
TAG="${TAG:-latest}"

echo "Pushing images to registry..."
echo "Registry: $REGISTRY"
echo "Tag: $TAG"
echo ""

# Push Dashboard
echo "Pushing Dashboard..."
docker push ${REGISTRY}/maxwell_dashboard:${TAG}

# Push Job Scanner (if built)
if docker images | grep -q "${REGISTRY}/job_scanner"; then
  echo "Pushing Job Scanner..."
  docker push ${REGISTRY}/job_scanner:${TAG}
fi

# Push MQTT Listener (if built)
if docker images | grep -q "${REGISTRY}/mqtt_listener"; then
  echo "Pushing MQTT Listener..."
  docker push ${REGISTRY}/mqtt_listener:${TAG}
fi

echo ""
echo "Push complete!"
EOF

chmod +x push-all.sh
```

Run the push:

```bash
./push-all.sh
```

### Manual Push

```bash
docker push ${REGISTRY}/maxwell_dashboard:${TAG}
```

## Step 5: Create Custom Docker Compose File

Create `docker-compose.custom.yml`:

```yaml
version: '3.8'

services:
  dashboard:
    image: ${REGISTRY}/maxwell_dashboard:${TAG:-latest}
    container_name: ephys-dashboard
    ports:
      - "8050:8050"
    volumes:
      - ./pipeline.yaml:/app/config/pipeline.yaml:ro
      - ~/.aws:/root/.aws:ro
    environment:
      - AWS_REGION=${AWS_REGION:-us-west-2}
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

  # Add other services as needed
  # job_scanner:
  #   image: ${REGISTRY}/job_scanner:${TAG:-latest}
  #   ...

  # mqtt_listener:
  #   image: ${REGISTRY}/mqtt_listener:${TAG:-latest}
  #   ...
```

## Step 6: Deploy with Custom Images

```bash
# Set registry and tag
export REGISTRY="your-registry"
export TAG="v1.0"

# Deploy
docker-compose -f docker-compose.custom.yml up -d
```

## Advanced: Multi-Stage Builds

For smaller images, use multi-stage builds. Edit `Services/MaxWell_Dashboard/docker/Dockerfile`:

```dockerfile
# Build stage
FROM python:3.10 as builder
WORKDIR /build
COPY docker/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.10-slim
WORKDIR /app

# Copy only the dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application
COPY src/ /app
# ... rest of Dockerfile
```

Rebuild with the optimized Dockerfile.

## Customizing Images

### Add Custom Dependencies

Edit `Services/MaxWell_Dashboard/docker/requirements.txt`:

```txt
# Add your custom packages
dash>=2.14.0
plotly>=5.17.0
your-custom-package>=1.0.0
```

Rebuild:

```bash
./build-all.sh
```

### Modify Source Code

1. Make changes to files in `Services/MaxWell_Dashboard/src/`
2. Rebuild the image:
   ```bash
   ./build-all.sh
   ```
3. Test locally
4. Push to registry:
   ```bash
   ./push-all.sh
   ```

### Use Custom Base Image

Edit Dockerfile:

```dockerfile
# Instead of:
FROM python:3.10

# Use your base image:
FROM your-registry/python:3.10-custom
```

## Version Tagging Strategy

### Development
```bash
export TAG="dev"
./build-all.sh
./push-all.sh
```

### Staging
```bash
export TAG="staging-$(date +%Y%m%d)"
./build-all.sh
./push-all.sh
```

### Production
```bash
export TAG="v1.0.0"
./build-all.sh
./push-all.sh

# Also tag as latest
docker tag ${REGISTRY}/maxwell_dashboard:v1.0.0 ${REGISTRY}/maxwell_dashboard:latest
docker push ${REGISTRY}/maxwell_dashboard:latest
```

### Git-Based Tagging
```bash
export TAG="git-$(git rev-parse --short HEAD)"
./build-all.sh
./push-all.sh
```

## Continuous Integration (CI/CD)

### GitHub Actions Example

Create `.github/workflows/build-and-push.yml`:

```yaml
name: Build and Push Images

on:
  push:
    branches: [ main, beta ]
    tags: [ 'v*' ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
    - uses: actions/checkout@v3

    - name: Log in to the Container registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}

    - name: Build and push Dashboard
      uses: docker/build-push-action@v4
      with:
        context: ./Services/MaxWell_Dashboard
        file: ./Services/MaxWell_Dashboard/docker/Dockerfile
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
```

### GitLab CI Example

Create `.gitlab-ci.yml`:

```yaml
variables:
  REGISTRY: registry.gitlab.com/$CI_PROJECT_PATH
  TAG: $CI_COMMIT_SHORT_SHA

stages:
  - build
  - push

build-dashboard:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - cd Services/MaxWell_Dashboard
    - docker build -f docker/Dockerfile -t ${REGISTRY}/dashboard:${TAG} .
    - docker push ${REGISTRY}/dashboard:${TAG}
```

## Air-Gapped Environments

For environments without internet access:

### 1. Export Images

On a machine with internet:

```bash
# Build images
./build-all.sh

# Save to tar files
docker save ${REGISTRY}/maxwell_dashboard:${TAG} -o dashboard.tar
docker save ${REGISTRY}/job_scanner:${TAG} -o job_scanner.tar
```

### 2. Transfer Files

Copy tar files to air-gapped environment (USB drive, internal network, etc.)

### 3. Load Images

On the air-gapped machine:

```bash
# Load images
docker load -i dashboard.tar
docker load -i job_scanner.tar

# Verify
docker images
```

### 4. Deploy

```bash
docker-compose -f docker-compose.custom.yml up -d
```

## Security Scanning

### Scan for Vulnerabilities

```bash
# Install trivy
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Scan image
trivy image ${REGISTRY}/maxwell_dashboard:${TAG}
```

### Fix High/Critical Vulnerabilities

1. Update base image in Dockerfile
2. Update Python dependencies in requirements.txt
3. Rebuild and rescan

## Troubleshooting Custom Builds

### Build Fails: "No space left on device"

```bash
# Clean up Docker
docker system prune -a --volumes

# Check disk space
df -h
```

### Build Fails: Cannot find requirements.txt

Check your build context:
```bash
# Build from service directory
cd Services/MaxWell_Dashboard
docker build -f docker/Dockerfile .

# Not from root
```

### Push Fails: "denied: requested access to the resource is denied"

```bash
# Re-login to registry
docker login your-registry

# Check registry permissions
docker push ${REGISTRY}/maxwell_dashboard:${TAG}
```

### Image is Too Large

- Use multi-stage builds
- Use slim base images (python:3.10-slim)
- Clean up in same RUN layer
- Avoid installing unnecessary packages

## Best Practices

1. **Tag images with versions**, not just `latest`
2. **Test locally before pushing**
3. **Use multi-stage builds** for smaller images
4. **Scan for vulnerabilities** before production
5. **Document custom changes** in your fork
6. **Keep Dockerfiles simple** and maintainable
7. **Use `.dockerignore`** to exclude unnecessary files
8. **Pin dependency versions** for reproducibility

## Cost Optimization

### Registry Storage Costs

- Delete old/unused tags
- Use image lifecycle policies
- Consider storage tiers

### AWS ECR Lifecycle Policy Example

```json
{
  "rules": [{
    "rulePriority": 1,
    "description": "Keep last 10 images",
    "selection": {
      "tagStatus": "any",
      "countType": "imageCountMoreThan",
      "countNumber": 10
    },
    "action": {"type": "expire"}
  }]
}
```

## Migration from Pre-Built Images

Already using pre-built images? Migrate to custom:

1. Build custom images with same configuration
2. Test custom images in development
3. Deploy to staging with custom images
4. Verify functionality
5. Deploy to production

No data loss - configuration and S3 data remain the same.

## Getting Help

- **Deployment Issues:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Configuration:** [Services/common/CONFIG_USAGE_GUIDE.md](Services/common/CONFIG_USAGE_GUIDE.md)
- **GitHub Issues:** https://github.com/braingeneers/EphysPipeline/issues

---

**Custom build complete!**  You now have full control over your EphysPipeline deployment.
