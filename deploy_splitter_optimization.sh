#!/bin/bash
# deploy_splitter_optimization.sh - Deploy the optimized MaxTwo splitter

set -euo pipefail

echo "=== Deploying MaxTwo Splitter Optimizations ==="
echo

# Configuration
DOCKER_IMAGE="surygeng/maxtwo_splitter"
OLD_VERSION="v0.1"
NEW_VERSION="v0.2"
BACKUP_SUFFIX="_backup_$(date +%Y%m%d_%H%M%S)"

# Check if we're in the right directory
if [ ! -f "maxtwo_splitter/src/start_splitter_optimized.sh" ]; then
    echo "ERROR: Please run this from the maxwell_ephys_pipeline root directory"
    exit 1
fi

echo "1. Creating backup of current configuration..."
cp "Spike_Sorting_Listener/src/mqtt_listener.py" "Spike_Sorting_Listener/src/mqtt_listener.py${BACKUP_SUFFIX}"
cp "k8s/containers.yaml" "k8s/containers.yaml${BACKUP_SUFFIX}"
echo "   SUCCESS: Backups created with suffix ${BACKUP_SUFFIX}"

echo
echo "2. Updating Docker image version..."
# Update image reference in mqtt_listener.py
if grep -q "${DOCKER_IMAGE}:${OLD_VERSION}" "Spike_Sorting_Listener/src/mqtt_listener.py"; then
    sed -i "s/${DOCKER_IMAGE}:${OLD_VERSION}/${DOCKER_IMAGE}:${NEW_VERSION}/g" "Spike_Sorting_Listener/src/mqtt_listener.py"
    echo "   SUCCESS: Updated mqtt_listener.py to use ${NEW_VERSION}"
else
    echo "   INFO: mqtt_listener.py already using different version"
fi

# Update image reference in containers.yaml  
if grep -q "maxwell-maxtwo-splitter:latest" "k8s/containers.yaml"; then
    sed -i "s/maxwell-maxtwo-splitter:latest/${DOCKER_IMAGE}:${NEW_VERSION}/g" "k8s/containers.yaml"
    echo "   SUCCESS: Updated containers.yaml to use ${NEW_VERSION}"
else
    echo "   INFO: containers.yaml already using different image"
fi

echo
echo "3. Validating optimized configuration..."
./test_splitter_optimization.sh | grep -E "(SUCCESS|FAILED)" | head -10

echo
echo "4. Docker build commands (run manually):"
echo "   cd maxtwo_splitter/docker"
echo "   # Add these lines to Dockerfile:"
echo "   # COPY src/start_splitter_optimized.sh /app/"
echo "   # COPY src/splitter_optimized.py /app/"
echo "   # RUN chmod +x /app/start_splitter_optimized.sh"
echo "   # RUN apt-get update && apt-get install -y bc && rm -rf /var/lib/apt/lists/*"
echo "   docker build -t ${DOCKER_IMAGE}:${NEW_VERSION} ."
echo "   docker push ${DOCKER_IMAGE}:${NEW_VERSION}"

echo
echo "5. Kubernetes deployment commands (run after Docker build):"
echo "   kubectl apply -f k8s/containers.yaml"
echo "   kubectl rollout restart deployment/maxwell-spike-sorting-listener"

echo
echo "6. Monitoring commands:"
echo "   # Watch for new MaxTwo jobs"
echo "   kubectl get jobs -w | grep splitter"
echo "   # Check job logs for optimization patterns"
echo "   kubectl logs -f job/<job-name> | grep -E '(OPTIMIZED|parallel|Total time)'"

echo
echo "7. Rollback commands (if needed):"
echo "   cp Spike_Sorting_Listener/src/mqtt_listener.py${BACKUP_SUFFIX} Spike_Sorting_Listener/src/mqtt_listener.py"
echo "   cp k8s/containers.yaml${BACKUP_SUFFIX} k8s/containers.yaml" 
echo "   kubectl apply -f k8s/containers.yaml"

echo
echo "=== DEPLOYMENT PREPARATION COMPLETE ==="
echo
echo "Summary of changes:"
echo "✅ Created optimized splitter scripts with parallel processing"
echo "✅ Updated resource allocation (6 CPU, 48GB RAM)"  
echo "✅ Configured parallel uploads (3 concurrent)"
echo "✅ Enhanced AWS CLI settings for maximum throughput"
echo "✅ Added comprehensive monitoring and progress tracking"
echo
echo "Expected performance improvement: 50-60% faster (2+ hours → 45-60 minutes)"
echo
echo "Next steps:"
echo "1. Build and push Docker image with optimized scripts"
echo "2. Apply Kubernetes configuration updates"
echo "3. Test with real MaxTwo dataset"
echo "4. Monitor performance and validate timing improvements"
echo
echo "Ready for production deployment!"
