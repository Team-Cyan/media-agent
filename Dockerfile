FROM python:3.14-slim

ARG VERSION=0.1.0
ARG REVISION=unknown
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.title="media-agent" \
    org.opencontainers.image.description="Docker-first completed-media import and linking tool for NAS libraries" \
    org.opencontainers.image.url="https://github.com/Team-Cyan/media-agent" \
    org.opencontainers.image.source="https://github.com/Team-Cyan/media-agent" \
    org.opencontainers.image.version="${VERSION}" \
    org.opencontainers.image.revision="${REVISION}" \
    org.opencontainers.image.created="${BUILD_DATE}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    MEDIA_AGENT_CONFIG=/app/config/config.yaml \
    MEDIA_AGENT_STATE_DIR=/app/.media-agent

WORKDIR /app

COPY pyproject.toml uv.lock README.md VERSION /app/
COPY src /app/src
COPY docker /app/docker

RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev --no-editable
RUN chmod +x /app/docker/entrypoint.sh

EXPOSE 8775

ENTRYPOINT ["/app/docker/entrypoint.sh"]
