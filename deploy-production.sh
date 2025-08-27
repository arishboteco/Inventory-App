#!/bin/bash
# 🚀 Production Deployment Script
# This script deploys the application to production environment with full security and monitoring

set -e  # Exit on any error

echo "🚀 Starting Production Deployment..."
echo "====================================="

# Configuration
PRODUCTION_ENV_FILE=".env.production"
DOCKER_COMPOSE_FILE="docker-compose.production.yml"
BACKUP_DIR="backups/production/$(date +%Y%m%d-%H%M%S)"
LOG_FILE="/var/log/inventory-deployment.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE" 2>/dev/null || true
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS: $1" >> "$LOG_FILE" 2>/dev/null || true
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1" >> "$LOG_FILE" 2>/dev/null || true
}

error() {
    echo -e "${RED}❌ $1${NC}"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" >> "$LOG_FILE" 2>/dev/null || true
    exit 1
}

highlight() {
    echo -e "${PURPLE}🎯 $1${NC}"
}

# Pre-deployment checks
pre_deployment_checks() {
    log "Running pre-deployment checks..."
    
    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        warning "Running as root. Consider using a non-root user for security."
    fi
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        error "Docker is not running. Please start Docker and try again."
    fi
    
    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        error "docker-compose is not installed. Please install it and try again."
    fi
    
    # Check if production environment file exists
    if [[ ! -f "$PRODUCTION_ENV_FILE" ]]; then
        error "Production environment file not found. Please create $PRODUCTION_ENV_FILE from template."
    fi
    
    # Check critical environment variables
    source "$PRODUCTION_ENV_FILE"
    critical_vars=("DJANGO_SECRET_KEY" "DATABASE_URL" "DJANGO_ALLOWED_HOSTS")
    for var in "${critical_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            error "Critical environment variable $var is not set in $PRODUCTION_ENV_FILE"
        fi
    done
    
    # Check SSL certificates
    if [[ ! -f "ssl/cert.pem" ]] || [[ ! -f "ssl/key.pem" ]]; then
        warning "SSL certificates not found. HTTPS will not work."
        echo "Please place SSL certificates in ssl/cert.pem and ssl/key.pem"
        echo "Continue anyway? (y/N)"
        read -r continue_without_ssl
        if [[ ! "$continue_without_ssl" =~ ^[Yy]$ ]]; then
            error "SSL certificates required for production deployment."
        fi
    fi
    
    # Check disk space
    available_space=$(df / | awk 'NR==2 {print $4}')
    if [[ $available_space -lt 5000000 ]]; then  # Less than 5GB
        warning "Low disk space available: $(($available_space/1000))MB"
    fi
    
    success "Pre-deployment checks completed"
}

