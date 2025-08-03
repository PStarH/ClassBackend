#!/bin/bash
# Django应用启动脚本
# 处理数据库迁移、静态文件收集等初始化任务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 等待数据库可用
wait_for_db() {
    log_info "Waiting for database to be ready..."
    
    until python manage.py dbshell --command="SELECT 1;" > /dev/null 2>&1; do
        log_warn "Database is unavailable - sleeping"
        sleep 2
    done
    
    log_info "Database is ready!"
}

# 等待Redis可用
wait_for_redis() {
    log_info "Waiting for Redis to be ready..."
    
    until python -c "
import redis
import os
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
r = redis.from_url(redis_url)
r.ping()
" > /dev/null 2>&1; do
        log_warn "Redis is unavailable - sleeping"
        sleep 2
    done
    
    log_info "Redis is ready!"
}

# 数据库迁移
run_migrations() {
    log_info "Running database migrations..."
    python manage.py migrate --noinput
    
    # 创建默认的管理员用户 (如果不存在)
    python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123',
        first_name='Admin',
        last_name='User'
    )
    print('Created default admin user: admin/admin123')
else:
    print('Admin user already exists')
EOF
}

# 收集静态文件
collect_static() {
    log_info "Collecting static files..."
    python manage.py collectstatic --noinput --clear
}

# 创建缓存表
create_cache_tables() {
    log_info "Creating cache tables..."
    python manage.py createcachetable || log_warn "Cache table already exists or creation failed"
}

# 数据库优化
optimize_database() {
    log_info "Running database optimizations..."
    python manage.py optimize_database --create-indexes --analyze-tables
}

# 启动应用的主函数
start_application() {
    case "$1" in
        "gunicorn")
            log_info "Starting Gunicorn server..."
            exec gunicorn config.wsgi:application \
                --bind 0.0.0.0:8000 \
                --workers ${GUNICORN_WORKERS:-4} \
                --worker-class ${GUNICORN_WORKER_CLASS:-sync} \
                --worker-connections ${GUNICORN_WORKER_CONNECTIONS:-1000} \
                --max-requests ${GUNICORN_MAX_REQUESTS:-1000} \
                --max-requests-jitter ${GUNICORN_MAX_REQUESTS_JITTER:-100} \
                --timeout ${GUNICORN_TIMEOUT:-30} \
                --keep-alive ${GUNICORN_KEEP_ALIVE:-5} \
                --access-logfile - \
                --error-logfile - \
                --log-level ${GUNICORN_LOG_LEVEL:-info} \
                --capture-output
            ;;
        "celery_worker")
            log_info "Starting Celery worker..."
            exec celery -A config worker \
                --loglevel=${CELERY_LOG_LEVEL:-info} \
                --concurrency=${CELERY_CONCURRENCY:-4} \
                --prefetch-multiplier=${CELERY_PREFETCH_MULTIPLIER:-1} \
                --max-tasks-per-child=${CELERY_MAX_TASKS_PER_CHILD:-1000} \
                --time-limit=${CELERY_TASK_TIME_LIMIT:-300} \
                --soft-time-limit=${CELERY_TASK_SOFT_TIME_LIMIT:-240}
            ;;
        "celery_beat")
            log_info "Starting Celery beat scheduler..."
            exec celery -A config beat \
                --loglevel=${CELERY_LOG_LEVEL:-info} \
                --scheduler=django_celery_beat.schedulers:DatabaseScheduler
            ;;
        "celery_flower")
            log_info "Starting Celery flower monitoring..."
            exec celery -A config flower \
                --port=5555 \
                --basic_auth=${FLOWER_BASIC_AUTH:-admin:flower123}
            ;;
        "shell")
            log_info "Starting Django shell..."
            exec python manage.py shell_plus
            ;;
        "test")
            log_info "Running tests..."
            exec python manage.py test
            ;;
        "migrate")
            log_info "Running migrations only..."
            run_migrations
            exit 0
            ;;
        "management")
            log_info "Running Django management command: ${@:2}"
            exec python manage.py "${@:2}"
            ;;
        *)
            log_error "Unknown command: $1"
            log_info "Available commands:"
            log_info "  gunicorn       - Start Gunicorn web server"
            log_info "  celery_worker  - Start Celery worker"
            log_info "  celery_beat    - Start Celery beat scheduler"
            log_info "  celery_flower  - Start Celery flower monitoring"
            log_info "  shell          - Start Django shell"
            log_info "  test           - Run tests"
            log_info "  migrate        - Run migrations only"
            log_info "  management     - Run Django management command"
            exit 1
            ;;
    esac
}

# 主执行流程
main() {
    log_info "Starting Smart Classroom AI Platform - Backend"
    log_info "Environment: ${BUILD_ENV:-development}"
    log_info "Django settings: ${DJANGO_SETTINGS_MODULE}"
    
    # 检查必要的环境变量
    if [[ -z "${SECRET_KEY}" ]]; then
        log_error "SECRET_KEY environment variable is required"
        exit 1
    fi
    
    # 等待依赖服务
    wait_for_db
    wait_for_redis
    
    # 初始化任务 (仅对web服务器执行)
    if [[ "$1" == "gunicorn" ]]; then
        run_migrations
        collect_static
        create_cache_tables
        
        # 生产环境优化
        if [[ "${BUILD_ENV}" == "production" ]]; then
            optimize_database
        fi
    fi
    
    # 启动应用
    start_application "$@"
}

# 信号处理
cleanup() {
    log_info "Received shutdown signal, cleaning up..."
    exit 0
}

trap cleanup SIGTERM SIGINT

# 执行主函数
main "$@"