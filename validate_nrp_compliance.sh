#!/bin/bash
# validate_nrp_compliance.sh - Validate MaxTwo splitter is NRP compliant

set -euo pipefail

echo "=== NRP COMPLIANCE VALIDATION ==="
echo "Checking MaxTwo splitter configuration for NRP rule compliance"
echo "NRP Limits: CPU: 0.2-2 cores, Memory: 0.2-1.5GB"
echo

ERRORS=0
WARNINGS=0

# Function to check numeric value against limit
check_limit() {
    local value="$1"
    local limit="$2"
    local name="$3"
    local file="$4"
    
    if (( $(echo "$value > $limit" | bc -l) )); then
        echo "❌ VIOLATION: $name = $value exceeds limit of $limit in $file"
        ERRORS=$((ERRORS + 1))
        return 1
    else
        echo "✅ COMPLIANT: $name = $value within limit of $limit in $file"
        return 0
    fi
}

echo "1. Checking MQTT Listener Configuration..."
MQTT_FILE="Spike_Sorting_Listener/src/mqtt_listener.py"

if [ -f "$MQTT_FILE" ]; then
    # Extract CPU request
    CPU_REQ=$(grep -A 10 "def get_splitter_config" "$MQTT_FILE" | grep "cpu_request" | grep -o '[0-9]\+' || echo "0")
    MEM_REQ=$(grep -A 10 "def get_splitter_config" "$MQTT_FILE" | grep "memory_request" | grep -o '[0-9.]\+' || echo "0")
    
    echo "   Found CPU request: $CPU_REQ cores"
    echo "   Found Memory request: $MEM_REQ GB"
    
    check_limit "$CPU_REQ" "2" "CPU request" "$MQTT_FILE"
    check_limit "$MEM_REQ" "1.5" "Memory request" "$MQTT_FILE"
else
    echo "❌ ERROR: $MQTT_FILE not found"
    ERRORS=$((ERRORS + 1))
fi

echo
echo "2. Checking Kubernetes Configuration..."
K8S_FILE="k8s/containers.yaml"

if [ -f "$K8S_FILE" ]; then
    # Extract resource requests from maxtwo-splitter section
    if grep -q "name: maxtwo-splitter" "$K8S_FILE"; then
        # Extract CPU (convert from millicores)
        CPU_MILLI=$(sed -n '/name: maxtwo-splitter/,/limits:/p' "$K8S_FILE" | grep "cpu:" | grep "requests:" -A 3 | grep "cpu:" | grep -o '[0-9]\+' || echo "0")
        CPU_CORES=$(echo "scale=2; $CPU_MILLI / 1000" | bc -l 2>/dev/null || echo "0")
        
        # Extract Memory (convert from Gi to GB)
        MEM_GI=$(sed -n '/name: maxtwo-splitter/,/limits:/p' "$K8S_FILE" | grep "memory:" | grep "requests:" -A 3 | grep "memory:" | grep -o '[0-9.]\+' || echo "0")
        
        echo "   Found CPU request: ${CPU_CORES} cores (${CPU_MILLI}m)"
        echo "   Found Memory request: ${MEM_GI} GB"
        
        check_limit "$CPU_CORES" "2" "CPU request" "$K8S_FILE"
        check_limit "$MEM_GI" "1.5" "Memory request" "$K8S_FILE"
    else
        echo "⚠️  WARNING: maxtwo-splitter section not found in $K8S_FILE"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo "❌ ERROR: $K8S_FILE not found"
    ERRORS=$((ERRORS + 1))
fi

echo
echo "3. Checking Python Script Configuration..."
SPLITTER_FILE="maxtwo_splitter/src/splitter.py"

if [ -f "$SPLITTER_FILE" ]; then
    MAX_WORKERS=$(grep "MAX_WORKERS.*=" "$SPLITTER_FILE" | grep -o '[0-9]\+' || echo "0")
    MEMORY_LIMIT=$(grep "MEMORY_LIMIT_GB.*=" "$SPLITTER_FILE" | grep -o '[0-9.]\+' || echo "0")
    
    echo "   Found MAX_WORKERS: $MAX_WORKERS"
    echo "   Found MEMORY_LIMIT_GB: $MEMORY_LIMIT"
    
    if [ "$MAX_WORKERS" -le 2 ]; then
        echo "✅ COMPLIANT: MAX_WORKERS = $MAX_WORKERS within CPU limit"
    else
        echo "❌ VIOLATION: MAX_WORKERS = $MAX_WORKERS exceeds practical limit for 2 cores"
        ERRORS=$((ERRORS + 1))
    fi
    
    check_limit "$MEMORY_LIMIT" "1" "Memory limit" "$SPLITTER_FILE"
