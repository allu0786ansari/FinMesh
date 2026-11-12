# FinMesh images. Two targets from one file:
#
#   runtime (default)  the package and its runtime dependencies, as an unprivileged user:
#                      the demo path, the analyst console and the X7 smoke test
#       docker build -t finmesh:local .
#       docker run --rm finmesh:local x7 --smoke
#
#   full               everything the research pipeline needs: the development tools
#                      (pytest, ruff, mypy), git (every result is stamped with the code
#                      commit), curl (the Ollama checks of the run scripts), the paper
#                      figures' serif font (Liberation Serif) and the stage
#                      runner docker/reproduce.sh. Compose mounts a checkout of the
#                      repository at /app and the data folder at /data, so results land in
#                      your checkout exactly as a native run would write them.
#       docker build --target full -t finmesh:full .
#
# The guide is docs/containers.md; compose.yaml wires both images up.
ARG PYTHON_VERSION=3.12

# ---------------------------------------------------------------------------- base
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    FINMESH_DATA=/data \
    MPLCONFIGDIR=/tmp/matplotlib

# LightGBM needs the OpenMP runtime, which the slim image does not ship.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.13.1

WORKDIR /app
# Dependencies first, so code changes reuse this layer. The Kaggle client is included so
# that `finmesh download` works inside the container.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --extra kaggle --no-install-project
COPY finmesh ./finmesh
RUN uv sync --locked --no-dev --extra kaggle

# ---------------------------------------------------------------------------- full
FROM base AS full

RUN apt-get update \
    && apt-get install --yes --no-install-recommends git curl fonts-liberation \
    && rm -rf /var/lib/apt/lists/*
# Development tools on top of the runtime environment.
RUN uv sync --locked --extra kaggle
# The pipeline runs as the host user (compose sets the user), so the environment must be
# usable by any uid; `uv sync` in scripts/ci_local.sh may also touch it.
RUN chmod -R a+rwX /opt/venv && mkdir -p /data && chmod a+rwx /data
COPY docker/reproduce.sh /opt/finmesh/reproduce.sh
ENV HOME=/tmp \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_NO_SYNC=1 \
    GIT_CONFIG_COUNT=1 \
    GIT_CONFIG_KEY_0=safe.directory \
    GIT_CONFIG_VALUE_0=*
VOLUME ["/data"]
ENTRYPOINT ["finmesh"]
CMD ["check"]

# ---------------------------------------------------------------------------- runtime
FROM base AS runtime

# Run as an unprivileged user; data (and any demo world's secrets) live in /data.
RUN useradd --create-home --uid 10001 finmesh \
    && mkdir -p /data && chown finmesh:finmesh /data
USER finmesh
VOLUME ["/data"]
EXPOSE 8050

ENTRYPOINT ["finmesh"]
CMD ["check"]
