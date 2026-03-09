# ── Stage 1: dependency installer ────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build deps into an isolated prefix so we can copy just the artifacts
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: lean runtime image ───────────────────────────────────────────────
FROM python:3.12-slim

# Non-root user for security
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY server.py .

# Ownership
RUN chown -R appuser:appuser /app

USER appuser

# Runtime env
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Run the server
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8000"]
