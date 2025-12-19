# Backend API Dockerfile
# FastAPI + PyMuPDF for PDF rendering

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PyMuPDF and healthcheck
RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    mupdf-tools \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies (includes FastAPI & uvicorn)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ ./api/
COPY services/ ./services/
COPY tools/ ./tools/
COPY config/ ./config/

# Create artifacts directory for cache
RUN mkdir -p /app/artifacts/page_cache

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=postgresql://postgres:postgres@db:5432/inca_rag
ENV LLM_ENABLED=0

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
