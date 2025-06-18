#!/bin/bash
# Maxwell Ephys Pipeline Deployment Script
# Deploys the complete pipeline with services and container job templates

set -e

# Configuration
NAMESPACE=${NAMESPACE:-"braingeneers"}
REGISTRY=${REGISTRY:-"localhost:5000"}
TAG=${TAG:-"latest"}
DRY_RUN=${DRY_RUN:-"false"}
VERBOSE=${VERBOSE:-"false"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check kubernetes connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check namespace
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_warning "Namespace $NAMESPACE does not exist, creating it..."
        kubectl create namespace "$NAMESPACE"
    fi
    
    log_success "Prerequisites check passed"
}

# Function to apply Kubernetes manifests
apply_manifest() {
    local manifest_file=$1
    local description=$2
    
    log_info "Deploying $description..."
    
    if [ "$DRY_RUN" = "true" ]; then
        log_info "DRY RUN: Would apply $manifest_file"
        if [ "$VERBOSE" = "true" ]; then
            kubectl apply -f "$manifest_file" --dry-run=client -o yaml
        fi
    else
        if [ "$VERBOSE" = "true" ]; then
            kubectl apply -f "$manifest_file" -v=6
        else
            kubectl apply -f "$manifest_file"
        fi
        log_success "Deployed $description"
    fi
}

# Function to wait for deployment readiness
wait_for_deployment() {
    local deployment_name=$1
    local timeout=${2:-300}  # 5 minutes default
    
    log_info "Waiting for deployment $deployment_name to be ready..."
    
    if [ "$DRY_RUN" = "false" ]; then
        if kubectl wait --for=condition=available --timeout=${timeout}s deployment/$deployment_name -n $NAMESPACE; then
            log_success "Deployment $deployment_name is ready"
        else
            log_error "Deployment $deployment_name failed to become ready within ${timeout} seconds"
            return 1
        fi
    fi
}

# Function to check service health
check_service_health() {
    local service_name=$1
    
    log_info "Checking health of service $service_name..."
    
    if [ "$DRY_RUN" = "false" ]; then
        # Get pods for the service
        pods=$(kubectl get pods -n $NAMESPACE -l app=$service_name -o jsonpath='{.items[*].metadata.name}')
        
        if [ -z "$pods" ]; then
            log_warning "No pods found for service $service_name"
            return 1
        fi
        
        for pod in $pods; do
            status=$(kubectl get pod $pod -n $NAMESPACE -o jsonpath='{.status.phase}')
            if [ "$status" != "Running" ]; then
                log_warning "Pod $pod is in $status state"
                # Show recent logs for debugging
                log_info "Recent logs for $pod:"
                kubectl logs --tail=10 $pod -n $NAMESPACE || true
            else
                log_success "Pod $pod is running"
            fi
        done
    fi
}

# Function to deploy services
deploy_services() {
    log_info "Deploying Maxwell Ephys Pipeline services..."
    
    # Apply service manifests
    apply_manifest "k8s/services.yaml" "Services and ConfigMaps"
    
    if [ "$DRY_RUN" = "false" ]; then
        # Wait for deployments to be ready
        wait_for_deployment "maxwell-spike-sorting-listener"
        wait_for_deployment "maxwell-job-scanner"
        wait_for_deployment "maxwell-dashboard"
        
        # Check service health
        check_service_health "maxwell-spike-sorting-listener"
        check_service_health "maxwell-job-scanner"
        check_service_health "maxwell-dashboard"
    fi
}

# Function to deploy container job templates
deploy_container_templates() {
    log_info "Deploying container job templates..."
    
    # Create a configmap for job templates (not actual jobs)
    apply_manifest "k8s/containers.yaml" "Container Job Templates"
}