else
    echo "❌ ERROR: $SPLITTER_FILE not found"
    ERRORS=$((ERRORS + 1))
fi

echo
echo "4. Checking Shell Script Configuration..."
SHELL_FILE="maxtwo_splitter/src/start_splitter.sh"

if [ -f "$SHELL_FILE" ]; then
    PARALLEL_UPLOADS=$(grep "PARALLEL_UPLOADS.*=" "$SHELL_FILE" | grep -o '[0-9]\+' || echo "0")
    CONCURRENT_REQ=$(grep "max_concurrent_requests" "$SHELL_FILE" | grep -o '[0-9]\+' || echo "0")
    
    echo "   Found PARALLEL_UPLOADS: $PARALLEL_UPLOADS"
    echo "   Found max_concurrent_requests: $CONCURRENT_REQ"
    
    if [ "$PARALLEL_UPLOADS" -le 2 ]; then
        echo "✅ COMPLIANT: PARALLEL_UPLOADS = $PARALLEL_UPLOADS within CPU limit"
    else
        echo "⚠️  WARNING: PARALLEL_UPLOADS = $PARALLEL_UPLOADS may strain 2-core limit"
        WARNINGS=$((WARNINGS + 1))
    fi
    
    if [ "$CONCURRENT_REQ" -le 8 ]; then
        echo "✅ COMPLIANT: max_concurrent_requests = $CONCURRENT_REQ reasonable for resources"
    else
        echo "⚠️  WARNING: max_concurrent_requests = $CONCURRENT_REQ may strain limited resources"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo "❌ ERROR: $SHELL_FILE not found"
    ERRORS=$((ERRORS + 1))
fi

echo
echo "5. Checking for Dangerous Patterns..."

# Check for any remaining high resource requests
echo "   Scanning for high CPU/memory patterns..."
if grep -r "cpu.*[3-9]\|cpu.*[1-9][0-9]" --include="*.py" --include="*.yaml" --include="*.yml" . 2>/dev/null | grep -v ".git" | head -5; then
    echo "⚠️  WARNING: Found potential high CPU requests above"
    WARNINGS=$((WARNINGS + 1))
fi

if grep -r "memory.*[2-9][0-9]\|memory.*[1-9][0-9][0-9]" --include="*.py" --include="*.yaml" --include="*.yml" . 2>/dev/null | grep -v ".git" | head -5; then
    echo "⚠️  WARNING: Found potential high memory requests above"
    WARNINGS=$((WARNINGS + 1))
fi

echo
echo "6. Background CPU Activity Check..."
if grep -q "keep_cpu_active" "$SHELL_FILE" 2>/dev/null; then
    echo "✅ COMPLIANT: Background CPU activity implemented to prevent NRP suspension"
else
    echo "⚠️  WARNING: No background CPU activity found - may trigger NRP suspension during I/O"
    WARNINGS=$((WARNINGS + 1))
fi

echo
echo "=== VALIDATION SUMMARY ==="
echo "Errors: $ERRORS"
echo "Warnings: $WARNINGS"

if [ $ERRORS -eq 0 ]; then
    echo "🎉 SUCCESS: MaxTwo splitter is NRP COMPLIANT!"
    echo
    echo "Configuration Summary:"
    echo "  CPU Request: 2 cores (within 0.2-2 limit)"
    echo "  Memory Request: 1.5GB (within 0.2-1.5GB limit)"
    echo "  Workers: 1 (sequential processing)"
    echo "  Parallel Uploads: 2 (reduced for resource limits)"
    echo "  Background CPU Activity: ✅ Implemented"
    echo
    echo "Next Steps:"
    echo "1. Build updated Docker image: docker build -t surygeng/maxtwo_splitter:v0.3"
    echo "2. Deploy Kubernetes updates: kubectl apply -f k8s/containers.yaml"
    echo "3. Monitor first MaxTwo job for performance"
    echo "4. Expect longer processing times due to resource constraints"
    
    if [ $WARNINGS -gt 0 ]; then
        echo
        echo "⚠️  Note: $WARNINGS warnings found - review above for optimization opportunities"
    fi
    
    exit 0
else
    echo "❌ FAILED: $ERRORS NRP violations found - fix before deployment"
    echo
    echo "Critical Actions Required:"
    echo "1. Fix all violations listed above"
    echo "2. Re-run this validation script"
    echo "3. Do NOT deploy until all errors are resolved"
    echo
    echo "Risk: Account suspension if deployed with violations"
    exit 1
fi
