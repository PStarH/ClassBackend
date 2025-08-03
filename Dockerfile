# Django后端Dockerfile - 多阶段构建优化
# 基于Python 3.13 Alpine镜像，优化镜像大小和安全性

# ================================
# 构建阶段
# ================================
FROM python:3.13-alpine as builder

# 构建参数
ARG BUILD_ENV=production
ARG REQUIREMENTS_FILE=production.txt

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装构建依赖
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    postgresql-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    rust \
    && apk add --no-cache \
    curl \
    git

# 创建虚拟环境
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# 升级pip和安装构建工具
RUN pip install --upgrade pip setuptools wheel

# 复制requirements文件
COPY requirements/ /requirements/

# 安装Python依赖
RUN pip install -r /requirements/${REQUIREMENTS_FILE}

# ================================
# 运行阶段
# ================================
FROM python:3.13-alpine as runtime

# 运行时参数
ARG BUILD_ENV=production
ARG APP_USER=appuser
ARG APP_GROUP=appgroup
ARG APP_UID=1000
ARG APP_GID=1000

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE="config.settings.${BUILD_ENV}" \
    BUILD_ENV=${BUILD_ENV}

# 安装运行时依赖
RUN apk add --no-cache \
    postgresql-client \
    curl \
    bash \
    tzdata \
    ca-certificates \
    && rm -rf /var/cache/apk/*

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 创建用户和组
RUN addgroup -g ${APP_GID} ${APP_GROUP} \
    && adduser -D -u ${APP_UID} -G ${APP_GROUP} -s /bin/bash ${APP_USER}

# 从构建阶段复制虚拟环境
COPY --from=builder /venv /venv

# 创建应用目录
WORKDIR /app

# 创建必要的目录
RUN mkdir -p /app/staticfiles /app/media /app/logs \
    && chown -R ${APP_USER}:${APP_GROUP} /app

# 复制应用代码
COPY --chown=${APP_USER}:${APP_GROUP} . /app/

# 复制启动脚本
COPY --chown=${APP_USER}:${APP_GROUP} docker/scripts/ /scripts/
RUN chmod +x /scripts/*.sh

# 切换到非root用户
USER ${APP_USER}

# 收集静态文件
RUN python manage.py collectstatic --noinput --clear

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# 暴露端口
EXPOSE 8000

# 设置启动命令
ENTRYPOINT ["/scripts/entrypoint.sh"]
CMD ["gunicorn"]