# Function to test deployment
test_deployment() {
    log_info "Testing deployment..."
    
    if [ "$DRY_RUN" = "false" ]; then
        # Test service connectivity
        log_info "Testing service connectivity..."
        
        # Check if dashboard is accessible
        if kubectl get service maxwell-dashboard -n $NAMESPACE &> /dev/null; then
            dashboard_ip=$(kubectl get service maxwell-dashboard -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
            if [ ! -z "$dashboard_ip" ]; then
                log_info "Dashboard should be accessible at: http://$dashboard_ip"
            else
                log_info "Dashboard service created, waiting for external IP..."
            fi
        fi
        
        # Check logs for any immediate errors
        log_info "Checking service logs for errors..."
        
        services=("maxwell-spike-sorting-listener" "maxwell-job-scanner" "maxwell-dashboard")
        for service in "${services[@]}"; do
            pods=$(kubectl get pods -n $NAMESPACE -l app=$service -o jsonpath='{.items[*].metadata.name}')
            for pod in $pods; do
                if kubectl logs --tail=5 $pod -n $NAMESPACE 2>/dev/null | grep -i error; then
                    log_warning "Found errors in logs for $pod"
                else
                    log_success "No immediate errors in logs for $pod"
                fi
            done
        done
    fi
}

# Function to show deployment status
show_status() {
    log_info "Maxwell Ephys Pipeline Deployment Status:"
    echo "==========================================="
    
    if [ "$DRY_RUN" = "false" ]; then
        echo "Namespace: $NAMESPACE"
        echo "Registry: $REGISTRY"
        echo "Tag: $TAG"
        echo ""
        
        echo "Services:"
        kubectl get deployments -n $NAMESPACE -l component=service -o wide
        echo ""
        
        echo "Pods:"
        kubectl get pods -n $NAMESPACE -l component=service -o wide
        echo ""
        
        echo "Services:"
        kubectl get services -n $NAMESPACE
        echo ""
        
        echo "ConfigMaps:"
        kubectl get configmaps -n $NAMESPACE -l app.kubernetes.io/part-of=maxwell-ephys-pipeline
        echo ""
        
        # Show resource usage
        echo "Resource Usage:"
        kubectl top pods -n $NAMESPACE --sort-by=memory 2>/dev/null || echo "Metrics server not available"
    fi
}

# Function to cleanup deployment
cleanup() {
    log_warning "Cleaning up Maxwell Ephys Pipeline deployment..."
    
    if [ "$DRY_RUN" = "true" ]; then
        log_info "DRY RUN: Would delete resources in namespace $NAMESPACE"
    else
        # Delete services
        kubectl delete -f k8s/services.yaml --ignore-not-found=true
        
        # Delete container templates
        kubectl delete -f k8s/containers.yaml --ignore-not-found=true
        
        # Delete any remaining jobs
        kubectl delete jobs -n $NAMESPACE -l component=container --ignore-not-found=true
        
        log_success "Cleanup completed"
    fi
}

# Function to show help
show_help() {
    cat << EOF
Maxwell Ephys Pipeline Deployment Script

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    deploy      Deploy the complete pipeline (default)
    services    Deploy only services
    containers  Deploy only container templates
    test        Test the deployment
    status      Show deployment status
    cleanup     Remove all deployed resources
    help        Show this help message

Options:
    -n, --namespace NAMESPACE   Kubernetes namespace (default: braingeneers)
    -r, --registry REGISTRY     Docker registry (default: localhost:5000)
    -t, --tag TAG              Image tag (default: latest)
    -d, --dry-run              Perform a dry run without applying changes
    -v, --verbose              Verbose output
    -h, --help                 Show this help message

Environment Variables:
    NAMESPACE      Kubernetes namespace
    REGISTRY       Docker registry
    TAG           Image tag
    DRY_RUN       Perform dry run (true/false)
    VERBOSE       Verbose output (true/false)

Examples:
    $0                                          # Deploy everything
    $0 deploy -n production -r docker.io/user  # Deploy to production
    $0 services --dry-run                       # Dry run services only
    $0 status                                   # Show status
    $0 cleanup                                  # Remove everything

EOF
}

# Main execution
main() {
    local command=${1:-"deploy"}
    
    case $command in
        deploy)
            check_prerequisites
            deploy_services
            deploy_container_templates
            test_deployment
            show_status
            ;;
        services)
            check_prerequisites
            deploy_services
            ;;
        containers)
            check_prerequisites
            deploy_container_templates
            ;;
        test)
            test_deployment
            ;;
        status)
            show_status
            ;;
        cleanup)
            cleanup
            ;;
        help|-h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Parse command line arguments
COMMAND=""
while [[ $# -gt 0 ]]; do
    case $1 in
        deploy|services|containers|test|status|cleanup|help)
            COMMAND=$1
            shift
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN="true"
            shift
            ;;
        -v|--verbose)
            VERBOSE="true"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main function with command
main $COMMAND