# Security validation
security_validation() {
    log "Running security validation..."
    
    # Check if DEBUG is disabled
    if grep -q "DEBUG=True" "$PRODUCTION_ENV_FILE"; then
        error "DEBUG=True found in production environment. This is a security risk."
    fi
    
    # Check secret key strength
    secret_key=$(grep "DJANGO_SECRET_KEY=" "$PRODUCTION_ENV_FILE" | cut -d'=' -f2)
    if [[ ${#secret_key} -lt 50 ]]; then
        warning "Django secret key appears to be short. Consider using a longer, more secure key."
    fi
    
    # Check allowed hosts
    allowed_hosts=$(grep "DJANGO_ALLOWED_HOSTS=" "$PRODUCTION_ENV_FILE" | cut -d'=' -f2)
    if [[ "$allowed_hosts" == *"localhost"* ]] || [[ "$allowed_hosts" == *"127.0.0.1"* ]]; then
        warning "localhost/127.0.0.1 found in ALLOWED_HOSTS. Remove for production."
    fi
    
    success "Security validation completed"
}

# Run comprehensive tests
run_production_tests() {
    log "Running production readiness tests..."
    
    # Set production test environment
    export DJANGO_SETTINGS_MODULE=inventory_app.settings_production
    
    # Run Django system checks
    if python manage.py check --settings=inventory_app.settings_production --deploy; then
        success "Django production checks passed"
    else
        error "Django production checks failed. Fix issues before deployment."
    fi
    
    # Run tests with production settings
    log "Running test suite with production settings..."
    if python manage.py test --settings=inventory_app.settings_production --verbosity=1; then
        success "All tests passed with production settings"
    else
        error "Tests failed with production settings. Deployment aborted."
    fi
    
    success "Production tests completed"
}

# Create comprehensive backup
create_backup() {
    log "Creating production backup..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup existing database if running
    if docker-compose -f "$DOCKER_COMPOSE_FILE" ps db | grep -q "Up"; then
        log "Backing up production database..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T db pg_dump -U inventory_user inventory_production > "$BACKUP_DIR/database.sql"
        success "Database backup created"
    fi
    
    # Backup static files
    if [[ -d "staticfiles" ]]; then
        log "Backing up static files..."
        tar -czf "$BACKUP_DIR/staticfiles.tar.gz" staticfiles/
        success "Static files backup created"
    fi
    
    # Backup media files
    if [[ -d "media" ]]; then
        log "Backing up media files..."
        tar -czf "$BACKUP_DIR/media.tar.gz" media/
        success "Media files backup created"
    fi
    
    # Backup configuration
    log "Backing up configuration files..."
    cp "$PRODUCTION_ENV_FILE" "$BACKUP_DIR/"
    cp nginx/production.conf "$BACKUP_DIR/"
    cp "$DOCKER_COMPOSE_FILE" "$BACKUP_DIR/"
    
    success "Comprehensive backup created in $BACKUP_DIR"
}

# Deploy to production
deploy() {
    log "Deploying to production environment..."
    
    # Pull latest images
    log "Pulling latest base images..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" pull db redis nginx monitoring
    
    # Build production application image
    log "Building production application image..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" build web
    
    # Stop existing containers gracefully
    log "Stopping existing containers..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down --remove-orphans
    
    # Start production services
    log "Starting production services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    success "Production services started"
}

# Health checks and validation
health_checks() {
    log "Performing comprehensive health checks..."
    
    # Wait for services to start
    log "Waiting for services to initialize..."
    sleep 60
    
    # Check service status
    services=("web" "db" "redis" "nginx")
    for service in "${services[@]}"; do
        if docker-compose -f "$DOCKER_COMPOSE_FILE" ps "$service" | grep -q "Up"; then
            success "$service container is running"
        else
            error "$service container failed to start"
        fi
    done
    
    # Check database connectivity
    log "Checking database connectivity..."
    if docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T web python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT 1')
print('Database connection: OK')
" --settings=inventory_app.settings_production; then
        success "Database connection established"
    else
        error "Database connection failed"
    fi
    
    # Check Redis connectivity
    log "Checking Redis connectivity..."
    if docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T redis redis-cli ping | grep -q "PONG"; then
        success "Redis connection established"
    else
        warning "Redis connection failed"
    fi
    
    # Check HTTPS endpoint
    log "Checking HTTPS endpoint..."
    max_attempts=20
    attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -k -f -s https://localhost/healthz > /dev/null; then
            success "HTTPS endpoint responding"
            break
        else
            log "HTTPS check attempt $attempt/$max_attempts failed, retrying in 15 seconds..."
            sleep 15
            ((attempt++))
        fi
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        error "HTTPS endpoint not responding after $max_attempts attempts"
    fi
    
    # Run production validation script
    log "Running production validation script..."
    if docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T web python staging_validation.py; then
        success "Production validation passed"
    else
        warning "Production validation had issues"
    fi
}

# Performance testing
performance_tests() {
    log "Running performance tests..."
    
    # Basic load test if Apache Bench is available
    if command -v ab &> /dev/null; then
        log "Running basic load test..."
        ab -n 100 -c 5 https://localhost/ > /tmp/loadtest.log 2>&1 || true
        success "Load test completed (check /tmp/loadtest.log for results)"
    else
        warning "Apache Bench not available, skipping load test"
    fi
}

# Setup monitoring
setup_monitoring() {
    log "Setting up monitoring and alerting..."
    
    # Check if monitoring container is running
    if docker-compose -f "$DOCKER_COMPOSE_FILE" ps monitoring | grep -q "Up"; then
        success "Monitoring service is running"
        log "Node Exporter available at: http://localhost:9100/metrics"
    else
        warning "Monitoring service not running"
    fi
    
    # Setup log rotation
    if command -v logrotate &> /dev/null; then
        log "Setting up log rotation..."
        sudo tee /etc/logrotate.d/inventory-production > /dev/null <<EOF
/var/log/django/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    create 644 appuser appuser
    postrotate
        docker-compose -f $PWD/$DOCKER_COMPOSE_FILE exec web kill -USR1 1
    endscript
}
EOF
        success "Log rotation configured"
    fi
}

# Cleanup old resources
cleanup() {
    log "Cleaning up old resources..."
    
    # Remove unused Docker images
    docker image prune -f
    
    # Remove old backup files (keep last 10)
    if [[ -d "backups/production" ]]; then
        cd backups/production
        ls -t | tail -n +11 | xargs -r rm -rf
        cd ../..
    fi
    
    success "Cleanup completed"
}

# Show deployment information
show_deployment_info() {
    echo ""
    echo "🎉 Production Deployment Completed Successfully!"
    echo "=============================================="
    echo ""
    echo "📊 Deployment Information:"
    echo "- Environment: Production"
    echo "- Timestamp: $(date)"
    echo "- Backup Location: $BACKUP_DIR"
    echo "- Log File: $LOG_FILE"
    echo ""
    echo "🔗 Access Information:"
    echo "- Application: https://$(grep DJANGO_ALLOWED_HOSTS $PRODUCTION_ENV_FILE | cut -d'=' -f2 | cut -d',' -f1)"
    echo "- Admin Panel: https://$(grep DJANGO_ALLOWED_HOSTS $PRODUCTION_ENV_FILE | cut -d'=' -f2 | cut -d',' -f1)/$(grep ADMIN_URL $PRODUCTION_ENV_FILE | cut -d'=' -f2)"
    echo "- Health Check: https://$(grep DJANGO_ALLOWED_HOSTS $PRODUCTION_ENV_FILE | cut -d'=' -f2 | cut -d',' -f1)/healthz"
    echo "- Monitoring: http://localhost:9100/metrics"
    echo ""
    echo "📋 Post-Deployment Tasks:"
    echo "1. Monitor application logs for any issues"
    echo "2. Set up external monitoring and alerting"
    echo "3. Configure automated backups"
    echo "4. Update DNS records if needed"
    echo "5. Test all critical functionality"
    echo ""
    echo "📝 Useful Commands:"
    echo "- View logs: docker-compose -f $DOCKER_COMPOSE_FILE logs -f"
    echo "- Restart services: docker-compose -f $DOCKER_COMPOSE_FILE restart"
    echo "- Scale web workers: docker-compose -f $DOCKER_COMPOSE_FILE up -d --scale web=3"
    echo "- Database backup: docker-compose -f $DOCKER_COMPOSE_FILE exec db pg_dump -U inventory_user inventory_production > backup.sql"
    echo ""
    highlight "🚀 Production deployment successful! Your application is now live."
}

# Rollback function
rollback() {
    error_msg="$1"
    warning "Production deployment failed: $error_msg"
    log "Starting emergency rollback procedure..."
    
    # Stop current deployment
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    
    # Restore from backup if available
    if [[ -d "$BACKUP_DIR" && -f "$BACKUP_DIR/database.sql" ]]; then
        log "Restoring database from backup..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" up -d db
        sleep 30
        docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T db psql -U inventory_user -d inventory_production < "$BACKUP_DIR/database.sql"
    fi
    
    error "Emergency rollback completed. Please investigate issues and retry deployment."
}

# Main deployment flow
main() {
    # Trap errors and rollback
    trap 'rollback "Unexpected error occurred"' ERR
    
    highlight "🚀 PRODUCTION DEPLOYMENT STARTING"
    echo "This will deploy the application to PRODUCTION environment."
    echo "Ensure you have:"
    echo "- Configured $PRODUCTION_ENV_FILE properly"
    echo "- SSL certificates in ssl/ directory"
    echo "- Reviewed all security settings"
    echo ""
    echo "Continue with production deployment? (y/N)"
    read -r confirm_deployment
    
    if [[ ! "$confirm_deployment" =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled by user."
        exit 0
    fi
    
    pre_deployment_checks
    security_validation
    run_production_tests
    create_backup
    deploy
    health_checks
    performance_tests
    setup_monitoring
    cleanup
    show_deployment_info
    
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
        rollback "Manual rollback requested"
        ;;
    "status")
        docker-compose -f "$DOCKER_COMPOSE_FILE" ps
        ;;
    "logs")
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f "${2:-web}"
        ;;
    "health")
        curl -f https://localhost/healthz && echo "✅ Health check passed"
        ;;
    "backup")
        create_backup
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|status|logs|health|backup}"
        echo ""
        echo "Commands:"
        echo "  deploy   - Deploy to production environment (default)"
        echo "  rollback - Rollback to previous version"
        echo "  status   - Show service status"
        echo "  logs     - Show service logs"
        echo "  health   - Check application health"
        echo "  backup   - Create backup only"
        exit 1
        ;;
esac
