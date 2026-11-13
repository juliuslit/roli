# roli nutrition MCP server. Build from the nutrition_service folder:
#   docker build -t roli-nutrition .
# Run (secrets only at runtime, never baked in):
#   docker run --rm -p 8000:8000 \
#     -e USDA_FDC_API_KEY=... -e ROLI_MCP_TOKEN=... \
#     -e ROLI_MCP_ALLOWED_HOSTS="localhost:*,127.0.0.1:*,your-host.example.com" \
#     roli-nutrition

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

# Exact pins first, so this layer is cached until requirements.txt changes.
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Only the package and its metadata. .dockerignore keeps .env, tests, fixtures and
# the virtual environment out of the build context.
COPY pyproject.toml ./
COPY roli_nutrition ./roli_nutrition
RUN pip install --no-cache-dir --no-deps .

# Run as an unprivileged user.
RUN useradd --create-home --shell /usr/sbin/nologin roli
USER roli

EXPOSE 8000

# The application factory reads USDA_FDC_API_KEY, ROLI_MCP_TOKEN and the allowlists
# from the environment when it builds the app, and refuses to start if any is unusable.
CMD ["sh", "-c", "exec uvicorn roli_nutrition.mcp_server:create_app --factory --host 0.0.0.0 --port ${PORT}"]
