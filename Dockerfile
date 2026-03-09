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

# Lightweight health-check: probe the MCP endpoint with an HTTP POST
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python - <<'EOF'
import urllib.request, urllib.error, json, sys
req = urllib.request.Request(
    "http://localhost:8000/mcp",
    data=json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize",
                     "params":{"protocolVersion":"2024-11-05","capabilities":{},
                               "clientInfo":{"name":"healthcheck","version":"0"}}}).encode(),
    headers={"Content-Type": "application/json",
             "Accept": "application/json, text/event-stream"},
    method="POST",
)
try:
    urllib.request.urlopen(req, timeout=5)
except urllib.error.HTTPError as e:
    sys.exit(0 if e.code < 500 else 1)
except Exception:
    sys.exit(1)
EOF

CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8000"]
