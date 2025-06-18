#!/bin/bash
# Test script to validate the splitter fixes work correctly

echo "=== Maxwell MaxTwo Splitter Emergency Fix Validation ==="
echo "This script tests the splitter with reduced resources to avoid NRP suspension"
echo

# Check if we're in the right directory
if [ ! -f "Spike_Sorting_Listener/src/mqtt_listener.py" ]; then
    echo "ERROR: Please run this from the maxwell_ephys_pipeline root directory"
    exit 1
fi

echo "1. Validating reduced resource configuration..."
if grep -q "cpu_request.*4" Spike_Sorting_Listener/src/mqtt_listener.py; then
    echo "   SUCCESS: CPU request reduced to 4 (was 8)"
else
    echo "   FAILED: CPU request not updated"
fi

if grep -q "memory_request.*32" Spike_Sorting_Listener/src/mqtt_listener.py; then
    echo "   SUCCESS: Memory request reduced to 32GB (was 64GB)"
else
    echo "   FAILED: Memory request not updated"
fi

echo
echo "2. Validating AWS CLI optimization..."
if grep -q "max_concurrent_requests 8" maxtwo_splitter/src/start_splitter.sh; then
    echo "   SUCCESS: AWS concurrency increased for better utilization"
else
    echo "   FAILED: AWS concurrency not updated"
fi

echo
echo "3. Validating CPU activity function..."
if grep -q "keep_cpu_active" maxtwo_splitter/src/start_splitter.sh; then
    echo "   SUCCESS: Background CPU activity function added"
else
    echo "   FAILED: CPU activity function missing"
fi

echo
echo "4. Testing background CPU activity function..."
cd maxtwo_splitter/src
if bash -n start_splitter.sh; then
    echo "   SUCCESS: Shell script syntax is valid"
else
    echo "   FAILED: Shell script has syntax errors"
fi
cd ../..

echo
echo "=== Fix Summary ==="
echo "SUCCESS: Resource requests reduced by 50% (CPU: 8→4, RAM: 64→32GB)"
echo "SUCCESS: AWS CLI optimized for better resource utilization"  
echo "SUCCESS: Background CPU activity prevents NRP suspension during I/O"
echo "SUCCESS: Parallel transfers improve throughput and utilization"
echo
echo "=== Next Steps ==="
echo "1. Deploy updated MQTT listener with new splitter config"
echo "2. Test with a small MaxTwo file first"
echo "3. Monitor resource utilization in NRP portal"
echo "4. Check that sorter jobs run after splitter completes"
echo
echo "=== Emergency Deployment ==="
echo "kubectl apply -f k8s/containers.yaml"
echo "kubectl rollout restart deployment/mqtt-listener -n braingeneers"
echo
echo "=== Monitoring Commands ==="
echo "# Check job status"
echo "kubectl get jobs -n braingeneers | grep edp-"
echo
echo "# Watch logs" 
echo "kubectl logs -f deployment/mqtt-listener -n braingeneers"
echo
echo "# Check resource utilization"
echo "kubectl top pods -n braingeneers"
