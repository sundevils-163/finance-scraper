#!/bin/bash

# Finance Scraper Deployment Script
# This script builds the Docker image and deploys to Kubernetes using Helm

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="junzhutx/finance-scraper"
IMAGE_TAG="${1:-latest}"
NAMESPACE="${2:-default}"
RELEASE_NAME="${3:-finance-scraper}"

echo -e "${GREEN}🚀 Finance Scraper Deployment Script${NC}"
echo "=================================="
echo "Image Name: $IMAGE_NAME"
echo "Image Tag: $IMAGE_TAG"
echo "Namespace: $NAMESPACE"
echo "Release Name: $RELEASE_NAME"
echo ""

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v helm &> /dev/null; then
        print_error "Helm is not installed or not in PATH"
        exit 1
    fi
    
    print_status "All prerequisites are satisfied"
}

# Build Docker image
build_image() {
    print_status "Building Docker image..."
    docker build --platform linux/amd64 -t "$IMAGE_NAME:$IMAGE_TAG" .
    docker push "$IMAGE_NAME:$IMAGE_TAG"
    print_status "Docker image built successfully"
}

# Check if namespace exists, create if not
ensure_namespace() {
    print_status "Ensuring namespace exists..."
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        print_warning "Namespace $NAMESPACE does not exist, creating..."
        kubectl create namespace "$NAMESPACE"
        print_status "Namespace $NAMESPACE created"
    else
        print_status "Namespace $NAMESPACE already exists"
    fi
}

# Deploy with Helm
deploy_helm() {
    print_status "Deploying with Helm..."
    
    # Check if release already exists
    if helm list -n "$NAMESPACE" | grep -q "$RELEASE_NAME"; then
        print_warning "Release $RELEASE_NAME already exists, upgrading..."
        helm upgrade "$RELEASE_NAME" ./helm/finance-scraper \
            --namespace "$NAMESPACE" \
            --set image.tag="$IMAGE_TAG" \
            --set image.repository="$IMAGE_NAME"
    else
        print_status "Installing new release..."
        helm install "$RELEASE_NAME" ./helm/finance-scraper \
            --namespace "$NAMESPACE" \
            --set image.tag="$IMAGE_TAG" \
            --set image.repository="$IMAGE_NAME"
    fi
    
    print_status "Helm deployment completed"
}

# Wait for deployment to be ready
wait_for_deployment() {
    print_status "Waiting for deployment to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/"$RELEASE_NAME" -n "$NAMESPACE"
    print_status "Deployment is ready"
}

# Show deployment status
show_status() {
    print_status "Deployment Status:"
    echo ""
    echo "Pods:"
    kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/name=finance-scraper"
    echo ""
    echo "Services:"
    kubectl get svc -n "$NAMESPACE" -l "app.kubernetes.io/name=finance-scraper"
    echo ""
    echo "To access the application:"
    echo "kubectl port-forward deployment/$RELEASE_NAME 8080:5000 -n $NAMESPACE"
    echo ""
    echo "Then visit: http://localhost:8080/health"
}

# Main execution
main() {
    check_prerequisites
    build_image
    ensure_namespace
    deploy_helm
    wait_for_deployment
    show_status
    
    print_status "Deployment completed successfully! 🎉"
}

# Run main function
main "$@" 