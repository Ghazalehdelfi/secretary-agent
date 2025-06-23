#!/bin/bash

# A2A Multi-Agent Google Cloud Platform Deployment Script (Updated with all secrets)
# This script deploys the A2A multi-agent system to Google Cloud Run with comprehensive secret management

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PROJECT_ID=""
REGION="us-central1"

# Helper functions
print_status() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check prerequisites
# check_prerequisites() {
#     print_status "Checking prerequisites..."
    
#     if ! command -v gcloud &> /dev/null; then
#         print_error "gcloud CLI is not installed. Please install it first."
#         exit 1
#     fi
    
#     if ! command -v docker &> /dev/null; then
#         print_error "Docker is not installed. Please install it first."
#         exit 1
#     fi
    
#     if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
#         print_error "Not authenticated with gcloud. Please run 'gcloud auth login' first."
#         exit 1
#     fi
    
#     print_success "Prerequisites check passed"
# }

# Function to get project ID
get_project_id() {
    if [ -z "agent-hackathon-461619" ]; then
        PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
        if [ -z "agent-hackathon-461619" ]; then
            print_error "No project ID set. Please provide one with --project-id or set it with 'gcloud config set project PROJECT_ID'"
            exit 1
        fi
    fi
    
    print_status "Using project ID: agent-hackathon-461619"
}

# Function to enable required APIs
# enable_apis() {
#     print_status "Enabling required Google Cloud APIs..."
    
#     gcloud services enable cloudbuild.googleapis.com --project="agent-hackathon-461619"
#     gcloud services enable run.googleapis.com --project="agent-hackathon-461619"
#     gcloud services enable secretmanager.googleapis.com --project="agent-hackathon-461619"
#     gcloud services enable containerregistry.googleapis.com --project="agent-hackathon-461619"
    
#     print_success "APIs enabled successfully"
# }

# Function to configure Docker
# configure_docker() {
#     print_status "Configuring Docker for Google Container Registry..."
    
#     gcloud auth configure-docker
    
#     print_success "Docker configured for GCR"
# }

# Function to build and push images
build_and_push_images() {
    print_status "Building and pushing Docker images..."
    
    # Build calendar agent
    print_status "Building a2a-calendar-agent..."
    docker build --platform linux/amd64 -f Dockerfile.calendar-agent -t "gcr.io/agent-hackathon-461619/a2a-calendar-agent:latest" .
    print_status "Pushing a2a-calendar-agent to GCR..."
    docker push "gcr.io/agent-hackathon-461619/a2a-calendar-agent:latest"
    
    # Build sync agent
    print_status "Building a2a-sync-agent..."
    docker build --platform linux/amd64 -f Dockerfile.sync-agent -t "gcr.io/agent-hackathon-461619/a2a-sync-agent:latest" .
    print_status "Pushing a2a-sync-agent to GCR..."
    docker push "gcr.io/agent-hackathon-461619/a2a-sync-agent:latest"
    
    # Build host agent
    print_status "Building a2a-host-agent..."
    docker build --platform linux/amd64 -f Dockerfile.host-agent -t "gcr.io/agent-hackathon-461619/a2a-host-agent:latest" .
    print_status "Pushing a2a-host-agent to GCR..."
    docker push "gcr.io/agent-hackathon-461619/a2a-host-agent:latest"
    
    cd ..
    
    print_success "Images built and pushed successfully"
}

