# Project Atticus - Legal Knowledge Graph Construction
# Multi-stage Docker build for production deployment

# Stage 1: Base image with dependencies
FROM python:3.10-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Stage 2: Development image
FROM base as development

# Copy entire project
COPY . .

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Expose API port
EXPOSE 8000

# Default command for development
CMD ["python", "scripts/run_api.py"]

# Stage 3: Production image
FROM base as production

# Create non-root user
RUN useradd -m -u 1000 atticus && chown -R atticus:atticus /app
USER atticus

# Copy only necessary files
COPY --chown=atticus:atticus src/ /app/src/
COPY --chown=atticus:atticus config/ /app/config/
COPY --chown=atticus:atticus prompts/ /app/prompts/
COPY --chown=atticus:atticus scripts/run_api.py /app/scripts/

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose API port
EXPOSE 8000

# Run as non-root user
CMD ["python", "scripts/run_api.py"]
