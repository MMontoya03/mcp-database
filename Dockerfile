FROM python:3.11-slim

# Set working directory
WORKDIR /app


# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager (igual que el video)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy project files (MISMO ORDEN)
COPY pyproject.toml uv.lock* ./
COPY src/ ./src/
COPY server.py ./

# Install project dependencies using uv (IGUAL)
RUN uv sync --frozen --no-cache --no-dev


# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

COPY server.py ./
EXPOSE 8000

# Health check (correcto para asyncpg)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import asyncio; from database import get_engine; \
async def c(): \
 e=get_engine(); \
 async with e.connect(): pass; \
 asyncio.run(c())" || exit 1

# Run the MCP server (IGUAL AL VIDEO)
CMD ["uv", "run", "python", "server.py"]
