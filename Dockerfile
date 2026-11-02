# FinMesh demo path and tools in one image (week 17).
#   docker build -t finmesh:local .
#   docker run --rm finmesh:local x7 --smoke          # the container smoke pipeline
#   docker compose --profile smoke up --build         # the same through compose
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    FINMESH_DATA=/data

# LightGBM needs the OpenMP runtime, which the slim image does not ship.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.13.1

WORKDIR /app
# Dependencies first, so code changes reuse this layer.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY finmesh ./finmesh
RUN uv sync --locked --no-dev

# Run as an unprivileged user; data (and any demo world's secrets) live in /data.
RUN useradd --create-home --uid 10001 finmesh \
    && mkdir -p /data && chown finmesh:finmesh /data
USER finmesh
VOLUME ["/data"]
EXPOSE 8050

ENTRYPOINT ["finmesh"]
CMD ["check"]
