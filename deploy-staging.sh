#!/bin/bash
# 🚀 Staging Deployment Script
# This script deploys the application to staging environment

set -e  # Exit on any error

echo "🚀 Starting Staging Deployment..."
echo "=================================="

# Configuration
STAGING_ENV_FILE=".env.staging"
DOCKER_COMPOSE_FILE="docker-compose.staging.yml"
BACKUP_DIR="backups/$(date +%Y%m%d-%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        error "Docker is not running. Please start Docker and try again."
    fi
    
    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        error "docker-compose is not installed. Please install it and try again."
    fi
    
    # Check if staging environment file exists
    if [[ ! -f "$STAGING_ENV_FILE" ]]; then
        warning "Staging environment file not found. Creating from template..."
        if [[ -f ".env.staging.example" ]]; then
            cp .env.staging.example "$STAGING_ENV_FILE"
            warning "Please edit $STAGING_ENV_FILE with your staging configuration."
            echo "Press Enter when ready to continue..."
            read
        else
            error "No staging environment template found."
        fi
    fi
    
    success "Prerequisites check passed"
}

# Run tests
run_tests() {
    log "Running tests before deployment..."
    
    # Set test environment
    export DJANGO_SETTINGS_MODULE=inventory_app.settings
    
    # Run tests
    if python manage.py test --verbosity=2; then
        success "All tests passed"
    else
        error "Tests failed. Deployment aborted."
    fi
}

# Create backup
create_backup() {
    log "Creating backup..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup database if it exists
    if docker-compose -f "$DOCKER_COMPOSE_FILE" ps db | grep -q "Up"; then
        log "Backing up database..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T db pg_dump -U staging_user staging_inventory > "$BACKUP_DIR/database.sql"
        success "Database backup created"
    fi
    
    # Backup static files if they exist
    if [[ -d "staticfiles" ]]; then
        log "Backing up static files..."
        tar -czf "$BACKUP_DIR/staticfiles.tar.gz" staticfiles/
        success "Static files backup created"
    fi
    
    success "Backup created in $BACKUP_DIR"
}

# Build and deploy
deploy() {
    log "Building and deploying application..."
    
    # Pull latest images
    log "Pulling latest base images..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" pull db redis nginx

    # Build frontend assets
    log "Installing Node.js dependencies and building assets..."
    npm install
    npm run build

    # Build application image
    log "Building application image..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" build web
    
    # Stop existing containers
    log "Stopping existing containers..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    
    # Start services
    log "Starting services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    success "Services started"
}

# Health checks
health_checks() {
    log "Performing health checks..."
    
    # Wait for services to start
    log "Waiting for services to initialize..."
    sleep 30
    
    # Check if web container is running
    if docker-compose -f "$DOCKER_COMPOSE_FILE" ps web | grep -q "Up"; then
        success "Web container is running"
    else
        error "Web container failed to start"
    fi
    
    # Check database connectivity
    log "Checking database connectivity..."
    if docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T web python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT 1')
print('Database connection: OK')
" --settings=inventory_app.settings_staging; then
        success "Database connection established"
    else
        error "Database connection failed"
    fi
    
    # Check health endpoint
    log "Checking health endpoint..."
    max_attempts=10
    attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s http://localhost/healthz > /dev/null; then
            success "Health endpoint responding"
            break
        else
            log "Health check attempt $attempt/$max_attempts failed, retrying in 10 seconds..."
            sleep 10
            ((attempt++))
        fi
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        error "Health endpoint not responding after $max_attempts attempts"
    fi
}

# Validation tests
validation_tests() {
    log "Running validation tests..."
    
    # Run critical tests in staging environment
    log "Running critical path tests..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T web python manage.py test \
        tests.test_item_service \
        tests.test_recipe_service \
        tests.test_dashboard_service \
        --settings=inventory_app.settings_staging
    
    success "Validation tests passed"
}

# Cleanup old resources
cleanup() {
    log "Cleaning up old resources..."
    
    # Remove unused Docker images
    docker image prune -f
    
    # Remove old backup files (keep last 5)
    if [[ -d "backups" ]]; then
        cd backups
        ls -t | tail -n +6 | xargs -r rm -rf
        cd ..
    fi
    
    success "Cleanup completed"
}

# Show deployment information
show_info() {
    echo ""
    echo "🎉 Staging Deployment Completed Successfully!"
    echo "==========================================="
    echo ""
    echo "📊 Deployment Information:"
    echo "- Environment: Staging"
    echo "- Timestamp: $(date)"
    echo "- Backup Location: $BACKUP_DIR"
    echo ""
    echo "🔗 Access Information:"
    echo "- Application: http://localhost"
    echo "- Admin Panel: http://localhost/admin"
    echo "- Health Check: http://localhost/healthz"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Perform user acceptance testing"
    echo "2. Validate all critical functionality"
    echo "3. Check performance metrics"
    echo "4. Review logs for any issues"
    echo ""
    echo "📝 Useful Commands:"
    echo "- View logs: docker-compose -f $DOCKER_COMPOSE_FILE logs -f"
    echo "- Stop services: docker-compose -f $DOCKER_COMPOSE_FILE down"
    echo "- Restart services: docker-compose -f $DOCKER_COMPOSE_FILE restart"
    echo ""
}

# Rollback function
rollback() {
    error_msg="$1"
    warning "Deployment failed: $error_msg"
    log "Starting rollback procedure..."
    
    # Stop current deployment
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    
    # Restore from backup if available
    if [[ -d "$BACKUP_DIR" && -f "$BACKUP_DIR/database.sql" ]]; then
        log "Restoring database from backup..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" up -d db
        sleep 10
        docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T db psql -U staging_user -d staging_inventory < "$BACKUP_DIR/database.sql"
    fi
    
    error "Rollback completed. Please check the issues and try again."
}

# Main deployment flow
main() {
    # Trap errors and rollback
    trap 'rollback "Unexpected error occurred"' ERR
    
    check_prerequisites
    run_tests
    create_backup
    deploy
    health_checks
    validation_tests
    cleanup
    show_info
    
    # Remove error trap on successful completion
    trap - ERR
}

# Handle command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "rollback")
        if [[ -z "$2" ]]; then
            echo "Usage: $0 rollback <backup_directory>"
            exit 1
        fi
        log "Rolling back to backup: $2"
        # Implement rollback logic here
        ;;
    "status")
        docker-compose -f "$DOCKER_COMPOSE_FILE" ps
        ;;
    "logs")
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f "${2:-web}"
        ;;
    "test")
        run_tests
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|status|logs|test}"
        echo ""
        echo "Commands:"
        echo "  deploy   - Deploy to staging environment (default)"
        echo "  rollback - Rollback to previous version"
        echo "  status   - Show service status"
        echo "  logs     - Show service logs"
        echo "  test     - Run tests only"
        exit 1
        ;;
esac
