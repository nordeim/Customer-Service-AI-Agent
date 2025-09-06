#!/bin/bash

# AI Customer Service Agent - Docker Infrastructure Startup Script
# This script sets up the complete Docker environment for development

set -e

echo "🚀 Starting AI Customer Service Agent Docker Infrastructure..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed and running
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! docker info &> /dev/null; then
    print_error "Docker is not running. Please start Docker service."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose."
    exit 1
fi

# Create .env.docker file if it doesn't exist
if [ ! -f ".env.docker" ]; then
    print_warning ".env.docker file not found. Creating from template..."
    cp .env.docker .env.docker
fi

# Create logs directory
mkdir -p logs

# Function to check if a service is healthy
check_service_health() {
    local service_name=$1
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for $service_name to be healthy..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose ps $service_name | grep -q "healthy"; then
            print_status "✅ $service_name is healthy"
            return 0
        fi
        
        if docker-compose ps $service_name | grep -q "Exit"; then
            print_error "❌ $service_name failed to start"
            docker-compose logs $service_name
            return 1
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "❌ $service_name failed to become healthy after $max_attempts attempts"
    return 1
}

# Function to check if required ports are available
check_ports() {
    local ports=("5432" "6379" "9200" "9300" "7687" "7474" "27017" "2181" "9092" "29092" "8000")
    local unavailable_ports=()
    
    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            unavailable_ports+=($port)
        fi
    done
    
    if [ ${#unavailable_ports[@]} -gt 0 ]; then
        print_warning "The following ports are already in use: ${unavailable_ports[*]}"
        print_warning "Please stop the services using these ports or modify the port configuration in .env.docker"
        exit 1
    fi
}

# Parse command line arguments
COMMAND="up"
DETACHED=""
BUILD=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--detach)
            DETACHED="-d"
            shift
            ;;
        --build)
            BUILD="--build"
            shift
            ;;
        down)
            COMMAND="down"
            shift
            ;;
        logs)
            COMMAND="logs"
            shift
            ;;
        stop)
            COMMAND="stop"
            shift
            ;;
        status)
            COMMAND="ps"
            shift
            ;;
        clean)
            COMMAND="clean"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [COMMAND] [OPTIONS]"
            echo "Commands:"
            echo "  up      - Start all services (default)"
            echo "  down    - Stop all services"
            echo "  logs    - Show service logs"
            echo "  stop    - Stop all services"
            echo "  status  - Show service status"
            echo "  clean   - Clean up volumes and images"
            echo ""
            echo "Options:"
            echo "  -d, --detach    - Run services in detached mode"
            echo "  --build         - Force rebuild of images"
            echo "  -h, --help      - Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Execute commands
case $COMMAND in
    up)
        print_status "Starting Docker infrastructure..."
        
        # Check ports before starting
        check_ports
        
        # Pull latest images
        print_status "Pulling Docker images..."
        docker-compose pull
        
        # Start services
        print_status "Starting services..."
        docker-compose up $DETACHED $BUILD
        
        if [ -z "$DETACHED" ]; then
            print_status "Services are running in foreground. Press Ctrl+C to stop."
        else
            print_status "Services started in detached mode."
            print_status "Checking service health..."
            
            # Wait a bit for services to initialize
            sleep 10
            
            # Check health of critical services
            check_service_health "postgres"
            check_service_health "redis"
            check_service_health "elasticsearch"
            check_service_health "neo4j"
            check_service_health "mongodb"
            check_service_health "kafka"
            
            print_status "✅ All services are healthy!"
            print_status "API should be available at: http://localhost:8000"
            print_status "Use 'docker-compose logs -f' to view logs"
            print_status "Use '$0 logs' to view service logs"
            print_status "Use '$0 status' to check service status"
        fi
        ;;
    down)
        print_status "Stopping and removing services..."
        docker-compose down
        ;;
    stop)
        print_status "Stopping services..."
        docker-compose stop
        ;;
    logs)
        print_status "Showing service logs..."
        docker-compose logs -f
        ;;
    ps|status)
        print_status "Service status:"
        docker-compose ps
        ;;
    clean)
        print_warning "This will remove all containers, volumes, and networks. Are you sure? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            print_status "Cleaning up Docker resources..."
            docker-compose down -v --remove-orphans
            docker system prune -f
            print_status "✅ Cleanup complete"
        else
            print_status "Cleanup cancelled"
        fi
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        exit 1
        ;;
esac

echo ""
print_status "Script completed successfully!"