# Function to deploy to Cloud Run
deploy_to_cloud_run() {
    print_status "Deploying services to Cloud Run..."
    
    # Deploy calendar agent first (no dependencies)
    print_status "Deploying calendar agent..."
    gcloud run deploy a2a-calendar-agent \
        --image="gcr.io/agent-hackathon-461619/a2a-calendar-agent:latest" \
        --region="us-central1" \
        --platform="managed" \
        --allow-unauthenticated \
        --port=10001 \
        --memory=512Mi \
        --cpu=1 \
        --set-env-vars="PYTHONPATH=/app,PYTHONUNBUFFERED=1" \
        --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest,SERVICE_EMAIL=SERVICE_EMAIL:latest,SERVICE_PASSWORD=SERVICE_PASSWORD:latest,SUPABASE_URL=SUPABASE_URL:latest,SUPABASE_ANON_KEY=SUPABASE_ANON_KEY:latest,service-creds=service-creds:latest" \
        --max-instances=10 \
        --min-instances=0
    
    # Deploy sync agent with calendar agent URL in registry
    print_status "Deploying sync agent..."
    gcloud run deploy a2a-sync-agent \
        --image="gcr.io/agent-hackathon-461619/a2a-sync-agent:latest" \
        --region="us-central1" \
        --platform="managed" \
        --allow-unauthenticated \
        --port=10002 \
        --memory=512Mi \
        --cpu=1 \
        --set-env-vars="PYTHONPATH=/app,PYTHONUNBUFFERED=1" \
        --set-env-vars="REGISTRY=https://a2a-calendar-agent-695627813996.us-central1.run.app" \
        --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest,SERVICE_EMAIL=SERVICE_EMAIL:latest,SERVICE_PASSWORD=SERVICE_PASSWORD:latest,SUPABASE_URL=SUPABASE_URL:latest,SUPABASE_ANON_KEY=SUPABASE_ANON_KEY:latest,service-creds=service-creds:latest" \
        --max-instances=10 \
        --min-instances=0
    
    # Deploy host agent with both calendar and sync agent URLs in registry
    print_status "Deploying host agent..."
    gcloud run deploy a2a-host-agent \
        --image="gcr.io/agent-hackathon-461619/a2a-host-agent:latest" \
        --region="us-central1" \
        --platform="managed" \
        --allow-unauthenticated \
        --port=10000 \
        --memory=512Mi \
        --cpu=1 \
        --set-env-vars="PYTHONPATH=/app,PYTHONUNBUFFERED=1" \
        --set-env-vars="REGISTRY=https://a2a-calendar-agent-695627813996.us-central1.run.app+https://a2a-sync-agent-695627813996.us-central1.run.app" \
        --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest,SERVICE_EMAIL=SERVICE_EMAIL:latest,SERVICE_PASSWORD=SERVICE_PASSWORD:latest,SUPABASE_URL=SUPABASE_URL:latest,SUPABASE_ANON_KEY=SUPABASE_ANON_KEY:latest" \
        --max-instances=10 \
        --min-instances=0
    
    print_success "All services deployed successfully!"
}

# Function to display deployment information
display_deployment_info() {
    print_status "Deployment completed successfully!"
    echo ""
    echo "🌐 Service URLs:"
    echo "   Host Agent (Orchestrator): $(gcloud run services describe a2a-host-agent --region="us-central1" --format="value(status.url)")"
    echo "   Calendar Agent: $(gcloud run services describe a2a-calendar-agent --region="us-central1" --format="value(status.url)")"
    echo "   Sync Agent: $(gcloud run services describe a2a-sync-agent --region="us-central1" --format="value(status.url)")"
    echo ""
    echo "🔗 Registry Configuration:"
    echo "   Calendar Agent Registry: (none - standalone)"
    echo "   Sync Agent Registry: $(gcloud run services describe a2a-calendar-agent --region="us-central1" --format="value(status.url)")"
    echo "   Host Agent Registry: $(gcloud run services describe a2a-calendar-agent --region="us-central1" --format="value(status.url)"),$(gcloud run services describe a2a-sync-agent --region="us-central1" --format="value(status.url)")"
}

# Function to clean up
cleanup() {
    print_status "Cleaning up local Docker images..."
    docker rmi "gcr.io/agent-hackathon-461619/a2a-host-agent:latest" 2>/dev/null || true
    docker rmi "gcr.io/agent-hackathon-461619/a2a-calendar-agent:latest" 2>/dev/null || true
    docker rmi "gcr.io/agent-hackathon-461619/a2a-sync-agent:latest" 2>/dev/null || true
    print_success "Cleanup completed"
}

# Main deployment function
main() {
    echo "🚀 A2A Multi-Agent Google Cloud Platform Deployment (Updated)"
    echo "============================================================"
    echo ""
    
    # check_prerequisites
    get_project_id
    # enable_apis
    # configure_docker
    # create_secrets
    build_and_push_images
    deploy_to_cloud_run
    display_deployment_info
    cleanup
    
    print_success "Deployment completed successfully!"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --project-id PROJECT_ID    Set the Google Cloud project ID"
        echo "  --region REGION           Set the deployment region (default: us-central1)"
        echo "  --help, -h                Show this help message"
        echo ""
        echo "Example:"
        echo "  $0 --project-id my-project-id --region us-west1"
        exit 0
        ;;
    --project-id)
        PROJECT_ID="$2"
        shift 2
        ;;
    --region)
        REGION="$2"
        shift 2
        ;;
esac

# Run main function
main "$@" 