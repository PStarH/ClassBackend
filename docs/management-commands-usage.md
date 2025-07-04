# 改进后的数据库和缓存管理命令使用指南

## 系统健康检查
python manage.py enhanced_db_manager health-check

## 数据库优化
python manage.py enhanced_db_manager optimize --verbose

## 性能分析
python manage.py enhanced_db_manager analyze --threshold 0.5

## 缓存统计
python manage.py enhanced_db_manager cache-stats

## 数据库维护
python manage.py enhanced_db_manager maintenance --tables users course_progress

## 缓存预热
python manage.py enhanced_db_manager warmup

## 实时监控
python manage.py enhanced_db_manager monitor

## 数据库清理
python manage.py enhanced_db_manager cleanup --force
