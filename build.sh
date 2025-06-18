#!/bin/bash
# Enhanced unified build script for Maxwell Ephys Pipeline
# Supports both services and containers with shared base images

set -e

# Configuration
REGISTRY=${REGISTRY:-"localhost:5000"}
TAG=${TAG:-"latest"}
PUSH=${PUSH:-"false"}
BUILD_PARALLEL=${BUILD_PARALLEL:-"false"}
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

# Function to build base images
build_base_images() {
    log_info "Building base images..."
    
    # Build service base image
    log_info "Building maxwell-service-base:$TAG"
    docker build -f docker/base/service.dockerfile -t maxwell-service-base:$TAG docker/base/
    
    # Build processing base image  
    log_info "Building maxwell-processing-base:$TAG"
    docker build -f docker/base/processing.dockerfile -t maxwell-processing-base:$TAG docker/base/
    
    log_success "Base images built successfully"
}

# Function to build component
build_component() {
    local component_type=$1
    local component_name=$2
    local component_path=$3
    
    log_info "Building $component_type: $component_name"
    
    # Determine Dockerfile and image name
    local dockerfile="docker/Dockerfile.$component_type"
    local image_name="$REGISTRY/maxwell-$component_name:$TAG"
    
    # Check if component has custom Dockerfile
    if [ -f "$component_path/docker/Dockerfile" ]; then
        dockerfile="$component_path/docker/Dockerfile"
        log_info "Using custom Dockerfile for $component_name"
    fi
    
    # Build the image
    if [ "$VERBOSE" = "true" ]; then
        docker build -f "$dockerfile" -t "$image_name" "$component_path"
    else
        docker build -f "$dockerfile" -t "$image_name" "$component_path" > /dev/null 2>&1
    fi
    
    # Push if requested
    if [ "$PUSH" = "true" ]; then
        log_info "Pushing $image_name"
        docker push "$image_name"
    fi
    
    log_success "Built $component_type: $component_name"
}

# Function to build all components of a type
build_components() {
    local component_type=$1
    local base_dir=$2
    
    log_info "Building all ${component_type}s..."
    
    if [ ! -d "$base_dir" ]; then
        log_warning "Directory $base_dir does not exist, skipping ${component_type}s"
        return
    fi
    
    local build_pids=()
    
    for component_path in "$base_dir"*/; do
        if [ -d "$component_path" ]; then
            component_name=$(basename "$component_path")
            
            if [ "$BUILD_PARALLEL" = "true" ]; then
                # Build in parallel
                (build_component "$component_type" "$component_name" "$component_path") &
                build_pids+=($!)
            else
                # Build sequentially
                build_component "$component_type" "$component_name" "$component_path"
            fi
        fi
    done
    
    # Wait for parallel builds to complete
    if [ "$BUILD_PARALLEL" = "true" ] && [ ${#build_pids[@]} -gt 0 ]; then
        log_info "Waiting for parallel builds to complete..."
        for pid in "${build_pids[@]}"; do
            wait $pid
        done
    fi
    
    log_success "All ${component_type}s built successfully"
}

# Function to validate build environment
validate_environment() {
    log_info "Validating build environment..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check required directories
    required_dirs=("docker/base" "shared")
    for dir in "${required_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            log_error "Required directory $dir does not exist"
            exit 1
        fi
    done
    
    log_success "Environment validation passed"
}

# Function to generate build summary
generate_summary() {
    log_info "Build Summary:"
    echo "==============================================="
    echo "Registry: $REGISTRY"
    echo "Tag: $TAG"
    echo "Push to registry: $PUSH"
    echo "Parallel build: $BUILD_PARALLEL"
    echo "Verbose output: $VERBOSE"
    echo "==============================================="
    
    # List built images
    log_info "Built images:"
    docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" \
        --filter "reference=maxwell-*:$TAG" \
        --filter "reference=$REGISTRY/maxwell-*:$TAG"
}

# Function to cleanup old images
cleanup_old_images() {
    log_info "Cleaning up old images..."
    
    # Remove dangling images
    dangling=$(docker images -f "dangling=true" -q)
    if [ ! -z "$dangling" ]; then
        docker rmi $dangling
        log_success "Removed dangling images"
    fi
    
    # Remove old tagged images (optional)
    if [ "$CLEANUP_OLD" = "true" ]; then
        log_warning "Removing old maxwell images..."
        docker images --format "{{.Repository}}:{{.Tag}}" | grep "maxwell-" | grep -v ":$TAG" | xargs -r docker rmi
    fi
}

# Main execution
main() {
    log_info "Starting Maxwell Ephys Pipeline build process..."
    log_info "Build configuration:"
    echo "  Registry: $REGISTRY"
    echo "  Tag: $TAG"
    echo "  Push: $PUSH"
    echo "  Parallel: $BUILD_PARALLEL"
    echo ""
    
    # Validate environment
    validate_environment
    
    # Build base images first
    build_base_images
    
    # Build services
    build_components "service" "services/"
    
    # Build containers
    build_components "container" "containers/"
    
    # Cleanup if requested
    if [ "$CLEANUP" = "true" ]; then
        cleanup_old_images
    fi
    
    # Generate summary
    generate_summary
    
    log_success "Maxwell Ephys Pipeline build completed successfully!"
}

# Help function
show_help() {
    cat << EOF
Maxwell Ephys Pipeline Build Script

Usage: $0 [OPTIONS]

Options:
    -h, --help              Show this help message
    -r, --registry REGISTRY Set Docker registry (default: localhost:5000)
    -t, --tag TAG           Set image tag (default: latest)
    -p, --push              Push images to registry
    -j, --parallel          Build components in parallel
    -v, --verbose           Verbose output
    -c, --cleanup           Cleanup old images after build
    --cleanup-old           Remove old tagged images (not just dangling)

Environment Variables:
    REGISTRY               Docker registry
    TAG                    Image tag
    PUSH                   Push to registry (true/false)
    BUILD_PARALLEL         Build in parallel (true/false)
    VERBOSE                Verbose output (true/false)
    CLEANUP                Cleanup after build (true/false)
    CLEANUP_OLD            Remove old tagged images (true/false)

Examples:
    $0                                          # Basic build
    $0 -r docker.io/username -t v1.0 -p        # Build and push to Docker Hub
    $0 -j -v                                    # Parallel build with verbose output
    $0 --cleanup --cleanup-old                 # Build with full cleanup

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -p|--push)
            PUSH="true"
            shift
            ;;
        -j|--parallel)
            BUILD_PARALLEL="true"
            shift
            ;;
        -v|--verbose)
            VERBOSE="true"
            shift
            ;;
        -c|--cleanup)
            CLEANUP="true"
            shift
            ;;
        --cleanup-old)
            CLEANUP_OLD="true"
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main function
main
